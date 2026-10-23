
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
SILVER_FILE = BASE_DIR / "silver" / "appointments_clean.csv"

st.set_page_config(
    page_title="Care Insights | Appointment Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Styling ----------
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,.22);
    padding: 18px 20px;
    border-radius: 14px;
}
[data-testid="stMetricLabel"] {font-size: 14px;}
[data-testid="stMetricValue"] {font-size: 28px;}
div[data-testid="stPlotlyChart"] {
    border: 1px solid rgba(128,128,128,.18);
    border-radius: 12px;
    padding: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Data ----------
@st.cache_data
def load_data(path, modified_time):
    df = pd.read_csv(path)
    for col in ["appointmentday", "scheduledday"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    for col in ["age", "sms_received", "scholarship", "hipertension",
                "diabetes", "alcoholism", "handcap"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

st.markdown("## 📊 Care Insights")
st.caption("Medical appointment attendance • Data quality and operational analytics")

if not SILVER_FILE.exists():
    st.error("Clean dataset not found. Run `python main.py` and `python clean_data.py` first.")
    st.stop()

df = load_data(str(SILVER_FILE), SILVER_FILE.stat().st_mtime)

# ---------- Sidebar ----------
st.sidebar.title("Dashboard Controls")
st.sidebar.caption("Adjust filters to explore appointment patterns.")

neighbourhood_options = sorted(df["neighbourhood"].dropna().unique().tolist())
selected_neighbourhoods = st.sidebar.multiselect(
    "Neighbourhood",
    neighbourhood_options,
    default=neighbourhood_options
)

gender_options = sorted(df["gender"].dropna().unique().tolist())
selected_genders = st.sidebar.multiselect(
    "Gender",
    gender_options,
    default=gender_options
)

sms_options = st.sidebar.multiselect(
    "SMS received",
    [0, 1],
    default=[0, 1],
    format_func=lambda value: "Received SMS" if value == 1 else "No SMS"
)

if df["appointmentday"].notna().any():
    min_date = df["appointmentday"].dropna().min().date()
    max_date = df["appointmentday"].dropna().max().date()
    selected_dates = st.sidebar.date_input(
        "Appointment date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
else:
    selected_dates = ()

# ---------- Filter ----------
filtered = df[
    df["neighbourhood"].isin(selected_neighbourhoods)
    & df["gender"].isin(selected_genders)
    & df["sms_received"].isin(sms_options)
].copy()

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    dates = filtered["appointmentday"].dt.date
    filtered = filtered[dates.between(start_date, end_date)].copy()

if filtered.empty:
    st.warning("No records match the selected filters. Adjust the filters in the sidebar.")
    st.stop()

total = len(filtered)
attended = int((filtered["no_show"] == "No").sum())
missed = int((filtered["no_show"] == "Yes").sum())
no_show_rate = missed / total * 100 if total else 0
attendance_rate = attended / total * 100 if total else 0
unique_patients = filtered["patientid"].nunique()

# ---------- KPI row ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Appointments", f"{total:,}")
k2.metric("Unique Patients", f"{unique_patients:,}")
k3.metric("Attendance Rate", f"{attendance_rate:.1f}%")
k4.metric("No-show Rate", f"{no_show_rate:.1f}%")

st.caption(
    f"Showing {total:,} appointments across "
    f"{filtered['neighbourhood'].nunique():,} neighbourhoods."
)
st.divider()

# ---------- Attendance + gender ----------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Attendance Breakdown")
    outcomes = pd.DataFrame({
        "Outcome": ["Attended", "Missed"],
        "Appointments": [attended, missed]
    })
    fig = px.pie(
        outcomes,
        names="Outcome",
        values="Appointments",
        hole=0.66,
        color="Outcome",
        color_discrete_map={
            "Attended": "#16A34A",
            "Missed": "#F97316"
        }
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>Appointments: %{value:,}<br>Share: %{percent}<extra></extra>"
    )
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=10),
        legend_title_text=""
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("No-show Rate by Gender")
    gender_summary = filtered.groupby("gender").agg(
        appointments=("appointmentid", "count"),
        missed=("no_show", lambda s: (s == "Yes").sum())
    ).reset_index()
    gender_summary["no_show_rate_percent"] = (
        gender_summary["missed"] / gender_summary["appointments"] * 100
    ).round(2)
    fig = px.bar(
        gender_summary,
        x="gender",
        y="no_show_rate_percent",
        text="no_show_rate_percent",
        color="gender",
        hover_data=["appointments", "missed"],
        labels={
            "gender": "Gender",
            "no_show_rate_percent": "No-show rate (%)",
            "appointments": "Appointments",
            "missed": "Missed"
        }
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        showlegend=False,
        yaxis_title="No-show rate (%)",
        xaxis_title="",
        margin=dict(t=25, b=20, l=10, r=10)
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Monthly trend ----------
st.divider()
st.subheader("Appointment Trends Over Time")

monthly_data = filtered.dropna(subset=["appointmentday"]).copy()
monthly_data["month"] = monthly_data["appointmentday"].dt.strftime("%Y-%m")
monthly_summary = monthly_data.groupby("month").agg(
    appointments=("appointmentid", "count"),
    missed=("no_show", lambda s: (s == "Yes").sum())
).reset_index().sort_values("month")

if not monthly_summary.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_summary["month"],
        y=monthly_summary["appointments"],
        mode="lines+markers",
        name="All appointments",
        line=dict(width=3)
    ))
    fig.add_trace(go.Scatter(
        x=monthly_summary["month"],
        y=monthly_summary["missed"],
        mode="lines+markers",
        name="Missed appointments",
        line=dict(width=3, dash="dot")
    ))
    fig.update_layout(
        hovermode="x unified",
        xaxis_title="Month",
        yaxis_title="Number of appointments",
        legend_title_text="",
        margin=dict(t=20, b=20, l=10, r=10)
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- SMS analysis ----------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("SMS and Attendance")
    sms_summary = filtered.groupby("sms_received").agg(
        appointments=("appointmentid", "count"),
        missed=("no_show", lambda s: (s == "Yes").sum())
    ).reset_index()
    sms_summary["no_show_rate_percent"] = (
        sms_summary["missed"] / sms_summary["appointments"] * 100
    ).round(2)
    sms_summary["SMS status"] = sms_summary["sms_received"].map(
        {0: "No SMS", 1: "Received SMS"}
    )
    fig = px.bar(
        sms_summary,
        x="SMS status",
        y="no_show_rate_percent",
        text="no_show_rate_percent",
        hover_data=["appointments", "missed"],
        labels={"no_show_rate_percent": "No-show rate (%)"}
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="No-show rate (%)",
        margin=dict(t=20, b=20, l=10, r=10)
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("No-show Rate by Age Group")
    age_df = filtered.dropna(subset=["age"]).copy()
    age_df = age_df[age_df["age"].between(0, 120)]
    age_df["age_group"] = pd.cut(
        age_df["age"],
        bins=[-1, 17, 29, 44, 59, 120],
        labels=["0–17", "18–29", "30–44", "45–59", "60+"]
    )
    age_summary = age_df.groupby("age_group", observed=False).agg(
        appointments=("appointmentid", "count"),
        missed=("no_show", lambda s: (s == "Yes").sum())
    ).reset_index()
    age_summary["no_show_rate_percent"] = (
        age_summary["missed"] / age_summary["appointments"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)
    fig = px.bar(
        age_summary,
        x="age_group",
        y="no_show_rate_percent",
        text="no_show_rate_percent",
        hover_data=["appointments", "missed"],
        labels={
            "age_group": "Age group",
            "no_show_rate_percent": "No-show rate (%)"
        }
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        showlegend=False,
        xaxis_title="Age group",
        yaxis_title="No-show rate (%)",
        margin=dict(t=20, b=20, l=10, r=10)
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Neighbourhood ranking ----------
st.divider()
st.subheader("Neighbourhood Performance")

neighbourhood_summary = filtered.groupby("neighbourhood").agg(
    appointments=("appointmentid", "count"),
    missed=("no_show", lambda s: (s == "Yes").sum())
).reset_index()
neighbourhood_summary["no_show_rate_percent"] = (
    neighbourhood_summary["missed"] /
    neighbourhood_summary["appointments"] * 100
).round(2)
neighbourhood_summary = neighbourhood_summary.sort_values(
    "no_show_rate_percent", ascending=False
)

top_n = st.slider(
    "Number of neighbourhoods to display",
    min_value=5,
    max_value=min(30, len(neighbourhood_summary)),
    value=min(10, len(neighbourhood_summary))
)
top_neighbourhoods = neighbourhood_summary.head(top_n)

fig = px.bar(
    top_neighbourhoods.sort_values("no_show_rate_percent"),
    x="no_show_rate_percent",
    y="neighbourhood",
    orientation="h",
    text="no_show_rate_percent",
    hover_data=["appointments", "missed"],
    labels={
        "no_show_rate_percent": "No-show rate (%)",
        "neighbourhood": "Neighbourhood"
    }
)
fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig.update_layout(
    showlegend=False,
    yaxis_title="",
    xaxis_title="No-show rate (%)",
    margin=dict(t=15, b=20, l=10, r=50)
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("View neighbourhood summary table"):
    st.dataframe(
        neighbourhood_summary,
        use_container_width=True,
        hide_index=True
    )

# ---------- Records and download ----------
with st.expander("Explore appointment records"):
    st.dataframe(
        filtered.drop(columns=["patientid"], errors="ignore"),
        use_container_width=True,
        hide_index=True
    )

st.download_button(
    "Download filtered report (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_appointment_report.csv",
    mime="text/csv"
)

st.caption(
    "Note: No-show rates describe patterns in this dataset; "
    "they do not establish that SMS, age, or gender causes missed appointments."
)
