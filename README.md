# Bond Portfolio Dashboard
https://bondrisk.streamlit.app/

## Overview
The **Bond Portfolio Dashboard** is a Streamlit-based web application designed to help users analyze and manage their bond portfolios. The dashboard allows users to upload bond portfolio data in CSV format, calculate key financial metrics, and visualize the impact of changes in Yield to Maturity (YTM) on the portfolio's gain/loss.

---

## Features

1. **File Upload**:
   - Upload your bond portfolio in CSV format.
   - The application supports flexible column mapping to handle variations in column names (e.g., case sensitivity, extra spaces).

2. **Data Cleaning**:
   - Automatically standardizes column names to ensure compatibility with the application.
   - Validates the presence of required columns and provides error messages if any are missing.

3. **Key Calculations**:
   - **Initial Investment Value**: Calculates the initial cost of each bond based on its price and face value.
   - **Book Value**: Computes the amortized value of the bond up to the current date.
   - **Market Value**: Determines the current market value of the bond based on the yield to maturity (YTM).
   - **Gain/Loss**: Calculates the difference between the market value and the book value.

4. **Dynamic Yield Adjustment**:
   - Users can input a new YTM value to see how it impacts the bond's gain or loss.

5. **Data Visualization**:
   - Displays the uploaded and processed portfolio data in an interactive table.
   - Provides insights into the portfolio's performance and the impact of yield changes.

---

## How It Works

1. **Upload Your Portfolio**:
   - Prepare a CSV file with the following columns:
     - `Purchased Date`: The date the bond was purchased.
     - `Maturity Date`: The date the bond matures.
     - `Purchased YTM`: The yield to maturity at the time of purchase.
     - `Coupon`: The annual coupon rate of the bond.
     - `Face Value`: The face value of the bond.
     - `Initial Inv Value`: The initial investment value of the bond.
     - `Book Value`: The amortized value of the bond up to the current date.

2. **Flexible Column Mapping**:
   - The application automatically maps column names in your CSV file to the expected names, even if they have extra spaces, different capitalization, or slight variations.

3. **Dynamic Yield Adjustment**:
   - Enter a new YTM value in the input field to calculate the impact on the bond's gain or loss.
   - The application recalculates the market value and gain/loss for each bond based on the new YTM.

4. **View Results**:
   - The dashboard displays the updated portfolio with the recalculated gain/loss.
   - Users can analyze the impact of yield changes on their bond portfolio.

---

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd bond-portfolio-dashboard
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   streamlit run bond_dashboard.py
   ```

---

## Requirements

- Python 3.8+
- Required Python packages (listed in `requirements.txt`):
  - `streamlit`
  - `pandas`
  - `numpy`
  - `numpy-financial`

---

## Folder Structure
```
portfolio/
│
├── bond_dashboard.py       # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .gitignore              # Git ignore file
├── README.md               # Project documentation
```

---

## License
This project is licensed under the MIT License. See the LICENSE file for details.

---

Yes — **you *can* find finance‑related datasets on Kaggle**, but **pure Treasury bond transaction data (with investor records + buys over time)** isn’t very common there. Most Kaggle financial datasets are about *market rates, credit card spending, fraud detection, or stock prices*, which are useful but may not *exactly match* your DW‑BI internship topic unless you adapt them.([Baselight][1])

Here’s what you *can* find on Kaggle and how you might use it:

### 📌 1. **Daily Treasury Real Yield Curve Rates**

* Contains historical daily yield rates for different maturities (5y, 7y, 10y, etc.).
* Not transactional (no investor or purchase table), but useful if you want **bond performance trends over time**.([Baselight][2])
* *Use case:* You could **combine this with synthetic transaction data** to simulate buys based on real yield rates — perfect for DW.

🔗 Example dataset: “Daily Treasury Real Yield Curve Rates” on Kaggle

---

### 📌 2. **Personal Budget / Spending Transaction Data**

* Has individual financial transactions (amounts, dates, categories).
* While not bond data, this *is* OLTP transactional data with time series.([Baselight][1])
* *Use case:* You could **adapt the structure** to simulate Treasury transactions (e.g., treat categories as bond types).

---

### 📌 3. **Credit Card Transactions Dataset**

* Contains detailed transaction records (millions of rows) with amounts, dates, and more.
* Very useful for OLTP modelling.([Baselight][3])
* *Use case:* You could use its structure (transactions per customer) as a **template** and adapt it to invest/bond transactions.

---

### ❌ What *isn’t* readily available

* **Direct Kaggle dataset of investor bond purchases** (e.g., individual buys of government bonds with investor IDs) *is not commonly published.*
* Most financial Kaggle data is **market data (rates, stock prices)** or **credit card transaction logs**, not direct Treasury purchase logs.

---

## ✅ What You *Can* Do for Your Assignment

### **Option A — Use a Related Kaggle Dataset + Transform It**

You could take a **credit card transactions dataset** and:

1. Rename fields to bond transactions (e.g., user → investor, amount → total value, category → bond type).
2. Add tables for **Investors** and **Bonds**.
3. Generate synthetic Bond transactions over 1+ years.

This satisfies the OLTP dataset requirement because it becomes:

* Raw transactional data
* 1‑to‑many relationships
* Enough richness for DW modelling

💡 This is a valid solution because you’re *transforming* an OLTP-like dataset into your bond/treasury scenario.

---

### **Option B — Use Real Financial Time Series + Generate Synthetic Transactions**

Take a yield curve dataset (e.g., Treasury rates), then:

1. Create synthetic investors.
2. Create synthetic bond purchase logs based on real yields over time.
3. Build investor/bond tables and transaction table.

This gives you:

* Real **market context**
* Synthetic but consistent transactional dataset
* DW readiness (fact + dimensions)

---

## Quick Examples of Kaggle Financial Datasets You *Can Explore*

| Dataset                                   | Description                               | Potential Use                                       |
| ----------------------------------------- | ----------------------------------------- | --------------------------------------------------- |
| **Daily Treasury Real Yield Curve Rates** | Historical yields for Treasury securities | Base for generating bond pricing & yield attributes |
| **Personal Budget Transactions**          | Financial transactions                    | Template structure for transactional modelling      |
| **Credit Card Transactions**              | Millions of transaction records           | Strong OLTP example to adapt/bend to your scenario  |

---

## Summary

✅ **Yes, Kaggle has finance datasets** that you can adapt for your DW assignment.
❗ But **a ready‑made Treasury bond transaction dataset with investor data does *not* currently exist on Kaggle**.
➡️ You’ll likely need to **transform/adapt** a related Kaggle finance dataset into your Treasury OLTP structure, or generate synthetic transactions on top of real market data.([Baselight][2])

---

If you want, I can **find 2–3 specific Kaggle dataset links with direct URLs** that *best match* your Treasury scenario (and tell you exactly how to adapt each one).

Would you like direct download links next?

[1]: https://baselight.app/u/kaggle/dataset/ismetsemedov_personal_budget_transactions_dataset?utm_source=chatgpt.com "Personal Budget Transactions Dataset by Kaggle | Finance and Economics | Baselight"
[2]: https://baselight.app/u/kaggle/dataset/odezi45_daily_treasury_real_yield_curve_rates?utm_source=chatgpt.com "Daily Treasury Real Yield Curve Rates by Kaggle | Finance and Economics | Baselight"
[3]: https://baselight.app/u/kaggle/dataset/priyamchoksi_credit_card_transactions_dataset?utm_source=chatgpt.com "Credit Card Transactions Dataset by Kaggle | Finance and Economics Data | Baselight"
