# StreamSight — Business Intelligence Platform

**Professional Sales Analytics & Anomaly Detection Dashboard**

Transform your sales data into actionable intelligence with real-time ML-powered insights, revenue forecasting, and fraud prevention.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Flask-2.0+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Key Features

### 🎯 **Anomaly Detection**
- **Isolation Forest ML** — Automatically detects unusual patterns in sales data
- Real-time anomaly scoring and flagging
- Customizable sensitivity thresholds
- Visual anomaly timeline and detailed records

### 📊 **Revenue Forecasting**
- **Prophet & Linear Regression** — Predict future sales trends
- Forecast confidence intervals
- Trend analysis and growth projections
- Interactive forecast visualizations

### 🛡️ **Fraud Detection**
- **5 Intelligent Detection Rules** — Identifies suspicious transactions instantly
- High-value transaction flagging
- Price anomaly detection
- Quantity spike alerts
- Transaction frequency analysis

### 📁 **Easy Data Import**
- Upload CSV or Excel files (.csv, .xlsx, .xls)
- Automatic data validation and preprocessing
- Support for custom date formats
- Batch processing capabilities

### 📧 **Email Alerts**
- Instant notifications for detected anomalies
- Customizable alert thresholds
- Daily summary reports
- Gmail integration (SMTP)

### 📄 **Professional Reports**
- Generate PDF reports with charts and insights
- Custom date range selection
- Executive summaries
- Detailed anomaly analysis

### 🔐 **Multi-User Authentication**
- User signup and login system
- SQLite database with password hashing
- Role-based access control
- Session management

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Step 1: Clone & Setup
```bash
cd StreamSight_Flask
pip install -r requirements.txt
```

### Step 2: Generate Sample Data (Optional)
```bash
python generate_data.py
```
This creates sample sales data in `data/sales_data.csv` for testing.

### Step 3: Run the Application
```bash
python app.py
```

### Step 4: Access the Platform
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 📋 First-Time Users

### Sign Up
1. Click **"Sign Up"** on the homepage
2. Enter username, email, and password
3. Confirm your password
4. Click **"Sign Up"** to create account
5. Redirected to login page
6. Use your credentials to sign in

### Upload Dataset
1. Go to **Dashboard**
2. Click **"📤 Upload Dataset"**
3. Select CSV or Excel file with columns: `date`, `total_sales`, `transaction_count`
4. Click upload
5. Wait for processing
6. View detected anomalies automatically

### Explore Features
- **Dashboard** — KPIs, sales trend chart, latest anomalies
- **Anomalies** — Detailed anomaly records with visualizations
- **Analytics** — Advanced analysis and trend insights
- **Forecast** — 30-day revenue forecasting
- **Fraud Detection** — Suspicious transaction analysis
- **Live Feed** — Real-time transaction simulation
- **Reports** — Export PDF reports
- **Settings** — Manage preferences

---

## 📊 Dataset Requirements

Your CSV/Excel file must contain these columns:

| Column | Type | Description |
|--------|------|-------------|
| `date` | Date (YYYY-MM-DD) | Transaction date |
| `total_sales` | Float | Daily revenue amount (₹) |
| `transaction_count` | Integer | Number of transactions |

**Example CSV:**
```
date,total_sales,transaction_count
2024-01-01,15000.50,45
2024-01-02,18500.75,52
2024-01-03,12300.00,38
```

---

## 🏗️ Project Structure

