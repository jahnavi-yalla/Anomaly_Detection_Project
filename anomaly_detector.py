"""
anomaly_detector.py — Isolation Forest anomaly detection engine
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    "total_sales","transaction_count","avg_transaction",
    "rolling_7d_mean","rolling_7d_std","day_of_week","month",
]

def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    if "total_sales" in df.columns and "transaction_count" in df.columns:
        daily = df.groupby("date").agg(
            total_sales      =("total_sales","sum"),
            transaction_count=("transaction_count","sum"),
        ).reset_index().sort_values("date")
        if "avg_transaction" in df.columns:
            avg = df.groupby("date")["avg_transaction"].mean().reset_index()
            daily = daily.merge(avg, on="date", how="left")
        else:
            daily["avg_transaction"] = daily["total_sales"] / daily["transaction_count"].replace(0,1)
    elif "amount" in df.columns:
        daily = df.groupby("date").agg(
            total_sales      =("amount","sum"),
            transaction_count=("amount","count"),
            avg_transaction  =("amount","mean"),
        ).reset_index().sort_values("date")
    else:
        raise ValueError("Dataset must contain total_sales and transaction_count columns")

    daily["rolling_7d_mean"] = daily["total_sales"].rolling(7, min_periods=1).mean()
    daily["rolling_7d_std"]  = daily["total_sales"].rolling(7, min_periods=1).std().fillna(0)
    daily["day_of_week"]     = daily["date"].dt.dayofweek
    daily["month"]           = daily["date"].dt.month
    daily["avg_transaction"] = daily["avg_transaction"].fillna(0)
    return daily

class SalesAnomalyDetector:
    def __init__(self, contamination=0.05, random_state=42):
        self.contamination = contamination
        self._scaler = StandardScaler()
        self._model  = IsolationForest(contamination=contamination,
                                        random_state=random_state, n_estimators=200)
        self._fitted = False

    def fit_predict(self, daily_df):
        df = daily_df.copy()
        X  = df[FEATURE_COLS].values
        Xs = self._scaler.fit_transform(X)
        self._model.fit(Xs)
        self._fitted = True
        df["anomaly_label"] = self._model.predict(Xs) == -1
        df["anomaly_score"] = self._model.score_samples(Xs)
        return df
