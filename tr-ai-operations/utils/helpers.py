"""General-purpose helpers: safe parsing, date math, formatting."""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional

import pandas as pd


def parse_date(value) -> Optional[dt.date]:
    """Best-effort parse of a spreadsheet cell into a date. Returns None if empty/invalid."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "-"}:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # last resort: let pandas try
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors="raise")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def parse_numeric(value) -> Optional[float]:
    """Best-effort parse of a numeric cell. Returns None if empty/invalid."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and pd.isna(value):
            return None
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-"}:
        return None
    text = text.replace(",", "")
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def normalize_header(name: str) -> str:
    """Lower-case, strip punctuation/whitespace variance for header matching."""
    name = str(name).strip().lower()
    name = name.replace("#", "")
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return False


def days_between(start: Optional[dt.date], end: Optional[dt.date]) -> Optional[int]:
    if start is None or end is None:
        return None
    return (end - start).days
