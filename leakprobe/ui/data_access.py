"""Read-only cached access to bundled synthetic data and benchmark reports."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from leakprobe.coverage import validate_full_channel_coverage
from leakprobe.paths import DATA, NET3_DATA, OUTPUTS


@st.cache_data(show_spinner=False)
def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_case_index(data_dir: str = str(NET3_DATA)) -> list[dict]:
    return read_json(str(Path(data_dir) / "cases.json"))


@st.cache_data(show_spinner=False)
def load_case_observations(case_id: str, data_dir: str = str(NET3_DATA)) -> pd.DataFrame:
    cases = load_case_index(data_dir)
    case = next((row for row in cases if row["case_id"] == case_id), None)
    if case is None:
        raise ValueError(f"Unknown case: {case_id}")
    observations = pd.read_csv(Path(data_dir) / case["observations_file"])
    metadata = read_json(str(Path(data_dir) / "metadata.json"))
    validate_full_channel_coverage(metadata, observations.columns, f"{case_id} observations")
    return observations


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


def load_latest_llm_trace() -> dict | None:
    """Read the newest saved full-channel Net3 investigation trace."""
    traces = list((OUTPUTS / "traces").glob("net3_full_high_signal_*_llm_trace.json"))
    if not traces:
        return None
    path = max(traces, key=lambda candidate: candidate.stat().st_mtime_ns)
    return _read_json_at_mtime(str(path), path.stat().st_mtime_ns)
