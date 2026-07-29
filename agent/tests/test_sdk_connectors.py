"""Tests for the direct-SDK trading connectors (Tiger, Longbridge).

Layer A is read-only; these tests exercise the parts that do not require the
optional broker SDKs or live credentials: profile registration, the paper/live
identity guard, config resolution, read/write classification, secret redaction,
and the service dispatch degrading cleanly when nothing is configured.
"""

from __future__ import annotations

import datetime
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from backtest.loaders import longbridge as longbridge_loader
from src.live.classification import ToolClass
from src.trading.connectors.longbridge import credentials as lb_credentials
from src.trading import profiles, service
from src.trading.connectors.alpaca import sdk as al
from src.trading.connectors.alpaca.classification import ALPACA_TOOL_CLASS
from src.trading.connectors.binance import sdk as bn
from src.trading.connectors.binance.classification import BINANCE_TOOL_CLASS
from src.trading.connectors.dhan import sdk as dh
from src.trading.connectors.dhan.classification import DHAN_TOOL_CLASS
from src.trading.connectors.futu import sdk as ft
from src.trading.connectors.futu.classification import FUTU_TOOL_CLASS
from src.trading.connectors.longbridge import sdk as lb
from src.trading.connectors.longbridge.classification import LONGBRIDGE_TOOL_CLASS
from src.trading.connectors.okx import sdk as ox
from src.trading.connectors.okx.classification import OKX_TOOL_CLASS
from src.trading.connectors.shoonya import sdk as sh
from src.trading.connectors.shoonya.classification import SHOONYA_TOOL_CLASS
from src.trading.connectors.tiger import sdk as tg
from src.trading.connectors.tiger.classification import TIGER_TOOL_CLASS

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Profile registration
# --------------------------------------------------------------------------- #


def test_sdk_profiles_registered() -> None:
    """All broker connectors register paper and read-only live profiles."""
    ids = {p.id for p in profiles.list_profiles()}
    assert {
        "tiger-paper-sdk", "tiger-live-sdk-readonly",
        "longbridge-paper-sdk", "longbridge-live-sdk-readonly",
        "alpaca-paper-sdk", "alpaca-live-sdk-readonly",
        "okx-paper-sdk", "okx-live-sdk-readonly",
        "binance-paper-sdk", "binance-live-sdk-readonly",
        "futu-paper-sdk", "futu-live-sdk-readonly",
        "dhan-paper-sdk", "dhan-live-sdk-readonly",
        "shoonya-paper-sdk", "shoonya-live-sdk-readonly",
    } <= ids


def test_no_discriminator_brokers_expose_no_live_trade_profile() -> None:
    """Brokers without a runtime paper/live discriminator (Longbridge, Dhan,
    Shoonya) must NOT register any live order-placing profile — the Longbridge
    precedent. A ``*-live-trade`` profile here would be a red-line regression."""
    ids = {p.id for p in profiles.list_profiles()}
    for broker in ("longbridge", "dhan", "shoonya"):
        assert f"{broker}-live-trade" not in ids
        # No live profile for these brokers may advertise an order capability.
        for p in profiles.list_profiles():
            if p.connector == broker and p.environment == "live":
                assert not any(".place" in cap or "requires_mandate" in cap for cap in p.capabilities)


@pytest.mark.parametrize(
    "profile_id, connector, environment",
    [
        ("tiger-paper-sdk", "tiger", "paper"),
        ("tiger-live-sdk-readonly", "tiger", "live"),
        ("longbridge-paper-sdk", "longbridge", "paper"),
        ("longbridge-live-sdk-readonly", "longbridge", "live"),
        ("alpaca-paper-sdk", "alpaca", "paper"),
        ("alpaca-live-sdk-readonly", "alpaca", "live"),
        ("okx-paper-sdk", "okx", "paper"),
        ("okx-live-sdk-readonly", "okx", "live"),
        ("binance-paper-sdk", "binance", "paper"),
        ("binance-live-sdk-readonly", "binance", "live"),
        ("futu-paper-sdk", "futu", "paper"),
        ("futu-live-sdk-readonly", "futu", "live"),
        ("dhan-paper-sdk", "dhan", "paper"),
        ("dhan-live-sdk-readonly", "dhan", "live"),
        ("shoonya-paper-sdk", "shoonya", "paper"),
        ("shoonya-live-sdk-readonly", "shoonya", "live"),
    ],
)
def test_sdk_profiles_are_readonly_broker_sdk(profile_id, connector, environment) -> None:
    """Layer A profiles are broker_sdk transport and strictly read-only."""
    profile = profiles.profile_by_id(profile_id)
    assert profile.connector == connector
    assert profile.environment == environment
    assert profile.transport == "broker_sdk"
    assert profile.readonly is True
    # No order-placing / mandate-gated capability is advertised in Layer A.
    assert not any(".place" in cap or "requires_mandate" in cap for cap in profile.capabilities)


# --------------------------------------------------------------------------- #
# Tiger paper/live identity guard (17-digit account rule)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "account, is_paper",
    [
        ("20191106192858300", True),   # 17-digit paper
        ("51230321", False),            # prime/standard
        ("U12300123", False),           # global
        ("", False),
        ("2019110619285830", False),    # 16 digits
        ("201911061928583000", False),  # 18 digits
    ],
)
def test_tiger_is_paper_account(account, is_paper) -> None:
    assert tg.is_paper_account(account) is is_paper


def test_tiger_paper_profile_rejects_live_account() -> None:
    """A paper profile pointed at a non-17-digit account fails closed."""
    cfg = tg.TigerConfig(tiger_id="x", private_key_path="x", account="U12300123", profile="paper")
    with pytest.raises(tg.TigerProfileMismatchError):
        tg._assert_profile(cfg)


def test_tiger_live_profile_rejects_paper_account() -> None:
    """A live profile pointed at a 17-digit paper account fails closed."""
    cfg = tg.TigerConfig(tiger_id="x", private_key_path="x", account="20191106192858300", profile="live-readonly")
    with pytest.raises(tg.TigerProfileMismatchError):
        tg._assert_profile(cfg)


def test_tiger_paper_profile_accepts_paper_account() -> None:
    cfg = tg.TigerConfig(tiger_id="x", private_key_path="x", account="20191106192858300", profile="paper")
    tg._assert_profile(cfg)  # must not raise


# --------------------------------------------------------------------------- #
# Config resolution
# --------------------------------------------------------------------------- #


def test_tiger_build_config_keeps_profile_credentials_atomic(monkeypatch, tmp_path) -> None:
    """Ignore request-level account overrides when building Tiger config."""
    monkeypatch.setattr(tg, "get_runtime_root", lambda: tmp_path)
    (tmp_path / "tiger.json").write_text(
        json.dumps({"account": "20191106192858300"}),
        encoding="utf-8",
    )
    cfg = tg.build_config({"profile": "paper"}, {"account": "U12300123"})
    assert cfg.profile == "paper"
    assert cfg.account == "20191106192858300"


