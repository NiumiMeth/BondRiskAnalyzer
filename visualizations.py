import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# ==================== PAGE SETUP ====================
st.set_page_config(layout="wide", page_title="Treasury Bond Risk Dashboard")
st.title("Treasury Bond Risk and Yield Shock Engine")
st.caption("Institutional-grade treasury analytics for bond valuation, sensitivity, and yield-shock impact")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
    .dashboard-section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #E6EEF8;
        margin-top: 0.35rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid #4F8BFF;
        padding-left: 0.55rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #10294A 0%, #173A66 100%);
        border: 1px solid rgba(98, 158, 255, 0.35);
        border-radius: 12px;
        padding: 0.75rem 0.85rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.22);
        min-height: 88px;
    }
    .kpi-label {
        color: #A8C9FF;
        font-size: 0.80rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        color: #FFFFFF;
        font-size: 1.25rem;
        font-weight: 750;
        line-height: 1.2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_section_title(title):
    st.markdown(f'<div class="dashboard-section-title">{title}</div>', unsafe_allow_html=True)


def render_kpi_cards(kpi_items):
    columns = st.columns(len(kpi_items))
    for column, (label, value) in zip(columns, kpi_items):
        column.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sensitivity_visuals(dataframe, pl_column, section_title):
    if dataframe.empty or pl_column not in dataframe.columns:
        return

    render_section_title(section_title)
    chart_left, chart_right = st.columns([1.6, 1])

    plot_df = dataframe.copy().sort_values(pl_column, key=lambda s: s.abs(), ascending=True)

    with chart_left:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=plot_df[pl_column],
            y=plot_df["ISIN"],
            orientation="h",
            marker_color=np.where(plot_df[pl_column] >= 0, "#35C759", "#FF4D4F"),
            name="P/L Impact"
        ))
        fig_bar.update_layout(
            title="P/L Impact by ISIN",
            xaxis_title="P/L Impact",
            yaxis_title="ISIN",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=45, b=25),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_right:
        abs_sum = plot_df[pl_column].abs().sum()
        if abs_sum > 0:
            fig_donut = go.Figure(data=[go.Pie(
                labels=plot_df["ISIN"],
                values=plot_df[pl_column].abs(),
                hole=0.55,
                sort=False,
                textinfo="label+percent"
            )])
            fig_donut.update_layout(
                title="Share of Impact",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=45, b=25)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

# ==================== FILE UPLOAD ====================

# Allow Excel or CSV upload
uploaded_file = st.file_uploader(
    "Upload Bond Portfolio File (Excel or CSV)", 
    type=["xlsx", "csv"]
)

