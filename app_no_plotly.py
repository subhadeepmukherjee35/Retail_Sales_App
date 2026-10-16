import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------
# RetailPulse Analytics | Multi-page Streamlit application
# Expected files are in ./data, or upload them in the sidebar.
# ---------------------------------------------------------
st.set_page_config(
    page_title="RetailPulse Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"
FILE_NAMES = {
    "Sales": "sales_cleaned.csv",
    "Customer segments": "customer_segments.csv",
    "Churn predictions": "customer_churn_predictions.csv",
    "Demand forecast": "demand_forecast_30_days.csv",
    "Inventory recommendations": "inventory_recommendations.csv",
}

st.sidebar.title("📊 RetailPulse")
st.sidebar.caption("Retail intelligence workspace")
page = st.sidebar.radio(
    "Navigate",
    [
        "Executive Dashboard",
        "Customer Analytics",
        "Churn Analysis",
        "Demand Forecast",
        "Inventory Optimization",
        "Explore Data",
    ],
)

with st.sidebar.expander("Data sources", expanded=False):
    st.caption("Files are read from the data folder by default. Upload a CSV to override a file for this session.")
    uploaded = {}
    for label, filename in FILE_NAMES.items():
        uploaded[label] = st.file_uploader(
            f"Upload {filename}",
            type=["csv"],
            key=f"upload_{label}",
        )


@st.cache_data(show_spinner="Loading data…")
def read_csv_bytes(file_bytes):
    from io import BytesIO
    return pd.read_csv(BytesIO(file_bytes))


def load_data(label):
    """Uploaded CSV takes priority, then the project's data folder."""
    file_obj = uploaded.get(label)
    if file_obj is not None:
        try:
            return read_csv_bytes(file_obj.getvalue()), "Uploaded file"
        except Exception as exc:
            st.error(f"Could not read uploaded {FILE_NAMES[label]}: {exc}")
            return None, "Upload error"

    path = DATA_DIR / FILE_NAMES[label]
    if path.exists():
        try:
            return pd.read_csv(path), str(path)
        except Exception as exc:
            st.error(f"Could not read {path.name}: {exc}")
            return None, "Read error"
    return None, "Missing"


def show_missing_files():
    st.error("One or more required CSV files are missing.")
    st.write(f"Expected folder: `{DATA_DIR}`")
    st.markdown("Create a `data` folder beside `app.py` and copy the CSV outputs from your notebook into it.")
    st.code("\n".join(FILE_NAMES.values()), language="text")
    st.info("You can also open **Data sources** in the sidebar and upload a CSV for the file you need.")
    st.stop()


def money(value):
    return f"₹{value:,.0f}"


def csv_download_button(df, filename, label="Download CSV"):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


sales, sales_source = load_data("Sales")
segments, segments_source = load_data("Customer segments")
churn, churn_source = load_data("Churn predictions")
forecast, forecast_source = load_data("Demand forecast")
inventory, inventory_source = load_data("Inventory recommendations")

# Prepare data where possible
if sales is not None:
    sales.columns = sales.columns.str.strip()
    if "Order_Date" in sales.columns:
        sales["Order_Date"] = pd.to_datetime(sales["Order_Date"], errors="coerce")
    for col in ["Sales", "Profit", "Quantity"]:
        if col in sales.columns:
            sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0)

if segments is not None:
    segments.columns = segments.columns.str.strip()
if churn is not None:
    churn.columns = churn.columns.str.strip()
    if "Last_Purchase" in churn.columns:
        churn["Last_Purchase"] = pd.to_datetime(churn["Last_Purchase"], errors="coerce")
if forecast is not None:
    forecast.columns = forecast.columns.str.strip()
    if "Date" in forecast.columns:
        forecast["Date"] = pd.to_datetime(forecast["Date"], errors="coerce")
    if "Forecast_Units" in forecast.columns:
        forecast["Forecast_Units"] = pd.to_numeric(forecast["Forecast_Units"], errors="coerce").fillna(0)
