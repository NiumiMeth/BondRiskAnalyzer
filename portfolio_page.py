from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import auth


st.set_page_config(page_title="Portfolio Manager", layout="wide")

# require user or admin role to view portfolio page
auth.require_role(["user", "admin"])

EXPECTED_COLUMNS = [
    "Port. Index",
    "Instrument",
    "Deal No.",
    "ISIN",
    "Initial Inv Date",
    "Maturity Date",
    "Coupon",
    "Maturity Value",
    "YTM",
    "Yield",
    "Market value",
    "Duration",
]


def parse_number(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace(",", "")
    if text == "":
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def parse_rate(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text == "":
        return np.nan
    has_percent = "%" in text
    text = text.replace("%", "").replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return np.nan
    if has_percent or number > 1:
        return number / 100.0
    return number


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    rename_map = {"Maturity Value ": "Maturity Value"}
    df = df.rename(columns=rename_map)
    return df


def load_portfolio(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df = clean_columns(df)

    missing_columns = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError("Input file is missing required columns: " + ", ".join(missing_columns))

    df = df[EXPECTED_COLUMNS].copy()
    df = df.dropna(how="all")

    df["ISIN"] = df["ISIN"].astype(str).str.strip()
    df = df[df["ISIN"].notna() & (df["ISIN"] != "") & (df["ISIN"] != "nan")].copy()

    df["Initial Inv Date"] = pd.to_datetime(df["Initial Inv Date"], dayfirst=True, errors="coerce")
    df["Maturity Date"] = pd.to_datetime(df["Maturity Date"], dayfirst=True, errors="coerce")

    for column in ["Maturity Value", "Market value", "Duration"]:
        df[column] = df[column].map(parse_number)

    df["Coupon"] = df["Coupon"].map(parse_rate)
    df["YTM"] = df["YTM"].map(parse_rate)
    df["Yield"] = df["Yield"].map(parse_rate)

    df = df.dropna(subset=["Initial Inv Date", "Maturity Date", "Maturity Value", "Coupon", "YTM", "Yield"])
    return df


def get_coupon_window(
    settlement_date: pd.Timestamp,
    maturity_date: pd.Timestamp,
    frequency: int = 2,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    months = int(12 / frequency)
    settlement = pd.Timestamp(settlement_date).normalize()
    maturity = pd.Timestamp(maturity_date).normalize()

    if settlement >= maturity:
        raise ValueError("Settlement date must be earlier than maturity date.")

    next_coupon = maturity
    while True:
        prev_coupon = next_coupon - pd.DateOffset(months=months)
        if prev_coupon <= settlement < next_coupon:
            return prev_coupon, next_coupon
        next_coupon = prev_coupon


def excel_price_actual_actual(
    settlement_date: pd.Timestamp,
    maturity_date: pd.Timestamp,
    coupon_rate: float,
    annual_yield: float,
    redemption: float = 100.0,
    frequency: int = 2,
) -> tuple[float, float, float]:
    settlement = pd.Timestamp(settlement_date).normalize()
    maturity = pd.Timestamp(maturity_date).normalize()

    if settlement >= maturity:
        return 0.0, 0.0, 0.0

    prev_coupon, next_coupon = get_coupon_window(settlement, maturity, frequency)

    e = (next_coupon - prev_coupon).days
    a = (settlement - prev_coupon).days
    dsc = (next_coupon - settlement).days

    if e <= 0:
        return 0.0, 0.0, 0.0

    coupon_per_100 = 100.0 * coupon_rate / frequency
    discount_base = 1.0 + annual_yield / frequency
    discount_base = max(discount_base, 1e-8)

    n = 0
    current = maturity
    while current > settlement:
        n += 1
        current = current - pd.DateOffset(months=int(12 / frequency))

    if n <= 0:
        return 0.0, 0.0, 0.0

    exponent = (n - 1) + (dsc / e)
    pv_red_plus_coupon = (redemption + coupon_per_100) / (discount_base**exponent)

    pv_intermediate = 0.0
    for k in range(1, n):
        k_exp = (k - 1) + (dsc / e)
        pv_intermediate += coupon_per_100 / (discount_base**k_exp)

    accrued_100 = coupon_per_100 * (a / e)
    clean_price_100 = pv_red_plus_coupon + pv_intermediate - accrued_100
    full_price_100 = clean_price_100 + accrued_100

    return clean_price_100, accrued_100, full_price_100


def run_portfolio_valuation(df: pd.DataFrame, valuation_date: pd.Timestamp) -> pd.DataFrame:
    output = df.copy()

    clean_price_100 = []
    accrued_100 = []
    price_100 = []
    clean_value = []
    full_value = []
    initial_inv_value = []
    book_value = []
    gain_loss = []

    for _, row in output.iterrows():
        face = float(row["Maturity Value"])
        purchase_date = pd.Timestamp(row["Initial Inv Date"])
        maturity_date = pd.Timestamp(row["Maturity Date"])
        coupon_rate = float(row["Coupon"])
        purchased_ytm = float(row["YTM"])
        selling_ytm = float(row["Yield"])

        clean_100_now, accrued_now_100, full_100_now = excel_price_actual_actual(
            settlement_date=valuation_date,
            maturity_date=maturity_date,
            coupon_rate=coupon_rate,
            annual_yield=selling_ytm,
            redemption=100.0,
            frequency=2,
        )

        clean_100_now = round(clean_100_now, 4)
        accrued_now_100 = round(accrued_now_100, 4)
        full_100_now = round(clean_100_now + accrued_now_100, 4)

        init_price_100, _, _ = excel_price_actual_actual(
            settlement_date=purchase_date,
            maturity_date=maturity_date,
            coupon_rate=coupon_rate,
            annual_yield=purchased_ytm,
            redemption=100.0,
            frequency=2,
        )
        init_price_100 = round(init_price_100, 4)
        init_value = init_price_100 * (face / 100.0)

        total_days = max((maturity_date - purchase_date).days, 1)
        elapsed_days = (pd.Timestamp(valuation_date) - purchase_date).days
        elapsed_days = min(max(elapsed_days, 0), total_days)

        book_val = (((face - init_value) / total_days) * elapsed_days) + init_value

        clean_val = clean_100_now * (face / 100.0)
        full_val = full_100_now * (face / 100.0)
        gl_value = clean_val - book_val

        clean_price_100.append(clean_100_now)
        accrued_100.append(accrued_now_100)
        price_100.append(full_100_now)
        clean_value.append(clean_val)
        full_value.append(full_val)
        initial_inv_value.append(init_value)
        book_value.append(book_val)
        gain_loss.append(gl_value)

    output["Clean Price"] = clean_price_100
    output["Accrued Int"] = accrued_100
    output["Price 100%"] = price_100
    output["Clean Value"] = clean_value
    output["Full Value"] = full_value
    output["Initial Inv Value"] = initial_inv_value
    output["Book Value"] = book_value
    output["Gain/Loss"] = gain_loss

    return output


def aggregate_by_isin(valued_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        valued_df.groupby("ISIN", as_index=False)
        .agg(
            Positions=("Deal No.", "count"),
            Face_Value=("Maturity Value", "sum"),
            Clean_Value=("Clean Value", "sum"),
            Full_Value=("Full Value", "sum"),
            Book_Value=("Book Value", "sum"),
            Gain_Loss=("Gain/Loss", "sum"),
            Input_Market_Value=("Market value", "max"),
        )
        .sort_values("ISIN")
    )
    grouped["Clean_minus_Book"] = grouped["Clean_Value"] - grouped["Book_Value"]
    grouped["Full_minus_Book"] = grouped["Full_Value"] - grouped["Book_Value"]
    return grouped


def main() -> None:
    st.title("Portfolio Manager")
    st.write("Add holdings manually or upload a portfolio file (same format as the dashboard).")

    if "portfolio_df" not in st.session_state:
        st.session_state["portfolio_df"] = pd.DataFrame(columns=EXPECTED_COLUMNS)

    uploaded_file = st.file_uploader("Upload portfolio CSV/Excel to add", type=["csv", "xlsx", "xls"])
    if uploaded_file:
        try:
            new_df = load_portfolio(uploaded_file)
            st.session_state["portfolio_df"] = pd.concat([st.session_state["portfolio_df"], new_df], ignore_index=True)
            st.success(f"Added {len(new_df)} rows to portfolio.")
        except Exception as e:
            st.error(f"Failed to load file: {e}")

    with st.expander("Add single holding manually"):
        with st.form("add_entry"):
            p_index = st.text_input("Port. Index", value="")
            instrument = st.text_input("Instrument", value="")
            deal_no = st.text_input("Deal No.", value="")
            isin = st.text_input("ISIN", value="")
            init_date = st.date_input("Initial Inv Date", value=date.today())
            mat_date = st.date_input("Maturity Date", value=date.today())
            coupon = st.text_input("Coupon (e.g. 5% or 0.05)", value="0.00")
            mat_value = st.number_input("Maturity Value", value=0.0, format="%.2f")
            ytm = st.text_input("YTM (e.g. 4% or 0.04)", value="0.00")
            yld = st.text_input("Yield (market) (e.g. 4% or 0.04)", value="0.00")
            market_val = st.number_input("Market value", value=0.0, format="%.2f")
            duration = st.number_input("Duration", value=0.0, format="%.2f")
            add_clicked = st.form_submit_button("Add to portfolio")

            if add_clicked:
                row = {
                    "Port. Index": p_index,
                    "Instrument": instrument,
                    "Deal No.": deal_no,
                    "ISIN": isin,
                    "Initial Inv Date": pd.Timestamp(init_date),
                    "Maturity Date": pd.Timestamp(mat_date),
                    "Coupon": coupon,
                    "Maturity Value": mat_value,
                    "YTM": ytm,
                    "Yield": yld,
                    "Market value": market_val,
                    "Duration": duration,
                }
                try:
                    tmp = pd.DataFrame([row])
                    tmp = clean_columns(tmp)
                    tmp["Coupon"] = tmp["Coupon"].map(parse_rate)
                    tmp["YTM"] = tmp["YTM"].map(parse_rate)
                    tmp["Yield"] = tmp["Yield"].map(parse_rate)
                    tmp["Maturity Value"] = tmp["Maturity Value"].map(parse_number)
                    st.session_state["portfolio_df"] = pd.concat([st.session_state["portfolio_df"], tmp], ignore_index=True)
                    st.success("Holding added to portfolio.")
                except Exception as e:
                    st.error(f"Could not add holding: {e}")

    st.markdown("---")
    st.subheader("Current Portfolio")
    if st.session_state["portfolio_df"].empty:
        st.info("No holdings in portfolio. Add manually or upload a file.")
        return

    st.dataframe(st.session_state["portfolio_df"], use_container_width=True)

    valuation_date = st.date_input("Valuation Date for totals", value=date.today())
    valuation_timestamp = pd.Timestamp(valuation_date)

    try:
        cleaned = clean_columns(st.session_state["portfolio_df"]).copy()
        for col in ["Maturity Value", "Market value", "Duration"]:
            cleaned[col] = cleaned[col].map(parse_number)
        cleaned["Coupon"] = cleaned["Coupon"].map(parse_rate)
        cleaned["YTM"] = cleaned["YTM"].map(parse_rate)
        cleaned["Yield"] = cleaned["Yield"].map(parse_rate)

        st.markdown("---")
        st.subheader("Yield Scenario Controls")
        control_left, control_right = st.columns([3, 1])
        with control_left:
            shock_pct = st.number_input(
                "Parallel Yield Shift (%)",
                min_value=-10.0,
                max_value=10.0,
                value=0.0,
                step=0.05,
                format="%.2f",
                help="Enter the yield shift in percent (e.g., 0.50 = +50 bps).",
            )
            funding_rate_pct = st.number_input(
                "Global Funding Rate (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Global funding (repo) rate used to compute funding cost if per-deal rate not provided.",
            )
            st.caption("Apply a parallel shift to the `Yield` column for scenario valuation.")
        with control_right:
            st.metric("Selected Shift", f"{shock_pct:+.2f}%")

        edit_yields = st.checkbox("Edit yields inline (apply before scenario)", value=False)
        if edit_yields:
            st.caption("Edit the `Yield` values in-place; these values will be used as the base for scenario shifts.")
            editable = st.experimental_data_editor(
                cleaned[["Port. Index", "Deal No.", "ISIN", "Yield"]], num_rows="dynamic"
            )
            # update yields from edited table
            try:
                cleaned = cleaned.copy()
                cleaned = cleaned.drop(columns=["Yield"]) .merge(
                    editable[["Port. Index", "Deal No.", "ISIN", "Yield"]], on=["Port. Index", "Deal No.", "ISIN"], how="left"
                )
            except Exception:
                # fallback: if merge fails, attempt to assign by index
                cleaned.loc[editable.index, "Yield"] = editable["Yield"].values

        # prepare base and shocked dataframes
        shock_rate = shock_pct / 100.0

        cleaned_base = cleaned.copy()
        cleaned_shocked = cleaned.copy()
        cleaned_shocked["Yield"] = cleaned_shocked["Yield"].fillna(0.0) + shock_rate

        valued_base = run_portfolio_valuation(cleaned_base, valuation_timestamp)
        valued_shocked = run_portfolio_valuation(cleaned_shocked, valuation_timestamp)

        # Compute funding cost and coupons received per deal
        try:
            purchase_vals = []
            holding_days = []
            funding_rates = []
            funding_costs = []
            coupons_received = []

            for _, row in cleaned.iterrows():
                face = float(row["Maturity Value"])
                purchase_date = pd.Timestamp(row["Initial Inv Date"])
                maturity_date = pd.Timestamp(row["Maturity Date"])
                coupon_rate = float(row["Coupon"])
                purchased_ytm = float(row["YTM"])

                # purchase full price (use excel_price_actual_actual)
                init_clean_100, init_accrued_100, init_full_100 = excel_price_actual_actual(
                    settlement_date=purchase_date,
                    maturity_date=maturity_date,
                    coupon_rate=coupon_rate,
                    annual_yield=purchased_ytm,
                    redemption=100.0,
                    frequency=2,
                )
                purchase_full_value = init_full_100 * (face / 100.0)

                days = max((valuation_timestamp - purchase_date).days, 0)

                # per-deal funding rate if provided, else global
                per_rate = None
                if "Funding Rate" in cleaned.columns:
                    try:
                        per_rate = parse_rate(row.get("Funding Rate", np.nan))
                    except Exception:
                        per_rate = None
                rate = float(per_rate) if (per_rate is not None and not pd.isna(per_rate)) else (funding_rate_pct / 100.0)

                f_cost = purchase_full_value * rate * (days / 365.0)

                # coupons received since purchase up to valuation
                try:
                    schedule = coupon_date.get_coupon_schedule(maturity_date, purchase_date, frequency=2)
                    passed_coupons = [d for d in schedule if (d <= valuation_timestamp) and (d >= purchase_date)]
                    coupon_amt = face * coupon_rate / 2.0
                    coupons_recv = coupon_amt * len(passed_coupons)
                except Exception:
                    coupons_recv = 0.0

                purchase_vals.append(purchase_full_value)
                holding_days.append(days)
                funding_rates.append(rate)
                funding_costs.append(f_cost)
                coupons_received.append(coupons_recv)

            valued_base = valued_base.copy()
            valued_shocked = valued_shocked.copy()

            valued_base["Purchase Full Value"] = purchase_vals
            valued_base["Holding Days"] = holding_days
            valued_base["Funding Rate"] = funding_rates
            valued_base["Funding Cost"] = funding_costs
            valued_base["Coupons Received"] = coupons_received

            valued_shocked["Purchase Full Value"] = purchase_vals
            valued_shocked["Holding Days"] = holding_days
            valued_shocked["Funding Rate"] = funding_rates
            valued_shocked["Funding Cost"] = funding_costs
            valued_shocked["Coupons Received"] = coupons_received

            # Net P/L per deal: (Sales Value - Purchase Value) + Coupons Received - Funding Cost
            valued_base["Net P/L"] = (valued_base["Full Value"] - valued_base["Purchase Full Value"]) + valued_base["Coupons Received"] - valued_base["Funding Cost"]
            valued_shocked["Net P/L"] = (valued_shocked["Full Value"] - valued_shocked["Purchase Full Value"]) + valued_shocked["Coupons Received"] - valued_shocked["Funding Cost"]
        except Exception as e:
            st.warning(f"Could not compute funding costs per deal: {e}")

        total_book_base = float(valued_base["Book Value"].sum())
        total_full_base = float(valued_base["Full Value"].sum())
        total_clean_base = float(valued_base["Clean Value"].sum())
        total_gl_base = float(valued_base["Gain/Loss"].sum())

        total_book_shocked = float(valued_shocked["Book Value"].sum())
        total_full_shocked = float(valued_shocked["Full Value"].sum())
        total_clean_shocked = float(valued_shocked["Clean Value"].sum())
        total_gl_shocked = float(valued_shocked["Gain/Loss"].sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Book Value (Base)", f"{total_book_base:,.2f}")
        m2.metric(
            "Full Value (Shocked)",
            f"{total_full_shocked:,.2f}",
            delta=f"{(total_full_shocked - total_full_base):,.2f}",
        )
        m3.metric(
            "Clean Value (Shocked)",
            f"{total_clean_shocked:,.2f}",
            delta=f"{(total_clean_shocked - total_clean_base):,.2f}",
        )
        m4.metric(
            "Gain/Loss (Shocked)",
            f"{total_gl_shocked:,.2f}",
            delta=f"{(total_gl_shocked - total_gl_base):,.2f}",
        )

        st.subheader("Valuation Details")
        tab_base, tab_shocked = st.tabs(["Base Valuation", "Shifted Valuation"])
        with tab_base:
            st.dataframe(valued_base, use_container_width=True)
            csv_base = valued_base.to_csv(index=False).encode("utf-8")
            st.download_button("Download base valuation CSV", data=csv_base, file_name="portfolio_valuation_base.csv", mime="text/csv")
        with tab_shocked:
            st.dataframe(valued_shocked, use_container_width=True)
            csv_shock = valued_shocked.to_csv(index=False).encode("utf-8")
            st.download_button("Download shocked valuation CSV", data=csv_shock, file_name="portfolio_valuation_shocked.csv", mime="text/csv")

        # Individual Bond Deep-Dive
        st.markdown("---")
        st.subheader("Individual Bond Deep-Dive")
        try:
            import coupon_date

            isin_options = sorted(cleaned["ISIN"].unique().tolist())
            sel_isin = st.selectbox("Select ISIN for deep-dive", isin_options)
            deals = cleaned[cleaned["ISIN"] == sel_isin]["Deal No."].astype(str).tolist()
            sel_deal = st.selectbox("Select Deal No.", deals)

            if st.button("Show Deep Dive"):
                sel_row = cleaned[(cleaned["ISIN"] == sel_isin) & (cleaned["Deal No."].astype(str) == sel_deal)].iloc[0]
                # store for standalone page if needed
                st.session_state["selected_bond"] = sel_row
                coupon_date.show_deep_dive(sel_row, valuation_timestamp)
            st.markdown("---")
            st.subheader("ISIN Deep-Dive (aggregate)")
            if st.button("Show ISIN Deep Dive"):
                try:
                    # filter valued_base rows for this ISIN
                    isin_rows = valued_base[valued_base["ISIN"] == sel_isin].copy()
                    if isin_rows.empty:
                        st.info("No positions found for selected ISIN.")
                    else:
                        # aggregate simple metrics
                        total_coupons_received = float(isin_rows["Coupons Received"].sum()) if "Coupons Received" in isin_rows.columns else 0.0
                        total_accrued = float(isin_rows["Accrued Int"].sum()) if "Accrued Int" in isin_rows.columns else 0.0
                        total_future_interest = 0.0
                        total_funding_cost = float(isin_rows["Funding Cost"].sum()) if "Funding Cost" in isin_rows.columns else 0.0
                        total_net_pl = float(isin_rows["Net P/L"].sum()) if "Net P/L" in isin_rows.columns else 0.0

                        # build combined schedule: date -> coupon sum, principal sum
                        schedule_map = {}
                        for _, r in isin_rows.iterrows():
                            mat = pd.Timestamp(r["Maturity Date"])            
                            init = pd.Timestamp(r["Initial Inv Date"])        
                            face = float(r["Maturity Value"])
                            coupon_rate = float(r["Coupon"])
                            per_coupon = face * coupon_rate / 2.0
                            sch = coupon_date.get_coupon_schedule(mat, init, frequency=2)
                            for d in sch:
                                key = pd.Timestamp(d).normalize()
                                if key not in schedule_map:
                                    schedule_map[key] = {"coupon": 0.0, "principal": 0.0}
                                schedule_map[key]["coupon"] += per_coupon
                            # principal on maturity
                            keym = pd.Timestamp(mat).normalize()
                            schedule_map[keym]["principal"] += face

                        # convert to dataframe
                        rows = []
                        for dt, vals in schedule_map.items():
                            is_passed = dt <= pd.Timestamp(valuation_timestamp).normalize()
                            rows.append({"Date": dt.date(), "Coupon": vals["coupon"], "Principal": vals["principal"], "Passed": is_passed})

                        sched_df = pd.DataFrame(rows).sort_values("Date")
                        # compute totals
                        passed_df = sched_df[sched_df["Passed"]]
                        future_df = sched_df[~sched_df["Passed"]]
                        total_future_interest = float(future_df["Coupon"].sum())

                        st.write("**ISIN Summary**")
                        st.write(f"Total coupons received (since purchase): {total_coupons_received:,.2f}")
                        st.write(f"Total accrued interest (as of valuation): {total_accrued:,.2f}")
                        st.write(f"Expected future coupon interest: {total_future_interest:,.2f}")
                        st.write(f"Total funding cost: {total_funding_cost:,.2f}")
                        st.write(f"Total Net P/L: {total_net_pl:,.2f}")

                        st.markdown("**Combined Coupon Schedule for ISIN**")
                        st.dataframe(sched_df.style.format({"Coupon": "{:,.2f}", "Principal": "{:,.2f}"}), use_container_width=True)

                        st.markdown("**Per-deal details for ISIN**")
                        st.dataframe(isin_rows, use_container_width=True)
                except Exception as ex:
                    st.error(f"ISIN deep-dive failed: {ex}")
        except Exception as e:
            st.error(f"Deep-dive unavailable: {e}")

        if st.button("Clear portfolio"):
            st.session_state["portfolio_df"] = pd.DataFrame(columns=EXPECTED_COLUMNS)
            st.experimental_rerun()

    except Exception as e:
        st.error(f"Could not compute valuation: {e}")


if __name__ == "__main__":
    main()