```
StreamSight_Flask/
│
├── 📄 app.py                      ← Main Flask application & routes
├── 📄 database.py                 ← SQLite user database management
├── 📄 anomaly_detector.py         ← Isolation Forest ML engine
├── 📄 generate_data.py            ← Sample data generator
├── 📄 requirements.txt            ← Python dependencies
├── 📄 README.md                   ← This file
│
├── 📁 templates/                  ← HTML Jinja2 templates
│   ├── base.html                  ← Navigation & base layout
│   ├── home.html                  ← Landing page (professional)
│   ├── signin.html                ← Signup form
│   ├── login.html                 ← Login form
│   ├── dashboard.html             ← Main analytics dashboard
│   ├── anomalies.html             ← Anomaly details page
│   ├── analytics.html             ← Advanced analytics
│   ├── forecast.html              ← Revenue forecasting
│   ├── fraud.html                 ← Fraud detection results
│   ├── live.html                  ← Live data feed
│   ├── reports.html               ← PDF report generation
│   ├── settings.html              ← User settings
│   ├── database.html              ← Database management
│   └── error.html                 ← Error page
│
├── 📁 static/                     ← Frontend assets
│   ├── css/
│   │   └── main.css               ← Custom styling
│   └── js/
│       └── main.js                ← Client-side logic
│
├── 📁 utils/                      ← Utility modules
│   ├── __init__.py
│   ├── fraud_detector.py          ← Fraud detection rules
│   ├── forecaster.py              ← Prophet & Linear forecasting
│   ├── email_notifier.py          ← Email alert system
│   └── pdf_report.py              ← PDF report generation
│
└── 📁 data/                       ← Data storage
    └── sales_data.csv            ← Sample dataset
```

---

## 🔐 Authentication & Roles

### Default Test Accounts

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin (all features) |
| `manager` | `manager123` | Manager (most features) |
| `viewer` | `viewer123` | Viewer (dashboard only) |

Or create your own account via Sign Up.

---

## 🛠️ Technology Stack

**Backend:**
- Flask 2.0+
- Python 3.8+
- SQLAlchemy
- Pandas & NumPy

**Machine Learning:**
- Scikit-learn (Isolation Forest)
- Prophet (Time series forecasting)
- Scipy (Linear regression)

**Frontend:**
- Bootstrap 5.3.2
- Plotly.js (Interactive charts)
- Vanilla JavaScript

**Database:**
- SQLite3
- Flask-SQLAlchemy

**Utilities:**
- ReportLab (PDF generation)
- smtplib (Email notifications)
- openpyxl (Excel files)

---

## 📖 How It Works

### 1. **Data Upload Flow**
- User uploads CSV/Excel file
- System validates data format
- Anomaly detection runs automatically
- Results displayed instantly

### 2. **Anomaly Detection Algorithm**
- **Isolation Forest** (sklearn)
- Trains on historical sales data
- Identifies statistical outliers
- Anomaly score: -1 to 1 (-1 = anomaly)

### 3. **Forecasting**
- **Prophet** — Captures seasonality & trends
- **Linear Regression** — Baseline forecasting
- 30-day future predictions
- Confidence intervals

### 4. **Fraud Detection**
5 rules applied to transactions:
1. High-value transaction flag (>99th percentile)
2. Price anomaly detection (deviation >3σ)
3. Quantity spike alert (>2x normal)
4. Extreme values check
5. Transaction frequency analysis

---

## 🔧 Configuration

### Optional: Email Alerts
Create a `.env` file in the root directory:
```ini
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
RECIPIENT_EMAIL=admin@example.com
```

Generate Gmail App Password:
1. Enable 2-factor authentication on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" and "Windows Computer"
4. Copy generated password to `.env`

---

## 📈 Example Use Cases

✅ **E-Commerce** — Detect sudden sales spikes or drops
✅ **Retail Chains** — Monitor store performance across locations
✅ **SaaS Platforms** — Track subscription revenue anomalies
✅ **Financial Services** — Fraud prevention in transactions
✅ **Logistics** — Identify supply chain disruptions
✅ **Manufacturing** — Monitor production metrics

---

## 🐛 Troubleshooting

**Import error on startup?**
```bash
pip install -r requirements.txt --force-reinstall
```

**Database locked error?**
```bash
# Remove the database and restart
rm instance/database.db
python app.py
```

**Charts not loading?**
- Clear browser cache (Ctrl+Shift+Delete)
- Check browser console for JavaScript errors
- Verify Plotly.js CDN is accessible

**Email alerts not working?**
- Verify Gmail credentials in `.env`
- Check .env file is in root directory
- Ensure "Less secure apps" or App Password is enabled

---

## 📜 License & Credits

MIT License — Feel free to use and modify for your projects.

Built with ❤️ using Flask, Scikit-learn, and Prophet.

---

## 📞 Support

For issues, questions, or feature requests, refer to the documentation or check the error page for diagnostic information.

**Platform Version:** 2.0
**Last Updated:** April 2024