if inventory is not None:
    inventory.columns = inventory.columns.str.strip()
    for col in ["Current_Stock", "Lead_Time_Days", "Avg_Daily_Demand", "Target_Stock", "Suggested_Reorder"]:
        if col in inventory.columns:
            inventory[col] = pd.to_numeric(inventory[col], errors="coerce").fillna(0)

# Consistent page header
st.title("📊 RetailPulse Analytics")
st.caption("Interactive retail sales, customer, forecasting, and inventory insights")
st.divider()

# ---------------------------------------------------------
# 1. EXECUTIVE DASHBOARD
# ---------------------------------------------------------
if page == "Executive Dashboard":
    if sales is None:
        show_missing_files()

    st.subheader("Executive Dashboard")
    st.write("Use the sidebar filters to focus on a period or sales channel.")

    filtered = sales.copy()

    # Date range filter
    if "Order_Date" in filtered.columns and filtered["Order_Date"].notna().any():
        valid_dates = filtered["Order_Date"].dropna()
        start_min, end_max = valid_dates.min().date(), valid_dates.max().date()
        chosen_range = st.sidebar.date_input(
            "Order date range",
            value=(start_min, end_max),
            min_value=start_min,
            max_value=end_max,
            key="sales_date_range",
        )
        if isinstance(chosen_range, (tuple, list)) and len(chosen_range) == 2:
            start_date, end_date = chosen_range
            filtered = filtered[
                filtered["Order_Date"].dt.date.between(start_date, end_date)
            ]

    # Channel filter
    if "Channel" in filtered.columns:
        channel_values = sorted(filtered["Channel"].fillna("Unknown").astype(str).unique())
        chosen_channels = st.sidebar.multiselect(
            "Sales channel",
            options=channel_values,
            default=channel_values,
            key="sales_channels",
        )
        filtered = filtered[
            filtered["Channel"].fillna("Unknown").astype(str).isin(chosen_channels)
        ]

    total_sales = filtered["Sales"].sum() if "Sales" in filtered.columns else 0
    total_profit = filtered["Profit"].sum() if "Profit" in filtered.columns else 0
    total_orders = filtered["Order_ID"].nunique() if "Order_ID" in filtered.columns else len(filtered)
    total_customers = filtered["Customer_ID"].nunique() if "Customer_ID" in filtered.columns else 0
    total_units = filtered["Quantity"].sum() if "Quantity" in filtered.columns else 0
    margin = (total_profit / total_sales * 100) if total_sales else 0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Sales", money(total_sales))
    k2.metric("Total Profit", money(total_profit))
    k3.metric("Profit Margin", f"{margin:.1f}%")
    k4.metric("Orders", f"{total_orders:,}")
    k5.metric("Customers", f"{total_customers:,}")
    k6.metric("Units Sold", f"{total_units:,.0f}")

    tab1, tab2, tab3 = st.tabs(["Sales trends", "Channel analysis", "Data preview"])
    with tab1:
        if "Order_Date" in filtered.columns and "Sales" in filtered.columns:
            trend = (
                filtered.dropna(subset=["Order_Date"])
                .set_index("Order_Date")["Sales"]
                .resample("MS").sum().rename("Sales").reset_index()
            )
            if not trend.empty:
                st.markdown("**Monthly Sales Trend**")
                st.line_chart(trend.set_index("Order_Date")[["Sales"]], use_container_width=True)
            else:
                st.info("No dated sales rows match the selected filters.")
        else:
            st.warning("The sales file needs Order_Date and Sales columns for this chart.")

        if "Order_Date" in filtered.columns and "Profit" in filtered.columns:
            monthly_profit = (
                filtered.dropna(subset=["Order_Date"])
                .set_index("Order_Date")["Profit"]
                .resample("MS").sum().rename("Profit").reset_index()
            )
            st.markdown("**Monthly Profit**")
            st.bar_chart(monthly_profit.set_index("Order_Date")[["Profit"]], use_container_width=True)

    with tab2:
        if "Channel" in filtered.columns and "Sales" in filtered.columns:
            by_channel = filtered.groupby("Channel", dropna=False, as_index=False)["Sales"].sum()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Sales by Channel**")
                st.bar_chart(by_channel.set_index("Channel")[["Sales"]], use_container_width=True)
            with c2:
                st.markdown("**Sales Contribution by Channel**")
                st.caption("Native Streamlit charts do not include a built-in pie/donut chart, so this uses a bar chart instead.")
                st.bar_chart(by_channel.set_index("Channel")[["Sales"]], use_container_width=True)
        else:
            st.info("Channel analysis requires Channel and Sales columns.")

    with tab3:
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        csv_download_button(filtered, "retailpulse_filtered_sales.csv", "Download filtered sales")

    with st.expander("About these metrics"):
        st.markdown(
            "- **Profit margin** = total profit ÷ total sales.\n"
            "- **Orders** counts unique Order_ID values when available.\n"
            "- KPI values respond to the date and channel filters."
        )

