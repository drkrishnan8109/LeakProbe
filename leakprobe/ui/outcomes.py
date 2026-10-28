"""After-action view of the held-out monitoring outcomes."""
import pandas as pd
import streamlit as st

from leakprobe.ui.data_access import load_outcome_records


def render_outcome_review() -> None:
    records = load_outcome_records()
    outcomes = pd.DataFrame(records)
    leak_count = int((outcomes["Verified outcome"] == "Leak confirmed").sum())
    normal_count = int((outcomes["Verified outcome"] == "Normal operation confirmed").sum())

    st.title("Monitoring history and outcomes")
    st.write("Review closed monitoring windows and their recorded outcomes.")
    metrics = st.columns(3)
    metrics[0].metric("Leak outcomes", leak_count)
    metrics[1].metric("Normal outcomes", normal_count)
    metrics[2].metric("Windows reviewed", len(outcomes))
    st.dataframe(outcomes, hide_index=True, use_container_width=True)
    st.caption("Outcomes are shown here for after-action review. The monitoring alert is computed without reading the outcome label.")
