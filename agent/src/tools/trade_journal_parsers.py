"""Trade journal format adapters.

Each parser normalizes one broker export format into a list of TradeRecord.
Supported: Tiger activity statements, Tonghuashun (同花顺), Eastmoney
(东方财富), Futu (富途), and generic CSV.

Encoding fallback order for CSV: utf-8 → utf-8-sig → gbk → gb2312.
Excel (.xlsx/.xls) always opens as utf-8 internally via openpyxl/xlrd.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

# Broker CSV/Excel cells often include ISO codes or currency glyphs around the
# number (Schwab/IBKR "$1,234.56", JP/CN "¥1000"). Commas are already stripped;
# without stripping these tokens float() fails and we silently store 0.0.
_CURRENCY_TOKEN_RE = re.compile(
    r"(?i)(?<![A-Za-z])(?:USDT|USDC|USD|EUR|GBP|JPY|CNY|HKD)(?![A-Za-z])|[$€£¥￥]"
)

FormatName = str  # "tiger" | "tonghuashun" | "eastmoney" | "futu" | "generic" | "unknown"

_A_SHARE_EXCHANGE_MAP = {
    # prefix → suffix; Shanghai Main + STAR, Shenzhen Main + SME + ChiNext, BSE
    ("6",): ".SH",
    ("0", "3"): ".SZ",
    ("4", "8"): ".BJ",
}

_BUY_TOKENS = {
    "buy",
    "b",
    "purchase",
    "buy to cover",
    "buy-to-cover",
    "buy_to_cover",
    "买入",
    "证券买入",
    "融资买入",
    "做多",
    "long",
}
_SELL_TOKENS = {
    "sell",
    "s",
    "sell short",
    "sell-short",
    "sell_short",
    "卖出",
    "证券卖出",
    "融券卖出",
    "做空",
    "short",
}


@dataclass(frozen=True)
class TradeRecord:
    """Standardized trade record (immutable).

    Attributes:
        datetime: ISO8601 timestamp, e.g. "2026-01-15 09:35:00".
        symbol: Exchange-qualified symbol, e.g. "600519.SH" / "AAPL" / "BTC-USDT".
        name: Human-readable instrument name.
        side: "buy" or "sell".
        quantity: Filled quantity.
        price: Filled price.
        amount: Gross amount (quantity * price, pre-fee).
        fee: Total fees (commission + stamp + transfer).
        market: "china_a" / "us" / "hk" / "crypto" / "other".
        multiplier: Contract multiplier used for notional and PnL calculations.
    """

    datetime: str
    symbol: str
    name: str
    side: str
    quantity: float
    price: float
    amount: float
    fee: float
    market: str
    multiplier: float = 1.0


# ---------------- File loading ----------------

def load_dataframe(path: str | Path) -> pd.DataFrame:
    """Load a CSV/Excel file into a DataFrame with encoding fallback.

    Args:
        path: Path to the file (.csv/.xlsx/.xls).

    Returns:
        Parsed DataFrame with raw column names (no normalization).

    Raises:
        FileNotFoundError: File does not exist.
        ValueError: Unsupported extension or all encodings failed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    ext = p.suffix.lower()
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(p, dtype=str)
    if ext != ".csv":
        raise ValueError(f"Unsupported extension: {ext}")

    last_err: Exception | None = None
    # utf-16 covers Excel "CSV UTF-16" / Unicode exports (BOM required).
    for enc in ("utf-8-sig", "utf-8", "utf-16", "gbk", "gb2312"):
        try:
            return pd.read_csv(p, dtype=str, encoding=enc)
        except UnicodeDecodeError as exc:
            last_err = exc
    raise ValueError(f"Failed to decode CSV with utf-8/utf-16/gbk/gb2312: {last_err}")


# ---------------- Format detection ----------------

