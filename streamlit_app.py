"""Streamlit entry point for the LeakProbe employee monitoring workbench."""
import streamlit as st

from leakprobe.ui.pages import (
    render_about,
    render_benchmarks,
    render_latest_llm_run,
)
from leakprobe.ui.monitoring import render_monitoring_dashboard
from leakprobe.ui.outcomes import render_outcome_review

st.set_page_config(
    page_title="LeakProbe | Network Monitoring",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("LeakProbe")
st.sidebar.caption("Employee monitoring desk")
st.sidebar.info("Full network coverage · 92 pressure + 117 flow channels")

page = st.navigation(
    {
        "Operations": [
            st.Page(render_monitoring_dashboard, title="Monitoring", icon="💧", default=True),
            st.Page(render_outcome_review, title="History & outcomes", icon=":material/history:"),
        ],
        "Analysis": [
            st.Page(render_latest_llm_run, title="Analysis trace", icon="🧠"),
            st.Page(render_benchmarks, title="Model performance", icon=":material/monitoring:"),
            st.Page(render_about, title="About", icon=":material/info:"),
        ],
    },
    position="sidebar",
)
page.run()
