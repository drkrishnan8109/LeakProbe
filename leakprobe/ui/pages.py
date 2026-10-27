"""Streamlit pages for case investigation, benchmark review, and project context."""
import pandas as pd
import streamlit as st

from leakprobe.net3_tools import Net3Investigation
from leakprobe.tools import Investigation
from leakprobe.ui.data_access import load_case_index, load_case_observations, load_report


def _show_demo_result(result: dict) -> None:
    ranking = result["ranking"]
    if not ranking:
        st.warning("No scenario could be compared with the available readings.")
        return
    winner = ranking[0]
    st.info(
        f"**Top-ranked scenario: {winner['scenario']}** · "
        f"Fit score {winner['normalized_rmse']:.3f}. Lower scores fit these readings better. "
        "This score is not a probability or field confirmation."
    )
    table = pd.DataFrame([
        {"Scenario": row["scenario"], "Normalized fit score": row["normalized_rmse"]}
        for row in ranking
    ])
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={"Normalized fit score": st.column_config.NumberColumn(format="%.3f")})


def _render_two_branch_demo() -> None:
    st.subheader("Two-branch example")
    st.caption("A small, fixed simulation with two candidate leak branches and stored synthetic readings.")
    if "demo_revealed" not in st.session_state:
        st.session_state.demo_revealed = {}
        st.session_state.demo_remaining = 20

    session = Investigation()
    session.revealed = dict(st.session_state.demo_revealed)
    session.remaining_minutes = st.session_state.demo_remaining
    col1, col2 = st.columns(2)
    col1.metric("Synthetic investigation time left", f"{session.remaining_minutes} min")
    col2.metric("Extra readings revealed", len(session.revealed))
    last_reading = st.session_state.pop("demo_last_reading", None)
    if last_reading:
        st.success(f"Synthetic pressure at {last_reading['point']}: {last_reading['pressure_head_m']:.2f} m. Comparison updated.")

    observations = session.observations.copy()
    observations["timestamp_utc"] = pd.to_datetime(observations["timestamp_utc"], utc=True)
    pressure, flow = st.columns(2)
    with pressure:
        st.markdown("**Upstream pressure · m head**")
        st.line_chart(observations.set_index("timestamp_utc")[["P01_pressure_m"]], height=250)
    with flow:
        st.markdown("**Upstream flow · L/s**")
        st.line_chart(observations.set_index("timestamp_utc")[["F01_flow_lps"]], height=250)

    if st.button("Compare the three scenarios", type="primary", key="demo_compare"):
        st.session_state.demo_result = session.compare_hypotheses()
    result = st.session_state.get("demo_result")
    if result:
        _show_demo_result(result)

    if st.button("Recommend a measurement", key="demo_recommend"):
        st.session_state.demo_recommendation = session.recommend_measurement()
    plan = st.session_state.get("demo_recommendation")
    if plan:
        if plan["recommended"]:
            recommended = next(row for row in plan["points"] if row["point"] == plan["recommended"])
            st.info(
                f"Suggested synthetic reading: **{recommended['point']}**, "
                f"{recommended['minutes']} minutes. {plan['method']}."
            )
            if st.button("Reveal this synthetic reading", key="demo_reveal"):
                reading = session.collect_demo_measurement(recommended["point"])
                st.session_state.demo_revealed = dict(session.revealed)
                st.session_state.demo_remaining = session.remaining_minutes
                st.session_state.demo_result = session.compare_hypotheses()
                st.session_state.demo_last_reading = {
                    "point": recommended["point"],
                    "pressure_head_m": reading["pressure_head_m"],
                }
                st.rerun()
        else:
            st.caption("No additional point fits the remaining demonstration budget.")

    if st.session_state.demo_revealed:
        st.caption("Revealed demo points: " + ", ".join(st.session_state.demo_revealed))
    if st.button("Reset two-branch example", key="demo_reset"):
        for key in ("demo_revealed", "demo_remaining", "demo_result", "demo_recommendation", "demo_last_reading"):
            st.session_state.pop(key, None)
        st.rerun()


