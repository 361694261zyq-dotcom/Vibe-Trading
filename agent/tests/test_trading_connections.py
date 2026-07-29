"""Tests for connector-first trading profile operations."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.trading import profiles, service
from src.tools import build_registry
from src.tools.trading_connector_tool import (
    TradingPlaceOrderTool,
    TradingSelectConnectionTool,
    TradingTigerAccountReadTool,
    TradingTigerActivityTool,
    TradingTigerMarketTool,
)

pytestmark = pytest.mark.unit


def _agent_config(server) -> SimpleNamespace:
    return SimpleNamespace(mcp_servers={"robinhood": server})


def test_remote_call_requires_enabled_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic remote reads must respect the operator MCP allowlist."""
    server = SimpleNamespace(
        url="https://agent.robinhood.com/mcp/trading",
        enabled_tools=["get_portfolio"],
        auth=SimpleNamespace(cache_dir="/tmp/vibe-no-token"),
    )
    monkeypatch.setattr("src.config.loader.load_agent_config", lambda: _agent_config(server))
    monkeypatch.setattr("src.live.registry.has_cached_oauth_token", lambda *_: True)

    result = service.get_positions("robinhood-live-mcp")

    assert result["status"] == "error"
    assert "not enabled" in result["error"]


def test_remote_call_requires_cached_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic remote reads must not trigger OAuth from tool/API/MCP paths."""
    server = SimpleNamespace(
        url="https://agent.robinhood.com/mcp/trading",
        enabled_tools=["get_equity_positions"],
        auth=SimpleNamespace(cache_dir="/tmp/vibe-no-token"),
    )
    monkeypatch.setattr("src.config.loader.load_agent_config", lambda: _agent_config(server))
    monkeypatch.setattr("src.live.registry.has_cached_oauth_token", lambda *_: False)

    result = service.get_positions("robinhood-live-mcp")

    assert result["status"] == "not_authorized"
    assert "connector authorize robinhood-live-mcp" in result["error"]


def test_ibkr_official_profile_does_not_advertise_unknown_generic_reads() -> None:
    """IBKR official MCP stays honest until stable remote tool names are known."""
    profile = profiles.profile_by_id("ibkr-live-official-mcp-readonly")

    assert profile.capabilities == ("mcp.read.discovery",)
    result = service.get_account(profile.id)
    assert result["status"] == "error"
    assert "does not support" in result["error"]


def test_connector_profile_id_for_broker_prefers_live_remote_mcp() -> None:
    """Broker on-ramps should resolve through the centralized profile registry."""
    assert service.connector_profile_id_for_broker("robinhood") == "robinhood-live-mcp"
    assert service.connector_profile_id_for_broker("ibkr") == "ibkr-live-official-mcp-readonly"
    assert service.connector_profile_id_for_broker("futurebroker") == "futurebroker-live-mcp"


def test_select_connection_tool_returns_canonical_profile_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Selecting a profile should persist and return the canonical id."""
    monkeypatch.setattr(profiles, "get_runtime_root", lambda: tmp_path)

    result = TradingSelectConnectionTool().execute(connection="IBKR-PAPER-LOCAL")

    assert result
    payload = json.loads(result)
    assert payload["status"] == "ok"
    assert payload["selected_profile"] == "ibkr-paper-local"
    assert profiles.load_selected_profile_id() == "ibkr-paper-local"


