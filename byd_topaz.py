import streamlit as st
import sqlite3
import pandas as pd
import tempfile

st.set_page_config(page_title="BYD Energy Viewer", layout="wide")
st.title("🚗 BYD Energy Consumption (Filtered)")

uploaded_file = st.file_uploader("Upload EC_database.db", type=["db", "sqlite"])

if not uploaded_file:
    st.stop()

# Save temp file safely
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
    tmp.write(uploaded_file.getbuffer())
    db_path = tmp.name

@st.cache_data
def load_data(path):
    conn = sqlite3.connect(path)
    df = pd.read_sql_query(
        "SELECT * FROM EnergyConsumption WHERE is_deleted = 0",
        conn
    )
    conn.close()
    return df

df = load_data(db_path)

if df.empty:
    st.error("No data found.")
    st.stop()

# -----------------------------
# Fix Data (TIMEZONE FIX)
# -----------------------------
# Source is GMT → convert to GMT+2
df["start_time"] = pd.to_datetime(df["start_timestamp"], unit="s", utc=True).dt.tz_convert("Africa/Johannesburg")
df["end_time"] = pd.to_datetime(df["end_timestamp"], unit="s", utc=True).dt.tz_convert("Africa/Johannesburg")

# Convert durations
df["duration_minutes"] = df["duration"] / 60
df["duration_hours"] = df["duration"] / 3600

# 🔥 FILTER: remove junk rows
df = df[
    (df["duration_hours"] > 0) &
    (df["trip"] >= 1)
]

# -----------------------------
# DATE FILTER DROPDOWN
# -----------------------------
st.sidebar.header("Filters")

date_filter = st.sidebar.selectbox(
    "Select time range",
    ["Last 7 days", "Last 30 days", "All time"]
)

now = pd.Timestamp.now(tz="Africa/Johannesburg")

if date_filter == "Last 7 days":
    df = df[df["start_time"] >= now - pd.Timedelta(days=7)]
elif date_filter == "Last 30 days":
    df = df[df["start_time"] >= now - pd.Timedelta(days=30)]
# "All time" = no filter

# -----------------------------
# Calculations
# -----------------------------
df["avg_speed_kmh"] = df["trip"] / df["duration_hours"]
df["wh_per_km"] = (df["electricity"] / df["trip"]) * 1000

# -----------------------------
# Summary
# -----------------------------
st.subheader("📊 Summary")

col1, col2, col3 = st.columns(3)

col1.metric("Total Distance (km)", f"{df['trip'].sum():.2f}")
col2.metric("Avg Speed (km/h)", f"{df['avg_speed_kmh'].mean():.2f}")
col3.metric("Efficiency (Wh/km)", f"{df['wh_per_km'].mean():.0f}")

# -----------------------------
# Table
# -----------------------------
st.subheader(f"📋 Trips ({date_filter})")

st.dataframe(
    df[[
        "start_time",
        "end_time",
        "trip",
        "duration_minutes",
        "avg_speed_kmh",
        "wh_per_km"
    ]].sort_values("start_time", ascending=False),
    use_container_width=True
)

# -----------------------------
# Charts
# -----------------------------
st.subheader("📈 Trends")

st.line_chart(df.set_index("start_time")["avg_speed_kmh"])
st.line_chart(df.set_index("start_time")["wh_per_km"])