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
    st.title(
        "Saved runs and traces",
        help=(
            "Browse saved investigation runs, their pattern comparisons, optional LLM summaries, "
            "and the recorded sequence of analysis-tool calls."
        ),
    )
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
    st.subheader(
        "Run history",
        help="A list of saved investigations, their case, outcome status, leading pattern, and run usage.",
    )
    st.dataframe(
        pd.DataFrame(history_rows), hide_index=True, use_container_width=True,
        column_config={
            "Saved at (UTC)": st.column_config.TextColumn(
                help="Time when this investigation was saved, shown in Coordinated Universal Time."
            ),
            "Case": st.column_config.TextColumn(
                help="Identifier of the sensor-feed case used in the investigation."
            ),
            "Status": st.column_config.TextColumn(
                help="Whether the saved investigation completed or stopped before completion."
            ),
            "Leading fit": st.column_config.TextColumn(
                help="The normal or pipe-specific pattern ranked closest to the feed."
            ),
            "Best fit error": st.column_config.NumberColumn(
                format="%.3f",
                help="Normalized mismatch for the leading pattern. Lower is closer; this is not a probability."
            ),
            "LLM requests": st.column_config.NumberColumn(
                help="Number of calls to the language-model provider. This does not count analysis-tool calls or expose the model's private internal reasoning."
            ),
            "Reported tokens": st.column_config.NumberColumn(
                help="Total input and output tokens reported for the language-model requests."
            ),
        },
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
        help="Choose which saved investigation to open below. This reads its saved trace and does not start a new provider request.",
    )
    saved_run = saved_runs[selected_index]
    status = saved_run.get("status", "unknown")
    if status != "completed":
        st.warning(f"The saved run status is **{status}**; review its result as incomplete.")
    tool_history = saved_run.get("trace", [])
    usage = saved_run.get("usage", [])
    total_tokens = sum(row.get("total_tokens", 0) for row in usage if isinstance(row, dict))
    summary = st.columns(4)
    summary[0].metric(
        "Case",
        saved_run.get("case_id") or "—",
        help="Identifier of the sensor-feed case used by this saved run.",
    )
    summary[1].metric(
        "Run status",
        status.title(),
        help="Whether the saved investigation completed or ended early.",
    )
    summary[2].metric(
        "LLM requests",
        len(usage),
        help=(
            "Number of calls to the language-model provider. This does not count the separate "
            "analysis-tool steps or expose the model's private internal reasoning."
        ),
    )
    summary[3].metric(
        "Reported tokens",
        f"{total_tokens:,}",
        help="Total input and output tokens reported by the language-model provider for this run.",
    )

    comparison = _run_comparison(saved_run)
    if comparison:
        st.subheader(
            "Full-channel comparison",
            help=(
                "Ranks the stored normal and leak patterns against the complete 92-pressure, "
                "117-flow feed. The comparison score is an error value, not a probability."
            ),
        )
        rows = [
            {"Rank": index, "Scenario": row["scenario"], "Pipe": row["leak_pipe"] or "—",
             "Normalized fit score": row["normalized_rmse"]}
            for index, row in enumerate(comparison["ranking"], start=1)
        ]
        st.dataframe(
            pd.DataFrame(rows), hide_index=True, use_container_width=True,
            column_config={
                "Rank": st.column_config.NumberColumn(
                    help="Position in the list, ordered from the closest fit upward."
                ),
                "Scenario": st.column_config.TextColumn(
                    help="The stored normal-operation or pipe-specific leak pattern being compared."
                ),
                "Pipe": st.column_config.TextColumn(
                    help="Pipe associated with a leak pattern; a dash means this row is normal operation."
                ),
                "Normalized fit score": st.column_config.NumberColumn(
                    format="%.3f",
                    help="Normalized mismatch between this pattern and the feed. Lower is closer; it is not a probability."
                ),
            },
        )
        st.caption(comparison["score_meaning"])

    answer = saved_run.get("answer")
    if answer:
        st.subheader(
            "LLM interpretation",
            help="A saved plain-language summary produced for this run. It explains tool results but does not change the detector's comparison.",
        )
        st.markdown(answer)
    else:
        st.info("The saved run has no final written interpretation.")

    with st.expander("Tool steps", icon=":material/info:"):
        st.caption(
            "The ordered analysis-tool calls recorded during this saved investigation. "
            "Opening the trace does not execute the tools again."
        )
        history = [{"Step": row.get("tool", "unknown").replace("_", " ").title()}
                   for row in tool_history]
        st.dataframe(
            pd.DataFrame(history),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Step": st.column_config.TextColumn(
                    help="Name of the analysis tool called at this step."
                )
            },
        )
        st.caption(f"Trace file: `{saved_run['trace_file']}`")


