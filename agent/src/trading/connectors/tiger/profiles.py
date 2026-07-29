"""Built-in Tiger Brokers connector profiles.

Layer A ships read-only paper and live profiles. Layer B/C adds two
order-placing profiles: a paper-execution profile (sandbox orders) and a
mandate-gated live profile. Read-only profiles stay ``readonly=True``; the
trade profiles set ``readonly=False`` and add the relevant ``orders.place``
capability.
"""

from __future__ import annotations

from src.trading.types import READ_CAPABILITIES, TradingProfile

TIGER_EXTENDED_READ_CAPABILITIES = (
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
    "market.status.read",
    "market.calendar.read",
    "market.depth.read",
    "market.ticks.read",
    "orders.history.read",
    "transactions.read",
    "accounts.managed.read",
    "account.assets.detail.read",
    "account.analytics.read",
    "account.funds.read",
    "positions.detail.read",
    "transfers.read",
    "option.exercise.read",
    "orders.detail.read",
)
TIGER_READ_CAPABILITIES = READ_CAPABILITIES + TIGER_EXTENDED_READ_CAPABILITIES

TIGER_PROFILES: tuple[TradingProfile, ...] = (
    TradingProfile(
        id="tiger-paper-sdk",
        connector="tiger",
        label="Tiger Paper · TigerOpen",
        environment="paper",
        transport="broker_sdk",
        capabilities=TIGER_READ_CAPABILITIES,
        readonly=True,
        config={"profile": "paper"},
        notes=(
            "Reads a Tiger paper account via the official tigeropen SDK. The paper "
            "profile fails closed unless the account number is a 17-digit Tiger "
            "paper account."
        ),
    ),
    TradingProfile(
        id="tiger-live-sdk-readonly",
        connector="tiger",
        label="Tiger Live · TigerOpen Read-Only",
        environment="live",
        transport="broker_sdk",
        capabilities=TIGER_READ_CAPABILITIES,
        readonly=True,
        config={"profile": "live-readonly"},
        notes="Reads a Tiger live account only. Order placement is not exposed in this profile.",
    ),
    TradingProfile(
        id="tiger-paper-trade",
        connector="tiger",
        label="Tiger Paper · TigerOpen Trade",
        environment="paper",
        transport="broker_sdk",
        capabilities=TIGER_READ_CAPABILITIES + ("orders.place",),
        readonly=False,
        config={"profile": "paper"},
        notes=(
            "Places orders against a Tiger paper (sandbox) account via the "
            "official tigeropen SDK. Fails closed unless the account number is a "
            "17-digit Tiger paper account. Paper accounts do not support GTC, so "
            "time-in-force is forced to DAY; notional orders are unsupported "
            "(quantity in units only)."
        ),
    ),
    TradingProfile(
        id="tiger-live-trade",
        connector="tiger",
        label="Tiger Live · TigerOpen Trade",
        environment="live",
        transport="broker_sdk",
        capabilities=TIGER_READ_CAPABILITIES + ("orders.place.requires_mandate",),
        readonly=False,
        config={"profile": "live"},
        notes=(
            "Places orders against a Tiger live account. Live orders go through "
            "the mandate gate (symbol allowlist, max order size, exposure and "
            "leverage limits, daily trade cap) before reaching the broker; "
            "quantity in units only, no notional path for stocks."
        ),
    ),
)
