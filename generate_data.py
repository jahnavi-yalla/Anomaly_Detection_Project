"""
generate_data.py — Run this once to create sample sales data
Usage: python generate_data.py
"""
import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)
days  = 365
dates = pd.date_range("2024-01-01", periods=days)
sales = np.random.normal(5000, 1000, days)

# Inject anomalies
for d, mult in [(50,4.5),(120,0.08),(200,3.8),(280,0.05),(300,4.2),(340,0.07)]:
    sales[d] *= mult

txns = np.random.randint(30, 80, days)

df = pd.DataFrame({
    "date":             dates.strftime("%Y-%m-%d"),
    "total_sales":      np.round(np.abs(sales), 2),
    "transaction_count":txns,
    "avg_transaction":  np.round(np.abs(sales)/txns, 2),
    "region":           np.random.choice(["North","South","East","West"], days),
    "product_category": np.random.choice(["Electronics","Clothing","Food","Home"], days),
    "payment_method":   np.random.choice(["UPI","Card","Cash","NetBanking"], days),
})

Path("data").mkdir(exist_ok=True)
df.to_csv("data/sales_data.csv", index=False)
print(f"✅ Generated {len(df)} days of sales data → data/sales_data.csv")
print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
print(f"   Anomalies injected on days: 50, 120, 200, 280, 300, 340")
