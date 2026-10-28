"""Streamlit pages over the complete Net3 sensor feed and saved results."""
import json

import pandas as pd
import streamlit as st

from leakprobe.net3_tools import Net3Investigation
from leakprobe.ui.data_access import (
    load_case_index,
    load_case_observations,
    load_latest_llm_trace,
    load_report,
)


def _render_case_feed(case_id: str, observations: pd.DataFrame) -> None:
    observations = observations.copy()
    observations["timestamp_utc"] = pd.to_datetime(observations["timestamp_utc"], utc=True)
    pressure_cols = [column for column in observations if column.startswith("pressure_")]
    flow_cols = [column for column in observations if column.startswith("flow_")]
    numeric = observations[[*pressure_cols, *flow_cols]]
    missing_count = int(numeric.isna().sum().sum())
    total_values = int(numeric.size)

    st.caption(
        f"Case {case_id} · full sensor feed: {len(pressure_cols)} pressure channels and "
        f"{len(flow_cols)} flow channels · {missing_count:,} missing readings "
        f"({missing_count / max(total_values, 1):.2%})"
    )
    observations = observations.set_index("timestamp_utc")
    pressure = observations[pressure_cols]
    flow = observations[flow_cols]
    pressure_summary = pd.DataFrame({
        "Minimum across network": pressure.min(axis=1),
        "Median across network": pressure.median(axis=1),
        "Maximum across network": pressure.max(axis=1),
    }, index=observations.index)
    flow_summary = pd.DataFrame({
        "Minimum across network": flow.min(axis=1),
        "Median across network": flow.median(axis=1),
        "Maximum across network": flow.max(axis=1),
    }, index=observations.index)
    left, right = st.columns(2)
    with left:
        st.markdown("**Pressure head · m**")
        st.line_chart(pressure_summary, height=280)
    with right:
        st.markdown("**Pipe flow · L/s**")
        st.line_chart(flow_summary, height=280)

    with st.expander("Full channel inventory"):
        pressure_names = [column.removeprefix("pressure_").removesuffix("_m")
                          for column in pressure_cols]
        flow_names = [column.removeprefix("flow_").removesuffix("_lps")
                      for column in flow_cols]
        pressure_panel, flow_panel = st.columns(2)
        pressure_panel.markdown("**92 pressure channels**")
        pressure_panel.write(", ".join(pressure_names))
        flow_panel.markdown("**117 flow channels**")
        flow_panel.write(", ".join(flow_names))


def _show_investigation_result(result: dict) -> None:
    ranking = result["ranking"]
    if not ranking:
        st.warning("No scenario could be compared with the available readings.")
        return
    decision = result["decision"]
    winner = ranking[0]
    fit = decision.get("best_fit_score")
    if decision["prediction"] == "leak":
        st.warning(f"Leak alert · best fit: {winner['scenario']} · score {fit:.3f}")
    elif decision["prediction"] == "normal":
        st.success(f"Normal-operation fit ranks first · score {fit:.3f}")
    else:
        st.warning(f"Review needed · {decision.get('reason', 'The result is uncertain.')}")
    st.caption(
        "The fit score ranks simulated reference patterns against all sensor channels. "
        "It is not a probability or a field confirmation."
    )
    table = pd.DataFrame([
        {"Rank": index, "Scenario": row["scenario"], "Candidate pipe": row["leak_pipe"] or "—",
         "Normalized fit score": row["normalized_rmse"]}
        for index, row in enumerate(ranking, start=1)
    ])
    st.dataframe(
        table, hide_index=True, use_container_width=True,
        column_config={"Normalized fit score": st.column_config.NumberColumn(format="%.3f")},
    )
    st.caption(result["score_meaning"])