if uploaded_file is not None:


    with st.spinner("Processing portfolio..."):
        # Load file
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df_raw = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file type. Please upload an Excel or CSV file.")
            st.stop()

        # COLUMN MAPPING
        canonical_columns = {
            "isin": "ISIN",
            "initial inv date": "Initial Inv Date",
            "initial investment date": "Initial Inv Date",
            "purchase date": "Initial Inv Date",
            "purchased date": "Initial Inv Date",
            "maturity date": "Maturity Date",
            "coupon": "Coupon",
            "maturity value": "Maturity Value",
            "maturity value ": "Maturity Value",
            "face value": "Maturity Value",
            "ytm": "YTM",
            "selling ytm": "YTM",
            "purchased ytm": "Purchased YTM",
            "purchase ytm": "Purchased YTM",
            "initial ytm": "Purchased YTM",
            "initial inv value": "Initial Inv Value",
            "initial investment value": "Initial Inv Value",
            "book value": "Book Value"
        }
        df_raw.columns = [str(col).strip().lower() for col in df_raw.columns]
        df_raw.rename(columns=canonical_columns, inplace=True)
        existing_cols = list(dict.fromkeys([v for v in canonical_columns.values() if v in df_raw.columns]))
        df = df_raw[existing_cols].copy()

        essential = ["ISIN", "Maturity Date", "Coupon", "Maturity Value", "YTM"]
        missing = [c for c in essential if c not in df.columns]
        if missing:
            st.error(f"Uploaded file is missing required columns: {', '.join(missing)}")
            st.stop()

        # DATA CLEANING
        df["Maturity Value"] = pd.to_numeric(df["Maturity Value"].astype(str).str.replace(",", ""), errors="coerce")
        df["Coupon"] = pd.to_numeric(df["Coupon"].astype(str).str.replace("%", ""), errors="coerce") / 100
        df["YTM"] = pd.to_numeric(df["YTM"], errors="coerce") / 100
        df["Maturity Date"] = pd.to_datetime(df["Maturity Date"], errors="coerce")
        if "Initial Inv Date" in df.columns:
            df["Initial Inv Date"] = pd.to_datetime(df["Initial Inv Date"], errors="coerce")
        if "Initial Inv Value" in df.columns:
            df["Initial Inv Value"] = pd.to_numeric(df["Initial Inv Value"].astype(str).str.replace(",", ""), errors="coerce")
        if "Book Value" in df.columns:
            df["Book Value"] = pd.to_numeric(df["Book Value"].astype(str).str.replace(",", ""), errors="coerce")
        if "Purchased YTM" in df.columns:
            df["Purchased YTM"] = pd.to_numeric(df["Purchased YTM"], errors="coerce") / 100
        df = df.dropna(subset=essential)

        # SPOT DATE
        spot_date = st.date_input("Spot / Settlement Date", value=datetime.today())
        spot_date = pd.to_datetime(spot_date)
        df["Years to Maturity"] = (df["Maturity Date"] - spot_date).dt.days 
        df = df[df["Years to Maturity"] > 0]

        # ISIN FILTER
        st.sidebar.markdown("**Filter by ISIN**")
        isin_options = df["ISIN"].unique().tolist()
        selected_isins = st.sidebar.multiselect("Select ISINs to view", isin_options, default=isin_options)
        df = df[df["ISIN"].isin(selected_isins)]

        # PAGE SELECTOR
        st.header("Select Analysis")
        page = st.radio("Choose analysis:", ["Total Yield Shock", "ISIN-wise Yield Shock"], horizontal=True)

        # BOND PRICING FUNCTIONS
        def _bond_cashflow_schedule(face, coupon_rate, years, freq=2):
            periods = years * freq
            coupon = face * coupon_rate / freq
            n_full = int(np.floor(periods))
            fractional = periods - n_full

            times = [t for t in range(1, n_full + 1)]
            cashflows = [coupon] * n_full

            if fractional > 1e-12:
                times.append(periods)
                cashflows.append(coupon + face)
            elif n_full > 0:
                cashflows[-1] += face
            else:
                times = [periods]
                cashflows = [coupon + face]

            return np.array(times, dtype=float), np.array(cashflows, dtype=float)

        def bond_price(face, coupon_rate, ytm, years, freq=2):
            times, cashflows = _bond_cashflow_schedule(face, coupon_rate, years, freq)
            discount = (1 + ytm / freq) ** times
            return float(np.sum(cashflows / discount))

        def macaulay_duration(face, coupon_rate, ytm, years, freq=2):
            times, cashflows = _bond_cashflow_schedule(face, coupon_rate, years, freq)
            discount = (1 + ytm / freq) ** times
            pv = cashflows / discount
            price = np.sum(pv)
            macaulay_periods = np.sum(times * pv) / price
            return float(macaulay_periods / freq)

        def modified_duration(face, coupon_rate, ytm, years, freq=2):
            return macaulay_duration(face, coupon_rate, ytm, years, freq) / (1 + ytm/freq)

        def convexity(face, coupon_rate, ytm, years, freq=2):
            price = bond_price(face, coupon_rate, ytm, years, freq)
            dy = 0.0001
            price_up = bond_price(face, coupon_rate, ytm + dy, years, freq)
            price_down = bond_price(face, coupon_rate, ytm - dy, years, freq)
            return (price_up + price_down - 2 * price) / (price * (dy ** 2))

        def _add_months(date_value, months):
            return (pd.Timestamp(date_value) + pd.DateOffset(months=months)).normalize()

        def excel_price_clean(settlement_date, maturity_date, coupon_rate, yield_rate, redemption=100, freq=2, basis=1):
            if basis != 1:
                return np.nan

            settlement = pd.Timestamp(settlement_date).normalize()
            maturity = pd.Timestamp(maturity_date).normalize()
            if pd.isna(settlement) or pd.isna(maturity) or settlement >= maturity:
                return np.nan

            months = int(12 / freq)

            prev_coupon = maturity
            safety = 0
            while prev_coupon > settlement and safety < 500:
                prev_coupon = _add_months(prev_coupon, -months)
                safety += 1

            next_coupon = _add_months(prev_coupon, months)

            e = (next_coupon - prev_coupon).days
            a = (settlement - prev_coupon).days
            dsc = (next_coupon - settlement).days

            if e <= 0 or dsc < 0:
                return np.nan

            n = 0
            coupon_date = next_coupon
            while coupon_date <= maturity and n < 500:
                n += 1
                coupon_date = _add_months(coupon_date, months)

            if n <= 0:
                return np.nan

            c = 100 * coupon_rate / freq
            y = 1 + yield_rate / freq
            frac = dsc / e

            pv = 0.0
            for k in range(1, n + 1):
                exponent = (k - 1) + frac
                pv += c / (y ** exponent)
            pv += redemption / (y ** ((n - 1) + frac))

            accrued_interest = c * (a / e)
            clean_price = pv - accrued_interest
            return float(clean_price)

        def calculated_initial_inv_value(row):
            if "Initial Inv Date" not in row.index:
                return np.nan

            inv_date = row["Initial Inv Date"]
            mat_date = row["Maturity Date"]
            face = row["Maturity Value"]
            coupon_rate = row["Coupon"]
            yld = row["Purchased YTM"] if "Purchased YTM" in row.index and pd.notnull(row.get("Purchased YTM", np.nan)) else row["YTM"]

            if pd.isna(inv_date) or pd.isna(mat_date) or pd.isna(face) or pd.isna(coupon_rate) or pd.isna(yld):
                return np.nan

            price_per_100 = excel_price_clean(inv_date, mat_date, coupon_rate, yld, redemption=100, freq=2, basis=1)
            if pd.isna(price_per_100):
                return np.nan

            return float(round(price_per_100, 4) * (face / 100))

        def calculated_book_value(row, spot_dt):
            mat_date = row["Maturity Date"]
            face = row["Maturity Value"]
            coupon_rate = row["Coupon"]
            yld = row["Purchased YTM"] if "Purchased YTM" in row.index and pd.notnull(row.get("Purchased YTM", np.nan)) else row["YTM"]

            if pd.isna(mat_date) or pd.isna(face) or pd.isna(coupon_rate) or pd.isna(yld):
                return np.nan

            price_per_100 = excel_price_clean(spot_dt, mat_date, coupon_rate, yld, redemption=100, freq=2, basis=1)
            if pd.isna(price_per_100):
                return np.nan

            return float(round(price_per_100, 4) * (face / 100))

        # BASE CALCULATIONS
        df["Price"] = df.apply(lambda row: bond_price(row["Maturity Value"], row["Coupon"], row["YTM"], row["Years to Maturity"]), axis=1)
        df["Market Value"] = df["Price"]
        df["Macaulay Duration"] = df.apply(lambda row: macaulay_duration(row["Maturity Value"], row["Coupon"], row["YTM"], row["Years to Maturity"]), axis=1)
        df["Modified Duration"] = df.apply(lambda row: modified_duration(row["Maturity Value"], row["Coupon"], row["YTM"], row["Years to Maturity"]), axis=1)
        df["Convexity"] = df.apply(lambda row: convexity(row["Maturity Value"], row["Coupon"], row["YTM"], row["Years to Maturity"]), axis=1)
        df["DV01"] = df["Modified Duration"] * df["Market Value"] * 0.0001
        if "Initial Inv Date" in df.columns:
            df["Initial Inv Value (Calculated)"] = df.apply(calculated_initial_inv_value, axis=1)
            df["Book Value (Calculated)"] = df.apply(lambda row: calculated_book_value(row, spot_date), axis=1)
            df["MTM vs Book (Calculated)"] = df["Market Value"] - df["Book Value (Calculated)"]
            if "Book Value" in df.columns:
                df["Book Value Diff"] = df["Book Value (Calculated)"] - df["Book Value"]
        else:
            st.info("To calculate Book Value from upload, include at least 'Initial Inv Date'. Optional fields: 'Initial Inv Value', 'Purchased YTM', and uploaded 'Book Value' for comparison.")

        # Per-ISIN summary table
        def maturity_date_summary(date_series):
            valid_dates = pd.to_datetime(date_series, errors="coerce").dropna()
            if valid_dates.empty:
                return ""
            unique_dates = sorted(valid_dates.dt.strftime("%Y-%m-%d").unique().tolist())
            if len(unique_dates) == 1:
                return unique_dates[0]
            return f"{unique_dates[0]} to {unique_dates[-1]}"

        def render_isin_summary(dataframe, market_value_col):
            isin_summary = (
                dataframe.groupby("ISIN", as_index=False)
                .agg(
                    Maturity_Date=("Maturity Date", maturity_date_summary),
                    Total_Maturity_Value=("Maturity Value", "sum"),
                    Total_Market_Value=(market_value_col, "sum"),
                )
                .rename(
                    columns={
                        "Maturity_Date": "Maturity Date",
                        "Total_Maturity_Value": "Total Maturity Value",
                        "Total_Market_Value": "Total Market Value",
                    }
                )
            )
            st.subheader("ISIN Summary (Separate ISIN Totals)")
            isin_summary_display = isin_summary.copy()
            for col in ["Total Maturity Value", "Total Market Value"]:
                isin_summary_display[col] = isin_summary_display[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notnull(x) else ""
                )
            st.dataframe(isin_summary_display, use_container_width=True)

        def render_grouped_portfolio_table(dataframe, mode="total"):
            st.subheader("Portfolio Details (Grouped by ISIN)")

            base_columns = [
                "ISIN",
                "Initial Inv Date", "Maturity Date", "Coupon", "Maturity Value", "YTM",
                "Years to Maturity",
                "Purchased YTM", "Initial Inv Value", "Initial Inv Value (Calculated)",
                "Book Value", "Book Value (Calculated)", "Market Value", "MTM vs Book (Calculated)",
                "Modified Duration", "DV01"
            ]

            total_shock_columns = [
                "New_YTM", "New Price", "Price Change", "P/L Impact", "Duration Approx P/L", "% Contribution to P/L"
            ]

            isin_shock_columns = [
                "ISIN_Specific_Shock", "ISIN_Specific_YTM", "ISIN_Specific_Price",
                "ISIN_Specific_Price Change", "ISIN_Specific_P/L Impact",
                "ISIN_Specific_Duration Approx P/L", "ISIN_Specific_% Contribution to P/L"
            ]

            selected_columns = base_columns + (total_shock_columns if mode == "total" else isin_shock_columns)
            selected_columns = [c for c in selected_columns if c in dataframe.columns]

            date_cols = ["Initial Inv Date", "Maturity Date"]
            pct_cols = [
                "Coupon", "YTM", "Purchased YTM", "New_YTM", "ISIN_Specific_YTM",
                "ISIN_Specific_Shock", "% Contribution to P/L", "ISIN_Specific_% Contribution to P/L"
            ]
            currency_cols = [
                "Maturity Value", "Initial Inv Value", "Initial Inv Value (Calculated)",
                "Book Value", "Book Value (Calculated)", "Market Value", "MTM vs Book (Calculated)",
                "New Price", "Price Change", "P/L Impact", "Duration Approx P/L",
                "ISIN_Specific_Price", "ISIN_Specific_Price Change", "ISIN_Specific_P/L Impact",
                "ISIN_Specific_Duration Approx P/L", "DV01"
            ]
            float_cols = ["Years to Maturity", "Modified Duration"]

            grouped_df = dataframe.sort_values(["ISIN", "Maturity Date"]).copy()
            combined_rows = []
            for isin, isin_df in grouped_df.groupby("ISIN", dropna=False):
                display_df = isin_df[selected_columns].copy()

                for col in date_cols:
                    if col in display_df.columns:
                        display_df[col] = pd.to_datetime(display_df[col], errors="coerce").dt.strftime("%Y-%m-%d")

                for col in pct_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "")

                for col in currency_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

                for col in float_cols:
                    if col in display_df.columns:
                        if col == "Years to Maturity":
                            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
                        else:
                            display_df[col] = display_df[col].apply(lambda x: f"{x:.4f}" if pd.notnull(x) else "")

                header_row = {col: "" for col in selected_columns}
                header_row["ISIN"] = f"ISIN: {isin}"

                combined_rows.append(pd.DataFrame([header_row], columns=selected_columns))
                combined_rows.append(display_df)

            if combined_rows:
                final_table = pd.concat(combined_rows, ignore_index=True)

                def highlight_isin_header(row):
                    isin_value = str(row.get("ISIN", ""))
                    if isin_value.startswith("ISIN:"):
                        return ["background-color: #DDE5FF; color: #111111; font-weight: 700;"] * len(row)
                    return [""] * len(row)

                styled_table = final_table.style.apply(highlight_isin_header, axis=1)
                st.dataframe(styled_table, use_container_width=True)

        if page == "Total Yield Shock":
            # ==================== YIELD SHOCK ====================
            render_section_title("Total (Parallel) Yield Shock Analysis")
            st.sidebar.header("Yield Shock Settings")
            shock_pct = st.sidebar.number_input("Parallel Yield Shock (%)", value=0.0, step=0.1)
            shock = shock_pct / 100

            df["New_YTM"] = df["YTM"] + shock
            df["New Price"] = df.apply(lambda row: bond_price(row["Maturity Value"], row["Coupon"], row["New_YTM"], row["Years to Maturity"]), axis=1)
            df["Price Change"] = df["New Price"] - df["Price"]
            df["P/L Impact"] = df["Price Change"]
            df["Duration Approx P/L"] = -df["Modified Duration"] * df["Market Value"] * shock
            total_pl = df["P/L Impact"].sum()
            df["% Contribution to P/L"] = df["P/L Impact"] / total_pl * 100 if total_pl != 0 else 0

            render_isin_summary(df, "New Price")


            # Portfolio Metrics
            total_mv = df["Market Value"].sum()
            weighted_duration = (df["Modified Duration"] * df["Market Value"]).sum() / total_mv
            total_dv01 = df["DV01"].sum()
            render_kpi_cards([
                ("Total Market Value", f"{total_mv:,.2f}"),
                ("Total P/L Impact", f"{total_pl:,.2f}"),
                ("Weighted Duration", f"{weighted_duration:.2f}"),
                ("Portfolio DV01", f"{total_dv01:,.2f}"),
            ])

            # Top 5 Most Sensitive ISINs
            top_sensitive = df[["ISIN", "Market Value", "Modified Duration", "DV01", "Price Change", "P/L Impact"]].copy()
            top_sensitive = top_sensitive.reindex(top_sensitive["P/L Impact"].abs().sort_values(ascending=False).index).head(5)
            top_sensitive_display = top_sensitive.copy()
            for col in ["Market Value", "Price Change", "P/L Impact", "DV01"]:
                if col in top_sensitive_display.columns:
                    top_sensitive_display[col] = top_sensitive_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
            st.dataframe(top_sensitive_display, use_container_width=True)
            render_sensitivity_visuals(top_sensitive, "P/L Impact", "Top 5 Most Sensitive ISINs (by P/L Impact)")

            # Affected ISINS
            render_section_title("ISINs Affected by Yield Shock")
            affected = df[["ISIN","Market Value","Modified Duration","DV01","Price Change","P/L Impact","% Contribution to P/L","Duration Approx P/L"]].sort_values("P/L Impact", ascending=True)
            def color_price(val):
                color = 'green' if val >= 0 else 'red'
                return f'color: {color}'
            st.dataframe(affected.style.applymap(color_price, subset=["Price Change","P/L Impact"]), use_container_width=True)

            render_grouped_portfolio_table(df, mode="total")

            # Yield Curve Visualization
            render_section_title("Yield Curve Visualization")
            fig_yield = go.Figure()
            fig_yield.add_trace(go.Scatter(
                x=df["Years to Maturity"],
                y=df["YTM"] * 100,
                mode='lines+markers',
                name='Original YTM',
                line=dict(color='blue', width=2)
            ))
            fig_yield.add_trace(go.Scatter(
                x=df["Years to Maturity"],
                y=df["New_YTM"] * 100,
                mode='lines+markers',
                name=f'YTM after {shock_pct:.2f}% shock',
                line=dict(color='red', width=2, dash='dash')
            ))
            fig_yield.update_layout(
                title='Yield Curve',
                xaxis_title='Years to Maturity',
                yaxis_title='Yield (%)',
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_yield, use_container_width=True)

            # Download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Risk Report", csv, "bond_risk_report.csv", "text/csv")

        elif page == "ISIN-wise Yield Shock":
            # ==================== ISIN-SPECIFIC YIELD SHOCK ====================
            render_section_title("ISIN-wise Yield Shock Analysis")
            st.sidebar.header("ISIN-Specific Yield Shock Settings")
            unique_isins = df["ISIN"].unique()
            isin_shocks = {}
            for isin in unique_isins:
                isin_shocks[isin] = st.sidebar.number_input(f"Yield Shock for ISIN {isin} (%)", value=0.0, step=0.1)

            def apply_isin_shock(row):
                isin = row["ISIN"]
                specific_shock = isin_shocks.get(isin, 0.0) / 100
                return row["YTM"] + specific_shock

            df["ISIN_Specific_Shock"] = df["ISIN"].map(lambda x: isin_shocks.get(x, 0.0) / 100)
            df["ISIN_Specific_YTM"] = df.apply(apply_isin_shock, axis=1)
            df["ISIN_Specific_Price"] = df.apply(lambda row: bond_price(row["Maturity Value"], row["Coupon"], row["ISIN_Specific_YTM"], row["Years to Maturity"]), axis=1)
            df["ISIN_Specific_Price Change"] = df["ISIN_Specific_Price"] - df["Price"]
            df["ISIN_Specific_P/L Impact"] = df["ISIN_Specific_Price Change"]
            df["ISIN_Specific_Maturity Date"] = df["Maturity Date"]
            df["ISIN_Specific_Market Value"] = df["ISIN_Specific_Price"]
            df["ISIN_Specific_Modified Duration"] = df["Modified Duration"]
            df["ISIN_Specific_DV01"] = df["DV01"]
            total_pl = df["ISIN_Specific_P/L Impact"].sum()
            df["ISIN_Specific_% Contribution to P/L"] = df["ISIN_Specific_P/L Impact"] / total_pl * 100 if total_pl != 0 else 0
            df["ISIN_Specific_Duration Approx P/L"] = -df["ISIN_Specific_Modified Duration"] * df["ISIN_Specific_Market Value"] * df["ISIN_Specific_Shock"]

            render_isin_summary(df, "ISIN_Specific_Market Value")

            # ...existing code...

            # ISIN-wise Price Change Table
            render_section_title("ISIN-wise Shock Price Changes")
            price_change_table = df[["ISIN", "Price", "ISIN_Specific_Price", "ISIN_Specific_Price Change"]].copy()
            # Sort by absolute price change descending
            price_change_table = price_change_table.reindex(
                price_change_table["ISIN_Specific_Price Change"].abs().sort_values(ascending=False).index
            )
            for col in ["Price", "ISIN_Specific_Price", "ISIN_Specific_Price Change"]:
                price_change_table[col] = price_change_table[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
            st.dataframe(price_change_table, use_container_width=True)

            # Portfolio Metrics
            total_mv = df["ISIN_Specific_Market Value"].sum()
            weighted_duration = (df["ISIN_Specific_Modified Duration"] * df["ISIN_Specific_Market Value"]).sum() / total_mv
            total_dv01 = df["ISIN_Specific_DV01"].sum()
            render_kpi_cards([
                ("Total Market Value", f"{total_mv:,.2f}"),
                ("Total P/L Impact", f"{total_pl:,.2f}"),
                ("Weighted Duration", f"{weighted_duration:.2f}"),
                ("Portfolio DV01", f"{total_dv01:,.2f}"),
            ])

            # Top 5 Most Sensitive ISINs (ISIN-wise Shock)
            top_isin_specific = df[["ISIN", "ISIN_Specific_P/L Impact", "ISIN_Specific_Price Change", "ISIN_Specific_Market Value", "ISIN_Specific_Modified Duration", "ISIN_Specific_DV01"]].copy()
            top_isin_specific = top_isin_specific.reindex(top_isin_specific["ISIN_Specific_P/L Impact"].abs().sort_values(ascending=False).index).head(5)
            top_isin_display = top_isin_specific.copy()
            for col in ["ISIN_Specific_P/L Impact", "ISIN_Specific_Price Change", "ISIN_Specific_Market Value", "ISIN_Specific_DV01"]:
                if col in top_isin_display.columns:
                    top_isin_display[col] = top_isin_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
            st.dataframe(top_isin_display, use_container_width=True)
            render_sensitivity_visuals(
                top_isin_specific.rename(columns={"ISIN_Specific_P/L Impact": "P/L Impact"}),
                "P/L Impact",
                "Top 5 Most Sensitive ISINs (ISIN-wise Yield Shock)"
            )

            render_grouped_portfolio_table(df, mode="isin")

            # ISIN-specific yield curve visualization
            render_section_title("ISIN-Specific Yield Curve Visualization")
            fig_isin_yield = go.Figure()
            fig_isin_yield.add_trace(go.Scatter(
                x=df["Years to Maturity"],
                y=df["YTM"] * 100,
                mode='lines+markers',
                name='Original YTM',
                line=dict(color='blue', width=2)
            ))
            fig_isin_yield.add_trace(go.Scatter(
                x=df["Years to Maturity"],
                y=df["ISIN_Specific_YTM"] * 100,
                mode='lines+markers',
                name='ISIN-Specific YTM',
                line=dict(color='green', width=2, dash='dot')
            ))
            fig_isin_yield.update_layout(
                title='ISIN-Specific Yield Curve',
                xaxis_title='Years to Maturity',
                yaxis_title='Yield (%)',
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_isin_yield, use_container_width=True)

            # Download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download ISIN-wise Risk Report", csv, "isin_wise_risk_report.csv", "text/csv")

else:
    st.info("Upload a portfolio file to begin analysis.")