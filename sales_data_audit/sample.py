"""Invented example data with known problems planted in it (not real sales)."""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta

PRODUCTS = {
    "P001": ("Cola Soda 2L", 8.50),
    "P002": ("Orange Juice 1L", 7.20),
    "P003": ("Corn Chips 150g", 6.10),
    "P004": ("Sparkling Water 500ml", 3.30),
    "P005": ("Chocolate Bar 90g", 5.00),
    "P006": ("Cola Soda Zero 2L", 8.50),
}
STORES = ["S01", "S02", "S03"]

# What make_sample() plants. Tests check the audit finds each one.
PLANTED = {"duplicates": 3, "negative_units": 2, "price_typo": 2, "empty_product": 2, "gap_days": 5, "bad_date": 1}


def make_sample(path, seed=7, days=60):
    rng = random.Random(seed)
    start = date(2026, 1, 1)
    rows = []
    for d in range(days):
        day = start + timedelta(days=d)
        for store in STORES:
            if store == "S02" and 20 <= d < 20 + PLANTED["gap_days"]:
                continue  # store S02 stopped sending data
            for sku, (name, base) in PRODUCTS.items():
                rows.append({"date": day.isoformat(), "store": store, "sku": sku, "product": name,
                             "units": rng.randint(3, 40), "price": round(base * rng.uniform(0.97, 1.03), 2)})
    rows[10]["units"] = -4
    rows[200]["units"] = -1
    rows[300]["price"] = round(rows[300]["price"] * 10, 2)  # misplaced decimal point
    rows[400]["price"] = round(rows[400]["price"] / 10, 2)
    rows[500]["product"] = ""
    rows[600]["product"] = ""
    rows[700]["date"] = "31/02/2026"
    for i in (50, 150, 250):
        rows.append(dict(rows[i]))
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "store", "sku", "product", "units", "price"])
        w.writeheader()
        w.writerows(rows)
    return len(rows)
