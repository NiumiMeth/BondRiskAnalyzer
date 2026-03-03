from __future__ import annotations

from datetime import date
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


st.set_page_config(page_title="Bond Portfolio Pricer", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.0rem; padding-bottom: 1.2rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 12px;}
    .stTabs [data-baseweb="tab"] {
        background: #111827;
        border: 1px solid #243244;
        border-radius: 10px 10px 0 0;
        padding: 10px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #172033;
        border-bottom: 2px solid #4F8BFF;
    }
    .section-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #E6EEF8;
        margin-top: 0.4rem;
        margin-bottom: 0.6rem;
        border-left: 4px solid #4F8BFF;
        padding-left: 0.55rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def render_section_title(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def render_portfolio_visuals(shock_position_df: pd.DataFrame) -> None:
    plot_df = (
        shock_position_df.groupby("ISIN", as_index=False)["Gain/Loss Delta"]
        .sum()
        .sort_values("Gain/Loss Delta", key=lambda s: s.abs(), ascending=False)
    )
    if plot_df.empty:
        return

    left, right = st.columns([1.5, 1])
    with left:
        fig_bar = go.Figure()
        fig_bar.add_trace(
            go.Bar(
                x=plot_df["ISIN"],
                y=plot_df["Gain/Loss Delta"],
                marker_color=np.where(plot_df["Gain/Loss Delta"] >= 0, "#35C759", "#FF4D4F"),
                name="G/L Delta",
            )
        )
        fig_bar.update_layout(
            title="Gain/Loss Delta by ISIN",
            xaxis_title="ISIN",
            yaxis_title="Gain/Loss Delta",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=45, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with right:
        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=plot_df["ISIN"],
                    values=plot_df["Gain/Loss Delta"].abs(),
                    hole=0.55,
                    sort=False,
                    textinfo="label+percent",
                )
            ]
        )
        fig_donut.update_layout(
            title="Share of Total Shock Impact",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=45, b=10),
        )
        st.plotly_chart(fig_donut, use_container_width=True)


def render_isin_visuals(selected_isin_df: pd.DataFrame, selected_isin: str) -> None:
    if selected_isin_df.empty:
        return

    chart_df = selected_isin_df.copy()
    chart_df["Deal No."] = chart_df["Deal No."].astype(str)

    left, right = st.columns([1.4, 1])
    with left:
        fig_deal = go.Figure()
        fig_deal.add_trace(
            go.Bar(
                x=chart_df["Deal No."],
                y=chart_df["Gain/Loss Delta"],
                marker_color=np.where(chart_df["Gain/Loss Delta"] >= 0, "#00D1FF", "#FF7B72"),
                name="Deal G/L Delta",
            )
        )
        fig_deal.update_layout(
            title=f"Deal-Level Gain/Loss Delta ({selected_isin})",
            xaxis_title="Deal No.",
            yaxis_title="Gain/Loss Delta",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=45, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig_deal, use_container_width=True)

    with right:
        fig_yield = go.Figure()
        fig_yield.add_trace(
            go.Scatter(
                x=chart_df["Maturity Date"],
                y=chart_df["Yield (Base)"] * 100,
                mode="lines+markers",
                name="Base Yield",
                line=dict(color="#3B82F6", width=2),
            )
        )
        fig_yield.add_trace(
            go.Scatter(
                x=chart_df["Maturity Date"],
                y=chart_df["Yield (Shocked)"] * 100,
                mode="lines+markers",
                name="Shocked Yield",
                line=dict(color="#F97316", width=2, dash="dot"),
            )
        )
        fig_yield.update_layout(
            title="Base vs Shocked Yield Curve",
            xaxis_title="Maturity Date",
            yaxis_title="Yield (%)",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=45, b=10),
        )
        st.plotly_chart(fig_yield, use_container_width=True)


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
    rename_map = {
        "Maturity Value ": "Maturity Value",
    }
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
        raise ValueError(
            "Input file is missing required columns: " + ", ".join(missing_columns)
        )

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


def get_future_coupon_dates(maturity_date: pd.Timestamp, valuation_date: pd.Timestamp) -> list[pd.Timestamp]:
    dates = []
    current = pd.Timestamp(maturity_date).normalize()
    valuation_date = pd.Timestamp(valuation_date).normalize()

    while current > valuation_date:
        dates.append(current)
        current = current - pd.DateOffset(months=6)

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


