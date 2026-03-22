"""
Price history (sparklines) and metric snapshots for UI cards.

Uses yfinance for OHLC history; Snowflake fundamentals + metrics with yfinance fallback.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.snowflake_rag_service import get_fundamentals, get_metrics

RANGE_YF: dict[str, tuple[str, str]] = {
    "7d": ("7d", "1d"),
    "30d": ("1mo", "1d"),
    "90d": ("3mo", "1d"),
}

# Intent classifier and free-text aliases -> fundamentals / metrics keys
_METRIC_ALIASES: dict[str, str] = {
    "gross_margin": "gross_margin",
    "grossmargin": "gross_margin",
    "gross": "gross_margin",
    "profit_margin": "profit_margin",
    "profitmargin": "profit_margin",
    "margin": "gross_margin",
    "revenue": "revenue",
    "sales": "revenue",
    "eps": "eps",
    "earnings": "eps",
    "pe_ratio": "pe_ratio",
    "pe": "pe_ratio",
    "p/e": "pe_ratio",
    "p_e": "pe_ratio",
    "roe": "roe",
    "fcf": "fcf",
    "free_cash_flow": "fcf",
    "beta": "beta",
    "debt": "debt_equity",
    "debt_equity": "debt_equity",
    "debt_to_equity": "debt_equity",
    "dividend": "div_yield",
    "div_yield": "div_yield",
    "yield": "div_yield",
}

_LABELS: dict[str, str] = {
    "gross_margin": "Gross Margin",
    "profit_margin": "Profit Margin",
    "revenue": "Revenue",
    "eps": "EPS",
    "pe_ratio": "P/E Ratio",
    "roe": "ROE",
    "fcf": "Free Cash Flow",
    "beta": "Beta",
    "debt_equity": "Debt / Equity",
    "div_yield": "Dividend Yield",
}


def normalize_metric_key(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    s = re.sub(r"[\s\-/]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return _METRIC_ALIASES.get(s, s if s in _LABELS else None)


def fetch_market_history(ticker: str, range_key: str) -> dict[str, Any]:
    import yfinance as yf

    if range_key not in RANGE_YF:
        range_key = "30d"
    period, interval = RANGE_YF[range_key]
    t = ticker.upper().strip()
    hist = yf.Ticker(t).history(period=period, interval=interval)
    points: list[dict[str, Any]] = []
    sparkline: list[dict[str, float]] = []
    if hist is None or hist.empty:
        return {
            "ticker": t,
            "range": range_key,
            "points": points,
            "sparkline": sparkline,
        }
    for idx, row in hist.iterrows():
        d = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        c = round(float(row["Close"]), 4)
        points.append({"date": d, "close": c})
        sparkline.append({"v": c})
    return {
        "ticker": t,
        "range": range_key,
        "points": points,
        "sparkline": sparkline,
    }


def _fmt_pct(x: Any) -> str | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if abs(v) <= 1.5 and v != 0:
        return f"{v * 100:.1f}%"
    return f"{v:.1f}%"


def _fmt_billions(x: Any) -> str | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if abs(v) >= 1e9:
        return f"${v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.2f}M"
    return f"${v:,.0f}"


def _fmt_num(x: Any) -> str | None:
    if x is None:
        return None
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return None


def _yfinance_info(ticker: str) -> dict[str, Any]:
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info or {}
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def build_metric_card(ticker: str, metric_key: str) -> dict[str, Any]:
    """
    Build a MetricCardResponse-shaped dict.
    """
    t = ticker.upper().strip()
    key = normalize_metric_key(metric_key) or metric_key.lower().strip()
    if key not in _LABELS:
        key = normalize_metric_key(metric_key.replace("_", " ")) or key

    label = _LABELS.get(key, key.replace("_", " ").title())
    fund = get_fundamentals(t) if key in _LABELS else {}
    mrow = get_metrics(t)
    # One yfinance info fetch for gaps Snowflake does not fill (or when fund row missing).
    yf_info = _yfinance_info(t)

    if not fund and not yf_info and not mrow:
        return {
            "metric_key": key,
            "metric": label,
            "value": "—",
            "period": "TTM",
            "change": None,
            "change_direction": None,
            "source": "UNAVAILABLE",
            "citation": None,
        }

    source: str = "SNOWFLAKE" if fund else "YFINANCE"
    value_str = "—"
    change: str | None = None
    direction: str | None = None
    period = "TTM"

    def rg_direction(rg: Any) -> tuple[str | None, str | None]:
        if rg is None:
            return None, None
        try:
            v = float(rg) * 100
            ch = f"{v:+.1f}% YoY"
            d = "up" if v >= 0 else "down"
            return ch, d
        except (TypeError, ValueError):
            return None, None

    if key == "gross_margin":
        raw = fund.get("gross_margin") if fund else None
        if raw is None:
            raw = yf_info.get("grossMargins")
        value_str = _fmt_pct(raw) or "—"
        rg = mrow.get("revenue_growth") if mrow else yf_info.get("revenueGrowth")
        change, direction = rg_direction(rg)
    elif key == "profit_margin":
        raw = fund.get("profit_margin") if fund else None
        if raw is None:
            raw = yf_info.get("profitMargins")
        value_str = _fmt_pct(raw) or "—"
    elif key == "revenue":
        raw = fund.get("revenue") if fund else None
        if raw is None:
            raw = yf_info.get("totalRevenue")
        value_str = _fmt_billions(raw) or "—"
        rg = mrow.get("revenue_growth") if mrow else yf_info.get("revenueGrowth")
        change, direction = rg_direction(rg)
    elif key == "eps":
        raw = fund.get("eps") if fund else None
        if raw is None:
            raw = yf_info.get("trailingEps")
        value_str = _fmt_num(raw) or "—"
    elif key == "pe_ratio":
        raw = fund.get("pe_ratio") if fund else None
        if raw is None:
            raw = yf_info.get("trailingPE")
        value_str = _fmt_num(raw) or "—"
    elif key == "roe":
        raw = fund.get("roe") if fund else None
        if raw is None:
            raw = yf_info.get("returnOnEquity")
        value_str = _fmt_pct(raw) if raw is not None else "—"
    elif key == "fcf":
        raw = fund.get("fcf") if fund else None
        if raw is None:
            raw = yf_info.get("freeCashflow")
        value_str = _fmt_billions(raw) or _fmt_num(raw) or "—"
    elif key == "beta":
        raw = fund.get("beta") if fund else None
        if raw is None:
            raw = mrow.get("beta") if mrow else None
        if raw is None:
            raw = yf_info.get("beta")
        value_str = _fmt_num(raw) or "—"
    elif key == "debt_equity":
        raw = fund.get("debt_equity") if fund else None
        if raw is None:
            raw = yf_info.get("debtToEquity")
        value_str = _fmt_num(raw) or "—"
    elif key == "div_yield":
        raw = fund.get("div_yield") if fund else None
        if raw is None:
            raw = yf_info.get("dividendYield")
        value_str = _fmt_pct(raw) if raw is not None else "—"
    else:
        value_str = "—"
        source = "UNAVAILABLE"

    if value_str == "—" and yf_info:
        source = "YFINANCE"

    return {
        "metric_key": key,
        "metric": label,
        "value": value_str,
        "period": period,
        "change": change,
        "change_direction": direction,
        "source": source if value_str != "—" else "UNAVAILABLE",
        "citation": None,
    }