def test_tiger_save_config_closes_descriptor_before_fdopen_failure(
    monkeypatch, tmp_path
) -> None:
    """Close the temporary descriptor when setup fails before fdopen owns it."""
    monkeypatch.setattr(tg, "get_runtime_root", lambda: tmp_path)
    real_close = tg.os.close
    closed: list[int] = []

    def close_descriptor(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    def fail_fchmod(descriptor: int, mode: int) -> None:
        del descriptor, mode
        raise OSError("permission failure")

    monkeypatch.setattr(tg.os, "close", close_descriptor)
    monkeypatch.setattr(tg.os, "fchmod", fail_fchmod)

    with pytest.raises(OSError, match="permission failure"):
        tg.save_config(tg.TigerConfig(profile="paper"))

    assert len(closed) == 1
    assert not list(tmp_path.glob(".tiger-*"))


def test_tiger_invalid_profile_rejected() -> None:
    with pytest.raises(tg.TigerConfigError):
        tg.TigerConfig.from_mapping({"profile": "live-trade-now"})


def test_tiger_client_rejects_conflicting_sdk_environment(monkeypatch) -> None:
    """Reject SDK environment variables that conflict with managed credentials."""
    monkeypatch.setenv("TIGEROPEN_PROPS_PATH", "/tmp/untrusted-tiger-config")
    with pytest.raises(tg.TigerConfigError, match="environment variables are not allowed"):
        tg._client_config(_tiger_paper_config())


def test_longbridge_build_config_and_region(monkeypatch, tmp_path) -> None:
    for env_name in (
        "LONGBRIDGE_APP_KEY",
        "LONGBRIDGE_APP_SECRET",
        "LONGBRIDGE_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(lb, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb_credentials, "get_runtime_root", lambda: tmp_path)
    cfg = lb.build_config({"profile": "live-readonly", "region": "cn"}, None)
    assert cfg.profile == "live-readonly"
    assert cfg.region == "cn"


def test_longbridge_invalid_region_rejected() -> None:
    with pytest.raises(lb.LongbridgeConfigError):
        lb.LongbridgeConfig.from_mapping({"region": "moon"})


def test_longbridge_with_overrides_preserves_atomic_credentials() -> None:
    cfg = lb.LongbridgeConfig(
        app_key="atomic-key",
        app_secret="atomic-secret",
        access_token="atomic-token",
        _credential_source="environment",
    )

    updated = cfg.with_overrides(
        app_key="ignored-key", profile="live-readonly", region="cn"
    )

    assert (updated.app_key, updated.app_secret, updated.access_token) == (
        "atomic-key",
        "atomic-secret",
        "atomic-token",
    )
    assert updated._credential_source == "environment"
    assert updated.profile == "live-readonly"
    assert updated.region == "cn"


def test_longbridge_public_config_redacts_secrets() -> None:
    """Secret material must never appear in status payloads or config reprs."""
    values = {
        "app_key": "repr-distinctive-app-key-7f31",
        "app_secret": "repr-distinctive-app-secret-8a42",
        "access_token": "repr-distinctive-access-token-9b53",
    }
    cfg = lb.LongbridgeConfig(**values)
    pub = lb._public_config(cfg)
    assert pub["app_secret"] == "***redacted***"
    assert pub["access_token"] == "***redacted***"
    assert pub["app_key"].endswith("***")
    assert all(value not in repr(cfg) for value in values.values())
    assert all(value not in repr(pub) for value in values.values())


def _set_longbridge_environment(monkeypatch, values) -> None:
    for field, env_name in {
        "app_key": "LONGBRIDGE_APP_KEY",
        "app_secret": "LONGBRIDGE_APP_SECRET",
        "access_token": "LONGBRIDGE_ACCESS_TOKEN",
    }.items():
        monkeypatch.setenv(env_name, values[field])


def test_connector_uses_environment_credentials(monkeypatch, tmp_path) -> None:
    values = {
        "app_key": "connector-environment-key",
        "app_secret": "connector-environment-secret",
        "access_token": "connector-environment-token",
    }
    _set_longbridge_environment(monkeypatch, values)
    monkeypatch.setattr(lb, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb_credentials, "get_runtime_root", lambda: tmp_path)

    cfg = lb.build_config({"profile": "live-readonly", "region": "cn"}, None)

    assert (cfg.app_key, cfg.app_secret, cfg.access_token) == tuple(values.values())
    assert cfg.profile == "live-readonly"
    assert cfg.region == "cn"
    monkeypatch.setattr(lb, "longbridge_available", lambda: False)
    assert lb.check_status(cfg)["credential_source"] == "environment"


def test_loader_and_connector_resolve_same_source(monkeypatch, tmp_path) -> None:
    values = {
        "app_key": "shared-file-key",
        "app_secret": "shared-file-secret",
        "access_token": "shared-file-token",
    }
    for env_name in (
        "LONGBRIDGE_APP_KEY",
        "LONGBRIDGE_APP_SECRET",
        "LONGBRIDGE_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(env_name, raising=False)
    (tmp_path / "longbridge.json").write_text(json.dumps(values), encoding="utf-8")
    monkeypatch.setattr(lb, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb_credentials, "get_runtime_root", lambda: tmp_path)

    connector = lb.build_config()
    loader = longbridge_loader.LongbridgeLoader()

    assert (connector.app_key, connector.app_secret, connector.access_token) == (
        loader._app_key,
        loader._app_secret,
        loader._access_token,
    )
    monkeypatch.setattr(lb, "longbridge_available", lambda: False)
    assert lb.check_status(connector)["credential_source"] == "runtime_file"
    assert loader._credential_source == "runtime_file"


def test_connector_reports_conflict_without_sdk_call(monkeypatch, tmp_path) -> None:
    environment = {
        "app_key": "conflict-environment-key",
        "app_secret": "conflict-environment-secret",
        "access_token": "conflict-environment-token",
    }
    runtime_file = {
        "app_key": "conflict-file-key",
        "app_secret": "conflict-file-secret",
        "access_token": "conflict-file-token",
    }
    _set_longbridge_environment(monkeypatch, environment)
    (tmp_path / "longbridge.json").write_text(json.dumps(runtime_file), encoding="utf-8")
    monkeypatch.setattr(lb, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb_credentials, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(
        lb,
        "_trade_context",
        lambda cfg: (_ for _ in ()).throw(AssertionError("SDK must not initialize")),
    )

    report = lb.check_status(lb.build_config())

    assert report["configured"] is False
    assert report["connection_state"] == "error"
    assert report["credential_source"] is None
    assert report["error_code"] == "credentials_conflict"
    assert all(
        field in report["error"]
        for field in ("app_key", "app_secret", "access_token")
    )
    with pytest.raises(lb.LongbridgeConfigError, match="sources conflict"):
        lb._require_resolved_config(lb.build_config())


def test_connector_status_redacts_credentials(monkeypatch, tmp_path) -> None:
    values = {
        "app_key": "status-sensitive-key",
        "app_secret": "status-sensitive-secret",
        "access_token": "status-sensitive-token",
    }
    secret_exception = RuntimeError(
        "authentication failed for " + "/".join(values.values())
    )
    _set_longbridge_environment(monkeypatch, values)
    monkeypatch.setattr(lb, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb_credentials, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb, "longbridge_available", lambda: True)
    monkeypatch.setattr(
        lb,
        "_trade_context",
        lambda cfg: SimpleNamespace(
            account_balance=lambda: (_ for _ in ()).throw(secret_exception)
        ),
    )

    report = lb.check_status(lb.build_config())
    serialized = str(report)

    assert report["configured"] is True
    assert report["connection_state"] == "error"
    assert report["error_code"] == "authentication_failed"
    assert report["error"] == "Longbridge authentication failed."
    assert all(value not in serialized for value in values.values())
    assert report["error"].__class__ is str
    assert secret_exception not in _exception_chain_from_payload(report)


def _exception_chain_from_payload(payload) -> tuple[BaseException, ...]:
    """Return exceptions publicly reachable from a returned payload."""
    seen: set[int] = set()
    found: list[BaseException] = []
    pending = list(payload.values()) if isinstance(payload, dict) else [payload]
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if isinstance(value, BaseException):
            found.append(value)
            if value.__cause__ is not None:
                pending.append(value.__cause__)
            if value.__context__ is not None:
                pending.append(value.__context__)
        elif isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, (list, tuple, set)):
            pending.extend(value)
    return tuple(found)


# --------------------------------------------------------------------------- #
# Read/write classification (live gate input)
# --------------------------------------------------------------------------- #


def test_tiger_order_ops_classified_write() -> None:
    for name in ("place_order", "cancel_order", "modify_order"):
        assert TIGER_TOOL_CLASS[name] is ToolClass.WRITE
    for name in ("get_assets", "get_positions", "get_bars"):
        assert TIGER_TOOL_CLASS[name] is ToolClass.READ


def test_longbridge_order_ops_classified_write() -> None:
    for name in ("submit_order", "cancel_order", "replace_order"):
        assert LONGBRIDGE_TOOL_CLASS[name] is ToolClass.WRITE
    for name in ("account_balance", "stock_positions", "candlesticks"):
        assert LONGBRIDGE_TOOL_CLASS[name] is ToolClass.READ


# --------------------------------------------------------------------------- #
# Service dispatch degrades cleanly when nothing is configured
# --------------------------------------------------------------------------- #


def test_service_check_connection_unconfigured_tiger(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(tg, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("tiger-paper-sdk")
    assert result["status"] == "error"
    assert "not configured" in result["error"]
    assert result["connector"] == "tiger"
    assert result["transport"] == "broker_sdk"


def test_service_check_connection_unconfigured_longbridge(monkeypatch, tmp_path) -> None:
    for env_name in (
        "LONGBRIDGE_APP_KEY",
        "LONGBRIDGE_APP_SECRET",
        "LONGBRIDGE_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(lb, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(lb_credentials, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("longbridge-paper-sdk")
    assert result["status"] == "error"
    assert "not configured" in result["error"]
    assert result["connector"] == "longbridge"
    assert result["transport"] == "broker_sdk"


# --------------------------------------------------------------------------- #
# Alpaca
# --------------------------------------------------------------------------- #


def test_alpaca_paper_live_host_and_flag() -> None:
    assert al.AlpacaConfig(profile="paper").is_paper is True
    assert al.AlpacaConfig(profile="paper").host == al.PAPER_HOST
    assert al.AlpacaConfig(profile="live-readonly").is_paper is False
    assert al.AlpacaConfig(profile="live-readonly").host == al.LIVE_HOST


def test_alpaca_invalid_feed_rejected() -> None:
    with pytest.raises(al.AlpacaConfigError):
        al.AlpacaConfig.from_mapping({"feed": "nasdaq"})


def test_alpaca_redacts_secrets() -> None:
    cfg = al.AlpacaConfig(api_key="AKFOURCHARS", secret_key="topsecret")
    pub = al._public_config(cfg)
    assert pub["secret_key"] == "***redacted***"
    assert "topsecret" not in str(pub)
    assert pub["api_key"].endswith("***")


def test_alpaca_classification() -> None:
    assert ALPACA_TOOL_CLASS["submit_order"] is ToolClass.WRITE
    assert ALPACA_TOOL_CLASS["cancel_order_by_id"] is ToolClass.WRITE
    assert ALPACA_TOOL_CLASS["get_account"] is ToolClass.READ


def test_alpaca_service_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(al, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("alpaca-paper-sdk")
    assert result["status"] == "error"
    assert result["connector"] == "alpaca"
    assert result["transport"] == "broker_sdk"


# --------------------------------------------------------------------------- #
# OKX
# --------------------------------------------------------------------------- #


def test_okx_flag_mapping() -> None:
    assert ox.OKXConfig(profile="paper").flag == "1"
    assert ox.OKXConfig(profile="live-readonly").flag == "0"
    assert ox.OKXConfig(profile="live").flag == "0"


def test_okx_redacts_secrets() -> None:
    cfg = ox.OKXConfig(api_key="KEYFOURXX", api_secret="sec", passphrase="pass")
    pub = ox._public_config(cfg)
    assert pub["api_secret"] == "***redacted***"
    assert pub["passphrase"] == "***redacted***"
    assert "sec" not in str(pub) or pub["api_secret"] == "***redacted***"


def test_okx_classification() -> None:
    assert OKX_TOOL_CLASS["place_order"] is ToolClass.WRITE
    assert OKX_TOOL_CLASS["cancel_order"] is ToolClass.WRITE
    assert OKX_TOOL_CLASS["get_account_balance"] is ToolClass.READ


def test_okx_service_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ox, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("okx-paper-sdk")
    assert result["status"] == "error"
    assert result["connector"] == "okx"


# --------------------------------------------------------------------------- #
# Binance
# --------------------------------------------------------------------------- #


def test_binance_testnet_host_mapping() -> None:
    assert bn.BinanceConfig(profile="paper").is_testnet is True
    assert "testnet" in bn.BinanceConfig(profile="paper").host
    assert bn.BinanceConfig(profile="live-readonly").is_testnet is False
    assert bn.BinanceConfig(profile="live-readonly").host == "https://api.binance.com"


def test_binance_classification() -> None:
    assert BINANCE_TOOL_CLASS["create_order"] is ToolClass.WRITE
    assert BINANCE_TOOL_CLASS["cancel_order"] is ToolClass.WRITE
    assert BINANCE_TOOL_CLASS["fetch_balance"] is ToolClass.READ


def test_binance_service_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(bn, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("binance-paper-sdk")
    assert result["status"] == "error"
    assert result["connector"] == "binance"


# --------------------------------------------------------------------------- #
# Futu (local OpenD gateway)
# --------------------------------------------------------------------------- #


def test_futu_trd_env_mapping() -> None:
    assert ft.FutuConfig(profile="paper").trd_env_name == "SIMULATE"
    assert ft.FutuConfig(profile="live-readonly").trd_env_name == "REAL"


def test_futu_classification() -> None:
    assert FUTU_TOOL_CLASS["place_order"] is ToolClass.WRITE
    assert FUTU_TOOL_CLASS["modify_order"] is ToolClass.WRITE
    assert FUTU_TOOL_CLASS["unlock_trade"] is ToolClass.WRITE
    assert FUTU_TOOL_CLASS["position_list_query"] is ToolClass.READ


def test_futu_service_unconfigured_gateway_down(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ft, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("futu-paper-sdk")
    # OpenD gateway is not running in CI → clean error, not a crash.
    assert result["status"] == "error"
    assert result["connector"] == "futu"
    assert result["transport"] == "broker_sdk"


def test_binance_redacts_secrets() -> None:
    cfg = bn.BinanceConfig(api_key="ABCD1234", api_secret="topsecret")
    pub = bn._public_config(cfg)
    assert pub["api_secret"] == "***redacted***"
    assert "topsecret" not in str(pub)
    assert pub["api_key"].endswith("***")


def test_binance_assert_host_consistent_profiles_pass() -> None:
    """Host property is the guard: paper→testnet host, live→api.binance.com.

    The host is derived from the profile (paper→``testnet_host``,
    live→``api.binance.com``), so a paper profile structurally cannot resolve to
    the live host. ``_assert_host`` is defense-in-depth over that derivation and
    must accept both consistent profiles without raising.
    """
    bn._assert_host(bn.BinanceConfig(profile="paper"))
    bn._assert_host(bn.BinanceConfig(profile="live-readonly"))
    assert "testnet" in bn.BinanceConfig(profile="paper").host
    assert bn.BinanceConfig(profile="live-readonly").host == "https://api.binance.com"


def test_okx_invalid_profile_rejected() -> None:
    with pytest.raises(ox.OKXConfigError):
        ox.OKXConfig.from_mapping({"profile": "go-live-now"})


# --------------------------------------------------------------------------- #
# Live gate: order ops are WRITE-pinned through the real classifier + registry
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "broker, order_op",
    [
        ("tiger", "place_order"),
        ("longbridge", "submit_order"),
        ("alpaca", "submit_order"),
        ("okx", "place_order"),
        ("binance", "create_order"),
        ("futu", "place_order"),
        ("dhan", "place_order"),
        ("shoonya", "place_order"),
    ],
)
def test_order_ops_write_pinned_via_registry(broker, order_op) -> None:
    """Every broker's order op resolves WRITE through the shared classifier."""
    from src.live import registry
    from src.live.classification import classify_tool

    curated = registry._BROKER_CURATED_MAPS[broker]
    assert classify_tool(order_op, None, curated) is ToolClass.WRITE


def test_unknown_op_does_not_classify_read() -> None:
    """An unmapped op resolves to UNKNOWN (never READ); the registry then treats
    UNKNOWN as WRITE (fail-closed) when wrapping the live channel."""
    from src.live import registry
    from src.live.classification import classify_tool

    curated = registry._BROKER_CURATED_MAPS["okx"]
    verdict = classify_tool("some_unmapped_future_tool", None, curated)
    assert verdict is not ToolClass.READ
    assert verdict in (ToolClass.WRITE, ToolClass.UNKNOWN)


# --------------------------------------------------------------------------- #
# Period mapping (generic token → per-SDK token)
# --------------------------------------------------------------------------- #


def test_period_maps_distinguish_minute_from_month() -> None:
    """The 1m (minute) vs 1M (month) tokens must not collide in any map."""
    assert tg._PERIOD_MAP["1m"] == "1min" and tg._PERIOD_MAP["1M"] == "month"
    assert ox._BAR_MAP["1m"] == "1m" and ox._BAR_MAP["1M"] == "1M"
    assert ft._KLTYPE_MAP["1m"] == "K_1M" and ft._KLTYPE_MAP["1M"] == "K_MON"


# --------------------------------------------------------------------------- #
# Read-path mapping with stubbed SDK clients (no broker SDK installed)
# --------------------------------------------------------------------------- #


class _FakeLbTrade:
    def today_orders(self):
        return [
            {"order_id": "1", "symbol": "700.HK", "status": "NewStatus", "quantity": 100},
            {"order_id": "2", "symbol": "700.HK", "status": "FilledStatus", "quantity": 100},
            {"order_id": "3", "symbol": "AAPL.US", "status": "CanceledStatus", "quantity": 5},
        ]


def test_longbridge_open_orders_filters_terminal(monkeypatch) -> None:
    monkeypatch.setattr(lb, "_trade_context", lambda cfg: _FakeLbTrade())
    out = lb.get_open_orders(lb.LongbridgeConfig(app_key="k", app_secret="s", access_token="t"))
    ids = [o["order_id"] for o in out["open_orders"]]
    assert ids == ["1"]  # filled + cancelled dropped


def test_longbridge_status_normalization_variants() -> None:
    """Terminal-status filtering must work across SDK string forms."""
    for terminal in ("Filled", "FilledStatus", "OrderStatus.Filled", "CANCELED", "Rejected"):
        assert not lb._is_open_order({"status": terminal})
    for live in ("NewStatus", "PartialFilledStatus", "PartialFilled", "WaitToNew"):
        assert lb._is_open_order({"status": live})


class _FakeTigerQuote:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get_bars(self, symbols, period=None, limit=None):
        self.calls.append({"period": period, "limit": limit})
        return []


def test_tiger_history_month_does_not_collapse_to_minute(monkeypatch) -> None:
    """Regression: ``1M`` (month) must map to ``month``, not ``1min``."""
    fake = _FakeTigerQuote()
    monkeypatch.setattr(tg, "_quote_client", lambda cfg: fake)
    monkeypatch.setattr(tg, "_assert_profile", lambda cfg: None)
    cfg = tg.TigerConfig(tiger_id="x", private_key_path="x", account="20191106192858300", profile="paper")
    tg.get_historical_bars("AAPL", config=cfg, period="1M", limit=12)
    assert fake.calls[-1]["period"] == "month"
    assert fake.calls[-1]["limit"] == 12


def test_trading_history_tool_exposes_period_and_limit() -> None:
    from src.tools.trading_connector_tool import TradingHistoryTool

    props = TradingHistoryTool.parameters["properties"]
    assert "period" in props and "limit" in props


class _FakeOkxMarket:
    def get_candlesticks(self, instId=None, bar=None, limit=None):
        return {"code": "0", "data": [["1700000000000", "100", "110", "90", "105", "12", "1200", "1200", "1"]]}


def test_okx_history_maps_candles_and_period(monkeypatch) -> None:
    monkeypatch.setattr(ox, "_market_client", lambda cfg: _FakeOkxMarket())
    out = ox.get_historical_bars("BTC-USDT", config=ox.OKXConfig(api_key="k", api_secret="s", passphrase="p"), period="1h")
    assert out["period"] == "1h" and out["bar"] == "1H"
    assert len(out["bars"]) == 1
    bar = out["bars"][0]
    assert bar["open"] == "100" and bar["close"] == "105" and bar["confirm"] == "1"


# --------------------------------------------------------------------------- #
# Dhan + Shoonya: structural paper-only cap (no runtime discriminator)
#
# Like Longbridge, these brokers expose no sandbox / no runtime paper/live
# discriminator (same token/login reaches the same real account). The order
# path is therefore structurally capped at paper: any non-paper config is
# refused at the first line, so a flipped ``profile`` override can never reach a
# live order. Paper orders are simulated locally (neither broker has a sandbox).
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mod, Config", [(dh, dh.DhanConfig), (sh, sh.ShoonyaConfig)])
@pytest.mark.parametrize("profile", ["live", "live-readonly"])
def test_in_broker_place_order_refuses_non_paper(mod, Config, profile) -> None:
    """A non-paper config is refused before any SDK call (fail-closed)."""
    result = mod.place_order(Config(profile=profile), symbol="RELIANCE", side="buy", quantity=1)
    assert result["status"] == "error"
    assert "paper-only" in result["error"]


@pytest.mark.parametrize("mod, Config", [(dh, dh.DhanConfig), (sh, sh.ShoonyaConfig)])
def test_in_broker_cancel_order_refuses_non_paper(mod, Config) -> None:
    result = mod.cancel_order(Config(profile="live"), "ORD1")
    assert result["status"] == "error"
    assert "paper-only" in result["error"]


@pytest.mark.parametrize("mod, Config", [(dh, dh.DhanConfig), (sh, sh.ShoonyaConfig)])
def test_in_broker_paper_place_order_simulated_locally(mod, Config) -> None:
    """Paper config simulates locally — no real money, no SDK call."""
    result = mod.place_order(Config(profile="paper"), symbol="RELIANCE", side="buy", quantity=10)
    assert result["status"] == "ok"
    assert result["is_paper"] is True
    assert result["order_status"] == "simulated_fill"
    assert result["paper_guard"] == "simulated_locally"


@pytest.mark.parametrize("mod, Config", [(dh, dh.DhanConfig), (sh, sh.ShoonyaConfig)])
def test_in_broker_paper_cancel_order_simulated(mod, Config) -> None:
    result = mod.cancel_order(Config(profile="paper"), "ORD1")
    assert result["status"] == "ok"
    assert result["cancelled"] is True
    assert result["is_paper"] is True


def test_in_broker_order_ops_classified_write() -> None:
    for name in ("place_order", "modify_order", "cancel_order"):
        assert DHAN_TOOL_CLASS[name] is ToolClass.WRITE
        assert SHOONYA_TOOL_CLASS[name] is ToolClass.WRITE
    for name in ("get_positions", "get_holdings"):
        assert DHAN_TOOL_CLASS[name] is ToolClass.READ
        assert SHOONYA_TOOL_CLASS[name] is ToolClass.READ


def test_dhan_redacts_access_token() -> None:
    cfg = dh.DhanConfig(client_id="C1", access_token="tok-abcdefgh-secret")
    pub = dh._public_config(cfg)
    assert "secret" not in str(pub)
    assert pub["access_token"].endswith("***")


def test_shoonya_redacts_secrets() -> None:
    cfg = sh.ShoonyaConfig(
        user_id="USER1", password="pw", vendor_code="V", api_secret="sec", totp_secret="totp"
    )
    pub = sh._public_config(cfg)
    for secret in ("password", "api_secret", "totp_secret"):
        assert pub[secret] == "***redacted***"
    assert "sec" not in str(pub) or pub["api_secret"] == "***redacted***"
    assert pub["user_id"].endswith("***")


def test_dhan_invalid_profile_rejected() -> None:
    with pytest.raises(dh.DhanConfigError):
        dh.DhanConfig.from_mapping({"profile": "go-live"})


def test_shoonya_invalid_profile_rejected() -> None:
    with pytest.raises(sh.ShoonyaConfigError):
        sh.ShoonyaConfig.from_mapping({"profile": "go-live"})


def test_dhan_service_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dh, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("dhan-paper-sdk")
    assert result["status"] == "error"
    assert result["connector"] == "dhan"
    assert result["transport"] == "broker_sdk"


def test_shoonya_service_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sh, "get_runtime_root", lambda: tmp_path)
    result = service.check_connection("shoonya-paper-sdk")
    assert result["status"] == "error"
    assert result["connector"] == "shoonya"
    assert result["transport"] == "broker_sdk"


# --------------------------------------------------------------------------- #
# Tiger official config and extended read APIs
# --------------------------------------------------------------------------- #


def _tiger_paper_config() -> tg.TigerConfig:
    return tg.TigerConfig(
        tiger_id="test-tiger-id",
        private_key_path="/tmp/test-tiger-key.pem",
        account="20191106192858300",
        profile="paper",
    )


def test_tiger_loads_official_properties_from_runtime_keys(monkeypatch, tmp_path) -> None:
    """Load official Tiger properties from the runtime keys directory."""
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    props = keys_dir / "tiger_openapi_config.properties"
    props.write_text(
        "tiger_id=test-tiger-id\n"
        "account=20191106192858300\n"
        "private_key_pk1=private-material-must-not-leak\n"
        "license=TBNZ\n"
        "env=PROD\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tg, "get_runtime_root", lambda: tmp_path)

    cfg = tg.load_config()

    assert cfg.properties_path == str(props)
    assert cfg.credential_source == "official_properties"
    assert cfg.tiger_id == "test-tiger-id"
    assert cfg.account == "20191106192858300"
    assert "private-material" not in repr(cfg)
    assert "private-material" not in json.dumps(tg._public_config(cfg))


def test_tiger_client_rejects_properties_identity_changed_after_validation(
    monkeypatch, tmp_path
) -> None:
    """Reject official properties whose identity changes after validation."""
    props = tmp_path / "tiger_openapi_config.properties"
    props.write_text(
        "tiger_id=original-id\n"
        "account=20191106192858300\n"
        "private_key_pk1=original-key\n",
        encoding="utf-8",
    )
    cfg = tg.TigerConfig(
        tiger_id="original-id",
        account="20191106192858300",
        properties_path=str(props),
        profile="paper",
    )
    monkeypatch.setattr(tg, "get_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(
        tg,
        "_properties_values",
        lambda path: {
            "tiger_id": "replacement-id",
            "account": "12345678",
            "private_key_pk1": "replacement-key",
        },
    )

    with pytest.raises(tg.TigerConfigError, match="identity changed"):
        tg._client_config(cfg)


def test_tiger_runtime_json_can_point_to_official_properties(monkeypatch, tmp_path) -> None:
    """Resolve official properties referenced by runtime JSON configuration."""
    props_dir = tmp_path / "official"
    props_dir.mkdir()
    props = props_dir / "tiger_openapi_config.properties"
    props.write_text(
        "tiger_id=official-id\naccount=20191106192858300\nprivate_key_pk1=secret\n",
        encoding="utf-8",
    )
    (tmp_path / "tiger.json").write_text(
        json.dumps({"properties_path": str(props_dir), "profile": "paper"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(tg, "get_runtime_root", lambda: tmp_path)

    cfg = tg.load_config()

    assert cfg.properties_path == str(props)
    assert cfg.tiger_id == "official-id"
    assert cfg.account == "20191106192858300"


def test_tiger_rejects_properties_outside_trusted_user_roots(monkeypatch, tmp_path) -> None:
    """Reject Tiger properties outside trusted user credential roots."""
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    untrusted = tmp_path / "workspace" / "tiger_openapi_config.properties"
    untrusted.parent.mkdir()
    untrusted.write_text("tiger_id=x\naccount=12345\nprivate_key_pk1=secret\n", encoding="utf-8")
    (runtime_root / "tiger.json").write_text(
        json.dumps({"properties_path": str(untrusted)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(tg, "get_runtime_root", lambda: runtime_root)

    with pytest.raises(tg.TigerConfigError, match="trusted user credential directory"):
        tg.load_config()


class _ExtendedTigerQuote:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get_option_expirations(self, symbols, market=None):
        self.calls.append(("expirations", {"symbols": symbols, "market": market}))
        return pd.DataFrame([{"symbol": "AAPL", "date": "2026-09-18", "timestamp": 1789696800000}])

    def get_option_chain(self, symbol, expiry, **kwargs):
        self.calls.append(("chain", {"symbol": symbol, "expiry": expiry, **kwargs}))
        return pd.DataFrame([{"identifier": "AAPL  260918C00200000", "strike": 200.0, "put_call": "CALL"}])

    def get_option_symbols(self, market=None, lang=None):
        self.calls.append(("option_symbols", {"market": market, "lang": lang}))
        return pd.DataFrame([{"symbol": "TCH.HK", "underlying_symbol": "00700"}])

    def get_option_briefs(self, identifiers, market=None, timezone=None):
        self.calls.append(
            ("option_briefs", {"identifiers": identifiers, "market": market, "timezone": timezone})
        )
        return pd.DataFrame([{"identifier": identifiers[0], "latest_price": 12.5}])

    def get_option_bars(self, identifiers, **kwargs):
        self.calls.append(("option_bars", {"identifiers": identifiers, **kwargs}))
        return pd.DataFrame([{"identifier": identifiers[0], "close": 12.5}])

    def get_option_depth(self, identifiers, market=None, timezone=None):
        self.calls.append(
            ("option_depth", {"identifiers": identifiers, "market": market, "timezone": timezone})
        )
        return {identifiers[0]: {"asks": [(12.6, 10)], "bids": [(12.4, 8)]}}

    def get_option_trade_ticks(self, identifiers, timezone=None):
        self.calls.append(("option_ticks", {"identifiers": identifiers, "timezone": timezone}))
        return pd.DataFrame([{"identifier": identifiers[0], "price": 12.5}])

    def get_option_timeline(self, identifiers, market=None, begin_time=None, timezone=None):
        self.calls.append(
            (
                "option_timeline",
                {
                    "identifiers": identifiers,
                    "market": market,
                    "begin_time": begin_time,
                    "timezone": timezone,
                },
            )
        )
        return pd.DataFrame([{"identifier": identifiers[0], "price": 12.5}])

    def get_option_analysis(self, symbols, **kwargs):
        self.calls.append(("option_analysis", {"symbols": symbols, **kwargs}))
        return [SimpleNamespace(symbol="AAPL", implied_vol_30_days=0.25)]

    def get_market_status(self, market=None):
        self.calls.append(("status", {"market": market}))
        return [SimpleNamespace(market=market, trading_status="TRADING", open_time="09:30")]

    def get_trading_calendar(self, market, begin_date=None, end_date=None):
        self.calls.append(("calendar", {"market": market, "begin_date": begin_date, "end_date": end_date}))
        return [{"date": "2026-07-28", "type": "TRADING"}]

    def get_depth_quote(self, symbols, market, trade_session=None):
        self.calls.append(
            ("depth", {"symbols": symbols, "market": market, "trade_session": trade_session})
        )
        return {"AAPL": {"bid": [{"price": 199.9, "volume": 10}], "ask": [{"price": 200.1, "volume": 12}]}}

    def get_trade_ticks(self, symbols, **kwargs):
        self.calls.append(("ticks", {"symbols": symbols, **kwargs}))
        return pd.DataFrame([{"symbol": "AAPL", "price": 200.0, "volume": 5, "time": 1785258000000}])


def test_tiger_extended_quote_reads_are_json_serializable(monkeypatch) -> None:
    """Return JSON-serializable payloads from extended quote reads."""
    quote = _ExtendedTigerQuote()
    monkeypatch.setattr(tg, "_quote_client", lambda cfg: quote)
    cfg = _tiger_paper_config()

    identifier = "AAPL  260918C00200000"
    payloads = [
        tg.get_option_expirations(["AAPL", "TSLA"], config=cfg, market="US"),
        tg.get_option_chain(
            "AAPL",
            "2026-09-18",
            config=cfg,
            market="US",
            return_greeks=True,
            option_filter={
                "delta_min": 0.2,
                "open_interest_min": 100,
                "in_the_money": True,
            },
        ),
        tg.get_option_symbols(config=cfg, market="HK", lang="zh_CN"),
        tg.get_option_briefs([identifier], config=cfg, market="US", timezone="US/Eastern"),
        tg.get_option_bars(
            [identifier],
            config=cfg,
            market="US",
            period="day",
            begin_time="2026-07-01",
            end_time="2026-07-31",
            limit=30,
            sort_dir="DESC",
        ),
        tg.get_option_depth([identifier], config=cfg, market="US"),
        tg.get_option_trade_ticks([identifier], config=cfg, timezone="US/Eastern"),
        tg.get_option_timeline(
            [identifier], config=cfg, market="US", begin_time="2026-07-28", timezone="US/Eastern"
        ),
        tg.get_option_analysis(
            ["AAPL"], config=cfg, market="US", period="52week", require_volatility_list=True
        ),
        tg.get_market_status(config=cfg, market="US"),
        tg.get_trading_calendar(config=cfg, market="US", begin_date="2026-07-01", end_date="2026-07-31"),
        tg.get_depth_quote("AAPL", config=cfg, market="US", trade_session="regular"),
        tg.get_trade_ticks("AAPL", config=cfg, trade_session="regular", limit=50),
    ]

    for payload in payloads:
        assert payload["status"] == "ok"
        json.dumps(payload, allow_nan=False)
    assert payloads[0]["expirations"][0]["date"] == "2026-09-18"
    assert payloads[1]["options"][0]["strike"] == 200.0
    assert payloads[2]["symbols"][0]["underlying_symbol"] == "00700"
    assert payloads[3]["options"][0]["latest_price"] == 12.5
    assert payloads[4]["bars"][0]["close"] == 12.5
    assert payloads[8]["analysis"][0]["symbol"] == "AAPL"
    assert payloads[-1]["ticks"][0]["price"] == 200.0
    assert quote.calls[0][1]["symbols"] == ["AAPL", "TSLA"]
    assert vars(quote.calls[1][1]["option_filter"])["delta_min"] == 0.2
    assert quote.calls[11][1]["symbols"] == ["AAPL"]
    assert quote.calls[12][1]["symbols"] == ["AAPL"]


def test_tiger_option_expirations_preserve_single_symbol_response(monkeypatch) -> None:
    """Keep the legacy symbol field for scalar expiration queries."""
    quote = _ExtendedTigerQuote()
    monkeypatch.setattr(tg, "_quote_client", lambda cfg: quote)

    result = tg.get_option_expirations("aapl", config=_tiger_paper_config())

    assert result["symbol"] == "AAPL"
    assert result["symbols"] == ["AAPL"]


def test_tiger_option_reads_reject_unsafe_batch_and_filter_inputs(monkeypatch) -> None:
    """Bound option batches and reject unknown OptionFilter fields."""
    quote = _ExtendedTigerQuote()
    monkeypatch.setattr(tg, "_quote_client", lambda cfg: quote)
    cfg = _tiger_paper_config()

    with pytest.raises(ValueError, match="at most 30"):
        tg.get_option_expirations([f"SYM{index}" for index in range(31)], config=cfg)
    with pytest.raises(ValueError, match="at most 30"):
        tg.get_option_briefs([f"OPT{index}" for index in range(31)], config=cfg)
    with pytest.raises(ValueError, match="unsupported option filter"):
        tg.get_option_chain(
            "AAPL",
            "2026-09-18",
            config=cfg,
            option_filter={"private_key": "not-allowed"},
        )


def test_tiger_option_contract_and_exercise_check_are_read_only(monkeypatch) -> None:
    """Query option contracts and exercise eligibility without mutations."""

    class TradeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def get_contract(self, **kwargs):  # noqa: ANN003, ANN201
            self.calls.append(("contract", kwargs))
            return SimpleNamespace(contract_id=123, symbol="AAPL", sec_type="OPT")

        def get_derivative_contracts(self, **kwargs):  # noqa: ANN003, ANN201
            self.calls.append(("derivatives", kwargs))
            return [SimpleNamespace(contract_id=123, symbol="AAPL", sec_type="OPT")]

        def check_option_exercise(self, **kwargs):  # noqa: ANN003, ANN201
            self.calls.append(("exercise_check", kwargs))
            return SimpleNamespace(can_exercise=True, account="20191106192858300")

    trade = TradeClient()
    monkeypatch.setattr(tg, "_trade_client", lambda cfg: trade)
    cfg = _tiger_paper_config()

    contract = tg.get_option_contract(
        "AAPL",
        config=cfg,
        expiry="20260918",
        strike=200.0,
        put_call="CALL",
        currency="USD",
    )
    derivatives = tg.get_option_derivative_contracts(
        "AAPL", "20260918", config=cfg, sec_type="OPT", lang="en_US"
    )
    check = tg.query_account_domain(
        "portfolio",
        "option_exercise_check",
        config=cfg,
        contract_id=123,
        exercise_type="EARLY",
        quantity=1,
    )

    assert contract["contract"]["contract_id"] == 123
    assert derivatives["contracts"][0]["sec_type"] == "OPT"
    assert check["data"]["can_exercise"] is True
    assert "20191106192858300" not in json.dumps(check)
    assert trade.calls[0][1]["sec_type"] == "OPT"
    assert trade.calls[2][1]["account"] == "20191106192858300"
    assert all("secret_key" not in params for _, params in trade.calls)


def test_tiger_quote_client_is_reused_per_credential_identity(monkeypatch) -> None:
    """Create and permission-grab one QuoteClient per credential identity."""
    created: list[object] = []

    class QuoteClient:
        def __init__(self, config) -> None:  # noqa: ANN001
            self.config = config
            created.append(config)

    monkeypatch.setattr("tigeropen.quote.quote_client.QuoteClient", QuoteClient)
    monkeypatch.setattr(tg, "_client_config", lambda cfg: SimpleNamespace(account=cfg.account))
    tg._clear_quote_client_cache()
    first = _tiger_paper_config()
    second = tg.TigerConfig(
        tiger_id=first.tiger_id,
        private_key_path=first.private_key_path,
        account="20191106192858301",
        profile="paper",
    )

    assert tg._quote_client(first) is tg._quote_client(first)
    assert tg._quote_client(second) is not tg._quote_client(first)
    assert len(created) == 2
    tg._clear_quote_client_cache()


def test_tiger_quote_client_cache_is_bounded(monkeypatch) -> None:
    """Bound cached quote clients across repeated account/profile changes."""
    created: list[object] = []

    class QuoteClient:
        def __init__(self, config) -> None:  # noqa: ANN001
            created.append(config)

    monkeypatch.setattr("tigeropen.quote.quote_client.QuoteClient", QuoteClient)
    monkeypatch.setattr(tg, "_client_config", lambda cfg: SimpleNamespace(account=cfg.account))
    tg._clear_quote_client_cache()

    first = _tiger_paper_config()
    for index in range(tg._QUOTE_CLIENT_CACHE_MAXSIZE + 4):
        cfg = tg.TigerConfig(
            tiger_id=first.tiger_id,
            private_key_path=first.private_key_path,
            account=f"2019110619285{index:04d}",
            profile="paper",
        )
        tg._quote_client(cfg)

    assert len(created) == tg._QUOTE_CLIENT_CACHE_MAXSIZE + 4
    assert len(tg._QUOTE_CLIENT_CACHE) == tg._QUOTE_CLIENT_CACHE_MAXSIZE
    tg._clear_quote_client_cache()


def test_tiger_json_safe_normalizes_pandas_missing_values() -> None:
    """Normalize pandas missing values into JSON-safe nulls."""
    payload = tg._records(pd.DataFrame([{"a": pd.NA, "b": pd.NaT, "c": float("nan")}]))
    assert payload == [{"a": None, "b": None, "c": None}]
    json.dumps(payload, allow_nan=False)


class _ExtendedTigerTrade:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get_orders(self, **kwargs):
        self.calls.append(("orders", kwargs))
        contract = SimpleNamespace(symbol="AAPL", currency="USD", sec_type="STK", market="US")
        rows = [
            SimpleNamespace(
                id=101,
                order_id=11,
                contract=contract,
                action="BUY",
                order_type="LMT",
                quantity=10,
                filled=10,
                remaining=0,
                avg_fill_price=199.5,
                limit_price=200.0,
                status="FILLED",
                order_time=1785250000000,
                trade_time=1785250100000,
            )
        ]
        return SimpleNamespace(result=rows, next_page_token="orders-next-2")

    def get_transactions(self, **kwargs):
        self.calls.append(("transactions", kwargs))
        contract = SimpleNamespace(symbol="AAPL", currency="USD", sec_type="STK", market="US")
        rows = [
            SimpleNamespace(
                id="TX1",
                order_id=101,
                contract=contract,
                action="BUY",
                filled_quantity=10,
                filled_price=199.5,
                filled_amount=1995.0,
                transacted_at=1785250100000,
            )
        ]
        return SimpleNamespace(result=rows, next_page_token="tx-next-2")


def test_tiger_order_history_and_transactions_forward_filters(monkeypatch) -> None:
    """Forward normalized filters to dedicated order and transaction APIs."""
    trade = _ExtendedTigerTrade()
    monkeypatch.setattr(tg, "_trade_client", lambda cfg: trade)
    cfg = _tiger_paper_config()

    orders = tg.get_order_history(
        config=cfg,
        market="US",
        symbol="AAPL",
        start_time="2026-07-01",
        end_time="2026-07-31",
        limit=50,
        states=["filled", "PartiallyFilled", "cancelled"],
        page_token="orders-next",
    )
    transactions = tg.get_transactions(
        config=cfg,
        market="US",
        symbol="AAPL",
        start_time=1782864000000,
        end_time=1785542399000,
        since_date="2026-07-01",
        to_date="20260731",
        limit=25,
    )

    assert orders["account"] == "201***"
    assert orders["orders"][0]["market"] == "US"
    assert orders["next_page_token"] == "orders-next-2"
    assert transactions["account"] == "201***"
    assert transactions["transactions"][0]["transaction_id"] == "TX1"
    assert transactions["next_page_token"] is None
    assert transactions["pagination_supported"] is False
    assert transactions["truncated"] is True
    assert trade.calls[0][1]["market"] == "US"
    assert trade.calls[0][1]["start_time"] == "2026-07-01"
    assert trade.calls[0][1]["states"] == ["Filled", "PartiallyFilled", "Cancelled"]
    assert trade.calls[0][1]["page_token"] == "orders-next"
    assert trade.calls[1][1]["start_time"] == 1782864000000
    assert trade.calls[1][1]["since_date"] == "20260701"
    assert trade.calls[1][1]["to_date"] == "20260731"
    assert "market" not in trade.calls[1][1]
    assert trade.calls[1][1]["page_token"] == ""


@pytest.mark.parametrize("state", ["unknown", "FILLED_AND_GONE"])
def test_tiger_order_history_rejects_unknown_states(state: str) -> None:
    """Reject unsupported order states in dedicated history queries."""
    with pytest.raises(ValueError, match="unsupported Tiger order state"):
        tg.get_order_history(config=_tiger_paper_config(), states=[state])


@pytest.mark.parametrize("date_value", ["2026/07/01", "2026071", "not-a-date"])
def test_tiger_transactions_reject_invalid_compact_dates(date_value: str) -> None:
    """Reject invalid compact dates in dedicated transaction queries."""
    with pytest.raises(ValueError, match="date must use YYYYMMDD or YYYY-MM-DD"):
        tg.get_transactions(config=_tiger_paper_config(), since_date=date_value)


def test_tiger_execution_payloads_apply_account_redaction(monkeypatch) -> None:
    """Apply account redaction to optional filled-order execution payloads."""

    class TradeClient:
        def __init__(self) -> None:
            self.filled_calls: list[dict] = []

        def get_open_orders(self, **kwargs):  # noqa: ANN003, ANN201
            del kwargs
            return []

        def get_filled_orders(self, **kwargs):  # noqa: ANN003, ANN201
            self.filled_calls.append(kwargs)
            return [SimpleNamespace(id=1, account="20191106192858300")]

    trade = TradeClient()
    monkeypatch.setattr(tg, "_trade_client", lambda cfg: trade)
    result = tg.get_open_orders(_tiger_paper_config(), include_executions=True)

    assert result["executions"][0]["order_id"] == 1
    assert "20191106192858300" not in json.dumps(result)
    start = trade.filled_calls[0]["start_time"]
    end = trade.filled_calls[0]["end_time"]
    assert isinstance(start, int)
    assert isinstance(end, int)
    window = datetime.timedelta(milliseconds=end - start)
    assert datetime.timedelta(days=89) <= window <= datetime.timedelta(days=90)


def test_tiger_write_failures_redact_sdk_exception_details(monkeypatch) -> None:
    """Redact Tiger SDK errors returned by order placement and cancellation."""
    secret = "account=12345678 key=/private/tiger.pem"
    monkeypatch.setattr(tg, "_assert_profile", lambda cfg: None)
    monkeypatch.setattr(
        tg,
        "_trade_client",
        lambda cfg: (_ for _ in ()).throw(ValueError(secret)),
    )
    config = _tiger_paper_config()

    placed = tg.place_order(
        config,
        symbol="AAPL",
        side="buy",
        quantity=1,
    )
    cancelled = tg.cancel_order(config, "123")

    assert placed == {"status": "error", "error": "Tiger connector request failed"}
    assert cancelled == {"status": "error", "error": "Tiger connector request failed"}
    assert secret not in str(placed) + str(cancelled)


def test_tiger_profiles_advertise_extended_reads() -> None:
    """Advertise extended read capabilities on Tiger SDK profiles."""
    expected = {
        "options.symbols.read",
        "options.expirations.read",
        "options.chain.read",
        "options.quotes.read",
        "options.history.read",
        "options.depth.read",
        "options.ticks.read",
        "options.timeline.read",
        "options.analysis.read",
        "options.contracts.read",
        "option.exercise.read",
        "market.status.read",
        "market.calendar.read",
        "market.depth.read",
        "market.ticks.read",
        "orders.history.read",
        "transactions.read",
    }
    for profile_id in ("tiger-paper-sdk", "tiger-live-sdk-readonly"):
        assert expected <= set(profiles.profile_by_id(profile_id).capabilities)


# --------------------------------------------------------------------------- #
# Tiger complete account-domain read surface
# --------------------------------------------------------------------------- #


class _TigerAccountReadClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __getattr__(self, name: str):
        if name.startswith(("get_", "query_")):
            def read_method(**kwargs):
                self.calls.append((name, kwargs))
                return [SimpleNamespace(kind=name, account=kwargs.get("account") or kwargs.get("account_id"))]

            return read_method
        raise AttributeError(name)


@pytest.mark.parametrize(
    ("group", "action", "params", "method"),
    [
        ("account", "managed_accounts", {}, "get_managed_accounts"),
        ("account", "assets", {"segment": True, "market_value": True}, "get_assets"),
        ("account", "prime_assets", {"base_currency": "USD"}, "get_prime_assets"),
        ("account", "aggregate_assets", {"seg_type": "SEC"}, "get_aggregate_assets"),
        ("account", "analytics", {"start_date": "2026-01-01", "end_date": "2026-07-31"}, "get_analytics_asset"),
        ("account", "fund_details", {"seg_types": ["SEC"], "limit": 50}, "get_fund_details"),
        ("account", "funding_history", {"seg_type": "SEC"}, "get_funding_history"),
        ("account", "segment_fund_available", {"from_segment": "SEC", "currency": "USD"}, "get_segment_fund_available"),
        ("account", "segment_fund_history", {"limit": 50}, "get_segment_fund_history"),
        ("portfolio", "positions", {"sec_type": "OPT", "market": "US", "expiry": "2026-09-18"}, "get_positions"),
        ("portfolio", "option_exercise_records", {"page": 1, "size": 20}, "get_option_exercise_records"),
        ("portfolio", "option_exercise_positions", {"exercise_type": "EARLY"}, "get_option_exercise_positions"),
        (
            "portfolio",
            "transfer_records",
            {"since_date": "2026-01-01", "to_date": "2026-07-31"},
            "get_position_transfer_records",
        ),
        (
            "portfolio",
            "transfer_external_records",
            {"since_date": "2026-01-01", "to_date": "2026-07-31"},
            "get_position_transfer_external_records",
        ),
        ("portfolio", "transfer_detail", {"transfer_id": "transfer-1"}, "get_position_transfer_detail"),
        ("activity", "order", {"order_id": 123, "show_charges": True}, "get_order"),
        ("activity", "open_orders", {"market": "US"}, "get_open_orders"),
        ("activity", "filled_orders", {"market": "US"}, "get_filled_orders"),
        ("activity", "cancelled_orders", {"market": "US"}, "get_cancelled_orders"),
    ],
)
def test_tiger_account_domain_read_actions_forward_safe_params(
    monkeypatch,
    group: str,
    action: str,
    params: dict,
    method: str,
) -> None:
    """Forward safe parameters for supported account-domain read actions."""
    client = _TigerAccountReadClient()
    monkeypatch.setattr(tg, "_trade_client", lambda cfg: client)

    result = tg.query_account_domain(group, action, config=_tiger_paper_config(), **params)

    assert result["status"] == "ok"
    assert result["action"] == action
    assert client.calls[0][0] == method
    forwarded = client.calls[0][1]
    assert "secret_key" not in forwarded
    if "account" in tg.TIGER_ACCOUNT_READ_SPECS[group][action].injected_params:
        assert forwarded["account"] == "20191106192858300"
    if "account_id" in tg.TIGER_ACCOUNT_READ_SPECS[group][action].injected_params:
        assert forwarded["account_id"] == "20191106192858300"
    serialized = json.dumps(result, allow_nan=False)
    assert "20191106192858300" not in serialized


def test_tiger_account_read_allowlist_excludes_state_changes() -> None:
    """Exclude history activity actions and mutations from account reads."""
    assert {"orders", "transactions"}.isdisjoint(tg.TIGER_ACCOUNT_READ_SPECS["activity"])
    methods = {
        spec.method
        for actions in tg.TIGER_ACCOUNT_READ_SPECS.values()
        for spec in actions.values()
    }
    assert not methods & {
        "place_order",
        "cancel_order",
        "modify_order",
        "submit_option_exercise",
        "cancel_option_exercise",
        "transfer_position",
    }


def test_tiger_account_domain_rejects_unknown_action() -> None:
    """Reject unsupported account-domain read actions."""
    with pytest.raises(ValueError, match="unsupported Tiger account read action"):
        tg.query_account_domain("account", "place_order", config=_tiger_paper_config())


def test_tiger_account_domain_requires_an_order_identifier() -> None:
    """Require an order identifier for single-order reads."""
    with pytest.raises(ValueError, match="order requires id or order_id"):
        tg.query_account_domain("activity", "order", config=_tiger_paper_config())


@pytest.mark.parametrize("field", ["account", "account_id", "secret_key"])
def test_tiger_account_domain_rejects_credential_and_account_overrides(field: str) -> None:
    """Reject credential and account overrides in account-domain reads."""
    with pytest.raises(ValueError, match="unsupported parameters"):
        tg.query_account_domain(
            "portfolio",
            "positions",
            config=_tiger_paper_config(),
            **{field: "attacker-controlled"},
        )


@pytest.mark.parametrize(
    ("group", "action", "params", "message"),
    [
        ("portfolio", "option_exercise_records", {"page": 0}, "page must be at least 1"),
        ("portfolio", "option_exercise_records", {"size": 101}, "limit must be between 1 and 100"),
        ("account", "fund_details", {"seg_types": ["SEC"], "start": -1}, "start must be non-negative"),
        ("account", "fund_details", {"seg_types": ["SEC"], "limit": 1001}, "limit must be between 1 and 1000"),
    ],
)
def test_tiger_account_domain_rejects_invalid_pagination_bounds(
    group: str,
    action: str,
    params: dict,
    message: str,
) -> None:
    """Reject invalid account-domain pagination bounds."""
    with pytest.raises(ValueError, match=message):
        tg.query_account_domain(group, action, config=_tiger_paper_config(), **params)


def test_tiger_position_normalization_preserves_option_contract_details() -> None:
    """Preserve option contract details during position normalization."""
    contract = SimpleNamespace(
        symbol="AAPL  260918C00200000",
        currency="USD",
        sec_type="OPT",
        expiry="20260918",
        strike=200.0,
        put_call="CALL",
        multiplier=100,
    )
    position = SimpleNamespace(
        contract=contract,
        quantity=2,
        average_cost=12.5,
        market_value=2750.0,
        unrealized_pnl=250.0,
        realized_pnl=10.0,
    )

    result = tg._position_to_dict(position)

    assert result["sec_type"] == "OPT"
    assert result["realized_pnl"] == 10.0
    assert result["contract"] == {
        "symbol": "AAPL  260918C00200000",
        "currency": "USD",
        "sec_type": "OPT",
        "expiry": "20260918",
        "strike": 200.0,
        "put_call": "CALL",
        "multiplier": 100,
    }