def run_yield_shock_analysis(
    valued_df: pd.DataFrame,
    valuation_date: pd.Timestamp,
    shock_bps: float,
) -> pd.DataFrame:
    output = valued_df.copy()
    shock_rate = shock_bps / 10000.0

    shocked_yield = []
    base_clean_price_100 = []
    base_accrued_100 = []
    base_price_100 = []
    base_clean_value = []
    base_full_value = []
    base_gl = []

    shocked_clean_price_100 = []
    shocked_accrued_100 = []
    shocked_price_100 = []
    shocked_clean_value = []
    shocked_full_value = []
    shocked_gl = []

    for _, row in output.iterrows():
        y_base = float(row["Yield"])
        y_shocked = max(-0.99, y_base + shock_rate)

        face = float(row["Maturity Value"])

        clean_100_base, accrued_100_base, full_100_base = excel_price_actual_actual(
            settlement_date=valuation_date,
            maturity_date=row["Maturity Date"],
            coupon_rate=float(row["Coupon"]),
            annual_yield=y_base,
            redemption=100.0,
            frequency=2,
        )
        clean_100_base = round(clean_100_base, 4)
        accrued_100_base = round(accrued_100_base, 4)
        full_100_base = round(clean_100_base + accrued_100_base, 4)

        clean_100_shocked, accrued_100_shocked, full_100_shocked = excel_price_actual_actual(
            settlement_date=valuation_date,
            maturity_date=row["Maturity Date"],
            coupon_rate=float(row["Coupon"]),
            annual_yield=y_shocked,
            redemption=100.0,
            frequency=2,
        )
        clean_100_shocked = round(clean_100_shocked, 4)
        accrued_100_shocked = round(accrued_100_shocked, 4)
        full_100_shocked = round(clean_100_shocked + accrued_100_shocked, 4)

        shocked_yield.append(y_shocked)

        base_clean_price_100.append(clean_100_base)
        base_accrued_100.append(accrued_100_base)
        base_price_100.append(full_100_base)
        base_clean_value.append(clean_100_base * (face / 100.0))
        base_full_value.append(full_100_base * (face / 100.0))
        base_gl.append((clean_100_base * (face / 100.0)) - float(row["Book Value"]))

        shocked_clean_price_100.append(clean_100_shocked)
        shocked_accrued_100.append(accrued_100_shocked)
        shocked_price_100.append(full_100_shocked)
        shocked_clean_value.append(clean_100_shocked * (face / 100.0))
        shocked_full_value.append(full_100_shocked * (face / 100.0))
        shocked_gl.append((clean_100_shocked * (face / 100.0)) - float(row["Book Value"]))

    output["Yield (Base)"] = output["Yield"]
    output["Yield (Shocked)"] = shocked_yield

    output["Price 100 (Base)"] = base_price_100
    output["Price 100 (Shocked)"] = shocked_price_100
    output["Price 100 Delta"] = output["Price 100 (Shocked)"] - output["Price 100 (Base)"]

    output["Clean Price (Base)"] = base_clean_price_100
    output["Clean Price (Shocked)"] = shocked_clean_price_100
    output["Clean Price Delta"] = output["Clean Price (Shocked)"] - output["Clean Price (Base)"]

    output["Clean Value (Base)"] = base_clean_value
    output["Clean Value (Shocked)"] = shocked_clean_value
    output["Clean Value Delta"] = output["Clean Value (Shocked)"] - output["Clean Value (Base)"]

    output["Full Value (Base)"] = base_full_value
    output["Full Value (Shocked)"] = shocked_full_value
    output["Full Value Delta"] = output["Full Value (Shocked)"] - output["Full Value (Base)"]

    output["Accrued Int (Base)"] = base_accrued_100
    output["Accrued Int (Shocked)"] = shocked_accrued_100
    output["Accrued Interest Delta"] = (
        output["Accrued Int (Shocked)"] - output["Accrued Int (Base)"]
    )

    output["Gain/Loss vs Book (Base)"] = base_gl
    output["Gain/Loss vs Book (Shocked)"] = shocked_gl
    output["Gain/Loss Delta"] = output["Gain/Loss vs Book (Shocked)"] - output["Gain/Loss vs Book (Base)"]

    return output


