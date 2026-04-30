"""
database.py — SQLite Database for StreamSight
Tables:
  - users           : login accounts with roles
  - datasets        : uploaded dataset metadata
  - anomaly_results : detected anomalies stored per run
  - fraud_results   : fraud scan results stored per run
  - alert_logs      : email alert history
  - settings        : per-user settings (contamination etc)
"""

import sqlite3
import hashlib
import os
from pathlib import Path
from datetime import datetime

DB_PATH = "data/streamsight.db"

# ── Connect ────────────────────────────────────────────────────────
def get_db():
    """Get a database connection."""
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# ── Hash password ──────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ── Init all tables ────────────────────────────────────────────────
def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT UNIQUE NOT NULL,
        password     TEXT NOT NULL,
        role         TEXT NOT NULL DEFAULT 'Viewer',
        display_name TEXT NOT NULL,
        created_at   TEXT DEFAULT (datetime('now'))
    )""")

    # Datasets table
    c.execute("""
    CREATE TABLE IF NOT EXISTS datasets (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL,
        filename     TEXT NOT NULL,
        rows         INTEGER,
        date_from    TEXT,
        date_to      TEXT,
        uploaded_by  TEXT,
        uploaded_at  TEXT DEFAULT (datetime('now'))
    )""")

    # Anomaly results
    c.execute("""
    CREATE TABLE IF NOT EXISTS anomaly_results (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name     TEXT,
        run_date         TEXT DEFAULT (datetime('now')),
        contamination    REAL,
        total_days       INTEGER,
        total_anomalies  INTEGER,
        anomaly_rate     REAL,
        run_by           TEXT
    )""")

    # Anomaly records (individual flagged days)
    c.execute("""
    CREATE TABLE IF NOT EXISTS anomaly_records (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id      INTEGER REFERENCES anomaly_results(id),
        date        TEXT,
        total_sales REAL,
        txn_count   INTEGER,
        anom_score  REAL,
        anom_type   TEXT
    )""")

    # Fraud results
    c.execute("""
    CREATE TABLE IF NOT EXISTS fraud_results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name    TEXT,
        run_date        TEXT DEFAULT (datetime('now')),
        total_flagged   INTEGER,
        total_at_risk   REAL,
        top_region      TEXT,
        top_reason      TEXT,
        run_by          TEXT
    )""")

    # Alert logs
    c.execute("""
    CREATE TABLE IF NOT EXISTS alert_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type  TEXT,
        recipient   TEXT,
        status      TEXT,
        message     TEXT,
        sent_at     TEXT DEFAULT (datetime('now')),
        sent_by     TEXT
    )""")

    # Settings per user
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        username       TEXT UNIQUE,
        contamination  REAL DEFAULT 0.05,
        biz_type       TEXT DEFAULT 'Retail Store',
        updated_at     TEXT DEFAULT (datetime('now'))
    )""")

    # Insert default users if not exist
    default_users = [
        ("admin",   "admin123",   "Admin",   "Admin User"),
        ("manager", "manager123", "Manager", "Store Manager"),
        ("viewer",  "viewer123",  "Viewer",  "Read-Only Viewer"),
    ]
    for username, password, role, display_name in default_users:
        c.execute("""
            INSERT OR IGNORE INTO users (username, password, role, display_name)
            VALUES (?, ?, ?, ?)
        """, (username, hash_password(password), role, display_name))

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")

