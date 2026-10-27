# Implementation Plan: Streamlit front end

## Overview

Create an offline-first Streamlit interface over LeakProbe's existing synthetic investigation code. The UI will expose the guided investigation, saved classifier benchmark reports, and clear provenance/limitations. It will not add real-data integrations or operational controls.

## Architecture decisions

- Use Streamlit's `st.Page` and `st.navigation` multipage entry point.
- Keep numerical ranking in `leakprobe/net3_tools.py` and existing demo tools.
- Cache only read-only data; retain case selection and revealed fixture state per browser session.
- Read saved benchmark JSON/Markdown. Do not train the benchmark during page reruns.
- Make any LLM summary optional and user-triggered; the first version works without secrets or provider calls.
- Assume Streamlit Community Cloud for hosting.

## Tasks

### Phase 1: Foundation

- [x] Add pinned Streamlit dependency and app entry point.
- [x] Add shared navigation, page title, and visible simulated-data notice.
- [x] Add read-only loaders for Net3 metadata, observations, and benchmark reports.

**Checkpoint:** app launches locally under Python 3.12 without an API key; missing data produces a readable error.

### Phase 2: Investigation flow

- [x] Add two-branch demo and standard Net3 case selection.
- [x] Run existing deterministic comparison and display time series, ranked fits, uncertainty, units, and provenance.
- [x] Add synthetic measurement recommendation/reveal, time budget, re-comparison, and reset.
- [x] Keep case truth hidden in the investigation view.

**Checkpoint:** selected case ranking matches the existing Python interface; measurement updates and budget behavior match the existing tool.

### Phase 3: Benchmark and guidance

- [x] Display saved classifier results for original and high-signal datasets.
- [x] Show precision, recall, false alarms, class totals, and confusion matrices with the in-sample/test distinction.
- [x] Add About page explaining synthetic assumptions and excluded real-world workflows.
- [x] Add the end-user README with local run, pages, benchmark interpretation, and limitations.

**Checkpoint:** displayed metrics match saved reports and every result is labeled synthetic.

### Phase 4: Hosting and optional provider call

- [x] Package dependencies and choose Community Cloud Python version/entry point.
- [ ] Deploy a preview after completing Community Cloud account setup.
- [ ] Keep provider-backed summaries out of this first release.

**Checkpoint:** hosted app works without provider secrets; any optional provider call is opt-in.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Users read fit scores as probabilities | Show score meaning beside every ranking and in the README. |
| Shared state leaks between sessions | Keep mutable investigation state per session; cache only immutable data. |
| High-signal benchmark is mistaken for realistic validation | Label it as an intentionally easy diagnostic on every page where it appears. |
| LLM calls incur cost or disclose data | Keep the first version offline; require an explicit click and deployment secret for later use. |
| Hosted dependencies or reference data exceed platform limits | Measure install/startup and memory on a preview before release; load only the sparse Net3 fixture by default. |

## Open decision

- Community Cloud account and repository access must be available for deployment.
