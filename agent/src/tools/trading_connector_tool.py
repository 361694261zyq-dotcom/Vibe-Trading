"""Connector-first trading tools.

Tools take an optional ``connection`` profile id. If omitted, they use the
selected profile from ``~/.vibe-trading/trading-connections.json``.
"""

from __future__ import annotations

import json
from typing import Any

from src.agent.tools import BaseTool
from src.trading.profiles import (
    list_profiles,
    load_selected_profile_id,
    profile_by_id,
    save_selected_profile_id,
)
from src.trading.service import (
    cancel_order,
    check_connection,
    get_account,
    get_history,
    get_open_orders,
    get_positions,
    get_quote,
    get_tiger_depth_quote,
    get_tiger_market_status,
    get_tiger_option_chain,
    get_tiger_option_expirations,
    get_tiger_order_history,
    get_tiger_trade_ticks,
    get_tiger_trading_calendar,
    get_tiger_transactions,
    place_order,
    query_tiger_account_domain,
)


def _json_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _connection(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _num_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _tiger_read_error() -> str:
    return "Tiger connector request failed"


TRADING_COMMON_PARAMETERS = {
    "connection": {
        "type": "string",
        "description": "Trading connector profile id, e.g. ibkr-paper-local or robinhood-live-mcp. Defaults to the selected profile.",
    },
    "host": {
        "type": "string",
        "description": "Optional local TWS/Gateway host override for local profiles.",
    },
    "port": {
        "type": "integer",
        "description": "Optional local TWS/Gateway port override for local profiles.",
    },
    "client_id": {
        "type": "integer",
        "description": "Optional local TWS/Gateway client id override for local profiles.",
    },
    "account": {
        "type": "string",
        "description": "Optional account code filter when supported by the connector.",
    },
}


def _overrides(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "host": _connection(kwargs.get("host")),
        "port": _int_or_none(kwargs.get("port")),
        "client_id": _int_or_none(kwargs.get("client_id")),
        "account": _connection(kwargs.get("account")),
    }


class TradingConnectionsTool(BaseTool):
    """List available trading connector profiles."""

    name = "trading_connections"
    description = (
        "List selectable trading connector profiles. Connectors come first; paper/live is a profile attribute."
    )
    parameters = {"type": "object", "properties": {}, "required": []}
    repeatable = True
    is_readonly = True

    def execute(self, **_: Any) -> str:
        """List connector profiles and mark the selected one."""
        try:
            selected = load_selected_profile_id()
            return _json_result(
                {
                    "status": "ok",
                    "selected_profile": selected,
                    "profiles": [profile.to_dict(selected=profile.id == selected) for profile in list_profiles()],
                }
            )
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingSelectConnectionTool(BaseTool):
    """Select the default trading connector profile."""

    name = "trading_select_connection"
    description = "Select the default trading connector profile for subsequent trading_* tool calls."
    parameters = {
        "type": "object",
        "properties": {
            "connection": {
                "type": "string",
                "description": "Profile id to select, e.g. ibkr-paper-local.",
            }
        },
        "required": ["connection"],
    }
    repeatable = True
    is_readonly = False

    def execute(self, **kwargs: Any) -> str:
        """Persist the selected profile id."""
        try:
            profile = profile_by_id(str(kwargs["connection"]).strip())
            path = save_selected_profile_id(profile.id)
            return _json_result({"status": "ok", "selected_profile": profile.id, "path": str(path)})
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingCheckTool(BaseTool):
    """Check a trading connector profile."""

    name = "trading_check"
    description = "Check whether a trading connector profile is configured and reachable. This never places orders."
    parameters = {
        "type": "object",
        "properties": TRADING_COMMON_PARAMETERS,
        "required": [],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Check connector readiness."""
        try:
            return _json_result(check_connection(_connection(kwargs.get("connection")), **_overrides(kwargs)))
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingAccountTool(BaseTool):
    """Read account summary from a trading connector profile."""

    name = "trading_account"
    description = "Read account summary from the selected trading connector profile. Read-only."
    parameters = TradingCheckTool.parameters
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Read account summary."""
        try:
            return _json_result(get_account(_connection(kwargs.get("connection")), **_overrides(kwargs)))
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingPositionsTool(BaseTool):
    """Read positions from a trading connector profile."""

    name = "trading_positions"
    description = "Read positions from the selected trading connector profile. Read-only."
    parameters = TradingCheckTool.parameters
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Read positions."""
        try:
            return _json_result(get_positions(_connection(kwargs.get("connection")), **_overrides(kwargs)))
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingOrdersTool(BaseTool):
    """Read open orders from a trading connector profile."""

    name = "trading_orders"
    description = "Read open orders from the selected trading connector profile. Read-only."
    parameters = {
        "type": "object",
        "properties": {
            **TRADING_COMMON_PARAMETERS,
            "include_executions": {"type": "boolean", "default": False},
        },
        "required": [],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Read open orders."""
        try:
            return _json_result(
                get_open_orders(
                    _connection(kwargs.get("connection")),
                    include_executions=bool(kwargs.get("include_executions", False)),
                    **_overrides(kwargs),
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingQuoteTool(BaseTool):
    """Read a quote from a trading connector profile."""

    name = "trading_quote"
    description = "Read a quote snapshot from the selected trading connector profile. Read-only."
    parameters = {
        "type": "object",
        "properties": {
            **TRADING_COMMON_PARAMETERS,
            "symbol": {"type": "string", "description": "Symbol, e.g. AAPL"},
            "exchange": {"type": "string", "default": "SMART"},
            "currency": {"type": "string", "default": "USD"},
            "sec_type": {"type": "string", "default": "STK"},
        },
        "required": ["symbol"],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Read quote snapshot."""
        try:
            return _json_result(
                get_quote(
                    str(kwargs["symbol"]),
                    _connection(kwargs.get("connection")),
                    exchange=str(kwargs.get("exchange") or "SMART"),
                    currency=str(kwargs.get("currency") or "USD"),
                    sec_type=str(kwargs.get("sec_type") or "STK"),
                    **_overrides(kwargs),
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingHistoryTool(BaseTool):
    """Read historical bars from a trading connector profile."""

    name = "trading_history"
    description = "Read historical bars from the selected trading connector profile. Read-only."
    parameters = {
        "type": "object",
        "properties": {
            **TradingQuoteTool.parameters["properties"],
            "duration": {"type": "string", "default": "30 D", "description": "IBKR (local_tws) duration string."},
            "bar_size": {"type": "string", "default": "1 day", "description": "IBKR (local_tws) bar size."},
            "what_to_show": {"type": "string", "default": "TRADES"},
            "use_rth": {"type": "boolean", "default": True},
            "period": {
                "type": "string",
                "default": "1d",
                "description": "Bar interval for SDK connectors (broker_sdk): 1m/5m/15m/30m/1h/4h/1d/1w/1M.",
            },
            "limit": {"type": "integer", "default": 90, "description": "Number of bars for SDK connectors."},
        },
        "required": ["symbol"],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Read historical bars."""
        try:
            return _json_result(
                get_history(
                    str(kwargs["symbol"]),
                    _connection(kwargs.get("connection")),
                    exchange=str(kwargs.get("exchange") or "SMART"),
                    currency=str(kwargs.get("currency") or "USD"),
                    sec_type=str(kwargs.get("sec_type") or "STK"),
                    duration=str(kwargs.get("duration") or "30 D"),
                    bar_size=str(kwargs.get("bar_size") or "1 day"),
                    what_to_show=str(kwargs.get("what_to_show") or "TRADES"),
                    use_rth=bool(kwargs.get("use_rth", True)),
                    period=str(kwargs.get("period") or "1d"),
                    limit=int(kwargs.get("limit") or 90),
                    **_overrides(kwargs),
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingTigerAccountReadTool(BaseTool):
    """Read the allowlisted TigerOpen account domain without trading mutations."""

    name = "trading_tiger_account_read"
    description = (
        "Read Tiger account data through an explicit read-only allowlist. Groups/actions: "
        "account(managed_accounts, assets, prime_assets, aggregate_assets, analytics, "
        "fund_details, funding_history, segment_fund_available, segment_fund_history); "
        "portfolio(positions, option_exercise_records, option_exercise_positions, "
        "transfer_records, transfer_external_records, transfer_detail); "
        "activity(order, open_orders, filled_orders, cancelled_orders). "
        "Credentials and account IDs always come from the selected Tiger profile."
    )
    parameters = {
        "type": "object",
        "properties": {
            "connection": TRADING_COMMON_PARAMETERS["connection"],
            "group": {"type": "string", "enum": ["account", "portfolio", "activity"]},
            "action": {"type": "string", "description": "One action listed in this tool's description."},
            "params": {
                "type": "object",
                "description": "Action-specific filters. account, account_id, and secret_key are rejected.",
                "additionalProperties": True,
            },
        },
        "required": ["group", "action"],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Dispatch one allowlisted Tiger account read."""
        try:
            params = kwargs.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("params must be an object")
            if len(params) > 30:
                raise ValueError("params has too many fields")
            result = query_tiger_account_domain(
                str(kwargs.get("group") or ""),
                str(kwargs.get("action") or ""),
                _connection(kwargs.get("connection")),
                **params,
            )
            return _json_result(result)
        except Exception:  # noqa: BLE001
            return _json_result({"status": "error", "error": _tiger_read_error()})


class TradingTigerMarketTool(BaseTool):
    """Read Tiger option, session, calendar, depth, and tick data."""

    name = "trading_tiger_market"
    description = (
        "Read TigerOpen market data. operation is option_expirations, option_chain, "
        "market_status, calendar, depth, or ticks. Read-only and Tiger profiles only."
    )
    parameters = {
        "type": "object",
        "properties": {
            "connection": TRADING_COMMON_PARAMETERS["connection"],
            "operation": {
                "type": "string",
                "enum": ["option_expirations", "option_chain", "market_status", "calendar", "depth", "ticks"],
            },
            "symbol": {"type": "string", "description": "Underlying or stock symbol when required."},
            "expiry": {"type": "string", "description": "Option expiry date, required for option_chain."},
            "market": {"type": "string", "enum": ["ALL", "US", "HK", "CN", "SG", "AU"]},
            "return_greeks": {"type": "boolean", "default": True},
            "timezone": {"type": "string"},
            "begin_date": {"type": "string", "description": "Calendar begin date, YYYY-MM-DD."},
            "end_date": {"type": "string", "description": "Calendar end date, YYYY-MM-DD."},
            "trade_session": {"type": "string"},
            "begin_index": {"type": "integer"},
            "end_index": {"type": "integer"},
            "limit": {"type": "integer", "default": 100},
        },
        "required": ["operation"],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Dispatch one Tiger market-data operation."""
        try:
            operation = str(kwargs.get("operation") or "").strip().lower()
            connection = _connection(kwargs.get("connection"))
            symbol = str(kwargs.get("symbol") or "")
            market = str(kwargs.get("market") or ("ALL" if operation == "market_status" else "US"))
            if operation == "option_expirations":
                result = get_tiger_option_expirations(symbol, connection, market=market)
            elif operation == "option_chain":
                result = get_tiger_option_chain(
                    symbol,
                    str(kwargs.get("expiry") or ""),
                    connection,
                    market=market,
                    return_greeks=bool(kwargs.get("return_greeks", True)),
                    timezone=_connection(kwargs.get("timezone")),
                )
            elif operation == "market_status":
                result = get_tiger_market_status(connection, market=market)
            elif operation == "calendar":
                result = get_tiger_trading_calendar(
                    connection,
                    market=market,
                    begin_date=_connection(kwargs.get("begin_date")),
                    end_date=_connection(kwargs.get("end_date")),
                )
            elif operation == "depth":
                result = get_tiger_depth_quote(
                    symbol,
                    connection,
                    market=market,
                    trade_session=_connection(kwargs.get("trade_session")),
                )
            elif operation == "ticks":
                result = get_tiger_trade_ticks(
                    symbol,
                    connection,
                    trade_session=_connection(kwargs.get("trade_session")),
                    begin_index=_int_or_none(kwargs.get("begin_index")),
                    end_index=_int_or_none(kwargs.get("end_index")),
                    limit=int(kwargs.get("limit") or 100),
                )
            else:
                raise ValueError("unsupported Tiger market operation")
            return _json_result(result)
        except Exception:  # noqa: BLE001
            return _json_result({"status": "error", "error": _tiger_read_error()})


class TradingTigerActivityTool(BaseTool):
    """Read Tiger historical orders and execution transactions."""

    name = "trading_tiger_activity"
    description = (
        "Read TigerOpen historical orders or execution transactions with time, symbol, "
        "market, security-type, and pagination filters. Read-only and Tiger profiles only."
    )
    parameters = {
        "type": "object",
        "properties": {
            "connection": TRADING_COMMON_PARAMETERS["connection"],
            "operation": {"type": "string", "enum": ["orders", "transactions"]},
            "market": {"type": "string", "enum": ["ALL", "US", "HK", "CN", "SG", "AU"], "default": "ALL"},
            "symbol": {"type": "string"},
            "order_id": {"type": "integer"},
            "start_time": {"description": "Order date/time or transaction epoch milliseconds."},
            "end_time": {"description": "Order date/time or transaction epoch milliseconds."},
            "limit": {"type": "integer", "default": 100},
            "states": {"type": "array", "items": {"type": "string"}},
            "sec_type": {"type": "string"},
            "page_token": {"type": "string"},
            "since_date": {"type": "string", "description": "Transaction begin date, YYYY-MM-DD."},
            "to_date": {"type": "string", "description": "Transaction end date, YYYY-MM-DD."},
        },
        "required": ["operation"],
    }
    repeatable = True
    is_readonly = True

    def execute(self, **kwargs: Any) -> str:
        """Dispatch an order-history or transaction query."""
        try:
            operation = str(kwargs.get("operation") or "").strip().lower()
            connection = _connection(kwargs.get("connection"))
            common = {
                "market": str(kwargs.get("market") or "ALL"),
                "symbol": _connection(kwargs.get("symbol")),
                "limit": int(kwargs.get("limit") or 100),
                "sec_type": _connection(kwargs.get("sec_type")),
                "page_token": _connection(kwargs.get("page_token")),
            }
            if operation == "orders":
                result = get_tiger_order_history(
                    connection,
                    start_time=kwargs.get("start_time"),
                    end_time=kwargs.get("end_time"),
                    states=list(kwargs.get("states") or []) or None,
                    **common,
                )
            elif operation == "transactions":
                result = get_tiger_transactions(
                    connection,
                    order_id=_int_or_none(kwargs.get("order_id")),
                    start_time=_int_or_none(kwargs.get("start_time")),
                    end_time=_int_or_none(kwargs.get("end_time")),
                    since_date=_connection(kwargs.get("since_date")),
                    to_date=_connection(kwargs.get("to_date")),
                    **common,
                )
            else:
                raise ValueError("operation must be 'orders' or 'transactions'")
            return _json_result(result)
        except Exception:  # noqa: BLE001
            return _json_result({"status": "error", "error": _tiger_read_error()})


class TradingPlaceOrderTool(BaseTool):
    """Place an order through a trading connector profile.

    Paper profiles place against the broker's sandbox account. Live profiles
    route through the bounded-autonomy mandate gate (mandate + kill switch +
    fail-closed pre-trade checks + audit) before any order reaches the broker.
    Not read-only; not repeatable (an order must never be silently re-issued).
    """

    name = "trading_place_order"
    description = (
        "Place an order through the selected trading connector profile. Paper "
        "profiles trade a sandbox account; live profiles are gated by the user's "
        "mandate and kill switch. side is 'buy' or 'sell'; give exactly one of "
        "quantity (units) or notional (account-currency amount)."
    )
    parameters = {
        "type": "object",
        "properties": {
            **TRADING_COMMON_PARAMETERS,
            "symbol": {"type": "string", "description": "Symbol, e.g. AAPL, BTC-USDT, 700.HK, HK.00700."},
            "side": {"type": "string", "enum": ["buy", "sell"]},
            "quantity": {"type": "number", "description": "Order size in units/shares/contracts. Exactly one of quantity/notional."},
            "notional": {"type": "number", "description": "Order size as an account-currency amount. Exactly one of quantity/notional."},
            "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
            "limit_price": {"type": "number", "description": "Required for limit orders."},
            "time_in_force": {"type": "string", "enum": ["day", "gtc"], "default": "day"},
        },
        "required": ["symbol", "side"],
    }
    repeatable = False
    is_readonly = False

    def execute(self, **kwargs: Any) -> str:
        """Place an order via the connector profile."""
        # LLMs frequently populate BOTH sizing fields, leaving the unused one at
        # 0; a zero size is never valid, so treat it as absent to preserve the
        # "exactly one of quantity/notional" contract.
        quantity = _num_or_none(kwargs.get("quantity")) or None
        notional = _num_or_none(kwargs.get("notional")) or None
        try:
            return _json_result(
                place_order(
                    str(kwargs["symbol"]),
                    _connection(kwargs.get("connection")),
                    side=str(kwargs.get("side") or ""),
                    quantity=quantity,
                    notional=notional,
                    order_type=str(kwargs.get("order_type") or "market"),
                    limit_price=_num_or_none(kwargs.get("limit_price")),
                    time_in_force=str(kwargs.get("time_in_force") or "day"),
                    **_overrides(kwargs),
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})


class TradingCancelOrderTool(BaseTool):
    """Cancel an order through a trading connector profile (risk-reducing)."""

    name = "trading_cancel_order"
    description = "Cancel an open order on the selected trading connector profile by order id."
    parameters = {
        "type": "object",
        "properties": {
            **TRADING_COMMON_PARAMETERS,
            "order_id": {"type": "string", "description": "Broker order id to cancel."},
            "symbol": {"type": "string", "description": "Symbol (required by some brokers, e.g. OKX/Binance)."},
        },
        "required": ["order_id"],
    }
    repeatable = False
    is_readonly = False

    def execute(self, **kwargs: Any) -> str:
        """Cancel an order via the connector profile."""
        try:
            return _json_result(
                cancel_order(
                    str(kwargs["order_id"]),
                    _connection(kwargs.get("connection")),
                    symbol=_connection(kwargs.get("symbol")),
                    **_overrides(kwargs),
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _json_result({"status": "error", "error": str(exc)})