def render_benchmarks() -> None:
    st.title(
        "Classifier benchmarks",
        help=(
            "Compare the held-out scores of three ways of training the same leak classifier: "
            "baseline, class-weighted, and SMOTE."
        ),
    )
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
        f"{report['test_counts']['leak']} leaks, {report['test_counts']['normal']} normal",
        help=(
            "Leak is treated as the positive result when calculating scores. The development "
            "recall target is used to choose the alert threshold before final evaluation on the "
            "held-out test cases."
        ),
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
        st.subheader(
            "Leak precision",
            help=(
                "Of the cases a classifier flags as leaks, the share that are actually labeled "
                "leaks in this test set. Higher precision means fewer false alarms."
            ),
        )
        st.bar_chart(scores.set_index("Variant")[["Leak precision"]], y_label="Rate")
    with recall_col:
        st.subheader(
            "Leak recall",
            help=(
                "Of the actual leak cases in this test set, the share that a classifier catches. "
                "Higher recall means fewer missed leaks."
            ),
        )
        st.bar_chart(scores.set_index("Variant")[["Leak recall"]], y_label="Rate")
    st.subheader(
        "Held-out test results",
        help=(
            "Final comparison on cases kept out of model training and threshold selection. "
            "Use these results as the main benchmark comparison."
        ),
    )
    st.dataframe(
        scores, hide_index=True, use_container_width=True,
        column_config={
            "Variant": st.column_config.TextColumn(
                help="Training approach used for this version of the leak classifier."
            ),
            "Leak precision": st.column_config.NumberColumn(
                format="percent",
                help="Among alerts labeled leak, the fraction that are actual leaks. Higher means fewer false alarms.",
            ),
            "Leak recall": st.column_config.NumberColumn(
                format="percent",
                help="Among actual leaks, the fraction flagged by the classifier. Higher means fewer missed leaks.",
            ),
            "Balanced accuracy": st.column_config.NumberColumn(
                format="percent",
                help="Average of the classifier's correct-leak rate and correct-normal rate; it gives both classes equal weight.",
            ),
            "TP leaks caught": st.column_config.NumberColumn(
                help="True positives: leak cases correctly flagged as leaks."
            ),
            "FN leaks missed": st.column_config.NumberColumn(
                help="False negatives: actual leak cases incorrectly left unflagged."
            ),
            "FP false alarms": st.column_config.NumberColumn(
                help="False positives: normal cases incorrectly flagged as leaks."
            ),
            "TN normal cleared": st.column_config.NumberColumn(
                help="True negatives: normal cases correctly left unflagged."
            ),
        },
    )
    with st.expander(
        "Development cross-validation and in-sample results",
        icon=":material/info:",
    ):
        st.caption(
            "Cross-validation repeatedly trains on part of the development set and checks held-aside "
            "development cases to choose a threshold. In-sample scores reuse training cases and are "
            "optimistic diagnostics; the held-out test table remains the main result."
        )
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
                "Variant": st.column_config.TextColumn(
                    help="Training approach used for this version of the leak classifier."
                ),
                "Threshold": st.column_config.NumberColumn(
                    format="%.3f",
                    help="Decision cutoff selected using held-aside development predictions."
                ),
                "Leak precision": st.column_config.NumberColumn(
                    format="percent",
                    help="Among development cases flagged as leaks, the fraction labeled as leaks."
                ),
                "Leak recall": st.column_config.NumberColumn(
                    format="percent",
                    help="Among development leaks, the fraction caught at this threshold."
                ),
                "Balanced accuracy": st.column_config.NumberColumn(
                    format="percent",
                    help="Average of the development leak-catch rate and normal-clearance rate."
                ),
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
            st.subheader(
                "In-sample training scores (optimistic diagnostic)",
                help=(
                    "Scores calculated on cases used to fit the classifier. They tend to look "
                    "better than performance on new cases, so use only as a training diagnostic."
                ),
            )
            st.dataframe(
                pd.DataFrame(in_sample_rows),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Variant": st.column_config.TextColumn(
                        help="Training approach used for this version of the leak classifier."
                    ),
                    "Leak precision": st.column_config.NumberColumn(
                        format="percent",
                        help="Among training cases flagged as leaks, the fraction labeled as leaks."
                    ),
                    "Leak recall": st.column_config.NumberColumn(
                        format="percent",
                        help="Among training leaks, the fraction caught."
                    ),
                    "Balanced accuracy": st.column_config.NumberColumn(
                        format="percent",
                        help="Average of training leak-catch rate and normal-clearance rate."
                    ),
                },
            )
        st.caption(
            "In-sample scores evaluate cases used for training. Use the held-out table as the main comparison.",
            help="The classifier has already seen these cases while fitting, so these scores can overstate performance on new feeds.",
        )


def render_about() -> None:
    st.title(
        "About this workbench",
        help="Product context, sensor-channel coverage, interpretation guidance, and current system scope.",
    )
    st.write(
        "LeakProbe compares a complete Net3 pressure and flow feed with stored normal-operation and candidate-leak patterns."
    )
    st.subheader(
        "Sensor coverage",
        help="The complete Net3 measurement layout required by the app and benchmark: 92 pressure channels and 117 flow channels.",
    )
    st.markdown(
        "- 92 pressure channels, one for every junction.\n"
        "- 117 flow channels, one for every pipe.\n"
        "- Every case and classifier benchmark is checked against this channel layout."
    )
    st.subheader(
        "How to read a result",
        help="Guidance for interpreting candidate matches, field checks, and classifier benchmark scores.",
    )
    st.markdown(
        "- The alert highlights the lowest-error candidate pattern; the fit score is not a probability.\n"
        "- Follow the normal field verification process before confirming a leak.\n"
        "- Benchmark precision and recall describe these stored cases; they do not establish field performance."
    )
    st.subheader(
        "Scope",
        help="The current boundaries of this workbench and the systems it does not connect to.",
    )
    st.info(
        "The bundled Net3 feed and labels are generated benchmark data. No utility telemetry, GIS, work orders, "
        "controls, crew dispatch, or excavation workflow is connected."
    )
