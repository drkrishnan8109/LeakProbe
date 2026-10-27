"""Streamlit operator workflow for the LeakProbe synthetic Net3 benchmark."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from leakprobe.net3_tools import Net3Investigation


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "net3"

st.set_page_config(page_title="LeakProbe | Investigation workbench", page_icon="💧", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1440px;padding-top:1.3rem;padding-bottom:2rem}
.brand{font-size:.78rem;font-weight:800;letter-spacing:.16em;color:#167354}
.brand span{display:block;font-size:.58rem;font-weight:600;letter-spacing:.19em;color:#71847b;margin-top:.25rem}
.eyebrow{font-size:.68rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#237b5c}
.packet{border:1px solid #dce8df;border-radius:12px;background:#fff;padding:1rem 1.15rem}
.packet-label{color:#708179;font-size:.74rem}.packet-value{font-weight:700;font-size:1rem;color:#203b30}
.simulated{padding:.5rem .7rem;border-radius:7px;background:#fff6df;color:#7d6224;font-size:.77rem}
.small-muted{font-size:.78rem;color:#74847c}
div[data-testid="stMetric"]{background:#f4f8f5;border:1px solid #e2ebe5;padding:.75rem;border-radius:10px}
</style>
<div class="brand">LEAKPROBE<span>NETWORK INVESTIGATION WORKSPACE</span></div>
""", unsafe_allow_html=True)

st.title("Investigate a suspected network anomaly")
st.markdown('<div class="eyebrow">Technical analyst workspace · synthetic benchmark</div>', unsafe_allow_html=True)
st.write("Review the incoming evidence, compare hydraulic hypotheses, then decide whether a follow-up measurement is useful.")

if not (DATA / "metadata.json").exists():
    st.error("The Net3 benchmark is missing. Include data/net3 in the deployed repository.")
    st.stop()

cases = json.loads((DATA / "cases.json").read_text(encoding="utf-8"))
test_cases = [case["case_id"] for case in cases if case["split"] == "test"]
metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))

