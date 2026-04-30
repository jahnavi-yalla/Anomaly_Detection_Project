"""
StreamSight — Flask Business Intelligence Platform
Run: python app.py
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import pandas as pd
import numpy as np
from pathlib import Path
import io, os, json

from anomaly_detector import SalesAnomalyDetector, aggregate_daily
from database import (
    init_db, verify_user, get_settings, save_settings,
    log_dataset, get_datasets, save_anomaly_run, get_anomaly_history,
    save_fraud_run, get_fraud_history, log_alert, get_alert_logs,
    get_db_summary, get_all_users, add_user, delete_user
)
from utils.fraud_detector import detect_fraud, fraud_summary
from utils.forecaster import run_forecast
from utils.email_notifier import send_anomaly_alert
from utils.pdf_report import generate_pdf_report

app = Flask(__name__)
app.secret_key = "streamsight_secret_key_2024"

# Initialize database on startup
init_db()

DATA_PATH = Path("data/sales_data.csv")

BUSINESS_PROFILES = {
    "Retail Store":        {"icon":"🏪","color":"#6366f1","metric":"Revenue"},
    "Restaurant":          {"icon":"🍽️","color":"#f59e0b","metric":"Orders"},
    "E-Commerce":          {"icon":"🛒","color":"#0ea5e9","metric":"GMV"},
    "Hospital/Clinic":     {"icon":"🏥","color":"#10b981","metric":"Billing"},
    "Warehouse/Logistics": {"icon":"🏭","color":"#8b5cf6","metric":"Throughput"},
    "Custom Business":     {"icon":"📊","color":"#e11d48","metric":"Revenue"},
}

# Users are now stored in SQLite database (see database.py)

ROLE_PERMISSIONS = {
    "Admin":   ["dashboard","anomalies","analytics","forecast","fraud","live","reports","settings"],
    "Manager": ["dashboard","anomalies","analytics","forecast","fraud","live","reports"],
    "Viewer":  ["dashboard","anomalies","analytics"],
}

# ── In-memory data store ───────────────────────────────────────────
_store = {"df": None, "result_df": None, "raw_df": None,
          "contamination": 0.05, "biz_type": "Retail Store",
          "uploaded_name": None}

def get_data():
    if _store["result_df"] is not None:
        return _store["result_df"], _store["raw_df"]
    if DATA_PATH.exists():
        raw = pd.read_csv(DATA_PATH, parse_dates=["date"])
        daily = aggregate_daily(raw)
        result = SalesAnomalyDetector(contamination=_store["contamination"]).fit_predict(daily)
        _store["result_df"] = result
        _store["raw_df"]    = raw
        return result, raw
    return None, None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def can_access(page):
    role = session.get("role","Viewer")
    return page in ROLE_PERMISSIONS.get(role,[])

# ════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ════════════════════════════════════════════════════════════════════
@app.route("/")
def home():
    """Home page with welcome ribbon and Sign Up/Login buttons."""
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration page."""
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not username or not email or not password:
            error = "All fields are required"
        elif password != confirm_password:
            error = "Passwords do not match"
        elif len(password) < 6:
            error = "Password must be at least 6 characters"
        else:
            # Add user with 'Viewer' role by default
            success, message = add_user(username, password, "Viewer", email)
            if success:
                return redirect(url_for("login", signup_success=True))
            else:
                error = message
    
    return render_template("signin.html", error=error)

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    signup_success = request.args.get("signup_success", False)
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        user = verify_user(username, password)
        if user:
            session["user"]    = username
            session["role"]    = user["role"]
            session["name"]    = user["display_name"]
            # Load user settings from DB
            s = get_settings(username)
            _store["contamination"] = s.get("contamination", 0.05)
            _store["biz_type"]      = s.get("biz_type", "Retail Store")
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error, signup_success=signup_success)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ════════════════════════════════════════════════════════════════════
# UPLOAD
# ════════════════════════════════════════════════════════════════════
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if "file" not in request.files:
        return jsonify({"success":False,"message":"No file uploaded"})
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"success":False,"message":"No file selected"})
    try:
        if f.filename.endswith((".xlsx",".xls")):
            df = pd.read_excel(f)
        else:
            df = pd.read_csv(f)
        required = ["date","total_sales","transaction_count"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            return jsonify({"success":False,"message":f"Missing columns: {', '.join(missing)}"})
        df["date"] = pd.to_datetime(df["date"])
        for col, fn in [
            ("avg_transaction",  lambda d: d["total_sales"]/d["transaction_count"]),
            ("region",           lambda d: pd.Series(["Default"]*len(d))),
            ("product_category", lambda d: pd.Series(["General"]*len(d))),
            ("payment_method",   lambda d: pd.Series(["Unknown"]*len(d))),
        ]:
            if col not in df.columns: df[col] = fn(df)
        daily  = aggregate_daily(df)
        result = SalesAnomalyDetector(contamination=_store["contamination"]).fit_predict(daily)
        _store["result_df"]    = result
        _store["raw_df"]       = df
        _store["uploaded_name"] = f.filename
        anomalies = result[result["anomaly_label"]]
        return jsonify({
            "success":True,
            "message":f"{f.filename} loaded — {len(df):,} rows",
            "rows": len(df),
            "anomalies": len(anomalies),
            "date_range": f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
        })
    except Exception as e:
        return jsonify({"success":False,"message":str(e)})

@app.route("/clear_upload", methods=["POST"])
@login_required
def clear_upload():
    _store["result_df"]    = None
    _store["raw_df"]       = None
    _store["uploaded_name"] = None
    get_data()
    return jsonify({"success":True})

@app.route("/set_biz", methods=["POST"])
@login_required
def set_biz():
    biz = request.json.get("biz","Retail Store")
    if biz in BUSINESS_PROFILES:
        _store["biz_type"] = biz
    return jsonify({"success":True})

# ════════════════════════════════════════════════════════════════════
# DASHBOARD ROUTES
# ════════════════════════════════════════════════════════════════════
def base_ctx():
    result_df, raw_df = get_data()
    if result_df is None:
        return None
    anomalies = result_df[result_df["anomaly_label"]]
    anom_pct  = len(anomalies)/len(result_df)*100
    biz       = BUSINESS_PROFILES[_store["biz_type"]]
    return {
        "result_df":result_df,"raw_df":raw_df,
        "anomalies":anomalies,"normals":result_df[~result_df["anomaly_label"]],
        "anom_pct":anom_pct,"biz":biz,
        "biz_type":_store["biz_type"],
        "biz_profiles":BUSINESS_PROFILES,
        "contamination":_store["contamination"],
        "uploaded_name":_store["uploaded_name"],
        "username":session.get("name","User"),
        "role":session.get("role","Viewer"),
        "can_access":can_access,
        "pages":ROLE_PERMISSIONS.get(session.get("role","Viewer"),[]),
    }

@app.route("/dashboard")
@login_required
def dashboard():
    if not can_access("dashboard"): return redirect(url_for("login"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html", msg="No data found. Run generate_data.py first.")
    result_df = ctx["result_df"]; anomalies = ctx["anomalies"]; normals = ctx["normals"]

    # Sales trend chart
    import plotly.graph_objects as go
    import plotly.utils
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.concat([result_df["date"],result_df["date"][::-1]]).astype(str).tolist(),
        y=pd.concat([result_df["rolling_7d_mean"]+result_df["rolling_7d_std"],
                     (result_df["rolling_7d_mean"]-result_df["rolling_7d_std"])[::-1]]).tolist(),
        fill="toself",fillcolor="rgba(79,70,229,.07)",
        line=dict(color="rgba(0,0,0,0)"),hoverinfo="skip",name="Band"))
    fig.add_trace(go.Scatter(x=normals["date"].astype(str).tolist(),y=normals["total_sales"].tolist(),
        mode="lines",line=dict(color="#4f46e5",width=2),name="Normal Sales"))
    fig.add_trace(go.Scatter(x=result_df["date"].astype(str).tolist(),y=result_df["rolling_7d_mean"].tolist(),
        mode="lines",line=dict(color="#f59e0b",dash="dot",width=1.5),name="7-Day Avg"))
    if not anomalies.empty:
        fig.add_trace(go.Scatter(x=anomalies["date"].astype(str).tolist(),y=anomalies["total_sales"].tolist(),
            mode="markers",marker=dict(size=11,color="#dc2626",symbol="x-thin",
            line=dict(width=3,color="#dc2626")),name="Anomaly"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=400,
        xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        margin=dict(l=4,r=4,t=36,b=8),hovermode="x unified",
        legend=dict(bgcolor="rgba(0,0,0,0)",borderwidth=0,orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))
    trend_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # Monthly bar chart
    monthly = result_df.copy()
    monthly["mon"] = monthly["date"].dt.to_period("M").astype(str)
    mc = monthly.groupby("mon")["anomaly_label"].sum().reset_index()
    bar = go.Figure(go.Bar(x=mc["mon"].tolist(),y=mc["anomaly_label"].tolist(),
        marker=dict(color=mc["anomaly_label"].tolist(),colorscale=[[0,"#818cf8"],[.5,"#7c3aed"],[1,"#dc2626"]],line=dict(width=0))))
    bar.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=260,
        xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        margin=dict(l=4,r=4,t=36,b=8))
    bar_json = json.dumps(bar, cls=plotly.utils.PlotlyJSONEncoder)

    # Distribution histogram
    hist = go.Figure()
    hist.add_trace(go.Histogram(x=normals["total_sales"].tolist(),name="Normal",marker_color="#4f46e5",opacity=0.7,nbinsx=35))
    hist.add_trace(go.Histogram(x=anomalies["total_sales"].tolist(),name="Anomaly",marker_color="#dc2626",opacity=0.85,nbinsx=20))
    hist.update_layout(barmode="overlay",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=260,
        xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        margin=dict(l=4,r=4,t=36,b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)",borderwidth=0,orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))
    hist_json = json.dumps(hist, cls=plotly.utils.PlotlyJSONEncoder)

    # Save anomaly run to database
    try:
        ds_name = _store.get("uploaded_name") or "default"
        save_anomaly_run(
            ds_name, _store["contamination"],
            len(result_df), len(anomalies), anom_pct,
            session.get("user","unknown"), anomalies
        )
    except: pass
    ctx.update({"trend_json":trend_json,"bar_json":bar_json,"hist_json":hist_json,
                "total_rev":result_df["total_sales"].sum()/1_000_000,
                "avg_daily":result_df["total_sales"].mean()})
    return render_template("dashboard.html", **ctx)

@app.route("/anomalies")
@login_required
def anomalies_page():
    if not can_access("anomalies"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html",msg="No data")
    import plotly.graph_objects as go, plotly.utils
    result_df = ctx["result_df"]; anomalies = ctx["anomalies"]; normals = ctx["normals"]
    sc = go.Figure()
    sc.add_trace(go.Scatter(x=normals["date"].astype(str).tolist(),y=normals["anomaly_score"].tolist(),
        mode="markers",marker=dict(size=4,color="#818cf8",opacity=0.4),name="Normal"))
    sc.add_trace(go.Scatter(x=anomalies["date"].astype(str).tolist(),y=anomalies["anomaly_score"].tolist(),
        mode="markers",marker=dict(size=10,color="#dc2626",symbol="x-thin",line=dict(width=2.5,color="#dc2626")),name="Anomaly"))
    threshold = result_df["anomaly_score"].quantile(0.05)
    sc.add_hline(y=threshold,line_dash="dot",line_color="#f59e0b",annotation_text="threshold",annotation_font_color="#d97706")
    sc.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=290,
        xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        margin=dict(l=4,r=4,t=36,b=8),hovermode="x unified",
        legend=dict(bgcolor="rgba(0,0,0,0)",borderwidth=0,orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))
    sc_json = json.dumps(sc, cls=plotly.utils.PlotlyJSONEncoder)
    mean_s = result_df["total_sales"].mean()
    anom_list = []
    for _,row in anomalies.sort_values("anomaly_score").head(30).iterrows():
        anom_list.append({
            "date": str(row["date"])[:10],
            "total_sales": f"{row['total_sales']:,.0f}",
            "transaction_count": int(row["transaction_count"]),
            "anomaly_score": f"{row['anomaly_score']:.4f}",
            "type": "SPIKE" if row["total_sales"] > mean_s*1.5 else "DROP"
        })
    ctx.update({"sc_json":sc_json,"anom_list":anom_list,
                "worst_score":f"{anomalies['anomaly_score'].min():.4f}" if not anomalies.empty else "N/A",
                "avg_anom_sales":f"{anomalies['total_sales'].mean():,.0f}" if not anomalies.empty else "N/A"})
    return render_template("anomalies.html", **ctx)

@app.route("/analytics")
@login_required
def analytics():
    if not can_access("analytics"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html",msg="No data")
    import plotly.graph_objects as go, plotly.express as px, plotly.utils
    result_df = ctx["result_df"]; anomalies = ctx["anomalies"]; normals = ctx["normals"]
    # Heatmap
    hm = result_df.copy()
    hm["week"] = hm["date"].dt.isocalendar().week.astype(int)
    hm["dow"]  = hm["date"].dt.day_name()
    pivot = hm.pivot_table(index="dow",columns="week",values="anomaly_label",aggfunc="sum").fillna(0)
    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    pivot = pivot.reindex([d for d in dow_order if d in pivot.index])
    hfig = px.imshow(pivot,color_continuous_scale=[[0,"#eff6ff"],[.4,"#4f46e5"],[.7,"#7c3aed"],[1,"#dc2626"]],
        labels=dict(color="Anomalies"),aspect="auto")
    hfig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=290,margin=dict(l=4,r=4,t=36,b=8))
    hmap_json = json.dumps(hfig, cls=plotly.utils.PlotlyJSONEncoder)
    # Rolling avg
    rfig = go.Figure()
    rfig.add_trace(go.Scatter(x=result_df["date"].astype(str).tolist(),y=result_df["rolling_7d_mean"].tolist(),
        mode="lines",fill="tozeroy",fillcolor="rgba(79,70,229,.07)",line=dict(color="#4f46e5",width=2),name="Rolling Mean"))
    rfig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=290,
        xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        margin=dict(l=4,r=4,t=36,b=8))
    roll_json = json.dumps(rfig, cls=plotly.utils.PlotlyJSONEncoder)
    # Bubble chart
    bub = px.scatter(result_df,x="transaction_count",y="total_sales",
        color="anomaly_label",size="avg_transaction",
        color_discrete_map={True:"#dc2626",False:"#4f46e5"},opacity=0.72)
    bub.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#9ca3af",size=11),height=370,
        xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
        margin=dict(l=4,r=4,t=36,b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)",borderwidth=0,orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))
    bub.update_traces(marker=dict(line=dict(width=0)))
    bub_json = json.dumps(bub, cls=plotly.utils.PlotlyJSONEncoder)
    ctx.update({"hmap_json":hmap_json,"roll_json":roll_json,"bub_json":bub_json})
    return render_template("analytics.html", **ctx)

@app.route("/forecast", methods=["GET","POST"])
@login_required
def forecast():
    if not can_access("forecast"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html",msg="No data")
    fc_result = None; fc_table = None; engine = None
    if request.method == "POST":
        periods = int(request.form.get("periods",30))
        result_df = ctx["result_df"]
        fc = run_forecast(result_df, periods=periods)
        fc_result = fc["fig_json"]
        engine    = fc["engine"]
        fut = fc["forecast_df"][fc["forecast_df"]["ds"] > result_df["date"].max()].copy()
        if not fut.empty:
            fut["ds"] = fut["ds"].dt.strftime("%Y-%m-%d")
            fut["yhat"] = fut["yhat"].round(0)
            fut["yhat_lower"] = fut["yhat_lower"].round(0)
            fut["yhat_upper"] = fut["yhat_upper"].round(0)
            fc_table = fut[["ds","yhat","yhat_lower","yhat_upper"]].head(30).to_dict("records")
    ctx.update({"fc_result":fc_result,"fc_table":fc_table,"engine":engine})
    return render_template("forecast.html", **ctx)

@app.route("/fraud", methods=["GET","POST"])
@login_required
def fraud():
    if not can_access("fraud"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html",msg="No data")
    import plotly.express as px, plotly.utils
    fraud_result = None; fraud_sum = None; rb_json = None
    if request.method == "POST":
        raw_df = ctx["raw_df"]
        flagged = detect_fraud(raw_df)
        sm = fraud_summary(flagged)
        fraud_result = flagged.to_dict("records") if not flagged.empty else []
        fraud_sum = sm
        # Save to database
        try:
            save_fraud_run(
                _store.get("uploaded_name") or "default",
                sm["total_flagged"], sm["total_at_risk"],
                sm["top_region"], sm["top_reason"],
                session.get("user","unknown")
            )
        except: pass
        if not flagged.empty:
            rc = flagged["fraud_reason"].str.split("; ").explode().value_counts().reset_index()
            rc.columns = ["Reason","Count"]
            rb = px.bar(rc,x="Count",y="Reason",orientation="h",color="Count",
                color_continuous_scale=[[0,"#818cf8"],[1,"#dc2626"]])
            rb.update_coloraxes(showscale=False)
            rb.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter",color="#9ca3af",size=11),height=260,yaxis_title="",
                xaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
                yaxis=dict(gridcolor="rgba(0,0,0,.05)",zeroline=False,showline=False),
                margin=dict(l=4,r=4,t=36,b=8))
            rb_json = json.dumps(rb, cls=plotly.utils.PlotlyJSONEncoder)
    ctx.update({"fraud_result":fraud_result,"fraud_sum":fraud_sum,"rb_json":rb_json})
    return render_template("fraud.html", **ctx)

@app.route("/reports", methods=["GET","POST"])
@login_required
def reports():
    if not can_access("reports"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html",msg="No data")
    msg = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "email":
            email_to = request.form.get("email_to","")
            rcpts = [r.strip() for r in email_to.split(",") if r.strip()]
            out = send_anomaly_alert(ctx["anomalies"], recipients=rcpts or None)
            msg = out["message"]
            # Log to database
            try:
                log_alert("email", email_to, "success" if out["success"] else "failed",
                          out["message"], session.get("user","unknown"))
            except: pass
    ctx.update({"msg":msg})
    return render_template("reports.html", **ctx)

@app.route("/download_pdf")
@login_required
def download_pdf():
    ctx = base_ctx()
    if ctx is None: return "No data", 400
    path = generate_pdf_report(ctx["result_df"], ctx["anomalies"])
    return send_file(path, as_attachment=True, download_name="anomaly_report.pdf")

@app.route("/download_csv/<dtype>")
@login_required
def download_csv(dtype):
    from flask import Response
    ctx = base_ctx()
    if ctx is None: return "No data", 400
    if dtype == "anomalies":
        df = ctx["anomalies"]
    elif dtype == "fraud":
        flagged = detect_fraud(ctx["raw_df"])
        df = flagged
    else:
        df = ctx["result_df"]
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":f"attachment;filename={dtype}.csv"})

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    if not can_access("settings"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html",msg="No data")
    if request.method == "POST":
        new_cont = float(request.form.get("contamination",0.05))
        _store["contamination"] = new_cont
        _store["result_df"] = None  # force recompute
        get_data()
        # Save to database
        save_settings(session.get("user","admin"), new_cont, _store["biz_type"])
        return redirect(url_for("settings"))
    ctx.update({"contamination":_store["contamination"]})
    return render_template("settings.html", **ctx)

@app.route("/live")
@login_required
def live():
    if not can_access("live"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    return render_template("live.html", **ctx)

@app.route("/live_tick")
@login_required
def live_tick():
    ctx = base_ctx()
    if ctx is None: return jsonify({})
    base = float(ctx["result_df"]["total_sales"].mean())
    cont = _store["contamination"]
    val = base * np.random.uniform(.45,1.55)
    if np.random.random() < cont:
        val += base * np.random.uniform(3,5)
    is_anom = val > base * 2.8
    return jsonify({"value":round(val,2),"is_anomaly":is_anom,"base":round(base,2)})

@app.route("/database")
@login_required
def database_page():
    if not can_access("settings"): return redirect(url_for("dashboard"))
    ctx = base_ctx()
    if ctx is None: return render_template("error.html", msg="No data")
    db_summary  = get_db_summary()
    anom_hist   = get_anomaly_history()
    fraud_hist  = get_fraud_history()
    alert_hist  = get_alert_logs()
    dataset_hist= get_datasets()
    all_users   = get_all_users()
    user_msg    = None
    if False:
        pass
    ctx.update({
        "db_summary":   db_summary,
        "anom_hist":    anom_hist,
        "fraud_hist":   fraud_hist,
        "alert_hist":   alert_hist,
        "dataset_hist": dataset_hist,
        "all_users":    all_users,
        "user_msg":     user_msg,
    })
    return render_template("database.html", **ctx)

@app.route("/add_user", methods=["POST"])
@login_required
def add_user_route():
    if not can_access("settings"): return redirect(url_for("dashboard"))
    username     = request.form.get("username","").strip()
    password     = request.form.get("password","").strip()
    role         = request.form.get("role","Viewer")
    display_name = request.form.get("display_name","").strip()
    if username and password and display_name:
        success, msg = add_user(username, password, role, display_name)
    return redirect(url_for("database_page"))

@app.route("/delete_user/<int:uid>", methods=["POST"])
@login_required
def delete_user_route(uid):
    if not can_access("settings"): return redirect(url_for("dashboard"))
    delete_user(uid)
    return redirect(url_for("database_page"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