def detect_format(df: pd.DataFrame) -> FormatName:
    """Detect broker format by column-name signature.

    Args:
        df: Raw DataFrame from load_dataframe.

    Returns:
        Format identifier; "unknown" when nothing matches (caller may still
        try GenericCSVParser).
    """
    cols = set(df.columns.astype(str))

    if {"成交时间", "证券代码", "操作"}.issubset(cols):
        return "tonghuashun"
    if {"买卖标志", "股票代码"}.issubset(cols) or {"买卖标志", "成交均价"}.issubset(cols):
        return "eastmoney"
    if {"Date", "Symbol", "Side"}.issubset(cols) or {"Date", "Symbol", "Direction"}.issubset(cols):
        return "futu"

    # Generic: any subset containing time/symbol/side hints
    lowered = {c.lower() for c in cols}
    if any(c in lowered for c in ("datetime", "time", "date")) and any(
        c in lowered for c in ("symbol", "ticker", "code")
    ):
        return "generic"
    return "unknown"


# ---------------- Parsers ----------------

def _normalize_side(raw: Any) -> str:
    """Return ``buy`` or ``sell`` for an exact supported direction alias.

    Raises:
        ValueError: Direction is missing or unsupported.
    """
    if raw is None or pd.isna(raw):
        raise ValueError("Trade side is required")
    s = str(raw).strip().lower()
    if not s:
        raise ValueError("Trade side is required")
    if s in _BUY_TOKENS:
        return "buy"
    if s in _SELL_TOKENS:
        return "sell"
    raise ValueError(f"Unsupported trade side: {raw!r}")


def _is_empty_code(raw: Any) -> bool:
    """True for None/NaN/blank securities codes from CSV/Excel cells."""
    if raw is None:
        return True
    try:
        if pd.isna(raw):
            return True
    except (TypeError, ValueError):
        pass
    return not str(raw).strip()


def _qualify_a_share(code: str) -> str:
    """Append .SH/.SZ/.BJ suffix to a bare A-share ticker."""
    if _is_empty_code(code):
        raise ValueError("empty securities code")
    code = str(code).strip()
    # Excel/CSV numeric cells stringify as "600519.0"/sci — not exchange suffixes.
    try:
        as_float = float(code)
        if as_float.is_integer() and abs(as_float) < 10_000_000:
            code = str(int(as_float))
    except (ValueError, OverflowError):
        pass
    code = code.zfill(6)
    if "." in code:
        return code.upper()
    first = code[0]
    for prefixes, suffix in _A_SHARE_EXCHANGE_MAP.items():
        if first in prefixes:
            return code + suffix
    return code


def _to_float(val: Any, default: float = 0.0) -> float:
    """Safely cast to float; return default on failure."""
    if val is None:
        return default
    try:
        s = str(val).strip().replace("\u2212", "-")
        s = _CURRENCY_TOKEN_RE.sub("", s).replace(",", "").strip()
        return float(s) if s else default
    except (ValueError, TypeError):
        return default


def parse_tonghuashun(df: pd.DataFrame) -> list[TradeRecord]:
    """Parse 同花顺 exports.

    Expected columns: 成交时间, 证券代码, 证券名称, 操作, 成交数量, 成交价格,
    成交金额, 手续费, 印花税, 过户费.
    """
    records: list[TradeRecord] = []
    for _, row in df.iterrows():
        raw_code = row.get("证券代码", "")
        if _is_empty_code(raw_code):
            continue
        qty = _to_float(row.get("成交数量"))
        price = _to_float(row.get("成交价格"))
        amount = _to_float(row.get("成交金额")) or qty * price
        fee = _to_float(row.get("手续费")) + _to_float(row.get("印花税")) + _to_float(row.get("过户费"))
        records.append(TradeRecord(
            datetime=_ths_datetime(row.get("成交时间", "")),
            symbol=_qualify_a_share(raw_code),
            name=str(row.get("证券名称", "")).strip(),
            side=_normalize_side(row.get("操作")),
            quantity=qty,
            price=price,
            amount=amount,
            fee=fee,
            market="china_a",
        ))
    return records


