# ============================================================
# Section 1: Imports
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import random
from datetime import datetime, timedelta, date

# ============================================================
# Section 2: Page config
# ============================================================
st.set_page_config(
    page_title="Sales Pipeline Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Section 3: Header
# ============================================================
st.title("📊 Sales Pipeline Management Dashboard")
st.markdown(
    """
    This dashboard helps sales managers identify pipeline bottlenecks,
    track deal progress, and prioritize actions using synthetic data.
    """
)

# ============================================================
# Section 4: Sidebar controls
# ============================================================
st.sidebar.header("Filters & Settings")
n_deals = st.sidebar.slider("Number of deals", 100, 2000, 500, 100)
start_date = st.sidebar.date_input("Start Date", date.today() - timedelta(days=90))
end_date   = st.sidebar.date_input("End Date",   date.today())

all_reps   = ["Alice", "Bob", "Carol", "David"]
all_stages = [
    "Prospecting", "Qualification", "Proposal",
    "Negotiation", "Closed Won", "Closed Lost",
]
reps   = st.sidebar.multiselect("Sales Reps",   all_reps,   default=all_reps)
stages = st.sidebar.multiselect("Deal Stages", all_stages, default=all_stages)
stalled_th = st.sidebar.slider("Stalled Threshold (days)", 10, 60, 30, 5)

# ============================================================
# Section 5: Regeneration logic via session_state
# ============================================================
if "seed" not in st.session_state:
    st.session_state.seed = 42

if st.sidebar.button("Regenerate Data"):
    st.session_state.seed = random.randint(0, 1_000_000)

# ============================================================
# Section 6: Data generation
# ============================================================
@st.cache_data
def gen_data(n: int, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    rows = []
    for _ in range(n):
        rep   = np.random.choice(all_reps)
        stage = np.random.choice(all_stages, p=[0.2]*4 + [0.1,0.1])
        days  = int(np.random.exponential(15)) + 1
        created = datetime.now() - timedelta(days=np.random.randint(0,90))
        updated = created + timedelta(days=days)
        value = float(np.round(np.random.uniform(1_000,20_000),0))
        status = (
            "Won"  if stage=="Closed Won"  else
            "Lost" if stage=="Closed Lost" else
            "Open"
        )
        rows.append({
            "rep": rep,
            "stage": stage,
            "time_in_stage": days,
            "created": created,
            "updated": updated,
            "value": value,
            "status": status,
        })
    return pd.DataFrame(rows)

# ============================================================
# Section 7: Load & filter
# ============================================================
df = gen_data(n_deals, st.session_state.seed)
df = df[df["created"].dt.date.between(start_date, end_date)]
df = df[df["rep"].isin(reps) & df["stage"].isin(stages)]

# ============================================================
# Section 8: KPI row
# ============================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Deals", df.shape[0])

win_rate = (df["status"]=="Won").sum() / max(1, len(df)) * 100
c2.metric("Win Rate", f"{win_rate:.1f}%")

avg_val = df["value"].mean() if not df.empty else 0
c3.metric("Avg Deal Value", f"${avg_val:,.0f}")

med_time = df["time_in_stage"].median() if not df.empty else 0
c4.metric("Median Time (days)", f"{med_time:.0f} d")

# ============================================================
# Section 9: Status pie
# ============================================================
status_counts = (
    df["status"]
    .value_counts()
    .reset_index(name="count")
    .rename(columns={"index": "status"})
)
pie = (
    alt.Chart(status_counts)
    .mark_arc(innerRadius=50)
    .encode(
        theta="count:Q",
        color="status:N",
        tooltip=["status","count"],
    )
)
st.altair_chart(pie, use_container_width=True)

# ============================================================
# Section 10: Open funnel
# ============================================================
funnel_df = (
    df[df["status"]=="Open"]["stage"]
    .value_counts()
    .reindex(all_stages, fill_value=0)
    .reset_index(name="count")
    .rename(columns={"index":"stage"})
)
funnel = (
    alt.Chart(funnel_df)
    .mark_bar()
    .encode(
        x=alt.X("count:Q", title="Deals"),
        y=alt.Y("stage:N", sort=all_stages),
        tooltip=["stage","count"],
    )
)
st.altair_chart(funnel, use_container_width=True)

# ============================================================
# Section 11: Deals by rep
# ============================================================
rep_counts = (
    df["rep"]
    .value_counts()
    .reset_index(name="count")
    .rename(columns={"index":"rep"})
)
bar_rep = (
    alt.Chart(rep_counts)
    .mark_bar()
    .encode(
        x="rep:N",
        y="count:Q",
        tooltip=["rep","count"],
    )
)
st.altair_chart(bar_rep, use_container_width=True)

# ============================================================
# Section 12: Avg time by stage
# ============================================================
avg_time = (
    df.groupby("stage")["time_in_stage"]
    .mean()
    .reindex(all_stages, fill_value=0)
    .reset_index()
    .rename(columns={"time_in_stage":"avg_days"})
)
bar_time = (
    alt.Chart(avg_time)
    .mark_bar()
    .encode(
        x="stage:N",
        y="avg_days:Q",
        tooltip=["stage","avg_days"],
    )
)
st.altair_chart(bar_time, use_container_width=True)

# ============================================================
# Section 13: Deals over time
# ============================================================
ts = (
    df.set_index("created")
    .resample("W")["rep"]
    .count()
    .reset_index(name="deals")
)
line_ts = (
    alt.Chart(ts)
    .mark_line(point=True)
    .encode(
        x="created:T",
        y="deals:Q",
        tooltip=["created","deals"],
    )
)
st.altair_chart(line_ts, use_container_width=True)

# ============================================================
# Section 14: Time-in-stage hist
# ============================================================
hist = (
    alt.Chart(df)
    .mark_bar()
    .encode(
        alt.X("time_in_stage:Q", bin=alt.Bin(maxbins=20), title="Days in Stage"),
        y="count():Q",
        tooltip=["count():Q"],
    )
)
st.altair_chart(hist, use_container_width=True)

# ============================================================
# Section 15: Stalled deals table
# ============================================================
st.header("🔍 Stalled Deals")
st.write("Open deals where time in stage > threshold:")
st.dataframe(
    df[(df["status"]=="Open") & (df["time_in_stage"]>stalled_th)][
        ["rep","stage","time_in_stage","value","created","updated"]
    ]
)

# ============================================================
# Section 16: Insights
# ============================================================
st.header("💡 Insights & Next Steps")
st.markdown(
    """
- **Move deals faster** from Qualification to Proposal  
- **Prioritize follow-up** on stalled deals  
- **Coach** low-performing reps with targeted guidance  
"""
)