# ---------------------------------------------------------
# 2. CUSTOMER ANALYTICS
# ---------------------------------------------------------
elif page == "Customer Analytics":
    if segments is None:
        show_missing_files()
    st.subheader("Customer Analytics — RFM Segmentation")

    required = {"Customer_ID", "Recency", "Frequency", "Monetary", "Segment"}
    if not required.issubset(segments.columns):
        st.error(f"Customer segments file is missing columns: {sorted(required - set(segments.columns))}")
        st.write("Columns found:", list(segments.columns))
        st.stop()

    data = segments.copy()
    for col in ["Recency", "Frequency", "Monetary", "Segment"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["Segment"])
    data["Segment"] = data["Segment"].astype(str)

    all_segments = sorted(data["Segment"].unique())
    selected_segments = st.multiselect("Choose customer segments", all_segments, default=all_segments)
    data = data[data["Segment"].isin(selected_segments)]

    a, b, c = st.columns(3)
    a.metric("Customers", f"{data['Customer_ID'].nunique():,}")
    b.metric("Average Spend", money(data["Monetary"].mean()) if not data.empty else "₹0")
    c.metric("Average Recency", f"{data['Recency'].mean():.1f} days" if not data.empty else "—")

    left, right = st.columns(2)
    with left:
        st.markdown("**Customer Frequency vs Monetary Value**")
        scatter_data = data[["Frequency", "Monetary", "Segment"]].dropna()
        if not scatter_data.empty:
            st.scatter_chart(
                scatter_data,
                x="Frequency",
                y="Monetary",
                color="Segment",
                use_container_width=True,
            )
        else:
            st.info("No valid frequency and monetary values are available to plot.")
    with right:
        summary = data.groupby("Segment", as_index=False).agg(
            Customers=("Customer_ID", "nunique"),
            Average_Spend=("Monetary", "mean"),
            Average_Recency=("Recency", "mean"),
            Average_Frequency=("Frequency", "mean"),
        )
        st.markdown("**Customers by Segment**")
        st.bar_chart(summary.set_index("Segment")[["Customers"]], use_container_width=True)

    with st.expander("Segment summary table", expanded=True):
        st.dataframe(summary.round(2), use_container_width=True, hide_index=True)
    st.subheader("Customer-level records")
    min_spend = float(data["Monetary"].min()) if not data.empty else 0.0
    max_spend = float(data["Monetary"].max()) if not data.empty else 0.0
    if max_spend > min_spend:
        spend_range = st.slider("Filter by total spend (₹)", min_spend, max_spend, (min_spend, max_spend))
        data = data[data["Monetary"].between(spend_range[0], spend_range[1])]
    st.dataframe(data, use_container_width=True, hide_index=True)
    csv_download_button(data, "retailpulse_customer_segments.csv")

