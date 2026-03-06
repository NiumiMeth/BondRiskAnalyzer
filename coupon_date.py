from __future__ import annotations

from datetime import date

import pandas as pd
import numpy as np
import streamlit as st


def get_future_coupon_dates(maturity_date: pd.Timestamp, valuation_date: pd.Timestamp) -> list[pd.Timestamp]:
    dates = []
    current = pd.Timestamp(maturity_date).normalize()
    valuation_date = pd.Timestamp(valuation_date).normalize()

    while current > valuation_date:
        dates.append(current)
        current = current - pd.DateOffset(months=6)

    return sorted(dates)


def get_coupon_schedule(maturity_date: pd.Timestamp, issue_date: pd.Timestamp, frequency: int = 2) -> list[pd.Timestamp]:
    """Return all coupon dates from (and including) the first coupon on/after issue_date up to maturity."""
    if pd.isna(maturity_date) or pd.isna(issue_date):
        return []
    maturity = pd.Timestamp(maturity_date).normalize()
    issue = pd.Timestamp(issue_date).normalize()
    if issue > maturity:
        return []

    months = int(12 / frequency)
    dates = []
    current = maturity
    while current >= issue:
        dates.append(current)
        current = current - pd.DateOffset(months=months)

    return sorted(dates)


def build_valuation_table(
    face_value: float,
    coupon_rate: float,
    annual_yield: float,
    maturity_date: pd.Timestamp,
    valuation_date: pd.Timestamp,
) -> tuple[pd.DataFrame, float, float, float, float]:
    coupon_dates = get_future_coupon_dates(maturity_date, valuation_date)
    if not coupon_dates:
        empty = pd.DataFrame(
            columns=[
                "Cash Flow Date",
                "Coupon CF",
                "Principal CF",
                "Total CF",
                "Exponent (n + frac)",
                "Discount Factor",
                "PV",
            ]
        )
        return empty, 0.0, 0.0, 0.0, 0.0

    next_coupon = coupon_dates[0]
    days_to_next_coupon = max((next_coupon - valuation_date).days, 0)
    frac = days_to_next_coupon / 182.0

    period_coupon = face_value * coupon_rate / 2.0

    rows = []
    dirty_price = 0.0
    for index, cash_date in enumerate(coupon_dates):
        exponent = index + frac
        coupon_cf = period_coupon
        principal_cf = face_value if cash_date == coupon_dates[-1] else 0.0
        total_cf = coupon_cf + principal_cf
        discount_factor = (1 + annual_yield / 2.0) ** exponent
        pv = total_cf / discount_factor
        dirty_price += pv

        rows.append(
            {
                "Cash Flow Date": cash_date.date(),
                "Coupon CF": coupon_cf,
                "Principal CF": principal_cf,
                "Total CF": total_cf,
                "Exponent (n + frac)": exponent,
                "Discount Factor": discount_factor,
                "PV": pv,
            }
        )

    accrued_interest = period_coupon * (1.0 - frac)
    accrued_interest = max(0.0, min(accrued_interest, period_coupon))
    clean_price = dirty_price - accrued_interest

    table = pd.DataFrame(rows)
    return table, dirty_price, clean_price, accrued_interest, frac


