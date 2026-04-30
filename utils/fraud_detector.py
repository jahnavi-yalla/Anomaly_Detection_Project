import pandas as pd
import numpy as np

def detect_fraud(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["fraud_score"] = 0
    df["fraud_reason"] = ""
    amt = next((c for c in ["avg_transaction","total_sales","amount"] if c in df.columns), None)
    if amt is None: return pd.DataFrame()
    mean_amt = df[amt].mean(); std_amt = df[amt].std()
    mean_txn = df["transaction_count"].mean() if "transaction_count" in df.columns else None
    std_txn  = df["transaction_count"].std()  if "transaction_count" in df.columns else None
    mask1 = df[amt] > mean_amt + 2.5*std_amt
    df.loc[mask1,"fraud_score"] += 4
    df.loc[mask1,"fraud_reason"] += "LARGE_TRANSACTION; "
    mask2 = df[amt].round(0).isin([9999,10000,4999,14999,19999])
    df.loc[mask2,"fraud_score"] += 3
    df.loc[mask2,"fraud_reason"] += "ROUND_AMOUNT; "
    if mean_txn is not None:
        mask3 = df["transaction_count"] > mean_txn + 2.0*std_txn
        df.loc[mask3,"fraud_score"] += 3
        df.loc[mask3,"fraud_reason"] += "HIGH_FREQUENCY; "
    mask4 = (df[amt] < mean_amt - 3.0*std_amt) & (df[amt] > 0)
    df.loc[mask4,"fraud_score"] += 2
    df.loc[mask4,"fraud_reason"] += "SUPPRESSED_SALES; "
    df["fraud_reason"] = df["fraud_reason"].str.strip("; ").str.strip()
    flagged = df[df["fraud_score"] >= 3].copy()
    out_cols = ["date"]
    for col in ["region","product_category","payment_method","transaction_count",amt,"fraud_score","fraud_reason"]:
        if col and col in flagged.columns and col not in out_cols:
            out_cols.append(col)
    return flagged[out_cols].sort_values("fraud_score",ascending=False).reset_index(drop=True)

def fraud_summary(flagged_df):
    if flagged_df.empty:
        return {"total_flagged":0,"total_at_risk":0.0,"top_region":"N/A","top_reason":"N/A"}
    amt = next((c for c in ["avg_transaction","total_sales","amount"] if c in flagged_df.columns),None)
    region_col = "region" if "region" in flagged_df.columns else None
    reasons = flagged_df["fraud_reason"].str.split("; ").explode()
    reasons = reasons[reasons.str.strip() != ""]
    return {
        "total_flagged": len(flagged_df),
        "total_at_risk": round(flagged_df[amt].sum(),2) if amt else 0.0,
        "top_region": flagged_df[region_col].value_counts().idxmax() if region_col else "N/A",
        "top_reason": reasons.value_counts().idxmax() if not reasons.empty else "N/A",
    }