# ── User functions ─────────────────────────────────────────────────
def verify_user(username: str, password: str):
    """Verify login. Returns user dict or None."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users():
    conn = get_db()
    users = conn.execute("SELECT id,username,role,display_name,created_at FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]

def add_user(username, password, role, display_name):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username,password,role,display_name) VALUES (?,?,?,?)",
            (username, hash_password(password), role, display_name)
        )
        conn.commit()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

# ── Settings functions ─────────────────────────────────────────────
def get_settings(username: str) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM settings WHERE username=?", (username,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"contamination": 0.05, "biz_type": "Retail Store"}

def save_settings(username: str, contamination: float, biz_type: str):
    conn = get_db()
    conn.execute("""
        INSERT INTO settings (username, contamination, biz_type, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(username) DO UPDATE SET
            contamination=excluded.contamination,
            biz_type=excluded.biz_type,
            updated_at=excluded.updated_at
    """, (username, contamination, biz_type))
    conn.commit()
    conn.close()

# ── Dataset functions ──────────────────────────────────────────────
def log_dataset(name, filename, rows, date_from, date_to, uploaded_by):
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO datasets (name,filename,rows,date_from,date_to,uploaded_by)
        VALUES (?,?,?,?,?,?)
    """, (name, filename, rows, str(date_from)[:10], str(date_to)[:10], uploaded_by))
    conn.commit()
    dataset_id = cursor.lastrowid
    conn.close()
    return dataset_id

def get_datasets():
    conn = get_db()
    rows = conn.execute("SELECT * FROM datasets ORDER BY uploaded_at DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Anomaly result functions ───────────────────────────────────────
def save_anomaly_run(dataset_name, contamination, total_days,
                     total_anomalies, anomaly_rate, run_by, anomaly_df):
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO anomaly_results
            (dataset_name, contamination, total_days, total_anomalies, anomaly_rate, run_by)
        VALUES (?,?,?,?,?,?)
    """, (dataset_name, contamination, total_days, total_anomalies, anomaly_rate, run_by))
    run_id = cursor.lastrowid

    # Save individual anomaly records
    mean_s = anomaly_df["total_sales"].mean() if not anomaly_df.empty else 0
    for _, row in anomaly_df.iterrows():
        anom_type = "SPIKE" if row["total_sales"] > mean_s * 1.5 else "DROP"
        conn.execute("""
            INSERT INTO anomaly_records (run_id,date,total_sales,txn_count,anom_score,anom_type)
            VALUES (?,?,?,?,?,?)
        """, (run_id, str(row["date"])[:10], float(row["total_sales"]),
              int(row["transaction_count"]), float(row["anomaly_score"]), anom_type))

    conn.commit()
    conn.close()
    return run_id

def get_anomaly_history():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM anomaly_results ORDER BY run_date DESC LIMIT 10
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Fraud result functions ─────────────────────────────────────────
def save_fraud_run(dataset_name, total_flagged, total_at_risk,
                   top_region, top_reason, run_by):
    conn = get_db()
    conn.execute("""
        INSERT INTO fraud_results
            (dataset_name,total_flagged,total_at_risk,top_region,top_reason,run_by)
        VALUES (?,?,?,?,?,?)
    """, (dataset_name, total_flagged, total_at_risk, top_region, top_reason, run_by))
    conn.commit()
    conn.close()

def get_fraud_history():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM fraud_results ORDER BY run_date DESC LIMIT 10
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Alert log functions ────────────────────────────────────────────
def log_alert(alert_type, recipient, status, message, sent_by):
    conn = get_db()
    conn.execute("""
        INSERT INTO alert_logs (alert_type,recipient,status,message,sent_by)
        VALUES (?,?,?,?,?)
    """, (alert_type, recipient, status, message, sent_by))
    conn.commit()
    conn.close()

def get_alert_logs():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM alert_logs ORDER BY sent_at DESC LIMIT 20
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Summary stats for dashboard ────────────────────────────────────
def get_db_summary():
    conn = get_db()
    summary = {
        "total_runs":     conn.execute("SELECT COUNT(*) FROM anomaly_results").fetchone()[0],
        "total_datasets": conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0],
        "total_alerts":   conn.execute("SELECT COUNT(*) FROM alert_logs").fetchone()[0],
        "total_fraud":    conn.execute("SELECT COUNT(*) FROM fraud_results").fetchone()[0],
    }
    conn.close()
    return summary

if __name__ == "__main__":
    init_db()