with st.sidebar:
    st.markdown("### Investigation packet")
    selected_case = st.selectbox("Case reference", test_cases, index=0)
    st.markdown('<div class="simulated">SIMULATED REPLAY · no live utility data</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**Network model**")
    st.caption(metadata["network"])
    st.markdown("**Evidence mode**")
    st.caption("Generated Net3 benchmark observations")
    st.markdown("**Analysis engine**")
    st.caption("Local deterministic hydraulic reference matcher")
    if st.button("Reset this investigation", use_container_width=True):
        st.session_state.analysis = None
        st.session_state.followup = None
        st.session_state.session = Net3Investigation(case_id=selected_case)
        st.rerun()

if st.session_state.get("case_ref") != selected_case:
    st.session_state.case_ref = selected_case
    st.session_state.analysis = None
    st.session_state.followup = None
    st.session_state.session = Net3Investigation(case_id=selected_case)

session = st.session_state.session
observation_rows = session.get_observations()["readings"]
observations = pd.DataFrame(observation_rows)
pressure_cols = [f"pressure_{node}_m" for node in metadata["monitor_pressure_nodes"]]
flow_cols = [f"flow_{pipe}_lps" for pipe in metadata["flow_sensors"]]
pressure_values = observations[pressure_cols]
flow_values = observations[flow_cols]
valid_count = int(observations[pressure_cols + flow_cols].notna().sum().sum())
available_count = int(observations[pressure_cols + flow_cols].size)
missing_count = available_count - valid_count

st.markdown("#### 1 · Review the incoming packet")
st.caption("A suspected anomaly has been queued for technical review. The benchmark supplies a fixed six-hour evidence window; it does not contain a real utility alert or operator notes.")
packet_cols = st.columns(4)
packet_items = [
    ("Case reference", selected_case),
    ("Evidence window", "6 hours · 15-minute samples"),
    ("Pressure / flow monitors", f"{len(pressure_cols)} / {len(flow_cols)}"),
    ("Readings available", f"{valid_count:,} / {available_count:,}"),
]
for col, (label, value) in zip(packet_cols, packet_items):
    with col:
        st.markdown(f'<div class="packet"><div class="packet-label">{label}</div><div class="packet-value">{value}</div></div>', unsafe_allow_html=True)
if missing_count:
    st.warning(f"{missing_count} sensor readings are missing in this packet. The matcher skips missing values.")
else:
    st.success("Packet check: all expected sensor readings are present.")

st.markdown("#### 2 · Inspect observed evidence")
tab_pressure, tab_flow, tab_network = st.tabs(["Pressure trends", "Flow trends", "Network & constraints"])
with tab_pressure:
    p_view = observations[["timestamp_utc", *pressure_cols]].copy().set_index("timestamp_utc")
    p_view.columns = [f"Junction {c.removeprefix('pressure_').removesuffix('_m')} · m" for c in pressure_cols]
    st.line_chart(p_view, height=310)
    st.caption("Observed pressure head in metres of water. Traces represent generated noisy sensor values.")
with tab_flow:
    f_view = observations[["timestamp_utc", *flow_cols]].copy().set_index("timestamp_utc")
    f_view.columns = [f"Pipe {c.removeprefix('flow_').removesuffix('_lps')} · L/s" for c in flow_cols]
    st.line_chart(f_view, height=310)
    st.caption("Observed flow in litres per second. Sensor dropouts remain missing rather than being filled in.")
with tab_network:
    n1, n2, n3 = st.columns(3)
    n1.metric("Junctions", metadata["junctions"])
    n2.metric("Pipes", metadata["pipes"])
    n3.metric("Measurement time budget", f"{session.remaining_minutes} min")
    st.markdown("**Candidate pipes in this held-out case**")
    st.write(" · ".join(metadata["candidate_pipes_by_split"][session.split]))
    st.markdown("**Available portable pressure-gauge points**")
    st.write(" · ".join(f"Junction {point}" for point in metadata["measurement_points"]))

st.divider()
st.markdown("#### 3 · Run the analysis")
st.caption("The analysis compares the observed time series with stored normal-operation and candidate-leak reference patterns.")
if st.session_state.analysis is None:
    if st.button("Run scenario comparison", type="primary", use_container_width=True):
        with st.spinner("Scoring candidate hydraulic patterns…"):
            st.session_state.analysis = session.compare_hypotheses()
        st.rerun()
else:
    result = st.session_state.followup or st.session_state.analysis
    decision = result["decision"]
    top = result["ranking"][0]
    prediction = decision["prediction"]
    assessment = ("Manual review · fit rejected" if prediction == "uncertain" else
                  "Normal operation ranks first" if prediction == "normal" else
                  f"Pipe {top['leak_pipe']} ranks first")
    st.markdown("##### Analysis result")
    m1, m2, m3 = st.columns(3)
    m1.metric("Current assessment", assessment)
    m2.metric("Best normalized RMSE", f"{top['normalized_rmse']:.2f}")
    gap = result["relative_fit_gap"]
    m3.metric("Gap to second-best fit", f"{gap:.1%}" if gap is not None else "—")
    if prediction == "uncertain":
        st.warning("The leading leak fit is too weak for an alarm under this benchmark's rejection threshold. Treat this as unresolved and review the model and evidence.")
    elif result["leading_scenarios_are_close"]:
        st.warning("Leading candidate fits are close. Current evidence does not clearly distinguish their pipe locations.")
    else:
        st.info("This is the best fit among the configured hypotheses. It is not a probability, a confirmed leak, or a field diagnosis.")
    st.caption(decision.get("reason", "Best-ranked hypothesis accepted."))
    ranking = pd.DataFrame([
        {"Rank": rank, "Scenario": "Normal operation" if row["scenario"] == "normal" else f"Leak candidate · pipe {row['leak_pipe']}",
         "Normalized RMSE ↓": row["normalized_rmse"]}
        for rank, row in enumerate(result["ranking"], start=1)
    ])
    st.dataframe(ranking.head(10), hide_index=True, use_container_width=True,
                 column_config={"Normalized RMSE ↓": st.column_config.NumberColumn(format="%.3f")})
    st.caption("Fit score only; lower is a closer match. Scores are not calibrated probabilities.")

    if st.session_state.followup is None:
        st.markdown("##### 4 · Review the next measurement")
        recommendation = session.recommend_measurement()
        point = recommendation["recommended"]
        if point:
            detail = next(row for row in recommendation["points"] if row["point"] == point)
            st.write(f"The simple planner selects **pressure at junction {point}**. Its predicted spread across the five leading pipe candidates is **{detail['pressure_spread_m']:.2f} m**. Collection takes **{detail['minutes']} minutes** from the **{session.remaining_minutes}-minute** budget.")
            st.caption("This ranks predicted pressure separation. It is not expected information gain, and the displayed follow-up value is a stored simulation fixture.")
            if st.button(f"Reveal simulated reading at junction {point}", type="primary"):
                session.collect_demo_measurement(point)
                st.session_state.followup = session.compare_hypotheses()
                st.rerun()
        else:
            st.warning("No feasible measurement remains within the time budget. Stop and review the investigation constraints.")
    else:
        st.markdown("##### 4 · Compare before and after the simulated result")
        before = st.session_state.analysis["ranking"][0]
        after = st.session_state.followup["ranking"][0]
        point = st.session_state.followup["measurements_used"][0]
        reading = session.revealed[point]
        st.info(f"Simulated reading: **{reading['pressure_head_m']:.2f} m** at junction **{point}** at **{reading['timestamp_utc']}**. This is not a field measurement. **{session.remaining_minutes} minutes** remain.")
        before_name = "Normal operation" if before["scenario"] == "normal" else f"Pipe {before['leak_pipe']}"
        after_name = "Normal operation" if after["scenario"] == "normal" else f"Pipe {after['leak_pipe']}"
        before_col, after_col = st.columns(2)
        before_col.metric("Before follow-up", before_name, f"RMSE {before['normalized_rmse']:.2f}")
        after_col.metric("After follow-up", after_name, f"RMSE {after['normalized_rmse']:.2f}")
        if st.session_state.followup["decision"]["prediction"] == "uncertain":
            st.warning("The updated fit remains uncertain. The workflow stops short of forcing a pipe-level conclusion.")
        st.caption("The benchmark provides a stored simulated result. A production workflow would enter an independently collected, quality-checked observation.")

st.divider()
st.caption("LeakProbe is an experimental decision-support prototype. All cases and readings shown here are synthetic; no utility systems are connected, and benchmark results do not establish field performance.")