def render_investigation() -> None:
    st.title("Net3 leak investigation")
    st.write("Compare a complete sensor feed with normal operation and candidate leak patterns.")
    try:
        cases = load_case_index()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Could not load the full-channel Net3 case index: {exc}")
        return
    case_by_id = {row["case_id"]: row for row in cases}
    case_ids = [row["case_id"] for row in cases]
    default_id = next((row["case_id"] for row in cases if row["split"] == "test"), case_ids[0])
    selected_case = st.selectbox(
        "Case", case_ids,
        index=case_ids.index(st.session_state.get("net3_case_id", default_id)),
        format_func=lambda case_id: f"{case_id} · {case_by_id[case_id]['split']} split",
        key="net3_case_picker",
    )
    if st.session_state.get("net3_case_id") != selected_case:
        st.session_state.net3_case_id = selected_case
        st.session_state.pop("net3_result", None)

    try:
        session = Net3Investigation(selected_case)
        observations = load_case_observations(selected_case)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load this full-coverage case: {exc}")
        return

    metrics = st.columns(4)
    metrics[0].metric("Split", case_by_id[selected_case]["split"])
    metrics[1].metric("Pressure channels", "92 / 92")
    metrics[2].metric("Flow channels", "117 / 117")
    metrics[3].metric("Candidate pipes", len(session.metadata["candidate_pipes_by_split"][session.split]))
    _render_case_feed(selected_case, observations)

    if st.button("Compare the full sensor feed", type="primary", key=f"net3_compare_{selected_case}"):
        st.session_state.net3_result = session.compare_hypotheses()
    result = st.session_state.get("net3_result")
    if result:
        _show_investigation_result(result)
    if st.button("Reset comparison", key=f"net3_reset_{selected_case}"):
        st.session_state.pop("net3_result", None)
        st.rerun()


def _trace_arguments(row: dict) -> dict:
    arguments = row.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
    return arguments if isinstance(arguments, dict) else {}


def render_latest_llm_run() -> None:
    st.title("Latest LLM investigation")
    st.write("Review the most recent saved Net3 investigation using all 209 sensor channels.")
    st.caption("This page reads the saved trace and does not make a provider call.")
    try:
        saved_run = load_latest_llm_trace()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Could not read the saved LLM trace: {exc}")
        return
    if saved_run is None:
        st.info("No Net3 LLM run is saved. Run `python run_demo.py` to create one.")
        return

    status = saved_run.get("status", "unknown")
    if status != "completed":
        st.warning(f"The saved run status is **{status}**; review its result as incomplete.")
    tool_history = saved_run.get("trace", [])
    usage = saved_run.get("usage", [])
    total_tokens = sum(row.get("total_tokens", 0) for row in usage if isinstance(row, dict))
    summary = st.columns(4)
    summary[0].metric("Case", saved_run.get("case_id") or "—")
    summary[1].metric("Run status", status.title())
    summary[2].metric("LLM requests", len(usage))
    summary[3].metric("Reported tokens", f"{total_tokens:,}")

    comparisons = [
        row["result"] for row in tool_history
        if row.get("tool") == "compare_hypotheses"
        and isinstance(row.get("result"), dict)
        and row["result"].get("ranking")
    ]
    if comparisons:
        st.subheader("Latest full-channel comparison")
        rows = [
            {"Rank": index, "Scenario": row["scenario"], "Pipe": row["leak_pipe"] or "—",
             "Normalized fit score": row["normalized_rmse"]}
            for index, row in enumerate(comparisons[-1]["ranking"], start=1)
        ]
        st.dataframe(
            pd.DataFrame(rows), hide_index=True, use_container_width=True,
            column_config={"Normalized fit score": st.column_config.NumberColumn(format="%.3f")},
        )
        st.caption(comparisons[-1]["score_meaning"])

    answer = saved_run.get("answer")
    if answer:
        st.subheader("LLM interpretation")
        st.markdown(answer)
    else:
        st.info("The saved run has no final written interpretation.")

    with st.expander("Tool steps"):
        history = [{"Step": row.get("tool", "unknown").replace("_", " ").title()}
                   for row in tool_history]
        st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)


