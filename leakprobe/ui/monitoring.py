"""Automatic employee monitoring dashboard for the configured Net3 feed."""
import numpy as np
import pandas as pd
import streamlit as st

from leakprobe.ui.data_access import load_monitoring_snapshot, load_network_layout


def _channel_columns(observations: pd.DataFrame, prefix: str) -> list[str]:
    return [column for column in observations.columns if column.startswith(prefix)]


def _baseline_series(observations: pd.DataFrame, normal_profiles: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    pressure_columns = _channel_columns(observations, "pressure_")
    flow_columns = _channel_columns(observations, "flow_")
    pressure_nodes = [column.removeprefix("pressure_").removesuffix("_m")
                      for column in pressure_columns]
    flow_pipes = [column.removeprefix("flow_").removesuffix("_lps")
                  for column in flow_columns]

    current_pressure = observations[pressure_columns].to_numpy(dtype=float)
    current_flow = observations[flow_columns].to_numpy(dtype=float)
    reference_pressure = np.asarray([
        [profile["pressure"][node] for node in pressure_nodes]
        for profile in normal_profiles
    ], dtype=float)
    reference_flow = np.asarray([
        [profile["flow"][pipe] for pipe in flow_pipes]
        for profile in normal_profiles
    ], dtype=float)

    pressure_observed_median = np.nanmedian(current_pressure, axis=1)
    pressure_normal_median = np.nanmedian(
        np.nanmedian(reference_pressure, axis=1), axis=0
    )
    flow_observed_median = np.nanmedian(np.abs(current_flow), axis=1)
    flow_normal_median = np.nanmedian(
        np.nanmedian(np.abs(reference_flow), axis=1), axis=0
    )
    elapsed_hours = (
        pd.to_datetime(observations["timestamp_utc"], utc=True)
        - pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[0]
    ).dt.total_seconds() / 3600

    pressure_chart = pd.DataFrame({
        "Current feed": pressure_observed_median,
        "Normal reference": pressure_normal_median,
    }, index=elapsed_hours)
    pressure_chart.index.name = "Elapsed hour"
    flow_chart = pd.DataFrame({
        "Current feed": flow_observed_median,
        "Normal reference": flow_normal_median,
    }, index=elapsed_hours)
    flow_chart.index.name = "Elapsed hour"
    return pressure_chart, flow_chart


def _reference_deviations(
    observations: pd.DataFrame,
    normal_profiles: list[dict],
    channel_type: str,
) -> tuple[int, int, list[dict]]:
    prefix, suffix, group = {
        "pressure": ("pressure_", "_m", "pressure"),
        "flow": ("flow_", "_lps", "flow"),
    }[channel_type]
    columns = _channel_columns(observations, prefix)
    sensors = [column.removeprefix(prefix).removesuffix(suffix) for column in columns]
    references = np.asarray([
        [profile[group][sensor] for sensor in sensors]
        for profile in normal_profiles
    ], dtype=float)
    lower, upper = np.nanpercentile(references, [5, 95], axis=0)
    current = observations[columns].to_numpy(dtype=float).T
    outside = ((current < lower) | (current > upper)) & np.isfinite(current)
    outside_per_sensor = outside.sum(axis=1)
    affected = int(np.count_nonzero(outside_per_sensor))
    total_observations = int(outside.sum())
    rows = [
        {
            "Sensor group": "Pressure" if channel_type == "pressure" else "Flow",
            "Channel": sensors[index],
            "Readings outside reference": int(count),
        }
        for index, count in enumerate(outside_per_sensor)
        if count
    ]
    return affected, total_observations, rows


def _network_map_spec(layout: dict, candidate_pipe: str | None) -> dict:
    pipes = [row for row in layout["pipes"] if row["id"] != candidate_pipe]
    highlighted = [row for row in layout["pipes"] if row["id"] == candidate_pipe]
    encodings = {
        "x": {"field": "x", "type": "quantitative", "axis": None},
        "x2": {"field": "x2"},
        "y": {"field": "y", "type": "quantitative", "axis": None},
        "y2": {"field": "y2"},
    }
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": 390,
        "autosize": {"type": "fit", "contains": "padding"},
        "config": {"view": {"stroke": None}, "axis": {"grid": False}},
        "layer": [
            {"data": {"values": pipes},
             "mark": {"type": "rule", "color": "#9aa9b4", "strokeWidth": 1},
             "encoding": encodings},
            {"data": {"values": layout["pumps"]},
             "mark": {"type": "rule", "color": "#64748b", "strokeWidth": 2,
                      "strokeDash": [5, 3]},
             "encoding": encodings},
            {"data": {"values": highlighted},
             "mark": {"type": "rule", "color": "#c2410c", "strokeWidth": 4},
             "encoding": encodings},
            {"data": {"values": layout["junctions"]},
             "mark": {"type": "point", "shape": "circle", "filled": True,
                      "color": "#0f6b78", "size": 28},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative", "axis": None},
                 "y": {"field": "y", "type": "quantitative", "axis": None},
                 "tooltip": [{"field": "id", "title": "Pressure sensor junction"}],
             }},
            {"data": {"values": layout["reservoirs"]},
             "mark": {"type": "point", "shape": "square", "filled": True,
                      "color": "#334155", "size": 90},
             "encoding": {
                 "x": {"field": "x", "type": "quantitative", "axis": None},
                 "y": {"field": "y", "type": "quantitative", "axis": None},
                 "tooltip": [{"field": "id", "title": "Reservoir"}],
             }},
        ],
    }


