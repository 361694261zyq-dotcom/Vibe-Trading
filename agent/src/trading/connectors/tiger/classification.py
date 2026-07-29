"""Curated read/write classification for Tiger Brokers SDK operations.

The trading layer classifies each connector operation as READ or WRITE so the
live gate can keep writes behind the mandate. Tiger is a direct-SDK connector
(not MCP), so the keys here are the connector's own operation names rather than
remote MCP tool names. Anything not listed and not a known read resolves to
WRITE (fail-closed) when the live gate consults this map.
"""

from __future__ import annotations

from src.live.classification import ToolClass

#: Tiger SDK operation read/write catalog. Read operations mirror the connector's
#: public read functions; write operations are the order-mutating SDK calls,
#: pinned WRITE so the live gate never treats them as plain reads.
TIGER_TOOL_CLASS: dict[str, ToolClass] = {
    # READ
    "get_account": ToolClass.READ,
    "get_assets": ToolClass.READ,
    "get_positions": ToolClass.READ,
    "get_open_orders": ToolClass.READ,
    "get_orders": ToolClass.READ,
    "get_filled_orders": ToolClass.READ,
    "get_stock_briefs": ToolClass.READ,
    "get_bars": ToolClass.READ,
    "get_option_symbols": ToolClass.READ,
    "get_option_expirations": ToolClass.READ,
    "get_option_chain": ToolClass.READ,
    "get_option_briefs": ToolClass.READ,
    "get_option_bars": ToolClass.READ,
    "get_option_depth": ToolClass.READ,
    "get_option_trade_ticks": ToolClass.READ,
    "get_option_timeline": ToolClass.READ,
    "get_option_analysis": ToolClass.READ,
    "get_option_contract": ToolClass.READ,
    "get_option_derivative_contracts": ToolClass.READ,
    "check_option_exercise": ToolClass.READ,
    "get_market_status": ToolClass.READ,
    "get_trading_calendar": ToolClass.READ,
    "get_depth_quote": ToolClass.READ,
    "get_trade_ticks": ToolClass.READ,
    "get_transactions": ToolClass.READ,
    "get_managed_accounts": ToolClass.READ,
    "get_prime_assets": ToolClass.READ,
    "get_aggregate_assets": ToolClass.READ,
    "get_analytics_asset": ToolClass.READ,
    "get_fund_details": ToolClass.READ,
    "get_funding_history": ToolClass.READ,
    "get_segment_fund_available": ToolClass.READ,
    "get_segment_fund_history": ToolClass.READ,
    "get_option_exercise_records": ToolClass.READ,
    "get_option_exercise_positions": ToolClass.READ,
    "get_position_transfer_records": ToolClass.READ,
    "get_position_transfer_external_records": ToolClass.READ,
    "get_position_transfer_detail": ToolClass.READ,
    "get_order": ToolClass.READ,
    "get_cancelled_orders": ToolClass.READ,
    # WRITE
    "place_order": ToolClass.WRITE,
    "cancel_order": ToolClass.WRITE,
    "modify_order": ToolClass.WRITE,
}