def _render_net3_investigation() -> None:
    st.subheader("Net3 case investigation")
    st.caption("Choose one bundled case, inspect its sensor readings, and compare normal with candidate leak fits.")
    cases = load_case_index()
    case_by_id = {row["case_id"]: row for row in cases}
    case_ids = [row["case_id"] for row in cases]
    default_id = next((row["case_id"] for row in cases if row["split"] == "test"), case_ids[0])
    selected_case = st.selectbox(
        "Synthetic case",
        case_ids,
        index=case_ids.index(st.session_state.get("net3_case_id", default_id)),
        format_func=lambda case_id: f"{case_id} · {case_by_id[case_id]['split']} split",
        key="net3_case_picker",
    )
    if st.session_state.get("net3_case_id") != selected_case:
        st.session_state.net3_case_id = selected_case
        st.session_state.net3_revealed = {}
        st.session_state.net3_remaining = 20
        st.session_state.pop("net3_result", None)
        st.session_state.pop("net3_recommendation", None)

    try:
        session = Net3Investigation(selected_case)
        session.revealed = dict(st.session_state.get("net3_revealed", {}))
        session.remaining_minutes = st.session_state.get("net3_remaining", 20)
        observations = load_case_observations(selected_case)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load this synthetic case: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Split", case_by_id[selected_case]["split"])
    col2.metric("Candidate pipes", len(session.metadata["candidate_pipes_by_split"][session.split]))
    col3.metric("Demo time left", f"{session.remaining_minutes} min")
    last_reading = st.session_state.pop("net3_last_reading", None)
    if last_reading:
        st.success(f"Stored synthetic pressure at {last_reading['point']}: {last_reading['pressure_head_m']:.2f} m. Comparison updated.")

    observations["timestamp_utc"] = pd.to_datetime(observations["timestamp_utc"], utc=True)
    pressure_cols = [column for column in observations if column.startswith("pressure_")]
    flow_cols = [column for column in observations if column.startswith("flow_")]
    left, right = st.columns(2)
    with left:
        pressure_selected = st.multiselect(
            "Pressure sensors · m head", pressure_cols,
            default=pressure_cols[:3], key=f"pressure_{selected_case}"
        )
        if pressure_selected:
            st.line_chart(observations.set_index("timestamp_utc")[pressure_selected], height=300)
    with right:
        flow_selected = st.multiselect(
            "Flow sensors · L/s", flow_cols,
            default=flow_cols[:3], key=f"flow_{selected_case}"
        )
        if flow_selected:
            st.line_chart(observations.set_index("timestamp_utc")[flow_selected], height=300)

    st.caption("Readings are synthetic and may include missing values. The case truth is not shown in this investigation view.")
    if st.button("Compare sensor readings", type="primary", key=f"net3_compare_{selected_case}"):
        st.session_state.net3_result = session.compare_hypotheses()
    result = st.session_state.get("net3_result")
    if result:
        decision = result["decision"]
        prediction = decision["prediction"]
        fit = decision.get("best_fit_score")
        if prediction == "leak":
            st.warning(f"Leak scenario ranks first. Best fit score: {fit:.3f}. This is a synthetic model match, not confirmation.")
        elif prediction == "normal":
            st.info(f"Normal-operation scenario ranks first. Best fit score: {fit:.3f}. Review the other fits and assumptions.")
        else:
            st.warning(f"The result is uncertain. {decision.get('reason', 'Review the available evidence.')}")

        ranking = pd.DataFrame([
            {"Scenario": row["scenario"], "Pipe": row["leak_pipe"] or "—",
             "Fit score": row["normalized_rmse"]}
            for row in result["ranking"]
        ])
        st.markdown("**Candidate ranking**")
        st.dataframe(ranking, hide_index=True, use_container_width=True,
                     column_config={"Fit score": st.column_config.NumberColumn(format="%.3f")})
        st.caption(result["score_meaning"])

    if st.button("Recommend a pressure point", key=f"net3_recommend_{selected_case}"):
        st.session_state.net3_recommendation = session.recommend_measurement()
    plan = st.session_state.get("net3_recommendation")
    if plan:
        if plan["recommended"]:
            point = plan["recommended"]
            option = next(row for row in plan["points"] if row["point"] == point)
            st.info(
                f"Suggested point: **{point}** · predicted pressure spread "
                f"{option['pressure_spread_m']:.2f} m across leading fits · "
                f"{option['minutes']} minutes. {plan['method']}"
            )
            if st.button("Reveal the stored synthetic reading", key=f"net3_reveal_{selected_case}"):
                reading = session.collect_demo_measurement(point)
                st.session_state.net3_revealed = dict(session.revealed)
                st.session_state.net3_remaining = session.remaining_minutes
                st.session_state.net3_result = session.compare_hypotheses()
                st.session_state.net3_last_reading = {
                    "point": point,
                    "pressure_head_m": reading["pressure_head_m"],
                }
                st.rerun()
        else:
            st.caption("No unmeasured pressure point fits the remaining demonstration budget.")
    revealed = st.session_state.get("net3_revealed", {})
    if revealed:
        st.caption("Synthetic readings revealed: " + ", ".join(revealed))
    if st.button("Reset this case", key=f"net3_reset_{selected_case}"):
        for key in ("net3_result", "net3_recommendation", "net3_revealed", "net3_last_reading"):
            st.session_state.pop(key, None)
        st.session_state.net3_remaining = 20
        st.rerun()


