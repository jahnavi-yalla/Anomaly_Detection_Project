# StreamSight Algorithms Documentation

## Overview

StreamSight uses three advanced algorithms to provide business intelligence:
1. **Anomaly Detection** — Isolation Forest ML
2. **Revenue Forecasting** — Prophet & Linear Regression
3. **Fraud Detection** — Rule-Based Scoring System

---

## 1. Anomaly Detection Algorithm

### Location
[anomaly_detector.py](anomaly_detector.py)

### Purpose
Automatically detects unusual patterns in sales data that deviate from normal behavior.

### How It Works

#### Step 1: Data Aggregation
Transforms raw transaction data into daily summaries:

```
Input: Raw transactions with dates and amounts
    ↓
Daily Aggregation:
  • total_sales: Sum of all sales per day
  • transaction_count: Number of transactions per day
  • avg_transaction: Average transaction amount per day
    ↓
Feature Engineering:
  • rolling_7d_mean: 7-day moving average of sales
  • rolling_7d_std: 7-day moving standard deviation
  • day_of_week: Day number (0=Monday, 6=Sunday)
  • month: Month number (1-12)
    ↓
Output: Daily dataframe with 8 features
```

#### Step 2: Feature Scaling
Normalizes all features to the same scale using `StandardScaler`:
- Converts each feature to mean=0, std=1
- Prevents features with large values from dominating the model
- Ensures each feature contributes equally

#### Step 3: Model Training
Trains an **Isolation Forest** ensemble with:
- **200 decision trees** — Multiple independent models for robustness
- **Contamination = 5%** — Expects top 5% of records to be anomalies
- **Random Forest approach** — Each tree randomly selects features and thresholds

**Why Isolation Forest?**
- Anomalies are "few and different"
- Easier to isolate than to define normal behavior
- No distance metrics needed (fast & scalable)
- Works well with mixed feature types

#### Step 4: Scoring & Labeling
For each day:
- **Anomaly Score** — Negative score (lower = more anomalous)
- **Anomaly Label** — Binary: True (anomaly) or False (normal)
- Score is based on path length through decision trees

### Output
```python
{
    'date': datetime,
    'total_sales': float,
    'transaction_count': int,
    'avg_transaction': float,
    'rolling_7d_mean': float,
    'rolling_7d_std': float,
    'day_of_week': int,
    'month': int,
    'anomaly_label': bool,        # True = anomaly
    'anomaly_score': float         # (-1.0 to 0) lower = more anomalous
}
```

### Key Parameters
| Parameter | Value | Effect |
|-----------|-------|--------|
| contamination | 0.05 (5%) | ~5% of records flagged as anomalies |
| n_estimators | 200 | More trees = more robust but slower |
| random_state | 42 | Reproducible results |

### Sensitivity Tuning
- **Lower contamination** (0.01) → Stricter, fewer flags
- **Higher contamination** (0.10) → More lenient, more flags

---

## 2. Revenue Forecasting Algorithm

### Location
[utils/forecaster.py](utils/forecaster.py)

### Purpose
Predict future sales trends with confidence intervals.

### How It Works

#### Method 1: Prophet (Primary)
**Facebook's Time Series Forecasting Library**

```
Historical Sales Data
    ↓
Decomposition:
  Trend Component → Long-term direction
  Yearly Seasonality → Annual patterns (holidays, seasons)
  Weekly Seasonality → Day-of-week effects
    ↓
Model Fitting:
  Estimates each component from data
    ↓
Forecast Generation:
  Extends each component 30 days into future
  Combines into final predictions
    ↓
Confidence Intervals:
  Adds historical uncertainty (±1.96 × std dev)
    ↓
Output: Forecast with yhat, yhat_lower, yhat_upper
```

**Advantages:**
- Handles seasonality automatically
- Robust to missing data & outliers
- Generates confidence bands
- Good with 1+ years of data

**Limitations:**
- Requires Prophet library
- Needs sufficient historical data

#### Method 2: Linear Regression (Fallback)
Used when Prophet is unavailable:

```
Historical Sales Data → Points (x, y)
    ↓
Fit Line: y = mx + b
  m = slope (trend direction)
  b = intercept
    ↓
Extend Line 30 Days Forward
    ↓
Confidence Bounds:
  Upper = forecast + 1.96 × historical_std_dev
  Lower = forecast - 1.96 × historical_std_dev
    ↓
Output: Linear trend with uncertainty
```

**Advantages:**
- Simple & always available
- Fast computation
- Good for linear trends

**Limitations:**
- Ignores seasonality
- Assumes constant trend
- Less accurate than Prophet

### Visualization
Uses **Plotly** to create interactive charts:

```
Trace 1: Historical Data (solid blue line)
Trace 2: Forecast Line (dashed purple)
Trace 3: Confidence Band (light purple fill)
```

Users can:
- Hover for exact values
- Zoom into date ranges
- Toggle lines on/off

### Parameters
| Parameter | Value | Effect |
|-----------|-------|--------|
| periods | 30 | Forecast 30 days ahead |
| yearly_seasonality | True | Model annual patterns |
| weekly_seasonality | True | Model weekly patterns |
| daily_seasonality | False | Skip daily patterns |

### Output
```python
{
    'fig_json': json_string,           # Plotly chart
    'forecast_df': DataFrame,          # Forecast data
    'engine': 'prophet' or 'linear'    # Which method used
}
```

---

