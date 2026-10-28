"""Streamlit entry point for the Leak Probe Water Leak Detection System."""
import streamlit as st

from leakprobe.ui.pages import (
    render_about,
    render_benchmarks,
    render_llm_run_history,
)
from leakprobe.ui.monitoring import render_monitoring_dashboard
from leakprobe.ui.outcomes import render_outcome_review

st.set_page_config(
    page_title="Leak Probe Water Leak Detection System",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title(
    "Leak Probe",
    help="The product name of this full-channel water leak detection system.",
)
st.sidebar.caption("Water Leak Detection System")
st.sidebar.caption(
    "Employee monitoring desk",
    help="The intended employee workflow is to review the automatic alert and verify any pipe candidate in the field.",
)
st.sidebar.info("Full network coverage · 92 pressure + 117 flow channels")
st.sidebar.caption(
    "Coverage counts all configured sensor channels in the Net3 feed.",
    help="A complete feed has one pressure channel for each of 92 junctions and one flow channel for each of 117 pipes.",
)

page = st.navigation(
    {
        "Operations": [
            st.Page(render_monitoring_dashboard, title="Monitoring", icon="💧", default=True),
            st.Page(render_outcome_review, title="History & outcomes", icon=":material/history:"),
        ],
        "Analysis": [
            st.Page(render_llm_run_history, title="Run history & traces", icon="🧠"),
            st.Page(render_benchmarks, title="Model performance", icon=":material/monitoring:"),
            st.Page(render_about, title="About", icon=":material/info:"),
        ],
    },
    position="sidebar",
)
page.run()