def render_investigation() -> None:
    st.title("Investigate a synthetic case")
    st.write("Compare pressure and flow evidence with normal and leak scenarios, then review a possible next measurement.")
    mode = st.radio(
        "Choose an example",
        ["Net3 network", "Two-branch walkthrough"],
        horizontal=True,
        key="investigation_mode",
    )
    if mode == "Net3 network":
        _render_net3_investigation()
    else:
        _render_two_branch_demo()


def render_benchmarks() -> None:
    st.title("Classifier benchmarks")
    st.write("Compare the saved baseline, class-weighted, and SMOTE results on synthetic cases.")
    report_name = st.selectbox("Dataset", ["Original Net3", "High-signal diagnostic"])
    try:
        report = load_report(report_name)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load the saved benchmark report: {exc}")
        return

    if report_name == "High-signal diagnostic":
        st.warning("This dataset uses intentionally large, long leaks to smoke-test the classifier. It is not field-performance evidence.")
    else:
        st.info("This is the original synthetic Net3 classifier benchmark. The test set has 80 leak and 20 normal cases.")

    st.caption(
        f"Positive class: leak · Development threshold target: "
        f"{report['target_leak_recall']:.0%} recall · "
        f"Test cases: {report['test_counts']['leak']} leaks, {report['test_counts']['normal']} normal"
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
        scores,
        hide_index=True,
        use_container_width=True,
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
            st.dataframe(
                pd.DataFrame(in_sample_rows), hide_index=True, use_container_width=True,
                column_config={
                    "Leak precision": st.column_config.NumberColumn(format="percent"),
                    "Leak recall": st.column_config.NumberColumn(format="percent"),
                    "Balanced accuracy": st.column_config.NumberColumn(format="percent"),
                },
            )
        st.caption("In-sample scores evaluate the model on cases it trained on. Use the held-out test table as the main comparison.")


def render_about() -> None:
    st.title("About this workbench")
    st.write(
        "LeakProbe is a research demonstration for investigating simulated water-network cases. "
        "It compares hydraulic reference patterns and helps the user inspect a possible next measurement."
    )
    st.subheader("What is included")
    st.markdown(
        "- A two-branch teaching example with stored synthetic readings.\n"
        "- The EPA Net3 example network with simulated pressure and flow observations.\n"
        "- A saved comparison of baseline, class-weighted, and SMOTE classifier experiments."
    )
    st.subheader("How to read a result")
    st.markdown(
        "- A fit score measures how closely a simulated scenario matches the supplied readings. It is not a probability.\n"
        "- A recommended pressure point is a demonstration heuristic. Its stored reading is synthetic, not a field measurement.\n"
        "- Precision and recall on these generated cases do not establish performance on a real utility network."
    )
    st.subheader("Scope")
    st.info(
        "No real telemetry, GIS, work-order system, pump or valve control, crew dispatch, or excavation workflow is connected. "
        "The app makes no field diagnosis."
    )
