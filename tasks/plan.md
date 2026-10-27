# Implementation Plan: Streamlit front end

## Overview

Create an offline-first Streamlit interface over LeakProbe's existing synthetic investigation code. The UI will expose the guided investigation, saved classifier benchmark reports, and clear provenance/limitations. It will not add real-data integrations or operational controls.

## Architecture decisions

- Use Streamlit's `st.Page` and `st.navigation` multipage entry point.
- Keep numerical ranking in `leakprobe/net3_tools.py` and existing demo tools.
- Cache only read-only data; retain case selection and revealed fixture state per browser session.
- Read saved benchmark JSON/Markdown. Do not train the benchmark during page reruns.
- Make any LLM summary optional and user-triggered; the first version works without secrets or provider calls.
- Assume Streamlit Community Cloud for hosting, pending user approval.

## Tasks

### Phase 1: Foundation

- [ ] Add pinned Streamlit dependency and app entry point.
- [ ] Add shared navigation, page title, and visible simulated-data notice.
- [ ] Add read-only loaders for Net3 metadata, observations, and benchmark reports.

**Checkpoint:** app launches locally under Python 3.12 without an API key; missing data produces a readable error.

### Phase 2: Investigation flow

- [ ] Add two-branch demo and standard Net3 case selection.
- [ ] Run existing deterministic comparison and display time series, ranked fits, uncertainty, units, and provenance.
- [ ] Add synthetic measurement recommendation/reveal, time budget, re-comparison, and reset.
- [ ] Keep case truth hidden until an optional teaching-mode reveal.

**Checkpoint:** selected case ranking matches the existing Python interface; measurement updates and budget behavior match the existing tool.

### Phase 3: Benchmark and guidance

- [ ] Display saved classifier results for original and high-signal datasets.
- [ ] Show precision, recall, false alarms, class totals, and confusion matrices with the in-sample/test distinction.
- [ ] Add About page explaining synthetic assumptions and excluded real-world workflows.
- [ ] Add the end-user README with local run, pages, benchmark interpretation, and limitations.

**Checkpoint:** displayed metrics match saved reports and every result is labeled synthetic.

### Phase 4: Hosting and optional provider call

- [ ] Package dependencies and choose Community Cloud Python version/entry point.
- [ ] Deploy a reviewed preview after user approval.
- [ ] Consider an explicit LLM summary button with secrets-based configuration and a clear cost notice.

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

- Confirm Streamlit Community Cloud as the hosting target, or name another Streamlit host.