def show_deep_dive(selected_row: pd.Series, valuation_timestamp: pd.Timestamp) -> None:
    st.markdown("---")
    st.header("Individual Bond Deep-Dive")

    isin = selected_row.get("ISIN", "")
    deal = selected_row.get("Deal No.", "")
    st.subheader(f"ISIN: {isin} — Deal: {deal}")

    face = float(selected_row.get("Maturity Value", 0.0))
    coupon = float(selected_row.get("Coupon", 0.0))
    base_yield = float(selected_row.get("Yield", 0.0))
    maturity_date = pd.Timestamp(selected_row.get("Maturity Date"))
    init_date = pd.Timestamp(selected_row.get("Initial Inv Date"))
    purchase_date = init_date
    purchased_ytm = float(selected_row.get("YTM", 0.0))

    st.write(f"Instrument: {selected_row.get('Instrument', '')}")
    st.write(f"Initial Investment Date: {selected_row.get('Initial Inv Date', '')}")

    # Full coupon schedule and split into passed vs future
    schedule = get_coupon_schedule(maturity_date, init_date, frequency=2)
    if not schedule:
        st.info("No coupon schedule found (check dates).")
        return

    passed = [d for d in schedule if d <= pd.Timestamp(valuation_timestamp).normalize()]
    future = [d for d in schedule if d > pd.Timestamp(valuation_timestamp).normalize()]

    st.markdown("**Coupon Schedule**")
    st.write("All coupon dates:")
    st.write([d.date().isoformat() for d in schedule])

    st.write("Coupons already paid (on or before valuation date):")
    st.write([d.date().isoformat() for d in passed])

    st.write("Upcoming coupon dates:")
    st.write([d.date().isoformat() for d in future])

    # allow per-bond yield adjustment
    st.subheader("Yield & Valuation")
    col1, col2 = st.columns([2, 1])
    with col1:
        y_input = st.number_input("Base Yield for this bond (%)", value=round(base_yield * 100.0, 4), format="%.4f")
        y_input_rate = float(y_input) / 100.0
    with col2:
        shock_local = st.number_input("Local Shift (bps)", min_value=-2000, max_value=2000, value=0, step=1)

    applied_yield = y_input_rate + (shock_local / 10000.0)

    calc_table, dirty_price, clean_price, accrued_interest, frac = build_valuation_table(
        face_value=face,
        coupon_rate=coupon,
        annual_yield=applied_yield,
        maturity_date=maturity_date,
        valuation_date=valuation_timestamp,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Face Value", f"{face:,.2f}")
    k2.metric("Dirty Value", f"{dirty_price:,.2f}")
    k3.metric("Accrued Interest", f"{accrued_interest:,.2f}")
    k4.metric("Clean Value", f"{clean_price:,.2f}")

    st.caption(f"Fraction used for first period = {frac:.6f}")
    st.subheader("Cash-flow Table")
    st.dataframe(calc_table, use_container_width=True)

    # Coupon amounts summary
    coupon_amt = face * coupon / 2.0
    # Count only coupons that occur on/after initial investment
    passed_after_purchase = [d for d in passed if d >= init_date]
    passed_interest = coupon_amt * len(passed_after_purchase)
    future_interest = coupon_amt * len(future)
    future_cashflows = future_interest
    # include principal if maturity is in the future list
    if pd.Timestamp(maturity_date).normalize() in future:
        future_cashflows += face

    st.markdown("---")
    st.subheader("Coupon P&L Summary")
    st.write(f"Coupon per payment: {coupon_amt:,.2f}")
    st.write(f"Coupons received since purchase: {len(passed_after_purchase)} (total interest: {passed_interest:,.2f})")
    st.write(f"Accrued interest (as of valuation): {accrued_interest:,.2f}")
    st.write(f"Expected future coupon interest (sum): {future_interest:,.2f}")
    st.write(f"Expected future cashflows (coupons + principal if not matured): {future_cashflows:,.2f}")

    # Funding cost and net P/L for this bond
    st.subheader("Funding & Net P/L")
    funding_rate_local = st.number_input("Funding Rate for this bond (%)", value=0.0, step=0.01, format="%.4f")
    days_held = max((pd.Timestamp(valuation_timestamp) - purchase_date).days, 0)

    # Compute purchase full value at purchase date using build_valuation_table
    try:
        _, purchase_dirty, purchase_clean, purchase_accrued, _ = build_valuation_table(
            face_value=face,
            coupon_rate=coupon,
            annual_yield=purchased_ytm,
            maturity_date=maturity_date,
            valuation_date=purchase_date,
        )
        purchase_full_value = purchase_dirty
    except Exception:
        purchase_full_value = 0.0

    funding_cost_local = purchase_full_value * (funding_rate_local / 100.0) * (days_held / 365.0)

    sales_value = dirty_price
    net_pl = (sales_value - purchase_full_value) + passed_interest - funding_cost_local

    st.write(f"Purchase Full Value: {purchase_full_value:,.2f}")
    st.write(f"Holding days: {days_held}")
    st.write(f"Funding cost: {funding_cost_local:,.2f}")
    st.write(f"Net P/L (Sales - Purchase + Coupons - Funding): {net_pl:,.2f}")


if __name__ == "__main__":
    st.set_page_config(page_title="Bond Deep Dive")
    st.title("Bond Deep Dive (standalone)")
    st.info("Run this page via the Portfolio Manager or provide a selected_row in `st.session_state['selected_bond']`.")

    if "selected_bond" in st.session_state:
        selected = st.session_state["selected_bond"]
        valuation_date = st.date_input("Valuation Date", value=date.today())
        show_deep_dive(selected, pd.Timestamp(valuation_date))
    else:
        st.write("No bond selected. Use the Portfolio Manager to open a deep-dive.")