def test_place_order_tool_treats_zero_unused_sizing_field_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM-filled zero quantity/notional fields must not violate sizing XOR."""
    calls: list[dict] = []

    def fake_place_order(symbol, connection, **kwargs):  # noqa: ANN001
        calls.append({"symbol": symbol, "connection": connection, **kwargs})
        return {"status": "ok", "echo": kwargs}

    monkeypatch.setattr("src.tools.trading_connector_tool.place_order", fake_place_order)

    quantity_result = json.loads(
        TradingPlaceOrderTool().execute(
            symbol="NVDA",
            connection="alpaca-paper-trade",
            side="buy",
            quantity=2,
            notional=0,
        )
    )
    notional_result = json.loads(
        TradingPlaceOrderTool().execute(
            symbol="NVDA",
            connection="alpaca-paper-trade",
            side="buy",
            quantity=0,
            notional=50,
        )
    )

    assert quantity_result["status"] == "ok"
    assert notional_result["status"] == "ok"
    assert calls[0]["quantity"] == 2.0
    assert calls[0]["notional"] is None
    assert calls[1]["quantity"] is None
    assert calls[1]["notional"] == 50.0


def test_live_broker_mcp_wrappers_are_hidden_from_agent_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connector-first registry must not expose broker-specific mcp_* tools."""
    server = SimpleNamespace(
        url="https://agent.robinhood.com/mcp/trading",
        enabled_tools=["get_positions"],
        auth=SimpleNamespace(cache_dir="/tmp/vibe-token"),
    )
    agent_config = SimpleNamespace(mcp_servers={"robinhood": server})
    monkeypatch.setattr("src.live.registry.is_live_broker", lambda *_: True)
    monkeypatch.setattr("src.live.registry.should_register_live_channel", lambda **_: True)

    def fail_build_wrappers(*_, **__):
        raise AssertionError("live broker wrappers should not be registered directly")

    monkeypatch.setattr("src.tools.mcp.build_mcp_tool_wrappers", fail_build_wrappers)

    registry = build_registry(agent_config=agent_config, include_shell_tools=False)

    assert "trading_positions" in registry.tool_names
    assert not any(name.startswith("mcp_robinhood_") for name in registry.tool_names)


def test_robinhood_generic_reads_use_current_agentic_mcp_tool_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression for #381: generic reads must not call stale Robinhood tool names."""
    calls: list[tuple[str, dict]] = []
    server = SimpleNamespace(
        url="https://agent.robinhood.com/mcp/trading",
        enabled_tools=[
            "get_portfolio",
            "get_equity_positions",
            "get_equity_orders",
            "get_equity_quotes",
        ],
        auth=SimpleNamespace(cache_dir="/tmp/vibe-token"),
    )

    class _Adapter:
        def __init__(self, server_name, server_config):  # noqa: ANN001
            assert server_name == "robinhood"
            assert server_config is server

        def call_tool(self, remote_name, arguments):  # noqa: ANN001
            calls.append((remote_name, dict(arguments)))
            return {"status": "ok"}

    monkeypatch.setattr("src.config.loader.load_agent_config", lambda: _agent_config(server))
    monkeypatch.setattr("src.live.registry.has_cached_oauth_token", lambda *_: True)
    monkeypatch.setattr("src.tools.mcp.MCPServerAdapter", _Adapter)

    assert service.get_account("robinhood-live-mcp")["status"] == "ok"
    assert service.get_positions("robinhood-live-mcp")["status"] == "ok"
    assert service.get_open_orders("robinhood-live-mcp")["status"] == "ok"
    assert service.get_quote("AAPL", "robinhood-live-mcp")["status"] == "ok"

    assert calls == [
        ("get_portfolio", {}),
        ("get_equity_positions", {}),
        ("get_equity_orders", {}),
        ("get_equity_quotes", {"symbols": ["AAPL"]}),
    ]


def test_tiger_extended_tools_are_registered() -> None:
    """Register all extended Tiger connector tools."""
    names = set(build_registry(include_shell_tools=False).tool_names)
    assert {"trading_tiger_market", "trading_tiger_activity", "trading_tiger_account_read"} <= names