# ---------------------------------------------------------
# 3. CHURN ANALYSIS
# ---------------------------------------------------------
elif page == "Churn Analysis":
    if churn is None:
        show_missing_files()
    st.subheader("Customer Churn-Risk Analysis")

    if "Churn_Risk_Label" not in churn.columns:
        st.error("The churn file needs a Churn_Risk_Label column.")
        st.write("Columns found:", list(churn.columns))
        st.stop()

    data = churn.copy()
    data["Churn_Risk_Label"] = pd.to_numeric(data["Churn_Risk_Label"], errors="coerce").fillna(0).astype(int)
    risk_labels = {1: "High risk", 0: "Lower risk"}
    data["Risk Category"] = data["Churn_Risk_Label"].map(risk_labels).fillna("Unknown")

    show_high_only = st.checkbox("Show only high-risk customers", value=False)
    if show_high_only:
        data = data[data["Churn_Risk_Label"] == 1]

    high_risk_count = int((churn["Churn_Risk_Label"].fillna(0).astype(int) == 1).sum())
    total = len(churn)
    rate = high_risk_count / total * 100 if total else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Customers analysed", f"{total:,}")
    m2.metric("High-risk customers", f"{high_risk_count:,}")
    m3.metric("High-risk share", f"{rate:.1f}%")

    if "Recency_Days" in data.columns and "Spend" in data.columns:
        data["Recency_Days"] = pd.to_numeric(data["Recency_Days"], errors="coerce")
        data["Spend"] = pd.to_numeric(data["Spend"], errors="coerce")
        st.markdown("**Customer Spend vs Days Since Last Purchase**")
        scatter_data = data[["Recency_Days", "Spend", "Risk Category"]].dropna()
        if not scatter_data.empty:
            st.scatter_chart(
                scatter_data,
                x="Recency_Days",
                y="Spend",
                color="Risk Category",
                use_container_width=True,
            )
        else:
            st.info("No valid recency and spend values are available to plot.")
    st.warning("Churn risk is a model-derived indicator, not proof that a customer will leave.")
    st.dataframe(data, use_container_width=True, hide_index=True)
    csv_download_button(data, "retailpulse_churn_risk.csv")

# ---------------------------------------------------------
# 4. DEMAND FORECAST
# ---------------------------------------------------------
elif page == "Demand Forecast":
    if forecast is None:
        show_missing_files()
    st.subheader("30-Day Demand Forecast")

    required = {"Date", "Forecast_Units"}
    if not required.issubset(forecast.columns):
        st.error(f"Forecast file is missing columns: {sorted(required - set(forecast.columns))}")
        st.write("Columns found:", list(forecast.columns))
        st.stop()

    data = forecast.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Forecast_Units"] = pd.to_numeric(data["Forecast_Units"], errors="coerce").fillna(0)
    data = data.dropna(subset=["Date"]).sort_values("Date")

    if data.empty:
        st.info("There are no valid forecast dates in the file.")
    else:
        a, b, c = st.columns(3)
        a.metric("Forecast horizon", f"{len(data)} days")
        b.metric("Forecast units total", f"{data['Forecast_Units'].sum():,.0f}")
        c.metric("Average units/day", f"{data['Forecast_Units'].mean():,.1f}")

        max_day = max(1, len(data))
        horizon = st.slider("Display forecast horizon (days)", 1, max_day, max_day)
        view = data.head(horizon)
        st.markdown("**Forecast Daily Demand**")
        st.line_chart(view.set_index("Date")[["Forecast_Units"]], use_container_width=True)
        st.dataframe(view, use_container_width=True, hide_index=True)
        csv_download_button(view, "retailpulse_demand_forecast.csv")

        with st.expander("Forecast interpretation"):
            st.write("This page displays the saved forecast generated by your notebook. Changing the display horizon filters the view; it does not retrain the forecasting model.")

