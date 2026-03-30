# 📈 Quantitative Trading Performance Dashboard & Risk Simulator

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-FF4B4B.svg)
![Plotly](https://img.shields.io/badge/Plotly-Interactive-3f4f75.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458.svg)

## 📌 Project Overview
This project is a full-stack quantitative analytics pipeline that transforms raw, unstructured MetaTrader 5 (MT5) execution logs into an institutional-grade performance dashboard. 

The core objective of this project is to prove the mathematical edge of a proprietary trading strategy by applying a strict **Fixed Fractional Risk Model (5% compounding)**. It features an automated data engineering pipeline, dynamic R-Multiple calculations, and an interactive Streamlit application that includes a **Compounding Risk Simulator** for forecasting future equity curves and withdrawal scenarios.

🌐 **[Live Dashboard Demo](#)** *(Insert your Streamlit Community Cloud link here later)*

---

## 🎯 Business Problem & Objective
Retail trading strategies often fail due to poor risk management and the inability to mathematically separate a strategy's edge from random market noise. Furthermore, broker reports (like MT5 HTML statements) often obscure true performance by mixing raw trade profit with non-trade cash flows (rebates, swaps, and withdrawals).

**Objective:** To build a fully automated pipeline that mathematically isolates the pure trading edge (Gross Trade Equity), normalizes the risk metric across multiple asset classes and currencies, and visualizes the true performance via key institutional quantitative metrics (KPIs).

---

## 📊 Key Metrics & Quantitative Evaluation (KPIs)

This dashboard evaluates performance using standard institutional metrics. Below are the definitions and specific calculation methodologies used in this pipeline.

### 1. Expectancy (Return on Risk / R-Multiple)
* **What it is:** The mathematical average amount the strategy expects to yield per trade, expressed as a ratio of the capital risked. 
* **Formula:** `(Win Rate % × Average Win R) - (Loss Rate % × Absolute Average Loss R)`
* **Calculation Note:** Because the account base currency is GBP but the traded assets (Gold, S&P 500, Oil) are priced in USD, calculating risk purely on asset price distance skews the data. This pipeline completely bypasses FX variance by calculating the R-Multiple based on Portfolio Risk: `R = Trade Profit (GBP) / (Rolling Account Capital (GBP) * 0.05)`.

### 2. Maximum Drawdown (Max DD)
* **What it is:** The largest single percentage drop in account equity from a historical peak to a subsequent trough. It is the ultimate test of strategy robustness and psychological pain tolerance.
* **Formula:** `Abs(Trough Value - Peak Value) / Peak Value`
* **Calculation Note:** Max Drawdown is calculated purely on *Closed Trade Equity*. It accurately scales with the compounding capital rather than tracking raw currency drops, giving an accurate percentage risk regardless of account size.

### 3. Annualized Sharpe Ratio
* **What it is:** Measures risk-adjusted performance, indicating how much excess return is generated per unit of volatility.
* **Formula:** `(Mean of Daily % Returns / Standard Deviation of Daily % Returns) * √252`
* **Calculation Note:** Daily returns were aggregated by grouping trade profits by their localized `exit_time` dates. A Sharpe ratio > 1.5 in this context indicates a highly consistent edge rather than volatile "gambling."

### 4. Profit Factor
* **What it is:** Shows how much money the strategy yields for every £1 it loses.
* **Formula:** `Gross Profit / Absolute Value of Gross Loss`
* **Calculation Note:** Institutional algorithms typically aim for a smooth, consistent Profit Factor between 1.4 and 2.0. Any value above 1.0 means the strategy is mathematically profitable.

---

## 🛠️ Methodology & Data Engineering

Building a reliable quantitative pipeline requires defending against "dirty" broker data. Important engineering edge cases solved in this project included:

1. **The MT5 "Hidden Space" Bug:** MetaTrader 5 exports often use non-breaking spaces (`\xa0`) as thousands separators instead of standard spaces or commas (e.g., `1 512.01`). Standard pandas string coercions turn these large winning trades into `NaN` values, artificially destroying the strategy's profitability. The pipeline explicitly scrubs `\xa0` via regex before float conversion.
2. **The "Future Capital" Trap:** Broker reports sort execution logs by *Entry Time*. If a compounding loop iterates over entry times, it will calculate position sizing based on capital from a trade that hasn't officially closed yet. The pipeline explicitly sorts all data by `exit_time` to guarantee true simulated equity.
3. **Gross Trade Equity vs. Net Balance:** The dashboard explicitly calculates **Gross Trade Equity** (Starting Capital + Trade P/L) to isolate the mathematical edge of the strategy. Non-trade cash flows (overnight swap fees, dividends, broker rebates) are intentionally filtered out to prevent broker-side fees from masking the raw quantitative edge.

---

## 🚀 Results & Dashboard Features
* **Automated Data Pipeline:** Cleans erratic MT5 HTML/CSV exports and standardizes financial data types.
* **Chronological Compounding Engine:** Dynamically rebuilds the account equity curve by applying the 5% risk calculation sequentially.
* **Currency-Agnostic Engine:** Calculates risk strictly in the account's base currency (GBP) to completely isolate the strategy's edge from USD/GBP exchange rate fluctuations.
* **Interactive Risk Simulator:** A session-state tracking simulator allowing users to adjust risk percentages (1%-25%), set initial capital, process dynamic withdrawals, and immediately visualize projected equity, Max Drawdown, and Sharpe Ratios.

---

## 📁 Project Structure

```text
├── data/
│   ├── raw/                 # Original MT5 CSV exports (ST01, ST02)
│   ├── interim/             # Standardized, cleaned, and sorted data
│   └── processed/           # Final engineered datasets with R-Multiples
│
├── notebooks/
│   ├── 01_Data_Loading_and_Cleaning.ipynb          # Handles datatypes and MT5 artifacts
│   └── 02_Feature_Engineering_and_Quant.ipynb      # Compounding loop and KPI generation
│
├── app/
│   └── dashboard.py         # Streamlit Application (UI, Plotly charts, Simulator)
│
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