## 3. Fraud Detection Algorithm

### Location
[utils/fraud_detector.py](utils/fraud_detector.py)

### Purpose
Identify suspicious transactions that may indicate fraud.

### How It Works

#### Step 1: Statistical Baseline
Calculate mean & standard deviation for key metrics:

```python
mean_amount = df[amount_column].mean()
std_amount = df[amount_column].std()

mean_txn_count = df['transaction_count'].mean()
std_txn_count = df['transaction_count'].std()
```

#### Step 2: Fraud Rules
Each rule calculates a **fraud score** (0-4+ points):

##### Rule 1: Large Transaction
```
IF amount > (mean + 2.5 × std_dev) THEN fraud_score += 4

Example:
  mean_amount = $5,000
  std_dev = $1,000
  threshold = $5,000 + 2.5×$1,000 = $7,500
  
  $12,000 sale → FLAGGED (way above normal)
```

##### Rule 2: Round Amount
```
IF amount ends in 9999, 10000, 4999, 14999, 19999 THEN fraud_score += 3

Example:
  $9,999 sale → Suspicious (too convenient/round)
  $10,000 sale → Suspicious (psychological pricing)
```

##### Rule 3: High Transaction Frequency
```
IF transaction_count > (mean + 2.0 × std_dev) THEN fraud_score += 3

Example:
  mean_txn = 100/day
  std_dev = 20
  threshold = 100 + 2×20 = 140 txns/day
  
  200 txns/day → FLAGGED (possible manipulation)
```

##### Rule 4: Suppressed Sales
```
IF amount < (mean - 3.0 × std_dev) AND amount > 0 THEN fraud_score += 2

Example:
  mean_amount = $5,000
  std_dev = $1,000
  threshold = $5,000 - 3×$1,000 = $2,000
  
  $500 sale → FLAGGED (artificially low, possible accounting trick)
```

#### Step 3: Aggregation
```
fraud_score = sum of all triggered rules

Reasons = list of all triggered rule names
```

#### Step 4: Thresholding
```
IF fraud_score >= 3 THEN "Flagged for Review"
ELSE "Approved"
```

### Fraud Score Interpretation
| Score | Risk Level | Action |
|-------|-----------|--------|
| 0-2 | Low | Approve |
| 3-4 | Medium | Review |
| 5-7 | High | Investigate |
| 8+ | Critical | Block & Alert |

### Output
```python
{
    'date': datetime,
    'transaction_count': int,
    'amount': float,
    'fraud_score': int,
    'fraud_reason': 'LARGE_TRANSACTION; ROUND_AMOUNT',  # All triggered rules
    ...other_columns
}
```

### Summary Metrics
```python
{
    'total_flagged': 47,           # Records flagged
    'total_at_risk': 285000.50,    # Sum of flagged amounts
    'top_region': 'Southeast',     # Most fraud hotspot
    'top_reason': 'LARGE_TRANSACTION'  # Most common rule
}
```

---

## Algorithm Comparison

| Algorithm | Type | Speed | Accuracy | Data Needs | Parameters |
|-----------|------|-------|----------|-----------|-----------|
| Anomaly Detection | ML (Ensemble) | Fast | High | 100+ records | contamination |
| Forecasting | Time Series | Fast | Medium-High | 1+ years | periods, seasonality |
| Fraud Detection | Rule-Based | Very Fast | Medium | 20+ records | thresholds (manual) |

---

## Workflow Integration

### In the Flask Application

```
User uploads CSV
    ↓
Database stores data
    ↓
Anomaly Detection
  ↓ Identifies unusual days
  ↓ Generates anomaly charts
    ↓
Forecasting
  ↓ Predicts next 30 days
  ↓ Creates forecast visualization
    ↓
Fraud Detection
  ↓ Scores each transaction
  ↓ Flags suspicious ones
    ↓
Results displayed in dashboard
```

---

## Performance Tuning

### Anomaly Detection
```python
# Stricter detection (fewer false positives)
SalesAnomalyDetector(contamination=0.02)

# Looser detection (catch more anomalies)
SalesAnomalyDetector(contamination=0.10)
```

### Forecasting
```python
# Short-term forecast
run_forecast(data, periods=7)  # 7 days

# Long-term forecast
run_forecast(data, periods=90)  # 3 months
```

### Fraud Detection
Modify thresholds in `fraud_detector.py`:
```python
mask1 = df[amt] > mean_amt + 2.5*std_amt  # Change 2.5 to be stricter/looser
```

---

## Best Practices

1. **Anomaly Detection**
   - Use at least 3 months of data
   - Retrain weekly for fresh patterns
   - Monitor false positive rate

2. **Forecasting**
   - Use 1+ year of data for seasonality
   - Update forecast weekly
   - Check confidence intervals for stability

3. **Fraud Detection**
   - Tune thresholds based on business domain
   - Monitor flagged transactions weekly
   - Adjust rules for seasonal changes
   - Combine with manual review for critical cases

---

## Dependencies

```
scikit-learn    # Isolation Forest
pandas          # Data manipulation
numpy           # Numerical operations
prophet         # Time series (optional, falls back to linear regression)
plotly          # Visualization
```

---

## References

- [Isolation Forest Paper](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08.pdf)
- [Prophet Documentation](https://facebook.github.io/prophet/)
- [Scikit-learn Ensemble Methods](https://scikit-learn.org/stable/modules/ensemble.html)
