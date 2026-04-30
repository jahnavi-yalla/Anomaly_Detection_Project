import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os
from dotenv import load_dotenv

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root,".env"), override=True)

EMAIL_HOST = "smtp.gmail.com"
EMAIL_USER = os.getenv("EMAIL_HOST_USER","").strip()
EMAIL_PASS = os.getenv("EMAIL_HOST_PASSWORD","").replace(" ","")
EMAIL_TO   = os.getenv("EMAIL_RECIPIENT","").strip()

def send_anomaly_alert(anomalies_df, recipients=None):
    if anomalies_df.empty: return {"success":False,"message":"No anomalies to report."}
    to_list = recipients or ([EMAIL_TO] if EMAIL_TO else [])
    if not to_list: return {"success":False,"message":"No recipient configured in .env"}
    if not EMAIL_USER: return {"success":False,"message":"EMAIL_HOST_USER not set in .env"}
    if not EMAIL_PASS: return {"success":False,"message":"EMAIL_HOST_PASSWORD not set in .env"}
    rows = ""
    for _,row in anomalies_df.iterrows():
        score = row.get("anomaly_score","N/A")
        s = f"{score:.4f}" if isinstance(score,float) else str(score)
        rows += f"<tr style='border-bottom:1px solid #f3f4f6'><td style='padding:8px 12px'>{str(row['date'])[:10]}</td><td style='padding:8px 12px;font-weight:700'>Rs.{row['total_sales']:,.0f}</td><td style='padding:8px 12px'>{row.get('transaction_count','N/A')}</td><td style='padding:8px 12px;font-family:monospace'>{s}</td></tr>"
    html = f"""<html><body style="font-family:Inter,sans-serif;background:#f5f7fa;padding:24px">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1)">
    <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px">
    <div style="font-size:1.5rem;font-weight:900;color:#fff;letter-spacing:-.03em">StreamSight</div>
    <div style="color:rgba(255,255,255,.7);font-size:.85rem;margin-top:3px">Anomaly Detection Alert</div></div>
    <div style="padding:28px 32px">
    <div style="background:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;padding:14px 18px;margin-bottom:20px;color:#dc2626;font-weight:700;font-size:.95rem">
    {len(anomalies_df)} anomaly(ies) detected - {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    <table style="width:100%;border-collapse:collapse;font-size:.85rem">
    <thead><tr style="background:#f7f8fa">
    <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb">Date</th>
    <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb">Sales</th>
    <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb">Transactions</th>
    <th style="padding:10px 12px;text-align:left;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb">Score</th>
    </tr></thead><tbody>{rows}</tbody></table>
    <div style="margin-top:20px;font-size:.75rem;color:#9ca3af;text-align:center">StreamSight | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div></div></body></html>"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[StreamSight] {len(anomalies_df)} Anomaly Alert(s) Detected"
    msg["From"] = EMAIL_USER; msg["To"] = ", ".join(to_list)
    msg.attach(MIMEText(html,"html"))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(EMAIL_HOST,465,context=ctx) as s:
            s.login(EMAIL_USER,EMAIL_PASS)
            s.sendmail(EMAIL_USER,to_list,msg.as_string())
        return {"success":True,"message":f"Email sent to {', '.join(to_list)}"}
    except smtplib.SMTPAuthenticationError: pass
    except Exception as e: return {"success":False,"message":str(e)}
    try:
        with smtplib.SMTP(EMAIL_HOST,587) as s:
            s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
            s.login(EMAIL_USER,EMAIL_PASS)
            s.sendmail(EMAIL_USER,to_list,msg.as_string())
        return {"success":True,"message":f"Email sent to {', '.join(to_list)}"}
    except Exception as e: return {"success":False,"message":str(e)}