# ---------------------------------------------------------
# 5. INVENTORY OPTIMIZATION
# ---------------------------------------------------------
elif page == "Inventory Optimization":
    if inventory is None:
        show_missing_files()
    st.subheader("Inventory & Reorder Recommendations")

    required = {"Product_ID", "Current_Stock", "Lead_Time_Days", "Avg_Daily_Demand"}
    if not required.issubset(inventory.columns):
        st.error(f"Inventory file is missing columns: {sorted(required - set(inventory.columns))}")
        st.write("Columns found:", list(inventory.columns))
        st.stop()

    data = inventory.copy()
    safety_days = st.slider("Safety stock buffer (days)", min_value=0, max_value=30, value=14)
    data["Target_Stock_Adjusted"] = (
        data["Avg_Daily_Demand"].clip(lower=0) *
        (data["Lead_Time_Days"].clip(lower=0) + safety_days)
    ).apply(lambda x: int(-(-x // 1)))
    data["Suggested_Reorder_Adjusted"] = (
        data["Target_Stock_Adjusted"] - data["Current_Stock"]
    ).clip(lower=0)

    needs_reorder = data[data["Suggested_Reorder_Adjusted"] > 0].copy()
    a, b, c = st.columns(3)
    a.metric("Products analysed", f"{len(data):,}")
    b.metric("Products needing reorder", f"{len(needs_reorder):,}")
    c.metric("Suggested units to reorder", f"{data['Suggested_Reorder_Adjusted'].sum():,.0f}")

    if not data.empty:
        top_n = st.slider("Products to show in chart", 5, min(30, max(5, len(data))), min(10, max(5, len(data))))
        top = data.nlargest(top_n, "Suggested_Reorder_Adjusted")
        st.markdown(f"**Top {min(top_n, len(data))} Products by Suggested Reorder**")
        reorder_chart = top.sort_values("Suggested_Reorder_Adjusted").set_index("Product_ID")
        st.bar_chart(reorder_chart[["Suggested_Reorder_Adjusted"]], use_container_width=True)

    filter_reorder = st.checkbox("Show only products needing reorder", value=True)
    table = needs_reorder if filter_reorder else data
    st.dataframe(table.sort_values("Suggested_Reorder_Adjusted", ascending=False), use_container_width=True, hide_index=True)
    csv_download_button(table, "retailpulse_inventory_recommendations.csv")

    with st.expander("How the interactive reorder estimate works"):
        st.write("Adjusted target stock = average daily demand × (supplier lead time + selected safety-buffer days).")
        st.write("Adjusted suggested reorder = max(adjusted target stock − current stock, 0).")
        st.caption("This recalculates a recommendation from saved inventory inputs; it does not update physical stock or place purchase orders.")

# ---------------------------------------------------------
# 6. EXPLORE DATA
# ---------------------------------------------------------
elif page == "Explore Data":
    st.subheader("Explore Project Data")
    st.write("Inspect CSV files, review column names, and download a copy.")

    available = {
        label: (df, source)
        for label, df, source in [
            ("Sales", sales, sales_source),
            ("Customer segments", segments, segments_source),
            ("Churn predictions", churn, churn_source),
            ("Demand forecast", forecast, forecast_source),
            ("Inventory recommendations", inventory, inventory_source),
        ]
        if df is not None
    }

    if not available:
        show_missing_files()

    selected_name = st.selectbox("Choose a dataset", list(available.keys()))
    selected_df, source = available[selected_name]
    st.caption(f"Source: {source} · Rows: {len(selected_df):,} · Columns: {len(selected_df.columns):,}")

    search = st.text_input("Search column names", placeholder="Type part of a column name…")
    column_names = list(selected_df.columns)
    if search:
        column_names = [c for c in column_names if search.lower() in c.lower()]
    st.write("Matching columns:", column_names)

    rows_to_show = st.slider("Rows to preview", 5, max(5, min(100, max(5, len(selected_df)))), min(20, max(5, len(selected_df))))
    st.dataframe(selected_df.head(rows_to_show), use_container_width=True, hide_index=True)
    csv_download_button(selected_df, f"retailpulse_{selected_name.lower().replace(' ', '_')}.csv")

    with st.expander("Dataset quality quick check"):
        quality = pd.DataFrame({
            "Column": selected_df.columns,
            "Data type": [str(t) for t in selected_df.dtypes],
            "Missing values": [int(v) for v in selected_df.isna().sum().values],
            "Missing %": [
                round(float(selected_df[c].isna().mean() * 100), 2)
                for c in selected_df.columns
            ],
        })
        st.dataframe(quality, use_container_width=True, hide_index=True)

# Footer / session info
st.divider()
st.caption("RetailPulse Analytics · Built with Python, Streamlit and Pandas")