def _ths_datetime(val: Any) -> str:
    """Normalize 成交时间; Excel serial floats become ISO datetime."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    # iterrows yields numpy integer/float scalars; bare pd.to_datetime(int) is ns-epoch.
    if pd.api.types.is_number(val) and not isinstance(val, (bool,)):
        ts = pd.to_datetime(float(val), unit="D", origin="1899-12-30", errors="coerce")
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
    # load_dataframe uses dtype=str; Excel serials arrive as "44927" / "44927.5".
    text = str(val).strip()
    if text and not any(ch in text for ch in "/-:"):
        try:
            serial = float(text)
        except ValueError:
            serial = None
        else:
            # Civil day serials; YYYYMMDD ints are >= 19_000_001.
            if 1.0 <= serial < 100_000.0:
                ts = pd.to_datetime(serial, unit="D", origin="1899-12-30", errors="coerce")
                if pd.notna(ts):
                    return ts.strftime("%Y-%m-%d %H:%M:%S")
    ts = pd.to_datetime(val, errors="coerce")
    if pd.notna(ts):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return text


def parse_eastmoney(df: pd.DataFrame) -> list[TradeRecord]:
    """Parse 东方财富 exports.

    Expected columns: 成交日期 (YYYYMMDD), 成交时间 (HH:MM:SS), 股票代码,
    股票名称, 买卖标志 (B/S), 成交数量, 成交均价, 成交金额, 佣金, 印花税.
    """
    records: list[TradeRecord] = []
    for _, row in df.iterrows():
        raw_code = row.get("股票代码", "")
        if _is_empty_code(raw_code):
            continue
        raw_date = str(row.get("成交日期", "")).strip()
        # Excel numeric YYYYMMDD cells stringify as "20260115.0".
        # Day-count serials (dtype=str load) arrive as "44941" / "44941.0".
        try:
            as_float = float(raw_date)
            if as_float.is_integer() and 19_000_001 <= int(as_float) <= 21_001_231:
                raw_date = f"{int(as_float):08d}"
            elif 1.0 <= as_float < 100_000.0:
                ts = pd.to_datetime(as_float, unit="D", origin="1899-12-30", errors="coerce")
                if pd.notna(ts):
                    raw_date = ts.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
        raw_time = str(row.get("成交时间", "")).strip()
        if len(raw_date) == 8 and raw_date.isdigit():
            iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        else:
            iso_date = raw_date
        dt = f"{iso_date} {raw_time}".strip()
        qty = _to_float(row.get("成交数量"))
        price = _to_float(row.get("成交均价"))
        amount = _to_float(row.get("成交金额")) or qty * price
        fee = _to_float(row.get("佣金")) + _to_float(row.get("印花税"))
        records.append(TradeRecord(
            datetime=dt,
            symbol=_qualify_a_share(raw_code),
            name=str(row.get("股票名称", "")).strip(),
            side=_normalize_side(row.get("买卖标志")),
            quantity=qty,
            price=price,
            amount=amount,
            fee=fee,
            market="china_a",
        ))
    return records


def _futu_market(symbol: str, market_hint: str) -> str:
    """Infer market from symbol/market column."""
    hint = market_hint.strip().lower()
    if hint in {"hk", "us", "cn"}:
        return {"hk": "hk", "us": "us", "cn": "china_a"}[hint]
    if symbol.endswith(".HK"):
        return "hk"
    if symbol.isalpha() or "." not in symbol:
        return "us"
    return "other"


def _futu_datetime(date_val: Any, time_val: Any) -> str:
    """Combine Futu Date+Time cells; Excel serial floats become ISO datetime."""
    # iterrows yields numpy integer/float scalars; bare pd.to_datetime(int) is ns-epoch.
    if pd.api.types.is_number(date_val) and not isinstance(date_val, (bool,)):
        if not (isinstance(date_val, float) and pd.isna(date_val)):
            serial = float(date_val)
            frac = 0.0
            time_is_frac = False
            if pd.api.types.is_number(time_val) and not isinstance(time_val, (bool,)):
                if not (isinstance(time_val, float) and pd.isna(time_val)):
                    candidate = float(time_val)
                    if 0.0 <= candidate < 1.0:
                        frac = candidate
                        time_is_frac = True
            ts = pd.to_datetime(serial + frac, unit="D", origin="1899-12-30", errors="coerce")
            if pd.notna(ts):
                if time_is_frac or time_val is None or (
                    isinstance(time_val, float) and pd.isna(time_val)
                ):
                    return ts.strftime("%Y-%m-%d %H:%M:%S")
                # Numeric Excel date + string/clock Time column.
                return f"{ts.strftime('%Y-%m-%d')} {str(time_val).strip()}".strip()
    # load_dataframe uses dtype=str; Excel serial dates arrive as "45321" / "45321.0".
    date_text = (
        ""
        if date_val is None or (isinstance(date_val, float) and pd.isna(date_val))
        else str(date_val).strip()
    )
    if date_text and not any(ch in date_text for ch in "/-:"):
        try:
            serial = float(date_text)
        except ValueError:
            serial = None
        else:
            if 1.0 <= serial < 100_000.0:
                frac = 0.0
                time_is_frac = False
                time_text = (
                    ""
                    if time_val is None or (isinstance(time_val, float) and pd.isna(time_val))
                    else str(time_val).strip()
                )
                if time_text and not any(ch in time_text for ch in "/-:"):
                    try:
                        candidate = float(time_text)
                    except ValueError:
                        candidate = None
                    else:
                        if 0.0 <= candidate < 1.0:
                            frac = candidate
                            time_is_frac = True
                ts = pd.to_datetime(serial + frac, unit="D", origin="1899-12-30", errors="coerce")
                if pd.notna(ts):
                    if time_is_frac or not time_text:
                        return ts.strftime("%Y-%m-%d %H:%M:%S")
                    return f"{ts.strftime('%Y-%m-%d')} {time_text}".strip()
    date = date_text
    time = "" if time_val is None or (isinstance(time_val, float) and pd.isna(time_val)) else str(time_val).strip()
    return f"{date} {time}".strip()


def parse_futu(df: pd.DataFrame) -> list[TradeRecord]:
    """Parse 富途 exports (English headers, HK+US mix).

    Expected columns: Date, Time, Symbol, Name, Side, Quantity, Price,
    Amount, Commission, Platform Fee, Market (optional).
    """
    records: list[TradeRecord] = []
    for _, row in df.iterrows():
        raw_symbol = row.get("Symbol", "")
        if _is_empty_code(raw_symbol):
            continue
        dt = _futu_datetime(row.get("Date", ""), row.get("Time", ""))
        symbol = str(raw_symbol).strip().upper()
        qty = _to_float(row.get("Quantity"))
        price = _to_float(row.get("Price"))
        amount = _to_float(row.get("Amount")) or qty * price
        fee = _to_float(row.get("Commission")) + _to_float(row.get("Platform Fee"))
        records.append(TradeRecord(
            datetime=dt,
            symbol=symbol,
            name=str(row.get("Name", "")).strip(),
            side=_normalize_side(row.get("Side") if "Side" in df.columns else row.get("Direction")),
            quantity=qty,
            price=price,
            amount=amount,
            fee=fee,
            market=_futu_market(symbol, str(row.get("Market", ""))),
        ))
    return records


def parse_generic(df: pd.DataFrame) -> list[TradeRecord]:
    """Parse a generic CSV with lowercase English headers.

    Matches columns case-insensitively. Expected (any alias in parens):
        datetime (time/date+time), symbol (ticker/code), name, side (direction),
        quantity (qty/size), price, amount (value/notional), fee (commission).
    """
    colmap: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower()
        colmap[key] = col

    def pick(*names: str) -> str | None:
        for n in names:
            if n in colmap:
                return colmap[n]
        return None

    dt_col = pick("datetime", "time")
    date_col = pick("date")
    sym_col = pick("symbol", "ticker", "code")
    name_col = pick("name", "instrument")
    side_col = pick("side", "direction", "action")
    qty_col = pick("quantity", "qty", "size", "volume")
    price_col = pick("price")
    amount_col = pick("amount", "value", "notional")
    fee_col = pick("fee", "commission", "fees")

    if side_col is None:
        raise ValueError(
            "Generic trade journal requires a side, direction, or action column"
        )

    records: list[TradeRecord] = []
    for _, row in df.iterrows():
        if sym_col and _is_empty_code(row.get(sym_col)):
            continue
        if dt_col:
            raw_dt = row.get(dt_col, "")
            dt = _generic_datetime_cell(raw_dt)
        elif date_col:
            raw_dt = row.get(date_col, "")
            dt = _generic_datetime_cell(raw_dt)
        else:
            dt = ""
        symbol = str(row.get(sym_col, "")).strip() if sym_col else ""
        qty = _to_float(row.get(qty_col)) if qty_col else 0.0
        price = _to_float(row.get(price_col)) if price_col else 0.0
        amount = _to_float(row.get(amount_col)) if amount_col else qty * price
        fee = _to_float(row.get(fee_col)) if fee_col else 0.0
        market = _infer_market_from_symbol(symbol)
        records.append(TradeRecord(
            datetime=dt,
            symbol=symbol.upper(),
            name=str(row.get(name_col, "")).strip() if name_col else "",
            side=_normalize_side(row.get(side_col)),
            quantity=qty,
            price=price,
            amount=amount or qty * price,
            fee=fee,
            market=market,
        ))
    return records


def _generic_datetime_cell(val: Any) -> str:
    """Normalize a generic datetime/date cell; Excel serials become ISO datetime."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if pd.api.types.is_number(val) and not isinstance(val, (bool,)):
        serial = float(val)
        if 1.0 <= serial < 100_000.0:
            ts = pd.to_datetime(serial, unit="D", origin="1899-12-30", errors="coerce")
            if pd.notna(ts):
                return ts.strftime("%Y-%m-%d %H:%M:%S")
    text = str(val).strip()
    if text and not any(ch in text for ch in "/-:"):
        try:
            serial = float(text)
        except ValueError:
            serial = None
        else:
            if 1.0 <= serial < 100_000.0:
                ts = pd.to_datetime(serial, unit="D", origin="1899-12-30", errors="coerce")
                if pd.notna(ts):
                    return ts.strftime("%Y-%m-%d %H:%M:%S")
    ts = pd.to_datetime(val, errors="coerce")
    if pd.notna(ts):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return text


