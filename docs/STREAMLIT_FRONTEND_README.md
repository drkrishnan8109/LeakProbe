# Streamlit front end

**Status:** the full-channel workbench is implemented locally. Community Cloud deployment still requires a signed-in account with repository access.

## Run locally

Use Python 3.12 from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app starts without an API key and makes no external model call.

## Pages

- **Investigate:** select one of the 500 high-signal Net3 cases, inspect network-wide pressure and flow summaries, then run the deterministic comparison. All 92 pressure and 117 flow channels are used; there is no sensor selector or optional gauge step.
- **Latest LLM run:** review the newest saved full-channel Net3 trace and its tool comparison. The page reads a file and does not call the provider.
- **Benchmarks:** compare baseline, class-weighted, and SMOTE results from the full-channel high-signal dataset.
- **About:** review the channel coverage and result limitations.

The stored case outcomes are available in the dataset files but remain hidden on the investigation page. The benchmark uses deliberately large, long leaks and matched operating ranges, so its results describe this controlled dataset only.

## Data and scoring

The canonical source is `data/net3_full_high_signal/`. Every observation file must have 92 pressure columns, 117 flow columns, and the timestamp column. A missing value within one of those channels is allowed; a missing channel or smaller sensor set is rejected when loaded.

The Streamlit page calls `Net3Investigation.compare_hypotheses()` and displays the returned ranking. Fit scores are error measures, not probabilities. The classifier table reads the saved report from `data/net3_full_high_signal_benchmark/report.json`; it does not retrain on app page reruns.

## App structure

```text
streamlit_app.py                 Streamlit entry point and navigation
leakprobe/ui/data_access.py      Cached read-only case and report loading
leakprobe/ui/pages.py            Investigation, saved LLM, benchmark, and About pages
leakprobe/net3_tools.py          Full-channel scenario comparison
leakprobe/coverage.py             92/117 channel validation
```

Streamlit's `st.Page` and `st.navigation` provide the multipage navigation. Mutable case state is limited to the selected case and its comparison result; cached objects are read-only.

## Hosting

The intended host is Streamlit Community Cloud. Deploy repository `drkrishnan8109/LeakProbe`, branch `feature/net3-synthetic-benchmark`, entry point `streamlit_app.py`, and Python 3.12. Community Cloud installs dependencies from the root `requirements.txt`. See [deployment guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [dependency setup](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

The CLI can create a saved LLM trace using the optional Nebius adapter. The Streamlit page only displays that trace; it does not call Nebius. Keep provider credentials in host secrets or `.env`, never in the repository.

## Current limits

The app does not connect to utility telemetry, GIS, work orders, controls, crew dispatch, or excavation workflows. The high-signal cases are generated benchmark data. They are intentionally easier than routine operating conditions and cannot establish field precision or recall.

The requested employee alert dashboard is a separate UI change. Its workflow and screen plan should be reviewed before implementation.
