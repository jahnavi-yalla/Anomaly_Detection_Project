from fpdf import FPDF
from datetime import datetime
import pandas as pd
from pathlib import Path

class AnomalyReport(FPDF):
    def header(self):
        self.set_fill_color(79,70,229)
        self.rect(0,0,210,22,"F")
        self.set_font("Helvetica","B",14)
        self.set_text_color(255,255,255)
        self.cell(0,22,"  StreamSight  |  Anomaly Detection Report",align="L",ln=True)
        self.set_text_color(0,0,0); self.ln(4)
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica","",8)
        self.set_text_color(150,150,150)
        self.cell(0,10,f"StreamSight  |  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Page {self.page_no()}",align="C")

def generate_pdf_report(result_df, anomalies, output_path="exports/anomaly_report.pdf"):
    Path("exports").mkdir(exist_ok=True)
    pdf = AnomalyReport()
    pdf.set_auto_page_break(auto=True,margin=16)
    pdf.add_page()
    pdf.set_font("Helvetica","",9); pdf.set_text_color(100,120,150)
    pdf.cell(0,6,f"Generated: {datetime.now().strftime('%B %d, %Y')} | Period: {str(result_df['date'].min())[:10]} to {str(result_df['date'].max())[:10]}",ln=True)
    pdf.ln(4)
    anom_rate = len(anomalies)/len(result_df)*100
    pdf.set_font("Helvetica","B",11); pdf.set_text_color(79,70,229)
    pdf.cell(0,9,"Executive Summary",ln=True)
    pdf.set_text_color(0,0,0); pdf.set_font("Helvetica","",9)
    pdf.cell(0,7,f"Total Days: {len(result_df)}  |  Anomalies: {len(anomalies)}  |  Rate: {anom_rate:.1f}%  |  Revenue: Rs {result_df['total_sales'].sum()/1000:.1f}K",ln=True)
    pdf.ln(4)
    if not anomalies.empty:
        pdf.set_font("Helvetica","B",11); pdf.set_text_color(79,70,229)
        pdf.cell(0,9,f"Anomaly Records ({len(anomalies)} found)",ln=True)
        pdf.set_fill_color(79,70,229); pdf.set_text_color(255,255,255); pdf.set_font("Helvetica","B",8)
        for h,w in zip(["Date","Total Sales","Transactions","Score","Type"],[30,40,35,30,25]):
            pdf.cell(w,8,h,border=1,fill=True)
        pdf.ln(); pdf.set_font("Helvetica","",8); mean_s=result_df["total_sales"].mean()
        for _,row in anomalies.sort_values("anomaly_score").head(30).iterrows():
            is_spike=row["total_sales"]>mean_s*1.5
            pdf.set_fill_color(254,242,242) if is_spike else pdf.set_fill_color(255,251,235)
            pdf.set_text_color(220,38,38) if is_spike else pdf.set_text_color(180,83,9)
            for v,w in zip([str(row["date"])[:10],f"Rs {row['total_sales']:,.0f}",str(int(row["transaction_count"])),f"{row['anomaly_score']:.4f}","SPIKE" if is_spike else "DROP"],[30,40,35,30,25]):
                pdf.cell(w,7,v,border=1,fill=True)
            pdf.ln(); pdf.set_text_color(0,0,0)
    pdf.ln(4); pdf.set_font("Helvetica","B",11); pdf.set_text_color(79,70,229)
    pdf.cell(0,9,"Recommendations",ln=True)
    pdf.set_font("Helvetica","",9); pdf.set_text_color(50,70,90)
    spikes=anomalies[anomalies["total_sales"]>result_df["total_sales"].mean()*1.5]
    drops =anomalies[anomalies["total_sales"]<result_df["total_sales"].mean()*0.5]
    recs=[]
    if len(spikes)>0: recs.append(f"- {len(spikes)} SPIKE day(s) detected - investigate for bulk orders or errors.")
    if len(drops)>0:  recs.append(f"- {len(drops)} DROP day(s) detected - check payment logs.")
    recs.append("- Review contamination threshold if results seem off.")
    recs.append("- Enable email alerts for real-time notifications.")
    for r in recs: pdf.multi_cell(0,7,r); pdf.ln(1)
    pdf.output(output_path)
    return output_path