def _infer_market_from_symbol(symbol: str) -> str:
    """Best-effort market inference from a symbol string."""
    s = symbol.upper()
    if s.endswith(".HK"):
        return "hk"
    if s.endswith(".SH") or s.endswith(".SZ") or s.endswith(".BJ"):
        return "china_a"
    if "-" in s and any(quote in s for quote in ("USDT", "USDC", "BTC", "USD")):
        return "crypto"
    # Binance-style concatenated pairs (BTCUSDT) are purely alphabetic, so the
    # isalpha() US-equity branch below would mis-label them without this check.
    for quote in ("USDT", "USDC", "BUSD"):
        if len(s) > len(quote) and s.endswith(quote):
            base = s[: -len(quote)]
            if base.isalpha() and len(base) >= 2:
                return "crypto"
    if s.isalpha():
        return "us"
    return "other"


_PARSERS = {
    "tonghuashun": parse_tonghuashun,
    "eastmoney": parse_eastmoney,
    "futu": parse_futu,
    "generic": parse_generic,
}


_TIGER_ACTIVITY_TYPES = frozenset({"股票", "期权"})
_TIGER_DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}")


def _read_csv_rows(path: Path) -> list[list[str]]:
    """Read a CSV with encoding fallback while preserving variable-width rows."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "gbk", "gb2312"):
        try:
            with path.open(encoding=encoding, newline="") as handle:
                return list(csv.reader(handle))
        except (UnicodeDecodeError, UnicodeError) as exc:
            last_error = exc
    raise ValueError(f"Failed to decode CSV with utf-8/utf-16/gbk/gb2312: {last_error}")


def _tiger_instrument(raw: str, market: str) -> tuple[str, str]:
    """Extract a stable symbol and display name from a Tiger instrument cell."""
    text = raw.strip()
    match = re.search(r"\(([^()]*)\)\s*$", text)
    symbol = (match.group(1) if match else text).strip().upper()
    name = text[: match.start()].strip() if match else text
    if market == "HK" and symbol.isdigit():
        symbol = f"{symbol.zfill(5)}.HK"
    elif market == "CN":
        symbol = _qualify_a_share(symbol)
    return symbol, name


def _tiger_datetime(raw: str) -> str:
    """Normalize Tiger's multiline timezone-labelled execution timestamp."""
    match = _TIGER_DATETIME_RE.search(" ".join(raw.split()))
    return match.group(0) if match else " ".join(raw.split()).strip()


