# Streamlit front end

**Status: implemented locally. Community Cloud deployment is the remaining step.**

## Run locally

Use Python 3.12 from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app works without an API key and makes no external model call.

## Pages

- **Investigate:** switch between the two-branch walkthrough and the 500-case sparse Net3 dataset. Inspect pressure and flow charts, compare scenarios, get a measurement recommendation, and reveal a stored synthetic reading.
- **Benchmarks:** compare saved baseline, class-weighted, and SMOTE reports for the original and high-signal datasets.
- **About:** review the simulation assumptions and limits.

The high-signal data uses intentionally large, long leaks. It is an easy classifier diagnostic, not evidence of field performance.

## Purpose

Build a browser-based, simulation-only LeakProbe workbench around the investigation tools already in this repository. The front end should help a user inspect sensor evidence, compare normal and leak hypotheses, understand uncertainty, and see which synthetic measurement could help next. It should not present the current demo as a live utility-monitoring or field-confirmation system.

## Proposed first release

### Investigation

- Start with the existing two-branch walkthrough and the standard sparse Net3 cases.
- Let the user select a Net3 case and explicitly run the deterministic comparison.
- Show pressure and flow time series with units, missing readings, and data provenance.
- Show ranked candidate pipes and their normalized fit scores. Label scores as fit diagnostics, never probabilities.
- Show the result as leak candidate, normal candidate, or uncertain, with the reason and limitations visible.
- Offer the existing measurement recommendation. A separate button reveals the stored synthetic reading, consumes the demo time budget, and refreshes the comparison.
- Keep the case truth label out of the initial investigation view; an optional answer reveal can be considered for teaching mode.

### Benchmark view

- Read the saved benchmark reports rather than training models whenever the page reruns.
- Compare precision, recall, confusion matrices, and false alarms for the baseline, class-weighted, and SMOTE variants.
- Let the user view the original benchmark and the intentionally high-signal diagnostic side by side.
- Label both as synthetic.

### About and limitations

- Explain the synthetic Net3 network, sensors, six-hour window, scenario assumptions, and current data limits.
- Distinguish observed readings, simulated readings, predictions, and confirmed facts in both labels and charts.
- State that the prototype does not control pumps or valves, dispatch crews, or authorize excavation.

## App structure

```text
streamlit_app.py                 Streamlit entry point and navigation
leakprobe/ui/data_access.py      Cached read-only dataset and report loading
leakprobe/ui/pages.py            Investigation, benchmark, and About pages
.streamlit/config.toml           App theme
```

Use Streamlit's `st.Page` and `st.navigation` for the three pages; the entry point can provide a shared title and persistent simulation notice. Streamlit currently recommends this approach for flexible multipage apps. [Official multipage app guidance](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)

Call existing Python investigation functions from the UI rather than reimplementing their scoring. Keep the selected case, revealed synthetic readings, and remaining demo budget in per-session state. Do not cache a mutable investigation object across users. Cache read-only tables and JSON with `st.cache_data`; Streamlit describes it as the data cache and distinguishes it from shared resource caching. [Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) · [Caching overview](https://docs.streamlit.io/develop/concepts/architecture/caching)

## Hosting

The intended host is Streamlit Community Cloud. Deploy repository `drkrishnan8109/LeakProbe`, branch `feature/net3-synthetic-benchmark`, entry point `streamlit_app.py`, and Python 3.12. Community Cloud installs dependencies from the root `requirements.txt`. [Deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) · [Dependency setup](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)

The first release does not include a provider-backed summary. If that feature is added later, make it opt-in and keep provider credentials in host secrets. [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

## Acceptance checks

- The app starts locally with the documented command and works without an API key.
- A selected Net3 case produces the same deterministic ranking and decision as the existing Python interface.
- Revealing a synthetic measurement updates the ranking and respects the existing time budget.
- Every displayed score has a label and explanation; none is presented as a probability or field confirmation.
- The benchmark page matches the saved JSON reports, including class counts and confusion matrices.
- Missing files or invalid case selections show a useful error instead of a blank page.
- Session data from one user cannot mutate another user's investigation.
- The optional LLM path is off until the user clicks it, and secrets remain outside source control.

## Explicitly outside the first release

Real utility data upload, SCADA/GIS/work-order integration, authentication, geographic maps, collaborative workspaces, operational alerts, and model calibration are not in the current demo. They need separate data, workflow, and security decisions before implementation.

## Deployment status

The code is ready for review. Community Cloud requires a signed-in account with access to the GitHub repository before it can provide a hosted URL.
