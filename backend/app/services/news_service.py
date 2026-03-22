"""
Load local cached datasets under `data/` (repo root).
Paths: prices/{TICKER}.csv, fundamentals/{TICKER}.json, news/{TICKER}.json, metrics/{TICKER}.json
Read-only; no LLM.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    # app/services/news_service.py -> parents[3] = inflect/
    return Path(__file__).resolve().parents[3]


def _data_dir() -> Path:
    return _repo_root() / "data"


def load_fundamentals_json(ticker: str) -> dict[str, Any] | None:
    p = _data_dir() / "fundamentals" / f"{ticker.upper()}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_news_json(ticker: str) -> dict[str, Any] | list[Any] | None:
    p = _data_dir() / "news" / f"{ticker.upper()}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_metrics_json(ticker: str) -> dict[str, Any] | None:
    p = _data_dir() / "metrics" / f"{ticker.upper()}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_prices_csv_tail(ticker: str, max_rows: int = 5) -> list[dict[str, str]] | None:
    """Return last N rows of OHLCV CSV as dicts if file exists."""
    p = _data_dir() / "prices" / f"{ticker.upper()}.csv"
    if not p.is_file():
        return None
    try:
        with p.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return []
        return rows[-max_rows:]
    except Exception:
        return None


def build_local_context_block(ticker: str | None) -> str:
    """Compact text block for orchestrator to append to research prompt."""
    if not ticker:
        return ""
    t = ticker.upper()
    parts: list[str] = []
    fn = load_fundamentals_json(t)
    if fn is not None:
        parts.append(f"Local fundamentals JSON keys: {list(fn.keys())[:12]}")
    nw = load_news_json(t)
    if nw is not None:
        s = str(nw)[:800]
        parts.append(f"Local news sample: {s}")
    mt = load_metrics_json(t)
    if mt is not None:
        parts.append(f"Local metrics sample: {str(mt)[:600]}")
    px = read_prices_csv_tail(t, max_rows=3)
    if px:
        parts.append(f"Local price CSV tail rows: {px}")
    if not parts:
        return ""
    return "\n\nLocal dataset hints (cached files):\n" + "\n".join(parts)
