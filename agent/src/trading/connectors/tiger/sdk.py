"""Tiger Brokers connector built on the official ``tigeropen`` SDK.

The module exposes normalized market, account, position, order, transaction,
and historical-data reads. Explicit order placement and cancellation methods
remain classified as writes and are protected by mandate gates when routed
through the trading service; direct connector calls remain ungated.

Auth is RSA-signed static-key (``tiger_id`` + a local PKCS#1 private key +
account number); no OAuth, no token refresh. Credentials never leave the user's
machine: the private key is read from a local path the operator configures.

Paper-vs-live identity guard (the documented Tiger discriminator): a paper
account number is 17 digits, all numeric (e.g. ``20191106192858300``); a
standard/prime account is 5–10 digits; a global account starts with ``U``. The
``paper`` profile fails closed unless the configured account matches the
17-digit paper format, so a live account can never be driven under a paper
profile by mistake.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from src.config.paths import get_runtime_root

CONFIG_FILENAME = "tiger.json"

#: Profiles this connector understands and their default account environment.
PROFILE_ENVIRONMENTS = {
    "paper": "paper",
    "live-readonly": "live",
    "live": "live",
}

#: A Tiger paper account number is exactly 17 numeric digits.
_PAPER_ACCOUNT_RE = re.compile(r"^\d{17}$")
_ORDER_STATUS_VALUES = {
    "PENDINGNEW": "PendingNew",
    "NEW": "Initial",
    "INITIAL": "Initial",
    "HELD": "Submitted",
    "SUBMITTED": "Submitted",
    "PARTIALLYFILLED": "PartiallyFilled",
    "FILLED": "Filled",
    "CANCELLED": "Cancelled",
    "CANCELED": "Cancelled",
    "PENDINGCANCEL": "PendingCancel",
    "REJECTED": "Inactive",
    "INACTIVE": "Inactive",
    "EXPIRED": "Invalid",
    "INVALID": "Invalid",
}


class TigerDependencyError(RuntimeError):
    """Raised when the optional ``tigeropen`` package is not installed."""


class TigerConfigError(RuntimeError):
    """Raised when the connector configuration is missing or invalid."""


class TigerProfileMismatchError(RuntimeError):
    """Raised when a profile's account does not match its declared environment."""


def is_paper_account(account: str | None) -> bool:
    """Return whether an account number is a Tiger paper account (17 digits)."""
    return bool(account) and bool(_PAPER_ACCOUNT_RE.match(account.strip()))


@dataclass(frozen=True)
class TigerConfig:
    """Tiger connector connection settings.

    Official TigerOpen properties are preferred as an atomic credential source.
    The legacy ``tiger_id`` + PEM path fields remain supported for existing users.
    """

    tiger_id: str = field(default="", repr=False)
    private_key_path: str = field(default="", repr=False)
    account: str = field(default="", repr=False)
    properties_path: str = field(default="", repr=False)
    credential_source: str = ""
    properties_has_private_key: bool = False
    profile: str = "paper"
    timeout: float = 15.0
    readonly: bool = True

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None = None) -> "TigerConfig":
        """Build a config from a JSON-like mapping, normalizing the profile."""
        payload = dict(data or {})
        profile = str(payload.get("profile") or "paper").strip().lower()
        if profile not in PROFILE_ENVIRONMENTS:
            raise TigerConfigError("profile must be 'paper', 'live-readonly' or 'live'")
        return cls(
            tiger_id=str(payload.get("tiger_id") or "").strip(),
            private_key_path=str(payload.get("private_key_path") or "").strip(),
            account=str(payload.get("account") or "").strip(),
            properties_path=str(payload.get("properties_path") or "").strip(),
            credential_source=str(payload.get("credential_source") or "").strip(),
            properties_has_private_key=bool(payload.get("properties_has_private_key", False)),
            profile=profile,
            timeout=float(payload.get("timeout") or 15.0),
            readonly=bool(payload.get("readonly", True)),
        )

    @property
    def environment(self) -> str:
        """Return ``paper`` or ``live`` for this profile."""
        return PROFILE_ENVIRONMENTS.get(self.profile, "paper")


@dataclass(frozen=True)
class TigerReadSpec:
    """Allowlisted TigerOpen account read operation."""

    method: str
    allowed_params: frozenset[str] = frozenset()
    required_params: frozenset[str] = frozenset()
    injected_params: frozenset[str] = frozenset({"account"})


TIGER_ACCOUNT_READ_SPECS: dict[str, dict[str, TigerReadSpec]] = {
    "account": {
        "managed_accounts": TigerReadSpec("get_managed_accounts", frozenset({"lang"})),
        "assets": TigerReadSpec(
            "get_assets",
            frozenset({"sub_accounts", "segment", "market_value"}),
        ),
        "prime_assets": TigerReadSpec(
            "get_prime_assets",
            frozenset({"base_currency", "consolidated", "lang"}),
        ),
        "aggregate_assets": TigerReadSpec(
            "get_aggregate_assets",
            frozenset({"seg_type", "base_currency"}),
        ),
        "analytics": TigerReadSpec(
            "get_analytics_asset",
            frozenset({"start_date", "end_date", "seg_type", "currency", "sub_account", "lang"}),
        ),
        "fund_details": TigerReadSpec(
            "get_fund_details",
            frozenset({"seg_types", "fund_type", "currency", "start", "limit", "start_date", "end_date", "lang"}),
            frozenset({"seg_types"}),
        ),
        "funding_history": TigerReadSpec(
            "get_funding_history",
            frozenset({"seg_type"}),
            injected_params=frozenset(),
        ),
        "segment_fund_available": TigerReadSpec(
            "get_segment_fund_available",
            frozenset({"from_segment", "currency"}),
            injected_params=frozenset(),
        ),
        "segment_fund_history": TigerReadSpec(
            "get_segment_fund_history",
            frozenset({"limit"}),
            injected_params=frozenset(),
        ),
    },
    "portfolio": {
        "positions": TigerReadSpec(
            "get_positions",
            frozenset(
                {
                    "sec_type",
                    "currency",
                    "market",
                    "symbol",
                    "sub_accounts",
                    "expiry",
                    "strike",
                    "put_call",
                    "asset_quote_type",
                    "lang",
                }
            ),
        ),
        "option_exercise_records": TigerReadSpec(
            "get_option_exercise_records",
            frozenset({"page", "size", "status", "exercise_type", "symbol", "order_by", "lang"}),
        ),
        "option_exercise_positions": TigerReadSpec(
            "get_option_exercise_positions",
            frozenset({"exercise_type", "lang"}),
            frozenset({"exercise_type"}),
        ),
        "option_exercise_check": TigerReadSpec(
            "check_option_exercise",
            frozenset(
                {
                    "contract_id",
                    "exercise_type",
                    "quantity",
                    "executing_date",
                    "is_force",
                    "itm_rate",
                    "lang",
                }
            ),
            frozenset({"contract_id", "exercise_type"}),
        ),
        "transfer_records": TigerReadSpec(
            "get_position_transfer_records",
            frozenset({"since_date", "to_date", "status", "market", "symbol", "lang"}),
            frozenset({"since_date", "to_date"}),
            frozenset({"account_id"}),
        ),
        "transfer_external_records": TigerReadSpec(
            "get_position_transfer_external_records",
            frozenset({"since_date", "to_date", "status", "market", "symbol", "lang"}),
            frozenset({"since_date", "to_date"}),
            frozenset({"account_id"}),
        ),
        "transfer_detail": TigerReadSpec(
            "get_position_transfer_detail",
            frozenset({"transfer_id", "lang"}),
            frozenset({"transfer_id"}),
            frozenset({"account_id"}),
        ),
    },
    "activity": {
        "order": TigerReadSpec(
            "get_order",
            frozenset({"id", "order_id", "is_brief", "show_charges", "lang"}),
        ),
        "open_orders": TigerReadSpec(
            "get_open_orders",
            frozenset(
                {
                    "sec_type",
                    "market",
                    "symbol",
                    "start_time",
                    "end_time",
                    "parent_id",
                    "sort_by",
                    "seg_type",
                    "lang",
                }
            ),
        ),
        "filled_orders": TigerReadSpec(
            "get_filled_orders",
            frozenset(
                {
                    "sec_type",
                    "market",
                    "symbol",
                    "start_time",
                    "end_time",
                    "sort_by",
                    "seg_type",
                    "lang",
                }
            ),
        ),
        "cancelled_orders": TigerReadSpec(
            "get_cancelled_orders",
            frozenset(
                {
                    "sec_type",
                    "market",
                    "symbol",
                    "start_time",
                    "end_time",
                    "sort_by",
                    "seg_type",
                    "lang",
                }
            ),
        ),
    },
}