def aggregate_shock_by_isin(shock_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        shock_df.groupby("ISIN", as_index=False)
        .agg(
            Positions=("Deal No.", "count"),
            Face_Value=("Maturity Value", "sum"),
            Book_Value=("Book Value", "sum"),
            Price100_Base=("Price 100 (Base)", "mean"),
            Price100_Shocked=("Price 100 (Shocked)", "mean"),
            CleanPrice_Base=("Clean Price (Base)", "mean"),
            CleanPrice_Shocked=("Clean Price (Shocked)", "mean"),
            Clean_Base=("Clean Value (Base)", "sum"),
            Clean_Shocked=("Clean Value (Shocked)", "sum"),
            Full_Base=("Full Value (Base)", "sum"),
            Full_Shocked=("Full Value (Shocked)", "sum"),
            Accrued_Base=("Accrued Int (Base)", "mean"),
            Accrued_Shocked=("Accrued Int (Shocked)", "mean"),
            GL_Base=("Gain/Loss vs Book (Base)", "sum"),
            GL_Shocked=("Gain/Loss vs Book (Shocked)", "sum"),
        )
        .sort_values("ISIN")
    )

    grouped["Price100_Delta"] = grouped["Price100_Shocked"] - grouped["Price100_Base"]
    grouped["CleanPrice_Delta"] = grouped["CleanPrice_Shocked"] - grouped["CleanPrice_Base"]
    grouped["Clean_Delta"] = grouped["Clean_Shocked"] - grouped["Clean_Base"]
    grouped["Full_Delta"] = grouped["Full_Shocked"] - grouped["Full_Base"]
    grouped["Accrued_Delta"] = grouped["Accrued_Shocked"] - grouped["Accrued_Base"]
    grouped["GL_Delta"] = grouped["GL_Shocked"] - grouped["GL_Base"]

    return grouped


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