def render_benchmarks() -> None:
    st.title("Classifier benchmarks")
    st.write("Compare baseline, class-weighted, and SMOTE results on complete sensor feeds.")
    report_name = "High-signal Net3"
    try:
        report = load_report(report_name)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load the saved benchmark report: {exc}")
        return

    st.warning(
        "This is the high-signal benchmark: leaks are intentionally large and long, "
        "and the train/test leak parameter ranges match."
    )
    st.caption(
        f"Positive class: leak · {report['pressure_channel_count']} pressure + "
        f"{report['flow_channel_count']} flow channels · Development threshold target: "
        f"{report['target_leak_recall']:.0%} recall · Test cases: "
        f"{report['test_counts']['leak']} leaks, {report['test_counts']['normal']} normal"
    )
    rows = []
    for name, variant in report["variants"].items():
        score = variant["held_out_test"]
        matrix = score["confusion_matrix"]
        rows.append({
            "Variant": name.replace("_", " ").title(),
            "Leak precision": score["leak_precision"],
            "Leak recall": score["leak_recall"],
            "Balanced accuracy": score["balanced_accuracy"],
            "TP leaks caught": matrix["tp_leak"],
            "FN leaks missed": matrix["fn_leak"],
            "FP false alarms": matrix["fp_false_alarm"],
            "TN normal cleared": matrix["tn_normal"],
        })
    scores = pd.DataFrame(rows)
    precision_col, recall_col = st.columns(2)
    with precision_col:
        st.markdown("**Leak precision**")
        st.bar_chart(scores.set_index("Variant")[["Leak precision"]], y_label="Rate")
    with recall_col:
        st.markdown("**Leak recall**")
        st.bar_chart(scores.set_index("Variant")[["Leak recall"]], y_label="Rate")
    st.markdown("**Held-out test results**")
    st.dataframe(
        scores, hide_index=True, use_container_width=True,
        column_config={
            "Leak precision": st.column_config.NumberColumn(format="percent"),
            "Leak recall": st.column_config.NumberColumn(format="percent"),
            "Balanced accuracy": st.column_config.NumberColumn(format="percent"),
        },
    )
    with st.expander("Development cross-validation and in-sample results"):
        development_rows = []
        for name, variant in report["variants"].items():
            score = variant["development_oof"]
            development_rows.append({
                "Variant": name.replace("_", " ").title(),
                "Threshold": variant["threshold"],
                "Leak precision": score["leak_precision"],
                "Leak recall": score["leak_recall"],
                "Balanced accuracy": score["balanced_accuracy"],
            })
        st.dataframe(
            pd.DataFrame(development_rows), hide_index=True, use_container_width=True,
            column_config={
                "Threshold": st.column_config.NumberColumn(format="%.3f"),
                "Leak precision": st.column_config.NumberColumn(format="percent"),
                "Leak recall": st.column_config.NumberColumn(format="percent"),
                "Balanced accuracy": st.column_config.NumberColumn(format="percent"),
            },
        )
        in_sample_rows = []
        for name, variant in report.get("development_in_sample", {}).items():
            score = variant["in_sample"]
            in_sample_rows.append({
                "Variant": name.replace("_", " ").title(),
                "Leak precision": score["leak_precision"],
                "Leak recall": score["leak_recall"],
                "Balanced accuracy": score["balanced_accuracy"],
            })
        if in_sample_rows:
            st.markdown("**In-sample training scores (optimistic diagnostic)**")
            st.dataframe(pd.DataFrame(in_sample_rows), hide_index=True, use_container_width=True)
        st.caption("In-sample scores evaluate cases used for training. Use the held-out table as the main comparison.")


def render_about() -> None:
    st.title("About this workbench")
    st.write(
        "LeakProbe compares a complete Net3 pressure and flow feed with stored normal-operation and candidate-leak patterns."
    )
    st.subheader("Sensor coverage")
    st.markdown(
        "- 92 pressure channels, one for every junction.\n"
        "- 117 flow channels, one for every pipe.\n"
        "- Every case and classifier benchmark is checked against this channel layout."
    )
    st.subheader("How to read a result")
    st.markdown(
        "- A fit score measures how closely a reference scenario matches the supplied readings. It is not a probability.\n"
        "- A rejected result is marked uncertain and should be reviewed.\n"
        "- Benchmark precision and recall describe these stored cases; they do not establish field performance."
    )
    st.subheader("Scope")
    st.info(
        "The bundled Net3 feed and labels are generated benchmark data. No utility telemetry, GIS, work orders, "
        "controls, crew dispatch, or excavation workflow is connected."
    )
