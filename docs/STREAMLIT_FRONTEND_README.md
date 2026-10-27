# Streamlit front end proposal

**Status: plan for review. No Streamlit application code has been added.**

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
- Label both as synthetic. Mark the high-signal results as deliberately easy and unsuitable as evidence of field performance.

### About and limitations

- Explain the synthetic Net3 network, sensors, six-hour window, scenario assumptions, and current data limits.
- Distinguish observed readings, simulated readings, predictions, and confirmed facts in both labels and charts.
- State that the prototype does not control pumps or valves, dispatch crews, or authorize excavation.

## Suggested structure

```text
streamlit_app.py                 Streamlit entry point and navigation
leakprobe/ui/data_access.py      Read-only dataset and report loading
leakprobe/ui/investigation.py    Investigation controls and result display
leakprobe/ui/benchmarks.py       Saved classifier benchmark comparisons
leakprobe/ui/about.py            Provenance, assumptions, and limitations
```

Use Streamlit's `st.Page` and `st.navigation` for the three pages; the entry point can provide a shared title and persistent simulation notice. Streamlit currently recommends this approach for flexible multipage apps. [Official multipage app guidance](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)

Call existing Python investigation functions from the UI rather than reimplementing their scoring. Keep the selected case, revealed synthetic readings, and remaining demo budget in per-session state. Do not cache a mutable investigation object across users. Cache read-only tables and JSON with `st.cache_data`; Streamlit describes it as the data cache and distinguishes it from shared resource caching. [Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) · [Caching overview](https://docs.streamlit.io/develop/concepts/architecture/caching)

## Implementation stages

1. **Foundation:** add a pinned Streamlit dependency and entry point; verify Python 3.12 local startup and included data loading.
2. **Investigation page:** connect the two-branch and Net3 modes to the existing deterministic tools; add charts, ranked fit table, uncertainty state, measurement action, and reset.
3. **Benchmark and About pages:** display saved reports and explain provenance, units, synthetic status, and limits.
4. **Optional LLM summary:** only after the offline interface works. Make it an explicit user action, use a provider key stored in deployment secrets, state that provider requests may incur charges, and never make a request on page load.
5. **Hosting:** assume Streamlit Community Cloud for the first hosted demo. Select the app entry point and Python version, install from the dependency file, and add any provider secret through the host's secrets settings. Never commit a secrets file. [Deploy to Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) · [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

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

## Approval assumption

This plan assumes Streamlit Community Cloud is the intended host. The first implementation would be an offline-first synthetic demo; the optional Nebius-backed summary would be a later, explicit feature.
