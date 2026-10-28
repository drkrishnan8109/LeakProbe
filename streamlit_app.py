"""Streamlit entry point for the synthetic LeakProbe workbench."""
import streamlit as st

from leakprobe.ui.pages import (
    render_about,
    render_benchmarks,
    render_investigation,
    render_latest_llm_run,
)

st.set_page_config(
    page_title="LeakProbe | Investigation Workbench",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("LeakProbe")
st.sidebar.caption("Hydraulic investigation workbench")
st.sidebar.info("Simulation only · Synthetic data · No field equipment connected")

page = st.navigation(
    [
        st.Page(render_investigation, title="Investigate", icon=":material/search:"),
        st.Page(render_latest_llm_run, title="Latest LLM run", icon="🧠"),
        st.Page(render_benchmarks, title="Benchmarks", icon=":material/monitoring:"),
        st.Page(render_about, title="About", icon=":material/info:"),
    ],
    position="sidebar",
)
page.run()
