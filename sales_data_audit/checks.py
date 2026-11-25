"""Checks over rows of a sell-out file.

Expected columns: date (YYYY-MM-DD), store, sku, product, units, price.
Each check returns a list of findings: dicts with check, severity, rows, message.
"""
from __future__ import annotations

import difflib
import re
import statistics
from collections import defaultdict
from datetime import date, timedelta

REQUIRED = ["date", "store", "sku", "product", "units", "price"]


def finding(check, severity, rows, message):
    return {"check": check, "severity": severity, "rows": sorted(rows), "message": message}


def _num(value):
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return None


def _date(value):
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def check_missing(rows):
    out = []
    for col in REQUIRED:
        bad = [r["_line"] for r in rows if not str(r.get(col, "")).strip()]
        if bad:
            out.append(finding("missing_value", "high", bad, f"{len(bad)} rows have an empty '{col}'"))
    return out


def check_bad_types(rows):
    out = []
    bad_dates = [r["_line"] for r in rows if str(r.get("date", "")).strip() and _date(r["date"]) is None]
    if bad_dates:
        out.append(finding("bad_date", "high", bad_dates, f"{len(bad_dates)} rows have a date that is not YYYY-MM-DD"))
    for col in ("units", "price"):
        bad = [r["_line"] for r in rows if str(r.get(col, "")).strip() and _num(r[col]) is None]
        if bad:
            out.append(finding("bad_number", "high", bad, f"{len(bad)} rows have a '{col}' that is not a number"))
    return out


def check_duplicates(rows):
    seen = defaultdict(list)
    for r in rows:
        seen[(r.get("date"), r.get("store"), r.get("sku"))].append(r["_line"])
    out = []
    for key, lines in seen.items():
        if len(lines) > 1:
            out.append(finding("duplicate_key", "high", lines,
                               f"{len(lines)} rows share date={key[0]} store={key[1]} sku={key[2]}"))
    return out


def check_non_positive(rows):
    out = []
    for col in ("units", "price"):
        bad = [r["_line"] for r in rows if (_num(r.get(col, "")) is not None and _num(r[col]) <= 0)]
        if bad:
            out.append(finding("non_positive", "medium", bad, f"{len(bad)} rows have '{col}' <= 0 (returns? or errors)"))
    return out


def check_price_outliers(rows, threshold=5.0):
    """Robust z-score (median and MAD) of price inside each SKU."""
    by_sku = defaultdict(list)
    for r in rows:
        p = _num(r.get("price", ""))
        if p is not None and p > 0:
            by_sku[r.get("sku")].append((r["_line"], p))
    out = []
    for sku, items in by_sku.items():
        if len(items) < 5:
            continue
        prices = [p for _, p in items]
        med = statistics.median(prices)
        mad = statistics.median(abs(p - med) for p in prices) or med * 0.02
        bad = [ln for ln, p in items if abs(p - med) / (1.4826 * mad) > threshold]
        if bad:
            out.append(finding("price_outlier", "medium", bad,
                               f"SKU {sku}: {len(bad)} prices far from the usual {med:.2f}"))
    return out


def check_date_gaps(rows, min_gap_days=2):
    by_store = defaultdict(set)
    for r in rows:
        d = _date(r.get("date", ""))
        if d:
            by_store[r.get("store")].add(d)
    out = []
    for store, days in by_store.items():
        ordered = sorted(days)
        for a, b in zip(ordered, ordered[1:]):
            if (b - a).days > min_gap_days:
                missing = (b - a).days - 1
                out.append(finding("date_gap", "medium", [],
                                   f"Store {store}: {missing} days with no data between {a} and {b}"))
    return out


def _norm(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).split()


def check_name_variants(rows, cutoff=0.8):
    """Different SKU codes with almost the same product name, or one SKU with many names."""
    names_by_sku = defaultdict(set)
    for r in rows:
        if r.get("sku") and r.get("product"):
            names_by_sku[r["sku"]].add(r["product"].strip())
    out = []
    for sku, names in names_by_sku.items():
        if len(names) > 1:
            out.append(finding("sku_many_names", "low", [], f"SKU {sku} has {len(names)} spellings: {sorted(names)}"))
    firsts = {sku: sorted(n)[0] for sku, n in names_by_sku.items()}
    skus = sorted(firsts)
    for i, a in enumerate(skus):
        for b in skus[i + 1:]:
            ratio = difflib.SequenceMatcher(None, " ".join(sorted(_norm(firsts[a]))), " ".join(sorted(_norm(firsts[b])))).ratio()
            if ratio >= cutoff:
                out.append(finding("name_near_duplicate", "medium", [],
                                   f"SKUs {a} and {b} look like the same product: '{firsts[a]}' / '{firsts[b]}'"))
    return out


def run_all(rows):
    findings = []
    for fn in (check_missing, check_bad_types, check_duplicates, check_non_positive,
               check_price_outliers, check_date_gaps, check_name_variants):
        findings.extend(fn(rows))
    return findings
