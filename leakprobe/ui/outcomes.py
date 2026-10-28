"""After-action view of the held-out monitoring outcomes."""
import pandas as pd
import streamlit as st

from leakprobe.ui.data_access import load_outcome_records


def render_outcome_review() -> None:
    records = load_outcome_records()
    outcomes = pd.DataFrame(records)
    leak_count = int((outcomes["Verified outcome"] == "Leak confirmed").sum())
    normal_count = int((outcomes["Verified outcome"] == "Normal operation confirmed").sum())

    st.title(
        "Monitoring history and outcomes",
        help=(
            "After-action view of the held-out monitoring windows and their recorded outcomes. "
            "These verified labels are kept separate from the live alert calculation."
        ),
    )
    st.write("Review closed monitoring windows and their recorded outcomes.")
    metrics = st.columns(3)
    metrics[0].metric(
        "Leak outcomes",
        leak_count,
        help="Number of reviewed windows whose stored outcome confirms a leak.",
    )
    metrics[1].metric(
        "Normal outcomes",
        normal_count,
        help="Number of reviewed windows whose stored outcome confirms normal operation.",
    )
    metrics[2].metric(
        "Windows reviewed",
        len(outcomes),
        help="Total number of held-out monitoring windows listed for after-action review.",
    )
    st.dataframe(
        outcomes,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Window": st.column_config.TextColumn(
                help="Identifier of the monitoring window that was assessed."
            ),
            "Verified outcome": st.column_config.TextColumn(
                help="Recorded reference label used to review the alert after the assessment."
            ),
            "Confirmed pipe": st.column_config.TextColumn(
                help="Pipe listed in the stored outcome for a confirmed leak; a dash means there is no leak pipe."
            ),
        },
    )
    st.caption(
        "Outcomes are shown here for after-action review. The monitoring alert is computed without reading the outcome label.",
        help=(
            "Keeping the outcome label out of the alert calculation prevents the answer from "
            "being used as an input to its own assessment."
        ),
    )
