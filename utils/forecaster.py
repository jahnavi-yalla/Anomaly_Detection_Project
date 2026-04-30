import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json

PLOT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#9ca3af", size=11),
    xaxis=dict(gridcolor="rgba(0,0,0,.05)", zeroline=False, showline=False),
    yaxis=dict(gridcolor="rgba(0,0,0,.05)", zeroline=False, showline=False),
    margin=dict(l=4, r=4, t=36, b=8), height=400,
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0,
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#fff", bordercolor="#e2e8f0",
                    font=dict(family="Inter", size=12, color="#111827")),
)

def run_forecast(result_df, periods=30):
    df = result_df[["date","total_sales"]].rename(columns={"date":"ds","total_sales":"y"})
    df["ds"] = pd.to_datetime(df["ds"])
    try:
        from prophet import Prophet
        m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        m.fit(df)
        future   = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        engine   = "prophet"
    except:
        x = np.arange(len(df))
        coeffs = np.polyfit(x, df["y"].values, 1)
        future_x = np.arange(len(df), len(df)+periods)
        future_dates = pd.date_range(df["ds"].max()+pd.Timedelta(days=1), periods=periods)
        yhat = np.polyval(coeffs, np.concatenate([x, future_x]))
        std  = df["y"].std()
        all_dates = pd.concat([df["ds"], pd.Series(future_dates)]).reset_index(drop=True)
        forecast = pd.DataFrame({"ds":all_dates,"yhat":yhat,
                                  "yhat_lower":yhat-1.96*std,"yhat_upper":yhat+1.96*std})
        engine = "linear"

    fut = forecast[forecast["ds"] > df["ds"].max()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["ds"],y=df["y"],mode="lines",
        line=dict(color="#4f46e5",width=2),name="Historical"))
    fig.add_trace(go.Scatter(
        x=pd.concat([fut["ds"],fut["ds"][::-1]]),
        y=pd.concat([fut["yhat_upper"],fut["yhat_lower"][::-1]]),
        fill="toself",fillcolor="rgba(79,70,229,.1)",
        line=dict(color="rgba(0,0,0,0)"),name="Confidence"))
    fig.add_trace(go.Scatter(x=fut["ds"],y=fut["yhat"],mode="lines",
        line=dict(color="#7c3aed",width=2.5,dash="dash"),name="Forecast"))
    fig.update_layout(**PLOT)
    return {"fig_json": fig.to_json(), "forecast_df": forecast, "engine": engine}