def to_excel_bytes(
    summary_df: pd.DataFrame,
    detail_df: pd.DataFrame,
    shock_position_df: pd.DataFrame,
    shock_isin_df: pd.DataFrame,
) -> tuple[bytes, str, str]:
    try:
        import openpyxl  # noqa: F401

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            summary_df.to_excel(writer, index=False, sheet_name="ISIN Summary")
            detail_df.to_excel(writer, index=False, sheet_name="Position Details")
            shock_position_df.to_excel(writer, index=False, sheet_name="Shock Position")
            shock_isin_df.to_excel(writer, index=False, sheet_name="Shock ISIN")
        return (
            buffer.getvalue(),
            "bond_portfolio_yield_shock_output.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ModuleNotFoundError:
        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zip_file:
            zip_file.writestr("isin_summary.csv", summary_df.to_csv(index=False))
            zip_file.writestr("position_details.csv", detail_df.to_csv(index=False))
            zip_file.writestr("shock_position.csv", shock_position_df.to_csv(index=False))
            zip_file.writestr("shock_isin.csv", shock_isin_df.to_csv(index=False))
        return (
            buffer.getvalue(),
            "bond_portfolio_yield_shock_output_csv.zip",
            "application/zip",
        )


def main() -> None:
    st.title("Bond Portfolio Pricing (Semi-Annual)")
    st.caption(
        "Upload CSV/Excel, calculate semi-annual PVs automatically, and view book value by ISIN."
    )

    uploaded_file = st.file_uploader(
        "Upload portfolio file",
        type=["csv", "xlsx", "xls"],
        help="Required columns: Port. Index, Instrument, Deal No., ISIN, Initial Inv Date, Maturity Date, Coupon, Maturity Value, YTM, Yield, Market value, Duration",
    )

    valuation_date = st.date_input("Valuation Date", value=date.today())

    if not uploaded_file:
        st.info("Please upload a CSV or Excel file to start valuation.")
        return

    try:
        portfolio_df = load_portfolio(uploaded_file)
    except Exception as error:
        st.error(f"Could not read file: {error}")
        return

    if portfolio_df.empty:
        st.warning("No valid bond rows were found after cleaning.")
        return

    valuation_timestamp = pd.Timestamp(valuation_date)
    valued_df = run_portfolio_valuation(portfolio_df, valuation_timestamp)
    summary_df = aggregate_by_isin(valued_df)

    render_section_title("Yield Shock Controls")
    control_left, control_right = st.columns([3, 1])
    with control_left:
        shock_pct = st.number_input(
            "Parallel Yield Shock (%)",
            min_value=-10.0,
            max_value=10.0,
            value=0.0,
            step=0.05,
            format="%.2f",
            help="Enter the yield change in percent (e.g., 0.50 means +50 bps).",
        )
        shock_bps = int(round(shock_pct * 100))
        st.caption(f"Selected shift: {shock_pct:+.2f}% ({shock_bps:+} bps)")
    with control_right:
        st.metric("Shocked Shift", f"{shock_pct:+.2f}%")

    shock_position_df = run_yield_shock_analysis(
        valued_df=valued_df,
        valuation_date=valuation_timestamp,
        shock_bps=float(shock_bps),
    )
    shock_isin_df = aggregate_shock_by_isin(shock_position_df)

    page_portfolio, page_isin = st.tabs(
        ["Page 1 - Yield Shock (Portfolio)", "Page 2 - Yield Shock (ISIN Wise)"]
    )

    with page_portfolio:
        st.subheader("Portfolio-wide impact")
        total_book = float(shock_position_df["Book Value"].sum())
        total_full_base = float(shock_position_df["Full Value (Base)"].sum())
        total_full_shocked = float(shock_position_df["Full Value (Shocked)"].sum())
        total_clean_base = float(shock_position_df["Clean Value (Base)"].sum())
        total_clean_shocked = float(shock_position_df["Clean Value (Shocked)"].sum())
        total_gl_base = float(shock_position_df["Gain/Loss vs Book (Base)"].sum())
        total_gl_shocked = float(shock_position_df["Gain/Loss vs Book (Shocked)"].sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Book Value", f"{total_book:,.2f}")
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
            "Gain/Loss vs Book (Shocked)",
            f"{total_gl_shocked:,.2f}",
            delta=f"{(total_gl_shocked - total_gl_base):,.2f}",
        )

        render_section_title("Shock Impact Visuals")
        render_portfolio_visuals(shock_position_df)

        st.subheader("All positions affected by yield shock")
        portfolio_cols = [
            "Port. Index",
            "Instrument",
            "Deal No.",
            "ISIN",
            "Initial Inv Date",
            "Maturity Date",
            "Maturity Value",
            "Coupon",
            "Yield (Base)",
            "Yield (Shocked)",
            "Price 100 (Base)",
            "Price 100 (Shocked)",
            "Price 100 Delta",
            "Clean Price (Base)",
            "Clean Price (Shocked)",
            "Clean Price Delta",
            "Accrued Int (Base)",
            "Accrued Int (Shocked)",
            "Accrued Interest Delta",
            "Full Value (Base)",
            "Full Value (Shocked)",
            "Full Value Delta",
            "Clean Value (Base)",
            "Clean Value (Shocked)",
            "Clean Value Delta",
            "Book Value",
            "Gain/Loss vs Book (Base)",
            "Gain/Loss vs Book (Shocked)",
            "Gain/Loss Delta",
        ]
        portfolio_formats = {
            "Maturity Value": "{:,.2f}",
            "Price 100 (Base)": "{:,.4f}",
            "Price 100 (Shocked)": "{:,.4f}",
            "Price 100 Delta": "{:,.4f}",
            "Clean Price (Base)": "{:,.4f}",
            "Clean Price (Shocked)": "{:,.4f}",
            "Clean Price Delta": "{:,.4f}",
            "Full Value (Base)": "{:,.2f}",
            "Full Value (Shocked)": "{:,.2f}",
            "Full Value Delta": "{:,.2f}",
            "Clean Value (Base)": "{:,.2f}",
            "Clean Value (Shocked)": "{:,.2f}",
            "Clean Value Delta": "{:,.2f}",
            "Book Value": "{:,.2f}",
            "Gain/Loss vs Book (Base)": "{:,.2f}",
            "Gain/Loss vs Book (Shocked)": "{:,.2f}",
            "Gain/Loss Delta": "{:,.2f}",
        }
        st.dataframe(
            shock_position_df[portfolio_cols].style.format(portfolio_formats),
            use_container_width=True,
        )

        download_bytes, download_name, download_mime = to_excel_bytes(
            summary_df=summary_df,
            detail_df=valued_df,
            shock_position_df=shock_position_df[portfolio_cols],
            shock_isin_df=shock_isin_df,
        )
        st.download_button(
            label="Download Yield Shock Results",
            data=download_bytes,
            file_name=download_name,
            mime=download_mime,
        )

    with page_isin:
        st.subheader("ISIN-wise impact")
        isin_impact_display = shock_isin_df.rename(
            columns={
                "Clean_Base": "Clean Value (Base)",
                "Clean_Shocked": "Clean Value (Shocked)",
                "Clean_Delta": "Clean Value Delta",
            }
        )
        isin_impact_formats = {
            "Face_Value": "{:,.2f}",
            "Book_Value": "{:,.2f}",
            "Clean_Value": "{:,.2f}",
            "Full_Value": "{:,.2f}",
            "Gain_Loss": "{:,.2f}",
            "Input_Market_Value": "{:,.2f}",
            "Price100_Base": "{:,.4f}",
            "Price100_Shocked": "{:,.4f}",
            "Price100_Delta": "{:,.4f}",
            "CleanPrice_Base": "{:,.4f}",
            "CleanPrice_Shocked": "{:,.4f}",
            "CleanPrice_Delta": "{:,.4f}",
            "Clean Value (Base)": "{:,.2f}",
            "Clean Value (Shocked)": "{:,.2f}",
            "Clean Value Delta": "{:,.2f}",
            "Full_Base": "{:,.2f}",
            "Full_Shocked": "{:,.2f}",
            "Full_Delta": "{:,.2f}",
        }
        st.dataframe(
            isin_impact_display.style.format(isin_impact_formats),
            use_container_width=True,
        )

        isin_options = sorted(shock_position_df["ISIN"].unique().tolist())
        selected_isin = st.selectbox("Select ISIN", isin_options)
        selected_isin_df = shock_position_df[shock_position_df["ISIN"] == selected_isin].copy()

        render_section_title("Selected ISIN Visuals")
        render_isin_visuals(selected_isin_df, selected_isin)

        st.subheader(f"Selected ISIN details: {selected_isin}")
        isin_detail_cols = [
            "Deal No.",
            "Initial Inv Date",
            "Maturity Date",
            "Maturity Value",
            "Coupon",
            "Yield (Base)",
            "Yield (Shocked)",
            "Price 100 (Base)",
            "Price 100 (Shocked)",
            "Price 100 Delta",
            "Clean Price (Base)",
            "Clean Price (Shocked)",
            "Clean Price Delta",
            "Full Value (Base)",
            "Full Value (Shocked)",
            "Full Value Delta",
            "Clean Value (Base)",
            "Clean Value (Shocked)",
            "Clean Value Delta",
            "Book Value",
            "Gain/Loss vs Book (Base)",
            "Gain/Loss vs Book (Shocked)",
            "Gain/Loss Delta",
        ]
        isin_detail_formats = {
            "Maturity Value": "{:,.2f}",
            "Price 100 (Base)": "{:,.4f}",
            "Price 100 (Shocked)": "{:,.4f}",
            "Price 100 Delta": "{:,.4f}",
            "Clean Price (Base)": "{:,.4f}",
            "Clean Price (Shocked)": "{:,.4f}",
            "Clean Price Delta": "{:,.4f}",
            "Full Value (Base)": "{:,.2f}",
            "Full Value (Shocked)": "{:,.2f}",
            "Full Value Delta": "{:,.2f}",
            "Clean Value (Base)": "{:,.2f}",
            "Clean Value (Shocked)": "{:,.2f}",
            "Clean Value Delta": "{:,.2f}",
            "Book Value": "{:,.2f}",
            "Gain/Loss vs Book (Base)": "{:,.2f}",
            "Gain/Loss vs Book (Shocked)": "{:,.2f}",
            "Gain/Loss Delta": "{:,.2f}",
        }
        st.dataframe(
            selected_isin_df[isin_detail_cols].style.format(isin_detail_formats),
            use_container_width=True,
        )

        deal_options = selected_isin_df["Deal No."].astype(str).tolist()
        selected_deal = st.selectbox("Select Deal No. for cash-flow table", deal_options)

        selected_row = selected_isin_df[selected_isin_df["Deal No."].astype(str) == selected_deal].iloc[0]

        basis_choice = st.selectbox(
            "Cash-flow table basis",
            ["Base Yield", "Shocked Yield"],
            index=0,
        )
        selected_rate = (
            float(selected_row["Yield (Base)"])
            if basis_choice == "Base Yield"
            else float(selected_row["Yield (Shocked)"])
        )

        calc_table, dirty_price, clean_price, accrued_interest, frac = build_valuation_table(
            face_value=float(selected_row["Maturity Value"]),
            coupon_rate=float(selected_row["Coupon"]),
            annual_yield=selected_rate,
            maturity_date=selected_row["Maturity Date"],
            valuation_date=valuation_timestamp,
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Face Value", f"{selected_row['Maturity Value']:,.2f}")
        k2.metric("Dirty Value", f"{dirty_price:,.2f}")
        k3.metric("Accrued Interest", f"{accrued_interest:,.2f}")
        k4.metric("Clean Value", f"{clean_price:,.2f}")

        st.caption(
            f"Fraction used for first period = days_to_next_coupon/182 = {frac:.6f}. Exponents follow: frac, 1+frac, 2+frac, ..."
        )
        st.dataframe(calc_table, use_container_width=True)


if __name__ == "__main__":
    main()