@pytest.mark.parametrize("error_type", [RuntimeError, ValueError])
def test_tiger_account_read_tool_redacts_unexpected_sdk_errors(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    """Redact unexpected Tiger SDK errors from account reads."""
    def fail(*args, **kwargs):  # noqa: ANN002, ANN003
        raise error_type(
            "account=20191106192858300 key=/Users/test/.vibe-trading/keys/private.pem"
        )

    monkeypatch.setattr("src.tools.trading_connector_tool.query_tiger_account_domain", fail)

    payload = json.loads(
        TradingTigerAccountReadTool().execute(group="account", action="assets")
    )

    assert payload == {"status": "error", "error": "Tiger connector request failed"}


def test_tiger_account_read_tool_dispatches_allowlisted_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch allowlisted Tiger account-read actions with parameters."""
    calls: list[dict] = []

    def fake_query(group, action, connection, **params):  # noqa: ANN001
        calls.append({"group": group, "action": action, "connection": connection, **params})
        return {"status": "ok", "data": []}

    monkeypatch.setattr("src.tools.trading_connector_tool.query_tiger_account_domain", fake_query)
    payload = json.loads(
        TradingTigerAccountReadTool().execute(
            group="portfolio",
            action="positions",
            connection="tiger-live-sdk-readonly",
            params={"sec_type": "OPT", "market": "US"},
        )
    )

    assert payload["status"] == "ok"
    assert calls == [
        {
            "group": "portfolio",
            "action": "positions",
            "connection": "tiger-live-sdk-readonly",
            "sec_type": "OPT",
            "market": "US",
        }
    ]


def test_tiger_market_tool_dispatches_option_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch Tiger option-chain requests with market parameters."""
    calls: list[dict] = []

    def fake_get_option_chain(symbol, expiry, connection, **kwargs):  # noqa: ANN001
        calls.append({"symbol": symbol, "expiry": expiry, "connection": connection, **kwargs})
        return {"status": "ok", "options": []}

    monkeypatch.setattr(
        "src.tools.trading_connector_tool.get_tiger_option_chain",
        fake_get_option_chain,
    )
    payload = json.loads(
        TradingTigerMarketTool().execute(
            operation="option_chain",
            connection="tiger-paper-sdk",
            symbol="AAPL",
            expiry="2026-09-18",
            market="US",
            return_greeks=True,
        )
    )

    assert payload["status"] == "ok"
    assert calls == [
        {
            "symbol": "AAPL",
            "expiry": "2026-09-18",
            "connection": "tiger-paper-sdk",
            "market": "US",
            "return_greeks": True,
            "timezone": None,
        }
    ]


def test_tiger_activity_tool_dispatches_transaction_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch Tiger transaction requests with activity filters."""
    calls: list[dict] = []

    def fake_get_transactions(connection, **kwargs):  # noqa: ANN001
        calls.append({"connection": connection, **kwargs})
        return {"status": "ok", "transactions": []}

    monkeypatch.setattr(
        "src.tools.trading_connector_tool.get_tiger_transactions",
        fake_get_transactions,
    )
    payload = json.loads(
        TradingTigerActivityTool().execute(
            operation="transactions",
            connection="tiger-live-sdk-readonly",
            market="US",
            symbol="AAPL",
            start_time=1782864000000,
            end_time=1785542399000,
            limit=25,
        )
    )

    assert payload["status"] == "ok"
    assert calls[0]["market"] == "US"
    assert calls[0]["start_time"] == 1782864000000
    assert calls[0]["end_time"] == 1785542399000
    assert calls[0]["limit"] == 25


def test_generic_tiger_reads_redact_sdk_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redact Tiger SDK failures across every generic read entry point."""
    secret = "account=12345678 key=/private/tiger.pem"

    class FailingTigerModule:
        """Simulate Tiger SDK failures containing sensitive details."""

        @staticmethod
        def build_config(config, overrides):  # noqa: ANN001, ANN201
            del config, overrides
            return object()

        def __getattr__(self, name: str):
            del name

            def fail(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
                del args, kwargs
                raise ValueError(secret)

            return fail

    monkeypatch.setattr(service, "_sdk_module", lambda connector: FailingTigerModule())
    calls = [
        lambda: service.check_connection("tiger-paper-sdk"),
        lambda: service.get_account("tiger-paper-sdk"),
        lambda: service.get_positions("tiger-paper-sdk"),
        lambda: service.get_open_orders("tiger-paper-sdk"),
        lambda: service.get_quote("AAPL", "tiger-paper-sdk"),
        lambda: service.get_history("AAPL", "tiger-paper-sdk"),
    ]

    for call in calls:
        result = call()
        assert result["status"] == "error"
        assert result["error"] == "Tiger connector request failed"
        assert secret not in str(result)


def test_tiger_extended_service_rejects_non_tiger_profile() -> None:
    """Reject non-Tiger profiles for extended Tiger services."""
    result = service.get_tiger_market_status("alpaca-paper-sdk", market="US")
    assert result["status"] == "error"
    assert "market.status.read" in result["error"]
