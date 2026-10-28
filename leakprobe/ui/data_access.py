"""Read-only cached access to bundled synthetic data and benchmark reports."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from leakprobe.paths import DATA, OUTPUTS


@st.cache_data(show_spinner=False)
def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_case_index(data_dir: str = str(DATA / "net3")) -> list[dict]:
    return read_json(str(Path(data_dir) / "cases.json"))


@st.cache_data(show_spinner=False)
def load_case_observations(case_id: str, data_dir: str = str(DATA / "net3")) -> pd.DataFrame:
    cases = load_case_index(data_dir)
    case = next((row for row in cases if row["case_id"] == case_id), None)
    if case is None:
        raise ValueError(f"Unknown case: {case_id}")
    return pd.read_csv(Path(data_dir) / case["observations_file"])


@st.cache_data(show_spinner=False)
def load_report(report_name: str) -> dict:
    report_paths = {
        "Original Net3": DATA / "net3_smote_benchmark" / "report.json",
        "High-signal diagnostic": DATA / "net3_high_signal_benchmark" / "report.json",
    }
    if report_name not in report_paths:
        raise ValueError("Unknown benchmark report.")
    return read_json(str(report_paths[report_name]))


@st.cache_data(show_spinner=False)
def _read_json_at_mtime(path: str, modified_ns: int) -> dict:
    """Cache a JSON artifact by path and modification time."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_latest_llm_trace() -> dict | None:
    """Read the saved demo trace and refresh the cache when a new run replaces it."""
    path = OUTPUTS / "traces" / "llm_trace.json"
    if not path.exists():
        return None
    return _read_json_at_mtime(str(path), path.stat().st_mtime_ns)