_PROPERTIES_FILENAME = "tiger_openapi_config.properties"


def build_config(
    profile_config: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> "TigerConfig":
    """Resolve saved credentials and fixed profile intent.

    Request-level credential and account overrides are intentionally ignored.
    """
    del overrides
    base = asdict(load_config())
    for key, value in dict(profile_config or {}).items():
        if value is not None:
            base[key] = value
    return TigerConfig.from_mapping(base)


def config_path() -> Path:
    """Return the user-level Tiger config path."""
    return get_runtime_root() / CONFIG_FILENAME


def _resolve_properties_file(value: str | Path) -> Path:
    """Resolve a properties file inside an approved user credential directory."""
    path = Path(value).expanduser().resolve()
    if path.is_dir():
        path = path / _PROPERTIES_FILENAME
    trusted_roots = (get_runtime_root().resolve(), (Path.home() / ".tigeropen").resolve())
    if not any(path.is_relative_to(root) for root in trusted_roots):
        raise TigerConfigError("Tiger properties must be inside a trusted user credential directory")
    if path.name != _PROPERTIES_FILENAME:
        raise TigerConfigError(f"Tiger properties file must be named {_PROPERTIES_FILENAME}")
    if not path.is_file():
        raise TigerConfigError("configured Tiger properties file was not found")
    return path


def _default_properties_file() -> Path | None:
    """Find an official properties file in supported user-level locations."""
    runtime_root = get_runtime_root()
    candidates = (
        runtime_root / "keys" / _PROPERTIES_FILENAME,
        runtime_root / _PROPERTIES_FILENAME,
        Path.home() / ".tigeropen" / _PROPERTIES_FILENAME,
    )
    return next((path.resolve() for path in candidates if path.is_file()), None)


def _properties_values(path: Path) -> dict[str, str]:
    """Parse the simple key/value form emitted by TigerOpen tooling."""
    values: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", "!")):
                continue
            key, separator, value = line.partition("=")
            if not separator:
                key, separator, value = line.partition(":")
            if separator:
                values[key.strip()] = value.strip()
    except OSError as exc:
        raise TigerConfigError("unable to read configured Tiger properties") from exc
    return values


def _properties_metadata(path: Path) -> dict[str, Any]:
    """Read non-secret identity metadata from an official properties file."""
    values = _properties_values(path)
    return {
        "tiger_id": values.get("tiger_id", ""),
        "account": values.get("account", ""),
        "properties_has_private_key": bool(
            values.get("private_key") or values.get("private_key_pk1") or values.get("private_key_pk8")
        ),
    }


def _with_official_properties(config: TigerConfig, path: Path) -> TigerConfig:
    """Attach an official properties source without retaining private material."""
    metadata = _properties_metadata(path)
    payload = asdict(config)
    payload.update(metadata)
    payload["properties_path"] = str(path)
    payload["credential_source"] = "official_properties"
    return TigerConfig.from_mapping(payload)


def load_config() -> TigerConfig:
    """Load Tiger settings, preferring configured or discovered official properties."""
    path = config_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        config = TigerConfig.from_mapping(payload)
        configured_properties = str(payload.get("properties_path") or "").strip()
        if configured_properties:
            return _with_official_properties(config, _resolve_properties_file(configured_properties))
        discovered = _default_properties_file()
        if discovered is not None:
            return _with_official_properties(config, discovered)
        if config.tiger_id or config.private_key_path or config.account:
            return TigerConfig.from_mapping({**asdict(config), "credential_source": "legacy_runtime_file"})
        return config
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise TigerConfigError(f"invalid Tiger config at {path}: {exc}") from exc


def save_config(config: TigerConfig) -> Path:
    """Atomically persist Tiger settings with owner-only permissions."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    payload.pop("properties_has_private_key", None)
    payload.pop("credential_source", None)
    content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".tiger-", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = -1
        with handle:
            handle.write(content)
        Path(temporary).replace(path)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        Path(temporary).unlink(missing_ok=True)
        raise
    return path


def tigeropen_available() -> bool:
    """Return whether the optional ``tigeropen`` SDK can be imported."""
    try:
        _require_tigeropen()
        return True
    except TigerDependencyError:
        return False


def check_status(config: TigerConfig | None = None) -> dict[str, Any]:
    """Check SDK readiness, config completeness, and account identity.

    Returns a JSON-serializable health report. Does not place or mutate any
    broker state.
    """
    cfg = config or load_config()
    report: dict[str, Any] = {
        "status": "ok",
        "config": _public_config(cfg),
        "sdk": {"package": "tigeropen", "installed": tigeropen_available()},
    }

    missing = _missing_fields(cfg)
    if missing:
        report["status"] = "error"
        report["error"] = f"Tiger connector not configured: missing {', '.join(missing)}."
        return report

    if not report["sdk"]["installed"]:
        report["status"] = "error"
        report["error"] = "Optional dependency missing: install with `pip install tigeropen`."
        return report

    try:
        _assert_profile(cfg)
    except (TigerProfileMismatchError, TigerConfigError):
        report["status"] = "error"
        report["error"] = "Tiger connector configuration is invalid"
        return report

    try:
        snapshot = get_account_snapshot(cfg)
    except Exception:  # noqa: BLE001 - broker SDK exceptions are not safe to expose
        report["status"] = "error"
        report["error"] = "Tiger connector request failed"
        return report

    report["account"] = {
        "account": _public_config(cfg)["account"],
        "is_paper": is_paper_account(cfg.account),
        "profile": cfg.profile,
        "assets_currency": [row.get("currency") for row in snapshot.get("assets", [])],
    }
    return report


def get_account_snapshot(config: TigerConfig | None = None) -> dict[str, Any]:
    """Fetch account assets / balance for the configured account."""
    cfg = config or load_config()
    _assert_profile(cfg)
    trade = _trade_client(cfg)
    assets = _safe_call(trade, "get_assets", account=cfg.account) or _safe_call(trade, "get_assets")
    rows = [_asset_to_dict(item) for item in _as_iter(assets)]
    return {
        "status": "ok",
        "profile": cfg.profile,
        "account": _public_config(cfg)["account"],
        "is_paper": is_paper_account(cfg.account),
        "assets": _redact_account_fields(rows),
    }


def get_positions(config: TigerConfig | None = None) -> dict[str, Any]:
    """Fetch current positions for the configured account."""
    cfg = config or load_config()
    _assert_profile(cfg)
    trade = _trade_client(cfg)
    positions = _safe_call(trade, "get_positions", account=cfg.account, sec_type=None) or _safe_call(
        trade, "get_positions"
    )
    rows = [_position_to_dict(item) for item in _as_iter(positions)]
    return {
        "status": "ok",
        "profile": cfg.profile,
        "account": _public_config(cfg)["account"],
        "positions": _redact_account_fields(rows),
    }


def get_open_orders(config: TigerConfig | None = None, *, include_executions: bool = False) -> dict[str, Any]:
    """Fetch open orders and, optionally, recently filled orders."""
    cfg = config or load_config()
    _assert_profile(cfg)
    trade = _trade_client(cfg)
    open_orders = _safe_call(trade, "get_open_orders", account=cfg.account) or _safe_call(trade, "get_open_orders")
    result: dict[str, Any] = {
        "status": "ok",
        "profile": cfg.profile,
        "account": _public_config(cfg)["account"],
        "open_orders": _redact_account_fields(
            [_order_to_dict(item) for item in _as_iter(open_orders)]
        ),
    }
    if include_executions:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        time_params = {
            "start_time": int(start_time.timestamp() * 1000),
            "end_time": int(end_time.timestamp() * 1000),
        }
        filled = _safe_call(
            trade,
            "get_filled_orders",
            account=cfg.account,
            **time_params,
        ) or _safe_call(trade, "get_filled_orders", **time_params)
        result["executions"] = _redact_account_fields(
            [_order_to_dict(item) for item in _as_iter(filled)]
        )
    return result


def get_quote(symbol: str, *, config: TigerConfig | None = None, **_: Any) -> dict[str, Any]:
    """Fetch a top-of-book quote snapshot for ``symbol``."""
    cfg = config or load_config()
    _assert_profile(cfg)
    quote = _quote_client(cfg)
    clean = symbol.strip().upper()
    briefs = _safe_call(quote, "get_stock_briefs", [clean])
    rows = [_quote_to_dict(item) for item in _as_iter(briefs)]
    payload = rows[0] if rows else {}
    return {"status": "ok", "symbol": clean, "quote": payload}


#: Canonical period token → Tiger ``get_bars`` period string.
# ``1H``/``1D``/``1W`` alias the lowercase tokens; ``1m`` vs ``1M`` stays case-sensitive.
_PERIOD_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "60min", "1H": "60min", "4h": "4hour", "4H": "4hour",
    "1d": "day", "1D": "day", "1w": "week", "1W": "week", "1M": "month",
}


def get_historical_bars(
    symbol: str,
    *,
    config: TigerConfig | None = None,
    period: str = "1d",
    limit: int = 90,
    **_: Any,
) -> dict[str, Any]:
    """Fetch historical OHLCV bars for ``symbol`` (``period`` is a canonical token)."""
    cfg = config or load_config()
    _assert_profile(cfg)
    quote = _quote_client(cfg)
    clean = symbol.strip().upper()
    # Case-sensitive: ``1m`` (minute) must not collide with ``1M`` (month).
    tiger_period = _PERIOD_MAP.get(period.strip(), "day")
    bars = _safe_call(quote, "get_bars", [clean], period=tiger_period, limit=int(limit))
    return {
        "status": "ok",
        "symbol": clean,
        "period": period,
        "bars": [_bar_to_dict(item) for item in _as_iter(bars)],
    }


def get_option_expirations(
    symbols: str | list[str],
    *,
    config: TigerConfig | None = None,
    market: str = "US",
) -> dict[str, Any]:
    """Read available option expiration dates for up to 30 underlyings."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_symbols = _bounded_text_list(symbols, name="symbols", maximum=30, upper=True)
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_option_expirations(clean_symbols, market=clean_market)
    result = {
        "status": "ok",
        "symbols": clean_symbols,
        "market": clean_market,
        "expirations": _records(rows),
    }
    if isinstance(symbols, str):
        result["symbol"] = clean_symbols[0]
    return result


def get_option_chain(
    symbol: str,
    expiry: str | int,
    *,
    config: TigerConfig | None = None,
    market: str = "US",
    return_greeks: bool = True,
    timezone: str | None = None,
    option_filter: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read an option chain, including official filters and optional Greeks."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_symbol = _required_symbol(symbol)
    clean_expiry = str(expiry or "").strip()
    if not clean_expiry:
        raise ValueError("expiry is required")
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_option_chain(
        clean_symbol,
        clean_expiry,
        option_filter=_option_filter(option_filter),
        return_greek_value=bool(return_greeks),
        market=clean_market,
        timezone=_optional_text(timezone),
    )
    return {
        "status": "ok",
        "symbol": clean_symbol,
        "expiry": clean_expiry,
        "market": clean_market,
        "options": _records(rows),
    }


def get_option_symbols(
    *,
    config: TigerConfig | None = None,
    market: str = "HK",
    lang: str | None = None,
) -> dict[str, Any]:
    """Read option-underlying symbol mappings, including Hong Kong mappings."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_option_symbols(market=clean_market, lang=_optional_text(lang))
    return {"status": "ok", "market": clean_market, "symbols": _records(rows)}


def get_option_briefs(
    identifiers: str | list[str],
    *,
    config: TigerConfig | None = None,
    market: str = "US",
    timezone: str | None = None,
) -> dict[str, Any]:
    """Read real-time quotes for up to 30 option contracts."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_identifiers = _bounded_text_list(identifiers, name="identifiers", maximum=30)
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_option_briefs(
        clean_identifiers,
        market=clean_market,
        timezone=_optional_text(timezone),
    )
    return {"status": "ok", "market": clean_market, "options": _records(rows)}


def get_option_bars(
    identifiers: str | list[str],
    *,
    config: TigerConfig | None = None,
    begin_time: str | int = -1,
    end_time: str | int = 4070880000000,
    period: str = "day",
    limit: int | None = None,
    sort_dir: str | None = None,
    market: str = "US",
    timezone: str | None = None,
) -> dict[str, Any]:
    """Read historical option bars for up to 30 contracts."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_identifiers = _bounded_text_list(identifiers, name="identifiers", maximum=30)
    clean_market = _market_token(market)
    params = {
        "begin_time": begin_time,
        "end_time": end_time,
        "period": _option_bar_period(period),
        "limit": _bounded_optional_limit(limit, maximum=1200),
        "sort_dir": _optional_text(sort_dir, upper=True),
        "market": clean_market,
        "timezone": _optional_text(timezone),
    }
    rows = _quote_client(cfg).get_option_bars(clean_identifiers, **params)
    return {"status": "ok", "market": clean_market, "bars": _records(rows)}


def get_option_depth(
    identifiers: str | list[str],
    *,
    config: TigerConfig | None = None,
    market: str = "US",
    timezone: str | None = None,
) -> dict[str, Any]:
    """Read option order-book depth for up to 30 contracts."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_identifiers = _bounded_text_list(identifiers, name="identifiers", maximum=30)
    clean_market = _market_token(market)
    depth = _quote_client(cfg).get_option_depth(
        clean_identifiers,
        market=clean_market,
        timezone=_optional_text(timezone),
    )
    return {"status": "ok", "market": clean_market, "depth": _json_safe(depth)}


def get_option_trade_ticks(
    identifiers: str | list[str],
    *,
    config: TigerConfig | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    """Read option trade ticks for up to 30 contracts."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_identifiers = _bounded_text_list(identifiers, name="identifiers", maximum=30)
    rows = _quote_client(cfg).get_option_trade_ticks(
        clean_identifiers,
        timezone=_optional_text(timezone),
    )
    return {"status": "ok", "ticks": _records(rows)}


def get_option_timeline(
    identifiers: str | list[str],
    *,
    config: TigerConfig | None = None,
    market: str = "US",
    begin_time: str | int | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    """Read intraday option timelines for up to 30 contracts."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_identifiers = _bounded_text_list(identifiers, name="identifiers", maximum=30)
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_option_timeline(
        clean_identifiers,
        market=clean_market,
        begin_time=_optional_value(begin_time),
        timezone=_optional_text(timezone),
    )
    return {"status": "ok", "market": clean_market, "timeline": _records(rows)}


def get_option_analysis(
    symbols: list[str] | list[dict[str, Any]],
    *,
    config: TigerConfig | None = None,
    period: str = "52week",
    market: str = "US",
    require_volatility_list: bool | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    """Read option volatility analysis for up to 10 underlyings."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_symbols = _option_analysis_symbols(symbols)
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_option_analysis(
        clean_symbols,
        period=_option_analysis_period(period),
        market=clean_market,
        require_volatility_list=require_volatility_list,
        lang=_optional_text(lang),
    )
    return {"status": "ok", "market": clean_market, "analysis": _records(rows)}


def get_option_contract(
    symbol: str,
    *,
    config: TigerConfig | None = None,
    currency: str | None = None,
    exchange: str | None = None,
    expiry: str | None = None,
    strike: float | None = None,
    put_call: str | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    """Read one option contract without exposing trading mutations."""
    cfg = config or load_config()
    _assert_profile(cfg)
    contract = _trade_client(cfg).get_contract(
        symbol=_required_symbol(symbol),
        sec_type="OPT",
        currency=_optional_text(currency, upper=True),
        exchange=_optional_text(exchange, upper=True),
        expiry=_optional_text(expiry),
        strike=strike,
        put_call=_optional_text(put_call, upper=True),
        lang=_optional_text(lang),
    )
    return {"status": "ok", "contract": _json_safe(contract)}


def get_option_derivative_contracts(
    symbol: str,
    expiry: str,
    *,
    config: TigerConfig | None = None,
    sec_type: str = "OPT",
    lang: str | None = None,
) -> dict[str, Any]:
    """Read option, warrant, or CBBC derivative contracts for an underlying."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_sec_type = _derivative_security_type(sec_type)
    clean_expiry = _required_text(expiry, "expiry")
    contracts = _trade_client(cfg).get_derivative_contracts(
        symbol=_required_symbol(symbol),
        sec_type=clean_sec_type,
        expiry=clean_expiry,
        lang=_optional_text(lang),
    )
    return {"status": "ok", "sec_type": clean_sec_type, "contracts": _records(contracts)}


def get_market_status(
    *,
    config: TigerConfig | None = None,
    market: str = "ALL",
) -> dict[str, Any]:
    """Read the current trading status for one market or all markets."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_market = _market_token(market, allow_all=True)
    statuses = _quote_client(cfg).get_market_status(clean_market)
    return {"status": "ok", "market": clean_market, "markets": _records(statuses)}


def get_trading_calendar(
    *,
    config: TigerConfig | None = None,
    market: str,
    begin_date: str | int | None = None,
    end_date: str | int | None = None,
) -> dict[str, Any]:
    """Read trading days for a market and optional date range."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_market = _market_token(market)
    rows = _quote_client(cfg).get_trading_calendar(
        clean_market,
        begin_date=_optional_value(begin_date),
        end_date=_optional_value(end_date),
    )
    return {
        "status": "ok",
        "market": clean_market,
        "begin_date": begin_date,
        "end_date": end_date,
        "calendar": _records(rows),
    }


def get_depth_quote(
    symbol: str,
    *,
    config: TigerConfig | None = None,
    market: str,
    trade_session: str | None = None,
) -> dict[str, Any]:
    """Read level-two order-book depth for one symbol."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_symbol = _required_symbol(symbol)
    clean_market = _market_token(market)
    depth = _quote_client(cfg).get_depth_quote(
        [clean_symbol],
        clean_market,
        trade_session=_optional_text(trade_session),
    )
    return {
        "status": "ok",
        "symbol": clean_symbol,
        "market": clean_market,
        "depth": _json_safe(depth),
    }


def get_trade_ticks(
    symbol: str,
    *,
    config: TigerConfig | None = None,
    trade_session: str | None = None,
    begin_index: int | None = None,
    end_index: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Read recent stock trade ticks for one symbol."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_symbol = _required_symbol(symbol)
    clean_limit = _bounded_limit(limit, maximum=1000)
    rows = _quote_client(cfg).get_trade_ticks(
        [clean_symbol],
        trade_session=_optional_text(trade_session),
        begin_index=begin_index,
        end_index=end_index,
        limit=clean_limit,
    )
    return {"status": "ok", "symbol": clean_symbol, "ticks": _records(rows)}


def _order_states(values: list[Any] | tuple[Any, ...] | None) -> list[str] | None:
    if not values:
        return None
    if len(values) > 100:
        raise ValueError("states must contain at most 100 items")
    result: list[str] = []
    for value in values:
        raw = value.value if isinstance(value, Enum) else value
        token = re.sub(r"[^A-Za-z0-9]", "", str(raw)).upper()
        normalized = _ORDER_STATUS_VALUES.get(token)
        if normalized is None:
            raise ValueError(f"unsupported Tiger order state: {raw}")
        result.append(normalized)
    return result


def _transaction_date(value: Any) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    compact = text.replace("-", "")
    if not re.fullmatch(r"\d{8}", compact):
        raise ValueError("date must use YYYYMMDD or YYYY-MM-DD")
    try:
        datetime.strptime(compact, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("date must use YYYYMMDD or YYYY-MM-DD") from exc
    return compact


def get_order_history(
    *,
    config: TigerConfig | None = None,
    market: str = "ALL",
    symbol: str | None = None,
    start_time: str | int | None = None,
    end_time: str | int | None = None,
    limit: int = 100,
    states: list[str] | None = None,
    sec_type: str | None = None,
    page_token: str | None = None,
) -> dict[str, Any]:
    """Read historical orders with Tiger-supported time and market filters."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_market = _market_token(market, allow_all=True)
    clean_states = _order_states(states)
    response = _trade_client(cfg).get_orders(
        account=cfg.account,
        sec_type=_optional_text(sec_type),
        market=clean_market,
        symbol=_optional_text(symbol, upper=True),
        start_time=_optional_value(start_time),
        end_time=_optional_value(end_time),
        limit=_bounded_limit(limit, maximum=1000),
        states=clean_states,
        page_token=_optional_text(page_token) or "",
    )
    items, next_page_token = _paged_items(response)
    return {
        "status": "ok",
        "profile": cfg.profile,
        "account": _public_config(cfg)["account"],
        "market": clean_market,
        "orders": _redact_account_fields([_order_to_dict(item) for item in items]),
        "next_page_token": next_page_token,
    }


def get_transactions(
    *,
    config: TigerConfig | None = None,
    market: str = "ALL",
    symbol: str | None = None,
    order_id: int | None = None,
    start_time: str | int | None = None,
    end_time: str | int | None = None,
    limit: int = 100,
    sec_type: str | None = None,
    page_token: str | None = None,
    since_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Read execution transactions with time filters and local market filtering."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_market = _market_token(market, allow_all=True)
    clean_limit = _bounded_limit(limit, maximum=1000)
    clean_since_date = _transaction_date(since_date)
    clean_to_date = _transaction_date(to_date)
    trade = _trade_client(cfg)
    request = {
        "account": cfg.account,
        "order_id": order_id,
        "symbol": _optional_text(symbol, upper=True),
        "sec_type": _optional_text(sec_type),
        "start_time": start_time,
        "end_time": end_time,
        "limit": clean_limit,
        "since_date": clean_since_date,
        "to_date": clean_to_date,
    }
    if clean_market == "ALL":
        response = trade.get_transactions(**request, page_token=_optional_text(page_token) or "")
        items, next_page_token = _paged_items(response)
        transactions = [_transaction_to_dict(item) for item in items]
        pagination_supported = True
        truncated = False
    else:
        if _optional_text(page_token):
            raise ValueError("page_token is not supported with a local transaction market filter")
        current_token = ""
        next_page_token = None
        transactions = []
        for _ in range(20):
            response = trade.get_transactions(**request, page_token=current_token)
            items, next_page_token = _paged_items(response)
            transactions.extend(
                item
                for item in (_transaction_to_dict(row) for row in items)
                if item.get("market") == clean_market
            )
            if len(transactions) >= clean_limit or not next_page_token or next_page_token == current_token:
                break
            current_token = next_page_token
        truncated = len(transactions) > clean_limit or bool(next_page_token)
        transactions = transactions[:clean_limit]
        next_page_token = None
        pagination_supported = False
    return {
        "status": "ok",
        "profile": cfg.profile,
        "account": _public_config(cfg)["account"],
        "market": clean_market,
        "transactions": _redact_account_fields(transactions),
        "next_page_token": next_page_token,
        "pagination_supported": pagination_supported,
        "truncated": truncated,
    }


def query_account_domain(
    group: str,
    action: str,
    *,
    config: TigerConfig | None = None,
    **params: Any,
) -> dict[str, Any]:
    """Execute one explicitly allowlisted TigerOpen account read operation."""
    cfg = config or load_config()
    _assert_profile(cfg)
    clean_group = str(group or "").strip().lower()
    clean_action = str(action or "").strip().lower()
    spec = TIGER_ACCOUNT_READ_SPECS.get(clean_group, {}).get(clean_action)
    if spec is None:
        raise ValueError("unsupported Tiger account read action")

    supplied = {key: value for key, value in params.items() if value is not None}
    unknown = set(supplied) - spec.allowed_params
    if unknown:
        raise ValueError(f"unsupported parameters for {clean_action}: {', '.join(sorted(unknown))}")
    missing = {key for key in spec.required_params if supplied.get(key) in (None, "", [])}
    if missing:
        raise ValueError(f"missing required parameters: {', '.join(sorted(missing))}")
    if clean_group == "activity" and clean_action == "order" and not (
        supplied.get("id") or supplied.get("order_id")
    ):
        raise ValueError("order requires id or order_id")

    call_params = _sanitize_account_read_params(supplied)
    if clean_group == "portfolio" and clean_action == "positions" and "sec_type" not in call_params:
        call_params["sec_type"] = None
    if "account" in spec.injected_params:
        call_params["account"] = cfg.account
    if "account_id" in spec.injected_params:
        call_params["account_id"] = cfg.account

    response = getattr(_trade_client(cfg), spec.method)(**call_params)
    return {
        "status": "ok",
        "profile": cfg.profile,
        "group": clean_group,
        "action": clean_action,
        "data": _redact_account_fields(_normalize_account_read_response(response)),
    }


def _sanitize_account_read_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize bounded account-read inputs without accepting credential fields."""
    result: dict[str, Any] = {}
    for key, value in params.items():
        if key in {"limit", "size"}:
            result[key] = _bounded_limit(value, maximum=1000 if key == "limit" else 100)
        elif key == "page":
            page = int(value)
            if page < 1:
                raise ValueError("page must be at least 1")
            result[key] = page
        elif key == "start":
            start = int(value)
            if start < 0:
                raise ValueError("start must be non-negative")
            result[key] = start
        elif key in {"market"}:
            result[key] = _market_token(value, allow_all=True)
        elif key in {"sec_type", "currency", "seg_type", "from_segment", "put_call"}:
            result[key] = _optional_text(value, upper=True)
        elif key in {"sub_accounts", "seg_types"}:
            if not isinstance(value, (list, tuple)) or len(value) > 100:
                raise ValueError(f"{key} must be a list with at most 100 items")
            result[key] = [str(item).strip().upper() for item in value if str(item).strip()]
        elif isinstance(value, str):
            text = value.strip()
            if len(text) > 256:
                raise ValueError(f"{key} is too long")
            result[key] = text
        else:
            result[key] = value
    return result


def _normalize_account_read_response(value: Any) -> Any:
    """Preserve complete SDK fields while producing strict JSON-compatible data."""
    if value is None:
        return None
    if callable(getattr(value, "to_dict", None)) and hasattr(value, "columns"):
        return _records(value)
    return _json_safe(value)


# ---------------------------------------------------------------------------
# Order placement (Layer B/C) — fails closed, never raises
# ---------------------------------------------------------------------------

#: Accepted ``side`` tokens → Tiger ``action`` (uppercase).
_ACTION_MAP = {"buy": "BUY", "sell": "SELL"}

#: Accepted ``time_in_force`` tokens → Tiger TIF string.
_TIF_MAP = {"day": "DAY", "gtc": "GTC"}


def place_order(
    config: TigerConfig,
    *,
    symbol: str,
    side: str,
    quantity: float | None = None,
    notional: float | None = None,
    order_type: str = "market",
    limit_price: float | None = None,
    time_in_force: str = "day",
) -> dict[str, Any]:
    """Place a stock order against the account in ``config``.

    This executes a REAL order against whatever account ``config`` points at: a
    paper config drives the Tiger paper (sandbox) account, a live config drives
    the live account. The connector only executes; authorization (mandate gate,
    kill switch) is the caller's responsibility. ``_assert_profile`` runs first
    so a live account can never be driven under a paper profile by mistake.

    Args:
        config: Resolved :class:`TigerConfig`. Its ``profile`` selects the
            account environment (paper account = sandbox order).
        symbol: Stock symbol, e.g. ``AAPL``.
        side: ``buy`` or ``sell`` (case-insensitive).
        quantity: Order size in units. Provide exactly one of ``quantity`` or
            ``notional``.
        notional: Notional amount. Tiger has no notional path for stocks, so a
            notional-only request fails closed with a clear error.
        order_type: ``market`` or ``limit`` (a ``limit`` order requires
            ``limit_price``).
        limit_price: Limit price; required for and only used by limit orders.
        time_in_force: ``day`` or ``gtc``. Paper accounts do not support GTC, so
            it is forced to DAY when ``config`` is a paper profile.

    Returns:
        ``{"status": "ok", "order_id": str, "symbol", "side", "profile", ...}``
        on success, otherwise ``{"status": "error", "error": str}``. Never
        raises: all failure modes are reported in the envelope.
    """
    # ---- input validation (fail closed before touching the SDK) ----
    side_key = str(side or "").strip().lower()
    action = _ACTION_MAP.get(side_key)
    if action is None:
        return {"status": "error", "error": "side must be 'buy' or 'sell'"}

    if (quantity is None) == (notional is None):
        return {"status": "error", "error": "provide exactly one of quantity or notional"}
    if notional is not None:
        return {"status": "error", "error": "Tiger requires quantity (units), not notional"}

    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        return {"status": "error", "error": "quantity must be a number"}
    if qty <= 0:
        return {"status": "error", "error": "quantity must be positive"}

    type_key = str(order_type or "").strip().lower()
    if type_key not in ("market", "limit"):
        return {"status": "error", "error": "order_type must be 'market' or 'limit'"}

    px: float | None = None
    if type_key == "limit":
        if limit_price is None:
            return {"status": "error", "error": "limit order requires limit_price"}
        try:
            px = float(limit_price)
        except (TypeError, ValueError):
            return {"status": "error", "error": "limit_price must be a number"}
        if px <= 0:
            return {"status": "error", "error": "limit_price must be positive"}

    tif_key = str(time_in_force or "").strip().lower()
    tif = _TIF_MAP.get(tif_key)
    if tif is None:
        return {"status": "error", "error": "time_in_force must be 'day' or 'gtc'"}

    clean_symbol = str(symbol or "").strip().upper()
    if not clean_symbol:
        return {"status": "error", "error": "symbol is required"}

    # ---- profile / environment guard ----
    try:
        _assert_profile(config)
    except (TigerProfileMismatchError, TigerConfigError) as exc:
        return {"status": "error", "error": str(exc)}

    # Paper accounts do not support GTC; force DAY rather than failing the order.
    paper = is_paper_account(config.account)
    if paper and tif == "GTC":
        tif = "DAY"

    # ---- build + submit ----
    try:
        from tigeropen.common.util.contract_utils import stock_contract  # type: ignore
        from tigeropen.common.util.order_utils import limit_order, market_order  # type: ignore
    except ModuleNotFoundError as exc:
        return {"status": "error", "error": f"tigeropen is not installed; run `pip install tigeropen` ({exc})"}

    try:
        trade = _trade_client(config)
        contract = stock_contract(symbol=clean_symbol, currency="USD")
        if type_key == "limit":
            order = limit_order(
                account=config.account,
                contract=contract,
                action=action,
                quantity=qty,
                limit_price=px,
                time_in_force=tif,
            )
        else:
            order = market_order(
                account=config.account,
                contract=contract,
                action=action,
                quantity=qty,
                time_in_force=tif,
            )
        # ``place_order`` mutates ``order.id`` with the global id and returns it;
        # read both defensively in case the SDK only does one.
        returned = trade.place_order(order)
        order_id = _obj_get(order, "id", None)
        if order_id is None:
            order_id = returned
    except Exception:  # noqa: BLE001 - broker SDK exceptions are not safe to expose
        return {"status": "error", "error": "Tiger connector request failed"}

    if order_id is None:
        return {"status": "error", "error": "Tiger did not return an order id"}

    # Best-effort rejection check: tigeropen mutates the order object with a
    # status/reason. A rejected order can still come back with an id, so don't
    # report success when the broker flagged it rejected.
    order_status = str(_obj_get(order, "status", "") or "")
    reason = _obj_get(order, "reason", None)
    if order_status.strip().lower() in ("rejected", "inactive") or (reason and str(reason).strip()):
        return {
            "status": "error",
            "error": "Tiger rejected order",
            "order_id": str(order_id),
            "symbol": clean_symbol,
        }

    return {
        "status": "ok",
        "order_id": str(order_id),
        "symbol": clean_symbol,
        "side": side_key,
        "profile": config.profile,
        "account": _public_config(config)["account"],
        "is_paper": paper,
        "order_type": type_key,
        "quantity": qty,
        "limit_price": px,
        "time_in_force": tif,
    }


def cancel_order(config: TigerConfig, order_id: Any, *, symbol: str | None = None) -> dict[str, Any]:
    """Cancel a previously placed order on the account in ``config``.

    Runs ``_assert_profile`` first so the cancel targets the intended account
    environment. Like :func:`place_order`, this never raises: every failure is
    returned in the envelope.

    Args:
        config: Resolved :class:`TigerConfig` selecting the account.
        order_id: The global order id returned by :func:`place_order`.
        symbol: Optional symbol, echoed back for caller convenience; Tiger
            cancels by id and does not require it.

    Returns:
        ``{"status": "ok", "order_id": str, "profile", ...}`` on success,
        otherwise ``{"status": "error", "error": str}``.
    """
    if order_id is None or str(order_id).strip() == "":
        return {"status": "error", "error": "order_id is required"}

    try:
        _assert_profile(config)
    except (TigerProfileMismatchError, TigerConfigError) as exc:
        return {"status": "error", "error": str(exc)}

    try:
        oid: Any = int(order_id)
    except (TypeError, ValueError):
        oid = order_id

    try:
        trade = _trade_client(config)
        # SDK accepts ``id=``; older builds use ``order_id=`` — try the canonical
        # keyword first and fall back so a signature drift still cancels.
        try:
            trade.cancel_order(id=oid)
        except TypeError:
            trade.cancel_order(order_id=oid)
    except Exception:  # noqa: BLE001 - broker SDK exceptions are not safe to expose
        return {"status": "error", "error": "Tiger connector request failed"}

    result: dict[str, Any] = {
        "status": "ok",
        "order_id": str(order_id),
        "profile": config.profile,
        "account": _public_config(config)["account"],
    }
    if symbol:
        result["symbol"] = str(symbol).strip().upper()
    return result


# ---------------------------------------------------------------------------
# SDK plumbing
# ---------------------------------------------------------------------------


def _require_tigeropen() -> ModuleType:
    try:
        import tigeropen  # type: ignore
    except ModuleNotFoundError as exc:
        raise TigerDependencyError("tigeropen is not installed; run `pip install tigeropen`.") from exc
    return tigeropen


def _client_config(cfg: TigerConfig):
    """Build a ``TigerOpenClientConfig`` from one trusted credential source."""
    _require_tigeropen()
    from tigeropen.common.util.signature_utils import read_private_key  # type: ignore
    from tigeropen.tiger_open_config import TigerOpenClientConfig  # type: ignore

    if any(name.startswith("TIGEROPEN_") for name in os.environ):
        raise TigerConfigError(
            "TIGEROPEN_* environment variables are not allowed with profile-scoped credentials"
        )
    if cfg.properties_path:
        properties_file = _resolve_properties_file(cfg.properties_path)
        values = _properties_values(properties_file)
        if values.get("tiger_id", "").strip() != cfg.tiger_id or values.get(
            "account", ""
        ).strip() != cfg.account:
            raise TigerConfigError("Tiger credential identity changed after profile validation")
        private_key = (
            values.get("private_key")
            or values.get("private_key_pk8")
            or values.get("private_key_pk1")
            or ""
        )
        client_config = TigerOpenClientConfig(
            props_path=str(properties_file),
            enable_dynamic_domain=False,
        )
        client_config.tiger_id = values.get("tiger_id", "")
        client_config.private_key = private_key
        client_config.account = values.get("account", "")
        client_config.license = values.get("license", "")
        client_config.secret_key = values.get("secret_key", "")
        client_config._sandbox_debug = values.get("env", "").upper() in {"SANDBOX", "TEST"}
        if not client_config.tiger_id or not client_config.private_key or not client_config.account:
            raise TigerConfigError("Tiger official properties are missing required credentials")
    else:
        key_path = Path(cfg.private_key_path).expanduser()
        if not key_path.exists():
            raise TigerConfigError("Tiger private key is not configured or unavailable")
        client_config = TigerOpenClientConfig(enable_dynamic_domain=False)
        client_config.private_key = read_private_key(str(key_path))
        client_config.tiger_id = cfg.tiger_id
        client_config.account = cfg.account
    try:
        client_config.timeout = cfg.timeout
    except Exception:  # noqa: BLE001 - older SDKs may not expose timeout
        pass
    return client_config


def _trade_client(cfg: TigerConfig):
    _require_tigeropen()
    from tigeropen.trade.trade_client import TradeClient  # type: ignore

    return TradeClient(_client_config(cfg))


_QUOTE_CLIENT_CACHE_MAXSIZE = 16
_QUOTE_CLIENT_CACHE: OrderedDict[tuple[Any, ...], Any] = OrderedDict()
_QUOTE_CLIENT_CACHE_LOCK = threading.Lock()


def _credential_revision(path_value: str) -> int | None:
    if not path_value:
        return None
    try:
        return Path(path_value).expanduser().stat().st_mtime_ns
    except OSError:
        return None


def _quote_client_cache_key(cfg: TigerConfig) -> tuple[Any, ...]:
    return (
        cfg.tiger_id,
        cfg.account,
        cfg.profile,
        cfg.timeout,
        cfg.credential_source,
        cfg.properties_path,
        _credential_revision(cfg.properties_path),
        cfg.private_key_path,
        _credential_revision(cfg.private_key_path),
    )


def _clear_quote_client_cache() -> None:
    """Clear cached quote clients, primarily for credential rotation and tests."""
    with _QUOTE_CLIENT_CACHE_LOCK:
        _QUOTE_CLIENT_CACHE.clear()


def _quote_client(cfg: TigerConfig):
    _require_tigeropen()
    key = _quote_client_cache_key(cfg)
    with _QUOTE_CLIENT_CACHE_LOCK:
        client = _QUOTE_CLIENT_CACHE.get(key)
        if client is not None:
            _QUOTE_CLIENT_CACHE.move_to_end(key)
            return client

        from tigeropen.quote.quote_client import QuoteClient  # type: ignore

        client = QuoteClient(_client_config(cfg))
        _QUOTE_CLIENT_CACHE[key] = client
        _QUOTE_CLIENT_CACHE.move_to_end(key)
        while len(_QUOTE_CLIENT_CACHE) > _QUOTE_CLIENT_CACHE_MAXSIZE:
            _QUOTE_CLIENT_CACHE.popitem(last=False)
        return client


def _assert_profile(cfg: TigerConfig) -> None:
    """Fail closed when the account does not match the declared environment."""
    account = (cfg.account or "").strip()
    if not account:
        raise TigerConfigError("Tiger account number is not configured")
    paper = is_paper_account(account)
    if cfg.environment == "paper" and not paper:
        raise TigerProfileMismatchError(
            "Configured profile is paper, but the account number is not a 17-digit Tiger paper account. "
            "Use a live profile only if you intend live-account access."
        )
    if cfg.environment == "live" and paper:
        raise TigerProfileMismatchError(
            "Configured profile is live, but the account number is a 17-digit Tiger paper account. "
            "Select a paper profile for paper accounts."
        )


def _missing_fields(cfg: TigerConfig) -> list[str]:
    missing = []
    if not cfg.tiger_id:
        missing.append("tiger_id")
    if not cfg.account:
        missing.append("account")
    if cfg.properties_path:
        if not cfg.properties_has_private_key:
            missing.append("private_key")
    elif not cfg.private_key_path:
        missing.append("private_key_path")
    return missing


def _public_config(cfg: TigerConfig) -> dict[str, Any]:
    """Return config metadata without credential material or sensitive paths."""
    data = asdict(cfg)
    data.pop("properties_has_private_key", None)
    if data.get("tiger_id"):
        data["tiger_id"] = data["tiger_id"][:4] + "***"
    if data.get("account"):
        data["account"] = _redact_account_value(data["account"])
    if data.get("private_key_path"):
        data["private_key_path"] = "***configured***"
    if data.get("properties_path"):
        data["properties_path"] = "***configured***"
    return data


def _redact_account_value(value: Any) -> str:
    text = str(value or "")
    return f"{text[:3]}***" if text else ""


def _redact_account_fields(value: Any) -> Any:
    """Recursively mask account identifiers in public Tiger responses."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).replace("_", "").lower()
            if normalized_key in {"account", "accountid", "subaccount"}:
                if isinstance(item, (list, tuple)):
                    result[str(key)] = [_redact_account_value(entry) for entry in item]
                else:
                    result[str(key)] = _redact_account_value(item)
            else:
                result[str(key)] = _redact_account_fields(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_redact_account_fields(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Defensive field extraction (SDK returns objects, dicts, or DataFrames)
# ---------------------------------------------------------------------------


_ALLOWED_MARKETS = frozenset({"US", "HK", "CN", "SG", "AU"})
_OPTION_FILTER_FIELDS = frozenset(
    {
        "implied_volatility_min",
        "implied_volatility_max",
        "open_interest_min",
        "open_interest_max",
        "delta_min",
        "delta_max",
        "gamma_min",
        "gamma_max",
        "theta_min",
        "theta_max",
        "vega_min",
        "vega_max",
        "rho_min",
        "rho_max",
        "in_the_money",
    }
)
_OPTION_BAR_PERIODS = frozenset({"day", "1min", "5min", "30min", "60min"})
_OPTION_ANALYSIS_PERIODS = frozenset({"3year", "52week", "26week", "13week"})
_DERIVATIVE_SECURITY_TYPES = frozenset({"OPT", "WAR", "IOPT"})


def _required_text(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    if len(text) > 256:
        raise ValueError(f"{name} is too long")
    return text


def _required_symbol(value: Any) -> str:
    return _required_text(value, "symbol").upper()


def _bounded_text_list(
    value: str | list[str] | tuple[str, ...],
    *,
    name: str,
    maximum: int,
    upper: bool = False,
) -> list[str]:
    values = [value] if isinstance(value, str) else list(value or [])
    if not values:
        raise ValueError(f"{name} is required")
    if len(values) > maximum:
        raise ValueError(f"{name} must contain at most {maximum} items")
    if not all(isinstance(item, str) for item in values):
        raise ValueError(f"{name} must contain only strings")
    result = [_required_text(item, name) for item in values]
    return [item.upper() for item in result] if upper else result


def _option_filter(value: Mapping[str, Any] | None) -> Any:
    if not value:
        return None
    unknown = set(value) - _OPTION_FILTER_FIELDS
    if unknown:
        raise ValueError(f"unsupported option filter fields: {', '.join(sorted(unknown))}")
    from tigeropen.quote.domain.filter import OptionFilter  # type: ignore

    return OptionFilter(**dict(value))


def _option_bar_period(value: Any) -> str:
    period = _required_text(value, "period")
    if period not in _OPTION_BAR_PERIODS:
        raise ValueError(f"option period must be one of {', '.join(sorted(_OPTION_BAR_PERIODS))}")
    return period


def _option_analysis_period(value: Any) -> str:
    period = _required_text(value, "period")
    if period not in _OPTION_ANALYSIS_PERIODS:
        raise ValueError(
            f"option analysis period must be one of {', '.join(sorted(_OPTION_ANALYSIS_PERIODS))}"
        )
    return period


def _option_analysis_symbols(value: Any) -> list[str] | list[dict[str, str]]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("symbols must be a non-empty list")
    if len(value) > 10:
        raise ValueError("symbols must contain at most 10 items")
    result: list[str | dict[str, str]] = []
    for item in value:
        if isinstance(item, Mapping):
            unknown = set(item) - {"symbol", "period"}
            if unknown:
                raise ValueError(f"unsupported option analysis fields: {', '.join(sorted(unknown))}")
            entry = {"symbol": _required_symbol(item.get("symbol"))}
            if item.get("period") is not None:
                entry["period"] = _option_analysis_period(item["period"])
            result.append(entry)
        else:
            result.append(_required_symbol(item))
    return result  # type: ignore[return-value]


def _derivative_security_type(value: Any) -> str:
    sec_type = _required_text(value, "sec_type").upper()
    if sec_type not in _DERIVATIVE_SECURITY_TYPES:
        raise ValueError(
            f"sec_type must be one of {', '.join(sorted(_DERIVATIVE_SECURITY_TYPES))}"
        )
    return sec_type


def _market_token(value: Any, *, allow_all: bool = False) -> str:
    market = str(value or ("ALL" if allow_all else "")).strip().upper()
    allowed = _ALLOWED_MARKETS | ({"ALL"} if allow_all else set())
    if market not in allowed:
        raise ValueError(f"market must be one of {', '.join(sorted(allowed))}")
    return market


def _optional_text(value: Any, *, upper: bool = False) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > 256:
        raise ValueError("text value is too long")
    return text.upper() if upper else text


def _optional_value(value: Any) -> Any:
    return None if value in (None, "") else value


def _bounded_limit(value: Any, *, maximum: int) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc
    if limit < 1 or limit > maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def _bounded_optional_limit(value: Any, *, maximum: int) -> int | None:
    return None if value in (None, "") else _bounded_limit(value, maximum=maximum)


def _json_safe(value: Any) -> Any:
    """Recursively convert SDK and pandas values to strict JSON-compatible data."""
    value_type = type(value)
    if value_type.__module__.startswith(("pandas", "numpy")) and value_type.__name__ in {
        "NAType",
        "NaTType",
    }:
        return None
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if hasattr(value, "__dict__"):
        return {
            str(key): _json_safe(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }
    return value


def _records(value: Any) -> list[dict[str, Any]]:
    """Normalize DataFrames, mappings, and SDK objects to plain row dictionaries."""
    if value is None:
        return []
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict) and hasattr(value, "columns"):
        return [_json_safe(row) for row in to_dict("records")]
    if isinstance(value, Mapping):
        return [_json_safe(value)]
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item) if isinstance(_json_safe(item), Mapping) else {"value": _json_safe(item)}
            for item in value
        ]
    normalized = _json_safe(value)
    return [normalized] if isinstance(normalized, Mapping) else [{"value": normalized}]


def _paged_items(value: Any) -> tuple[list[Any], str | None]:
    """Extract items and the next-page token from list or SDK response envelopes."""
    if value is None:
        return [], None
    if isinstance(value, (list, tuple)):
        return list(value), None
    for name in ("result", "items", "orders", "transactions"):
        items = _obj_get(value, name, None)
        if items is not None:
            token = _first(value, ("next_page_token", "page_token"))
            return _as_iter(items), str(token) if token else None
    return _as_iter(value), None


def _as_iter(value: Any) -> list[Any]:
    if value is None:
        return []
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict) and hasattr(value, "columns"):
        return list(to_dict("records"))
    if isinstance(value, Mapping):
        return [dict(value)]
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]



def _obj_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _first(obj: Any, names: tuple[str, ...], default: Any = None) -> Any:
    for name in names:
        value = _obj_get(obj, name, None)
        if value is not None:
            return value
    return default


def _asset_to_dict(item: Any) -> dict[str, Any]:
    return {
        "currency": _first(item, ("currency",)),
        "cash": _first(item, ("cash", "cash_balance")),
        "net_liquidation": _first(item, ("net_liquidation", "net_liquidation_value")),
        "buying_power": _first(item, ("buying_power",)),
        "equity_with_loan": _first(item, ("equity_with_loan", "equity_with_loan_value")),
        "unrealized_pnl": _first(item, ("unrealized_pnl", "unrealized_pl")),
    }


def _position_to_dict(item: Any) -> dict[str, Any]:
    contract = _obj_get(item, "contract")
    details = _json_safe(item)
    row = dict(details) if isinstance(details, Mapping) else {}
    row.update(
        {
            "symbol": _first(contract, ("symbol",)) or _first(item, ("symbol",)),
            "currency": _first(contract, ("currency",)) or _first(item, ("currency",)),
            "sec_type": _first(contract, ("sec_type", "secType")),
            "quantity": _first(item, ("quantity", "position_qty", "position")),
            "average_cost": _first(item, ("average_cost", "avg_cost")),
            "market_value": _first(item, ("market_value",)),
            "unrealized_pnl": _first(item, ("unrealized_pnl", "unrealized_pl")),
            "contract": _json_safe(contract),
        }
    )
    return _json_safe(row)


def _order_to_dict(item: Any) -> dict[str, Any]:
    contract = _obj_get(item, "contract")
    return _json_safe(
        {
            "order_id": _first(item, ("id", "order_id")),
            "account_order_id": _first(item, ("order_id",)),
            "symbol": _first(contract, ("symbol",)) or _first(item, ("symbol",)),
            "market": _first(contract, ("market",)),
            "currency": _first(contract, ("currency",)),
            "sec_type": _first(contract, ("sec_type", "secType")),
            "action": _first(item, ("action",)),
            "order_type": _first(item, ("order_type", "type")),
            "quantity": _first(item, ("quantity",)),
            "filled": _first(item, ("filled",)),
            "remaining": _first(item, ("remaining",)),
            "avg_fill_price": _first(item, ("avg_fill_price",)),
            "limit_price": _first(item, ("limit_price",)),
            "status": str(_first(item, ("status",)) or ""),
            "order_time": _first(item, ("order_time",)),
            "trade_time": _first(item, ("trade_time",)),
            "update_time": _first(item, ("update_time",)),
        }
    )


def _transaction_to_dict(item: Any) -> dict[str, Any]:
    contract = _obj_get(item, "contract")
    return _json_safe(
        {
            "transaction_id": _first(item, ("id", "transaction_id")),
            "order_id": _first(item, ("order_id",)),
            "symbol": _first(contract, ("symbol",)) or _first(item, ("symbol",)),
            "market": _first(contract, ("market",)),
            "currency": _first(contract, ("currency",)),
            "sec_type": _first(contract, ("sec_type", "secType")),
            "action": _first(item, ("action",)),
            "filled_quantity": _first(item, ("filled_quantity", "quantity")),
            "filled_price": _first(item, ("filled_price", "price")),
            "filled_amount": _first(item, ("filled_amount", "amount")),
            "transacted_at": _first(item, ("transacted_at", "time")),
        }
    )


def _quote_to_dict(item: Any) -> dict[str, Any]:
    return _json_safe(
        {
            "symbol": _first(item, ("symbol",)),
            "last": _first(item, ("latest_price", "last_price", "latest")),
            "bid": _first(item, ("bid_price", "bid")),
            "ask": _first(item, ("ask_price", "ask")),
            "open": _first(item, ("open",)),
            "high": _first(item, ("high",)),
            "low": _first(item, ("low",)),
            "prev_close": _first(item, ("pre_close", "prev_close")),
            "volume": _first(item, ("volume",)),
            "time": str(_first(item, ("latest_time", "time"), "")),
        }
    )


def _bar_to_dict(item: Any) -> dict[str, Any]:
    return _json_safe(
        {
            "time": str(_first(item, ("time", "date"), "")),
            "open": _first(item, ("open",)),
            "high": _first(item, ("high",)),
            "low": _first(item, ("low",)),
            "close": _first(item, ("close",)),
            "volume": _first(item, ("volume",)),
        }
    )


def _safe_call(obj: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    """Call ``obj.name(*args, **kwargs)`` if it exists, retrying without kwargs.

    Tiger SDK signatures vary across versions (some read methods take an
    ``account`` kwarg, some bind it from the client config). We try the richer
    call first and fall back to the no-arg form so a signature drift degrades to
    a usable call instead of an error.
    """
    fn = getattr(obj, name, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except TypeError:
        try:
            return fn(*args)
        except TypeError:
            return fn()