def _tiger_number(raw: str, field: str, row_number: int, *, blank_zero: bool = False) -> float:
    """Parse a Tiger numeric cell without silently accepting malformed values."""
    text = _CURRENCY_TOKEN_RE.sub("", str(raw)).replace(",", "").strip()
    if not text and blank_zero:
        return 0.0
    try:
        value = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Tiger row {row_number} has invalid {field}: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Tiger row {row_number} has invalid {field}: {raw!r}")
    return value


def parse_tiger_activity_statement(path: str | Path) -> list[TradeRecord] | None:
    """Parse the order-level trade section from a Tiger activity statement.

    Returns ``None`` when the CSV is not a Tiger activity statement. Tiger also
    emits blank-instrument execution rows and ``TOTAL`` rows; those are omitted
    because the preceding named ``DATA`` row already contains the order total.
    """
    p = Path(path)
    if p.suffix.lower() != ".csv":
        return None
    rows = _read_csv_rows(p)
    if not any(row and row[0].lstrip("\ufeff") == "活动报表" for row in rows[:5]):
        return None

    header = next(
        (
            row
            for row in rows
            if len(row) > 10
            and row[0] == "交易明细"
            and row[4] == "代码"
            and "成交时间" in row
        ),
        None,
    )
    if header is None:
        raise ValueError("Tiger activity statement has no trade-detail section")

    columns = {name: index for index, name in enumerate(header) if name}
    required = {"代码", "市场", "交易类型", "数量", "交易价格", "成交额", "成交时间"}
    missing = sorted(required - columns.keys())
    if missing:
        raise ValueError(f"Tiger trade-detail section is missing columns: {missing}")

    amount_index = columns["成交额"]
    records: list[TradeRecord] = []
    for row_number, row in enumerate(rows, start=1):
        if (
            len(row) < amount_index + 6
            or row[0] != "交易明细"
            or row[3] != "DATA"
            or row[1] not in _TIGER_ACTIVITY_TYPES
            or not row[columns["代码"]].strip()
        ):
            continue

        market_code = row[columns["市场"]].strip().upper()
        symbol, name = _tiger_instrument(row[columns["代码"]], market_code)
        signed_quantity = _tiger_number(row[columns["数量"]], "quantity", row_number)
        quantity = abs(signed_quantity)
        price = abs(_tiger_number(row[columns["交易价格"]], "price", row_number))
        amount = abs(_tiger_number(row[amount_index], "amount", row_number))
        fees = sum(
            _tiger_number(value, "fee", row_number, blank_zero=True)
            for value in row[amount_index + 1 : -5]
        )
        if not symbol or quantity == 0:
            continue
        multiplier = amount / (price * quantity) if price and quantity else 1.0
        market = {"US": "us", "HK": "hk", "CN": "china_a"}.get(
            market_code,
            "other",
        )
        records.append(
            TradeRecord(
                datetime=_tiger_datetime(row[-3]),
                symbol=symbol,
                name=name,
                side="buy" if signed_quantity > 0 else "sell",
                quantity=quantity,
                price=price,
                amount=amount,
                fee=abs(fees),
                market=market,
                multiplier=multiplier,
            )
        )

    if not records:
        raise ValueError("Tiger activity statement contains no supported stock or option trades")
    return records


def parse_file(path: str | Path) -> tuple[FormatName, list[TradeRecord]]:
    """End-to-end: load file, detect format, parse.

    Args:
        path: File path.

    Returns:
        (format_name, records). Falls back to generic if detection is unknown
        but columns look parsable; otherwise raises ValueError.

    Raises:
        ValueError: Unknown format with no usable columns.
    """
    tiger_records = parse_tiger_activity_statement(path)
    if tiger_records is not None:
        return "tiger", tiger_records

    df = load_dataframe(path)
    fmt = detect_format(df)
    if fmt == "unknown":
        try:
            records = parse_generic(df)
            if records and records[0].symbol:
                return "generic", records
        except Exception:
            pass
        raise ValueError(f"Unrecognized trade journal format. Columns: {list(df.columns)}")
    return fmt, _PARSERS[fmt](df)


def records_to_dataframe(records: list[TradeRecord]) -> pd.DataFrame:
    """Convert records to a standardized DataFrame (datetime column parsed)."""
    if not records:
        return pd.DataFrame(columns=[f.name for f in TradeRecord.__dataclass_fields__.values()])
    df = pd.DataFrame([asdict(r) for r in records])
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df.sort_values("datetime").reset_index(drop=True)
