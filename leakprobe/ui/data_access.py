"""Read-only cached access to bundled synthetic data and benchmark reports."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from leakprobe.net3_tools import Net3Investigation
from leakprobe.paths import DATA, NET3_DATA, OUTPUTS

MONITORING_CASE_ID = "case_402"  # Held-out Pipe 247 leak used for the alternate map example.


@st.cache_data(show_spinner=False)
def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_case_index(data_dir: str = str(NET3_DATA)) -> list[dict]:
    return read_json(str(Path(data_dir) / "cases.json"))


@st.cache_data(show_spinner=False)
def load_monitoring_snapshot(case_id: str = MONITORING_CASE_ID) -> dict:
    """Load the configured feed, normal references, and automatic assessment."""
    session = Net3Investigation(case_id)
    return {
        "case_id": session.case_id,
        "split": session.split,
        "observations": session.observations,
        "comparison": session.compare_hypotheses(),
        "normal_profiles": session.hypotheses["normal"],
        "pressure_sensors": session.metadata["monitor_pressure_nodes"],
        "flow_sensors": session.metadata["flow_sensors"],
    }


@st.cache_data(show_spinner=False)
def load_network_layout() -> dict:
    """Return the bundled Net3 topology and element coordinates for the map."""
    import wntr

    network_path = DATA / "networks" / "Net3.inp"
    network = wntr.network.WaterNetworkModel(str(network_path))
    coordinates = {}
    for name, node in network.nodes():
        point = getattr(node, "coordinates", None)
        if point and len(point) >= 2:
            coordinates[name] = [float(point[0]), float(point[1])]

    pipes = []
    for name, pipe in network.pipes():
        start = coordinates.get(pipe.start_node_name)
        end = coordinates.get(pipe.end_node_name)
        if start and end:
            pipes.append({"id": name, "x": start[0], "y": start[1],
                          "x2": end[0], "y2": end[1]})

    pumps = []
    for name, pump in network.pumps():
        start = coordinates.get(pump.start_node_name)
        end = coordinates.get(pump.end_node_name)
        if start and end:
            pumps.append({"id": name, "x": start[0], "y": start[1],
                          "x2": end[0], "y2": end[1]})

    junctions = [{"id": name, "x": coordinates[name][0], "y": coordinates[name][1]}
                 for name in network.junction_name_list if name in coordinates]
    reservoirs = [{"id": name, "x": coordinates[name][0], "y": coordinates[name][1]}
                  for name in network.reservoir_name_list if name in coordinates]
    return {"pipes": pipes, "pumps": pumps, "junctions": junctions,
            "reservoirs": reservoirs}


@st.cache_data(show_spinner=False)
def load_outcome_records() -> list[dict]:
    """Read held-out ground-truth outcomes for after-action review."""
    labels = read_json(str(NET3_DATA / "truth_labels.json"))
    return [
        {
            "Window": case["case_id"],
            "Verified outcome": ("Leak confirmed" if labels[case["case_id"]]["incident"] == "single_leak"
                                 else "Normal operation confirmed"),
            "Confirmed pipe": labels[case["case_id"]]["leak_pipe"] or "—",
        }
        for case in load_case_index()
        if case["split"] == "test"
    ]


@st.cache_data(show_spinner=False)
def load_report(report_name: str) -> dict:
    report_paths = {
        "High-signal Net3": DATA / "net3_full_high_signal_benchmark" / "report.json",
    }
    if report_name not in report_paths:
        raise ValueError("Unknown benchmark report.")
    return read_json(str(report_paths[report_name]))


@st.cache_data(show_spinner=False)
def _read_json_at_mtime(path: str, modified_ns: int) -> dict:
    """Cache a JSON artifact by path and modification time."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_llm_trace_history() -> list[dict]:
    """Read saved full-channel LLM runs, newest first, without caching the directory scan."""
    saved_runs = []
    for path in (OUTPUTS / "traces").glob("net3_full_high_signal_*_llm_trace.json"):
        modified_ns = path.stat().st_mtime_ns
        run = _read_json_at_mtime(str(path), modified_ns)
        saved_at = run.get("saved_at_utc")
        timestamp = datetime.fromisoformat(saved_at) if saved_at else datetime.fromtimestamp(
            modified_ns / 1_000_000_000, tz=timezone.utc
        )
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        saved_runs.append((timestamp, {
            **run,
            "trace_file": path.name,
            "saved_at_utc": timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        }))
    return [run for _, run in sorted(saved_runs, key=lambda item: item[0], reverse=True)]
