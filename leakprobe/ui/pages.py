"""Streamlit pages over the complete Net3 sensor feed and saved results."""
import json

import pandas as pd
import streamlit as st

from leakprobe.ui.data_access import (
    load_llm_trace_history,
    load_report,
)


def _run_comparison(saved_run: dict) -> dict | None:
    comparisons = [
        row["result"] for row in saved_run.get("trace", [])
        if row.get("tool") == "compare_hypotheses"
        and isinstance(row.get("result"), dict)
        and row["result"].get("ranking")
    ]
    return comparisons[-1] if comparisons else None


def render_llm_run_history() -> None:
    st.title("Saved runs and traces")
    st.write("Browse saved Net3 investigations and open each run's result and tool trace.")
    st.caption("This page reads local trace files. Opening a saved run does not call the provider.")
    try:
        saved_runs = load_llm_trace_history()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Could not read the saved LLM run history: {exc}")
        return
    if not saved_runs:
        st.info("No Net3 LLM runs are saved. Run `python run_demo.py` to create one.")
        return

    history_rows = []
    for run in saved_runs:
        comparison = _run_comparison(run)
        ranking = comparison["ranking"] if comparison else []
        winner = ranking[0] if ranking else {}
        token_count = sum(
            row.get("total_tokens", 0)
            for row in run.get("usage", [])
            if isinstance(row, dict)
        )
        history_rows.append({
            "Saved at (UTC)": run["saved_at_utc"],
            "Case": run.get("case_id") or "—",
            "Status": run.get("status", "unknown").title(),
            "Leading fit": winner.get("scenario", "—").replace("leak_pipe:", "Pipe "),
            "Best fit error": winner.get("normalized_rmse"),
            "LLM requests": len(run.get("usage", [])),
            "Reported tokens": token_count,
        })
    st.subheader("Run history")
    st.dataframe(
        pd.DataFrame(history_rows), hide_index=True, use_container_width=True,
        column_config={"Best fit error": st.column_config.NumberColumn(format="%.3f")},
    )

    selected_index = st.selectbox(
        "Open a saved run",
        options=list(range(len(saved_runs))),
        format_func=lambda index: (
            f"{saved_runs[index].get('case_id') or 'Unknown case'} · "
            f"{saved_runs[index]['saved_at_utc']} · "
            f"{saved_runs[index].get('status', 'unknown').title()}"
        ),
        key="saved_llm_run_selector",
    )
    saved_run = saved_runs[selected_index]
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

    comparison = _run_comparison(saved_run)
    if comparison:
        st.subheader("Full-channel comparison")
        rows = [
            {"Rank": index, "Scenario": row["scenario"], "Pipe": row["leak_pipe"] or "—",
             "Normalized fit score": row["normalized_rmse"]}
            for index, row in enumerate(comparison["ranking"], start=1)
        ]
        st.dataframe(
            pd.DataFrame(rows), hide_index=True, use_container_width=True,
            column_config={"Normalized fit score": st.column_config.NumberColumn(format="%.3f")},
        )
        st.caption(comparison["score_meaning"])

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
        st.caption(f"Trace file: `{saved_run['trace_file']}`")


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
        "- The alert highlights the lowest-error candidate pattern; the fit score is not a probability.\n"
        "- Follow the normal field verification process before confirming a leak.\n"
        "- Benchmark precision and recall describe these stored cases; they do not establish field performance."
    )
    st.subheader("Scope")
    st.info(
        "The bundled Net3 feed and labels are generated benchmark data. No utility telemetry, GIS, work orders, "
        "controls, crew dispatch, or excavation workflow is connected."
    )
