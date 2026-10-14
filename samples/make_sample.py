"""Builds samples/coffee_shop_sales.csv - a realistic demo file with known patterns.

Patterns planted on purpose (Tally should find these):
  * sales grow steadily over the two years
  * weekends are busier than weekdays
  * the Airport store charges more per item and gets lower ratings
  * members give higher ratings than walk-in customers
  * a handful of huge catering orders in October 2024
Things that are pure noise (Tally should NOT report these):
  * payment method, barista
"""

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
stores = ["Downtown", "Campus", "Airport", "Suburb"]
store_p = [0.4, 0.25, 0.15, 0.2]
cats = {"Coffee": 4.5, "Tea": 3.75, "Pastry": 3.25, "Sandwich": 8.5, "Merch": 18.0}
cat_p = [0.45, 0.15, 0.2, 0.15, 0.05]
baristas = ["Alex", "Sam", "Jordan", "Riley", "Casey", "Morgan"]

rows = []
order_id = 10001
for i, day in enumerate(days):
    growth = 1 + 0.35 * i / len(days)
    weekend = 1.55 if day.dayofweek >= 5 else 1.0
    n = rng.poisson(5.2 * growth * weekend)
    for _ in range(n):
        store = rng.choice(stores, p=store_p)
        cat = rng.choice(list(cats), p=cat_p)
        member = rng.random() < 0.35
        qty = int(rng.choice([1, 1, 1, 2, 2, 3, 4]))
        price = cats[cat] * (1.25 if store == "Airport" else 1.0) * rng.uniform(0.95, 1.05)
        rating = 4.0 + (0.45 if member else 0) - (0.6 if store == "Airport" else 0) + rng.normal(0, 0.6)
        rating = int(np.clip(round(rating), 1, 5))
        rows.append({
            "Order ID": order_id, "Date": day.strftime("%m/%d/%Y"), "Store": store, "Category": cat,
            "Customer Type": "Member" if member else "Walk-in", "Quantity": qty,
            "Unit Price": round(price, 2), "Payment Method": rng.choice(["Card", "Cash", "Mobile"]),
            "Barista": rng.choice(baristas), "Rating": rating,
        })
        order_id += 1

# a few big catering orders
for d in ["2024-10-04", "2024-10-11", "2024-10-18", "2024-10-25"]:
    rows.append({
        "Order ID": order_id, "Date": pd.Timestamp(d).strftime("%m/%d/%Y"), "Store": "Downtown", "Category": "Sandwich",
        "Customer Type": "Walk-in", "Quantity": int(rng.integers(45, 70)), "Unit Price": 8.5,
        "Payment Method": "Card", "Barista": "Alex", "Rating": 5,
    })
    order_id += 1

df = pd.DataFrame(rows).sort_values(["Date", "Order ID"], key=lambda s: pd.to_datetime(s) if s.name == "Date" else s)
df["Revenue"] = (df["Quantity"] * df["Unit Price"]).round(2)
df["Unit Price"] = df["Unit Price"].map(lambda v: f"${v:,.2f}")
df["Revenue"] = df["Revenue"].map(lambda v: f"${v:,.2f}")
out = Path(__file__).with_name("coffee_shop_sales.csv")
df.to_csv(out, index=False)
print(f"wrote {len(df)} rows to {out}")