def render_monitoring_dashboard() -> None:
    st.title("Network monitoring")
    st.write("The current full-channel feed is checked automatically against normal operation and candidate leak patterns.")
    try:
        with st.spinner("Checking the latest monitoring window…"):
            snapshot = load_monitoring_snapshot()
            layout = load_network_layout()
    except (OSError, ValueError, KeyError, ImportError) as exc:
        st.error(f"The monitoring feed could not be loaded: {exc}")
        return

    observations = snapshot["observations"]
    comparison = snapshot["comparison"]
    ranking = comparison["ranking"]
    decision = comparison["decision"]
    pressure_columns = _channel_columns(observations, "pressure_")
    flow_columns = _channel_columns(observations, "flow_")
    total_sensor_channels = len(pressure_columns) + len(flow_columns)
    missing_readings = int(observations[[*pressure_columns, *flow_columns]].isna().sum().sum())
    sample_count = len(observations)
    latest_time = pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[-1]
    window_hours = (latest_time - pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[0]).total_seconds() / 3600
    candidate_pipe = decision.get("best_scenario", "")
    candidate_pipe = candidate_pipe.removeprefix("leak_pipe:") if candidate_pipe != "normal" else None
    best_leak = next((row for row in ranking if row["scenario"] != "normal"), None)
    normal_fit = next((row for row in ranking if row["scenario"] == "normal"), None)

    pressure_affected, pressure_outside, pressure_rows = _reference_deviations(
        observations, snapshot["normal_profiles"], "pressure"
    )
    flow_affected, flow_outside, flow_rows = _reference_deviations(
        observations, snapshot["normal_profiles"], "flow"
    )

    metrics = st.columns(4)
    metrics[0].metric("Network status", decision["prediction"].replace("_", " ").title())
    metrics[1].metric("Best candidate", f"Pipe {candidate_pipe}" if candidate_pipe else "None")
    metrics[2].metric("Sensor channels", f"{total_sensor_channels} / 209")
    metrics[3].metric("Monitoring window", f"{window_hours:g} h · {sample_count} readings")
    st.caption(
        f"Latest reading: {latest_time.strftime('%d %b %Y %H:%M UTC')} · "
        f"{missing_readings:,} missing sensor values"
    )

    if decision["prediction"] == "leak":
        st.error(f"Leak alert — review candidate pipe {candidate_pipe}")
        st.write("The leak pattern for this pipe is the best fit across the complete pressure and flow feed.")
        st.info("Recommended next step: verify the indicated pipe through the normal field-check process. This dashboard does not create a work order or dispatch a crew.")
    elif decision["prediction"] == "normal":
        st.success("No leak alert — normal operation is the best-fitting pattern for this window.")
    else:
        st.warning("Review required — the current feed does not support a clear leak or normal result.")

    st.subheader("Readings compared with the normal baseline")
    pressure_chart, flow_chart = _baseline_series(observations, snapshot["normal_profiles"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Median network pressure · m**")
        st.line_chart(pressure_chart, height=245, y_label="Pressure head (m)")
    with right:
        st.markdown("**Median absolute pipe flow · L/s**")
        st.line_chart(flow_chart, height=245, y_label="Flow (L/s)")
    st.caption("The normal reference is the median of 24 stored normal-operation profiles. The charts summarize the network; the alert comparison uses all 92 pressure and 117 flow channels.")

    st.subheader("Network and sensor map")
    st.vega_lite_chart(None, _network_map_spec(layout, candidate_pipe), use_container_width=True)
    st.caption("Blue circles are the 92 pressure junctions. Pipe segments carry the 117 flow channels. The highlighted pipe is the top leak candidate; dashed segments are pumps.")

    st.subheader("Evidence for this monitoring window")
    evidence = st.columns(4)
    evidence[0].metric("Pressure channels outside reference", f"{pressure_affected} / 92")
    evidence[1].metric("Pressure readings outside", pressure_outside)
    evidence[2].metric("Flow channels outside reference", f"{flow_affected} / 117")
    evidence[3].metric("Flow readings outside", flow_outside)
    st.caption("Outside-reference counts describe readings beyond the 5th–95th percentile of normal profiles. They are evidence for review, not a calibrated alert probability.")

    deviation_rows = sorted(pressure_rows + flow_rows,
                            key=lambda row: row["Readings outside reference"], reverse=True)
    if deviation_rows:
        with st.expander("Channels with the most baseline departures"):
            st.dataframe(pd.DataFrame(deviation_rows[:10]), hide_index=True, use_container_width=True)
    if ranking:
        with st.expander("Scenario fit details"):
            fit_metrics = st.columns(2)
            fit_metrics[0].metric(
                "Best leak fit · lower is closer",
                f"{best_leak['normalized_rmse']:.3f}" if best_leak else "—",
            )
            fit_metrics[1].metric(
                "Normal-operation fit · lower is closer",
                f"{normal_fit['normalized_rmse']:.3f}" if normal_fit else "—",
            )
            details = [{
                "Rank": rank,
                "Scenario": row["scenario"].replace("leak_pipe:", "Pipe "),
                "Normalized fit error": row["normalized_rmse"],
            } for rank, row in enumerate(ranking[:6], start=1)]
            st.dataframe(pd.DataFrame(details), hide_index=True, use_container_width=True)
            st.caption(comparison["score_meaning"])
    with st.expander("Feed record details"):
        st.write({
            "Feed record": snapshot["case_id"],
            "Window start": pd.to_datetime(observations["timestamp_utc"], utc=True).iloc[0].strftime("%d %b %Y %H:%M UTC"),
            "Latest reading": latest_time.strftime("%d %b %Y %H:%M UTC"),
            "Pressure channels present": f"{len(pressure_columns)} / 92",
            "Flow channels present": f"{len(flow_columns)} / 117",
            "Missing individual readings": f"{missing_readings:,}",
        })
