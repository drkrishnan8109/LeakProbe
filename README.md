# LeakProbe learning demo

A runnable Python project for a small two-branch example and a larger synthetic benchmark based on EPA's EPANET Example Network 3 (Net3). The default walkthrough uses NVIDIA Nemotron through Nebius Token Factory; the scripted path remains available offline.

**This is an educational subset of the PRD, not the complete LeakProbe product.** All observations, measurements, and operational notes are synthetic. No sensors, utility accounts, or physical equipment are connected.

## Quick start in VS Code

1. Extract `leakprobe-demo.zip`.
2. Install **Python 3.12** (3.11 is also intended to work) and VS Code's Microsoft Python extension. Python 3.13/3.14 are not supported by this pinned demo dependency set.
3. In VS Code, choose **File → Open Folder** and select the extracted `leakprobe-demo` folder itself.
4. Open **Terminal → New Terminal**. Install the dependencies, configure Nebius, and run the commands below for your operating system.
5. Select the virtual environment using **Python: Select Interpreter** in the command palette.

### macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-llm.txt
cp .env.example .env
# Add your Nebius API key to .env, then:
python run_demo.py
```

To run locally without sending data to a provider, use `python run_demo.py --scripted`.

### Windows PowerShell

Using the environment's executable directly avoids PowerShell activation-policy problems:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt
Copy-Item .env.example .env
# Add your Nebius API key to .env, then:
.\.venv\Scripts\python.exe run_demo.py
```

For the offline scripted walkthrough, add `--scripted`.

In the remaining commands, Windows users can replace `python` with `.\.venv\Scripts\python.exe` unless their environment is activated.

Live mode sends synthetic observations and tool results to Nebius and may incur charges. Scripted mode makes no inference API calls. `python run_demo.py` uses the two-branch case; add `--network net3` to use the larger benchmark after generating it.

If you use full Visual Studio rather than VS Code, install its Python workload, open this folder, select the same environment, and run `run_demo.py` as the startup file. The terminal commands remain the same. Only macOS/Python 3.12 execution was tested here; Windows/Linux instructions have not been executed.

## What happens when you run it

`python run_demo.py` sends the synthetic case and allowlisted tool definitions to Nemotron, which chooses the investigation steps. Python runs the hydraulic simulations, validates tool arguments, enforces the measurement budget, and returns the synthetic reading. If the model tries to finish after collecting a reading without comparing again, the runtime performs that comparison and asks the model to update its conclusion.

Use `python run_demo.py --scripted` for the reproducible two-branch sequence:

1. Build the network and simulate normal, leak A, and leak B scenarios.
2. Generate ten upstream observations with small reproducible noise.
3. Read the network and fictional maintenance notes.
4. Compare the three scenarios using upstream observations. A and B should be tied.
5. Recommend MA because it can distinguish A from B and fits the 20-minute budget.
6. Reveal one synthetic MA measurement from the fixture and consume 15 minutes.
7. Compare again. Branch A should fit the supplied fixture best.
8. Write the entire sequence to `outputs/traces/scripted_trace.json`.

The scripted sequence is not an LLM transcript. Both modes use the same two-branch investigation tools.

## Streamlit front end

Start the browser app locally from the repository root:

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app includes an investigation workbench, the latest saved LLM investigation, classifier benchmarks, and an About page. The LLM page reads `outputs/traces/llm_trace.json`; it makes no provider calls and requires no API key. All readings are synthetic. See [the Streamlit run and hosting guide](docs/STREAMLIT_FRONTEND_README.md).

## Generate the larger Net3 benchmark

WNTR's official Net3 example is included at `data/networks/Net3.inp` so generation works offline. Net3 contains 92 junctions, 117 pipes, 2 pumps, and 2 reservoirs. This is a public benchmark model, not a validated model of a particular city. WNTR documents reading EPANET input files and simulating Net3; see [WNTR's getting-started example](https://usepa.github.io/WNTR/getting_started.html), the [source network](https://github.com/USEPA/WNTR/blob/main/examples/networks/Net3.inp), and the [WNTR license](https://github.com/USEPA/WNTR/blob/main/LICENSE.md).

The checked-in Net3 datasets currently contain **500 cases**: 400 development cases (320 leak, 80 normal) and 100 held-out test cases (80 leak, 20 normal). Leak pipes are split between development and test, so test pipes are not among the development candidates. The current stored reference bank contains 24 leak profiles for each of 24 candidate pipes, plus 3 normal-operation profiles. A profile is one simulated scenario and parameter combination; it is not an observation case.

To generate a fresh 500-case benchmark and a larger 200-profile reference bank, run:

```bash
python generate_data.py --network net3 --cases 500 --train-fraction 0.8 --seed 2026 --patterns-per-scenario 200
```

Regenerating replaces the checked-in data. The rejection thresholds below are calibrated to the current stored cases and reference profiles; they do not automatically transfer to a newly generated bank. Re-evaluate and recalibrate before using new data.

Evaluate the held-out cases without making LLM calls:

```bash
python evaluate_net3.py --split test
```

To compare the same 500 labeled cases with pressure measured at every junction and flow measured in every pipe, create a paired full-observation dataset. This uses the existing case labels, train/test split, candidate-pipe split, and reference parameter samples, while creating new full-coverage observations and prediction profiles:

```bash
python generate_full_net3_dataset.py
python evaluate_net3.py --split test --data-dir data/net3_full_pipes_data
```

Use `--split all` to produce a descriptive report over all 500 cases. This combines development and held-out cases, so treat it as an overall dataset summary rather than a held-out performance estimate:

```bash
python evaluate_net3.py --split all --data-dir data/net3_full_pipes_data
```

The standard dataset records pressure at 12 junctions and flow in 8 pipes. The companion records pressure at all 92 junctions and flow in all 117 pipes at each time step. It reuses the original readings for the 20 existing sensors and adds readings for the newly covered locations. It has no optional measurement points because every junction is already observed. This tests a best-case instrumentation setup; it does not represent a real utility's sensor deployment. The two datasets use the same scenario labels, so their held-out results can be compared directly.

The generator simulates six hours at 15-minute intervals. Cases include normal operation and one leak, with varied pipe location, leak diameter, start and duration, overall demand, sensor noise, and sparse sensor dropouts. The 24 spatially distributed candidate pipes are divided into disjoint train and test sets, and parameter ranges also differ between splits. Candidate predictions search a coarse grid of leak and demand parameters. Truth labels and synthetic measurement fixtures are stored separately from observations; they are instructional files, not tamper-proof hidden data.

Run the scripted path on the first held-out test case:

```bash
python run_demo.py --scripted --network net3
```

Or ask Nemotron to investigate it:

```bash
python run_demo.py --network net3
```

Pass `--case case_020` to choose another generated case. Net3 tool scores compare pipes only within that case's train or test candidate set. The optional pressure-gauge planner uses pressure spread across the leading five candidates as a simple heuristic, not a calibrated information-gain method.

### Net3 rejection threshold and current results

The Net3 detector is a **physics-based reference-pattern matcher**, not a machine-learning model trained on the 400 development cases. The development cases were used to choose a rejection threshold. The detector ranks normal and candidate-leak fits by normalized RMSE, which is a fit score and **not a probability**. If a leak scenario ranks first but its fit score exceeds the threshold, the tool returns `uncertain` instead of a leak alarm. The evaluator counts `uncertain` as no leak alarm for binary metrics and also reports how many cases were rejected.

The two observation sets have different score scales, so they use different cutoffs: **5.9836** for sparse coverage and **64.2958** for full coverage. On the 100 held-out full-coverage cases, the threshold changed the confusion matrix (TP / FN / FP / TN) from **61 / 19 / 12 / 8** to **32 / 48 / 3 / 17**. Specificity rose from 40% to 85%, while leak recall fell from 76.2% to 40%; 38 cases were rejected as uncertain. Balanced accuracy moved from 58.1% to 62.5%. This is a more cautious alarm setting, not a general accuracy improvement.

For sparse coverage, the threshold changed the confusion matrix from **44 / 36 / 12 / 8** to **20 / 60 / 3 / 17**. Specificity rose from 40% to 85%, while recall fell from 55% to 25%; 33 cases were rejected. Across all 500 full-observation cases, the threshold produced 153 TP, 247 FN, 24 FP, and 76 TN, rejecting 292 cases. This combines development and test data, so it is descriptive only. Full before-and-after metrics and pipe-localization results are in [the comparison report](outputs/evaluations/net3_full_pipes_comparison.md).

### Experimental recall-led classifier benchmark

The optional benchmark in `leakprobe/smote_benchmark.py` builds one feature row per case from sensor time-series summaries and compares a baseline, class weighting, and SMOTE. It is separate from the physics-based detector and uses synthetic data only. SMOTE is applied within each training fold. The classifier's positive class is leak; the default threshold aims for at least **90% leak recall** on out-of-fold development predictions, choosing the threshold with the highest precision among eligible thresholds. The held-out test split is used only for final reporting.

Install the pinned optional dependencies from `requirements.txt`, then run:

```bash
python -m leakprobe.smote_benchmark
```

Set another recall target or output location with `--target-recall 0.95` or `--output PATH`. Features, per-case test predictions, and reports are written to `data/net3_smote_benchmark/` by default; source data under `data/net3/` is read-only for this workflow. This experiment does not establish field performance or an operational alert threshold.

To create a separate, intentionally high-signal classifier smoke-test dataset using the same 500 case IDs, labels, and pipe split, run:

```bash
python -m leakprobe.generate_high_signal_dataset
python -m leakprobe.smote_benchmark --source data/net3_high_signal --output data/net3_high_signal_benchmark
```

This variant gives leaks 28–35 mm openings lasting 4–4.5 hours and uses the same demand range in both splits. It is designed to make the synthetic leak signal easier to detect and to check that the classifier pipeline can learn a clear pattern. It is intentionally easier than the original benchmark and is **not representative of field conditions**. The original `data/net3/` files are not modified.

## Project layout

```text
leakprobe/                 Python package: simulator, tools, agent, benchmark, CLI logic
data/
  demo/                    Two-branch demo fixtures
  networks/                EPANET network model files
  net3/                    500-case sparse-observation benchmark
  net3_high_signal/        Separate 500-case, intentionally easy synthetic diagnostic
  net3_high_signal_benchmark/ Results for the high-signal classifier diagnostic
  net3_smote_benchmark/    Isolated recall-led classifier benchmark outputs
  net3_full_pipes_data/    Paired full-observation benchmark
docs/                      PRD, actual example results, environment notes
outputs/
  diagrams/                Workflow diagrams and their source files
  evaluations/             Metric reports
  presentation/            Presentation source
  traces/                  Example scripted and LLM investigation traces
  demo_video/              Demo-video project files
tests/                     Simulator, evaluator, tool, and agent tests
```

The short root scripts (`run_demo.py`, `agent.py`, `generate_data.py`, `generate_full_net3_dataset.py`, and `evaluate_net3.py`) preserve the established command line interface. Their implementation lives in the `leakprobe/` package. The main references are [the pitch brief](PITCH.md), [the PRD](docs/LeakProbe-PRD.md), [actual example results](docs/EXAMPLE_RESULTS.md), and [the full-observation evaluation report](outputs/evaluations/net3_full_pipes_comparison.md).

## The network and units

```text
R0: fixed supply head 42 m
 |
P0: 200 m long, 150 mm diameter — F01 measures flow here
 |
J1: P01 measures pressure here
 |\
 | \
PA  PB: each 300 m long, 100 mm diameter
 |   |
J2  J3: each requests 5 L/s
MA  MB: possible portable-gauge locations
```

All junctions have elevation 0 m. All pipes use Hazen–Williams roughness coefficient 130. Full requested household demand is delivered when pressure head is at least 20 m; WNTR's pressure-dependent demand model reduces it at lower pressures.

WNTR uses meters, seconds, and cubic meters/second. We convert flow to liters/second for CSV display. `pressure_m` is pressure **head** in meters of water, not bar or meters of pipe length. Schematic coordinates are not geographic coordinates.

The model runs from 02:00 to 02:45 in five-minute intervals, giving ten rows. A 16 mm circular leak opening starts halfway along PA or PB at 02:20. WNTR computes its discharge from pressure; we do not prescribe a 5.2 L/s leak.

Normal demand is constant, so normal predictions are flat. The leak is abrupt, so its predictions jump at 02:20. This intentionally replaces the earlier hand-written gradually increasing example with actual solver results. Actual predicted numbers differ from the previous illustrative 40/34/28 m values; this network was not calibrated to those invented readings.

## Generate predictions without the walkthrough

```bash
python generate_data.py
```

Or use the simulator from your own Python file:

```python
from leakprobe.simulator import simulate

normal = simulate('normal')
leak = simulate('leak_A', hole_diameter_mm=12)
print(leak)
leak.to_csv('my_12mm_leak.csv', index=False)
```

Supported scenario names are `normal`, `leak_A`, and `leak_B`. Hole diameter must be finite and in (0, 30] mm. Every simulation starts from a fresh network so changes cannot contaminate another scenario.

## How comparison and measurement selection work

The comparison tool aligns timestamps and compares all ten upstream readings with each prediction. Flow and pressure errors are each divided by an illustrative scale of 0.2 in their respective units. It then calculates root mean squared normalized error. Once collected, a branch measurement adds one more residual against the scenario's final pressure prediction.

**A lower score means a better fit among the three predefined scenarios. It is not a probability, confidence interval, or proof of a leak.** The scaling values are demonstration settings, not fitted sensor uncertainty. This small two-branch walkthrough has no rejection threshold. Net3 uses the dataset-specific rejection thresholds described above, but these cutoffs are not a calibrated posterior or a general model-mismatch detector.

The measurement planner compares the A-versus-B predicted pressures at MA and MB. Among feasible, unmeasured locations, it selects the largest pressure separation per minute. This is a simple heuristic, not the PRD's expected-information-gain algorithm.

MA takes 10 minutes to travel/setup plus 5 minutes to measure. MB takes 25 plus 5. The initial budget is 20 minutes. The tool enforces the budget even if the LLM requests MB. Repeated requests for a measurement already collected return that observation without charging twice.

The demo measurement at 03:00 reuses the final predicted hydraulic state plus a small offset. This assumes the network stays steady after 02:20. A real application needs predictions at the true collection time and actual measured data.

## Live Nemotron investigation through Nebius

Live mode requires a Nebius API key, an accessible tool-calling model, internet access, and sufficient account balance. ChatGPT Pro is not an API credential. Your reported Token Factory credits are not checked by this project. Use `--scripted` to run offline.

### 1. Install the optional adapter

```bash
python -m pip install -r requirements-llm.txt
```

The package named `openai` is used only as an API-compatible client. These requests go to the configured **Nebius** endpoint, not OpenAI.

### 2. Create the configuration file

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code and enter your key:

```dotenv
NEBIUS_API_KEY=your_actual_nebius_key
NEBIUS_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1/
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
```

The endpoint and model above follow Nebius's published cookbook. Confirm availability and the appropriate region in your own account. Do not share `.env`, put your key in a screenshot, or add it to version control.

### 3. Run the live investigation

```bash
python agent.py
```

The application sends the instruction and tool schemas to the model. The model may request:

```json
{"name":"compare_hypotheses","arguments":{}}
```

Python executes that function and sends back real simulator-based results. The model can then request `recommend_measurement`, `collect_demo_measurement` with `{"point":"MA"}`, and `compare_hypotheses` again. Tool choice is not forced, so actual behavior varies by model.

A final answer and the tool results are saved to `outputs/traces/llm_trace.json`. The trace stores tool calls/results and available usage counts; it does not capture private reasoning or API credentials. You can inspect exactly which evidence the model received.

**Live mode sends synthetic observations, operations records, and tool outputs to your configured provider and may incur charges.** It allows at most eight model requests, up to 2048 requested output tokens per response, and at most sixteen tool executions. There is no guaranteed monetary spending cap; provider reasoning-token accounting may vary. Requests time out after 60 seconds and are not automatically retried.

### What the LLM can and cannot do

It can read the provided evidence, notice that a flushing schedule was cancelled, compare supported scenarios, request a feasible demo measurement, and explain why its conclusion changes.

It cannot simulate flushing or sensor bias in this starter version. Those remain untested alternatives. The numeric scenario comparison does not automatically interpret the operations notes. That interpretation belongs to the LLM or the reader.

Tools use an allowlist and JSON-schema validation. The model cannot invoke shell commands, arbitrary file paths, or utility controls through this interface. Observation tools exclude hidden fixture readings until requested. The fixture is still present on disk for teaching, so this is not a tamper-proof blind benchmark.

The output text itself is not a formally verified report. Treat any unsupported numerical statement or overconfident final answer as an evaluation failure. Never use it to authorize excavation or field operations.

## Tests and verification

```bash
python -m unittest discover -s tests -v
```

The current suite has 17 tests covering normal flow balance, pressure symmetry, leak onset, input validation, upstream ambiguity, evidence updating, rejection behavior, time-budget enforcement, invalid tool requests, and provider-independent tool-call round trips with a fake client.

The local simulator and scripted flow were executed on Python 3.12/macOS. The agent loop was tested with a fake client, **not a paid live Nebius request**. Provider access, billing, and actual model tool-call behavior remain to be tested with your own account.

This is an easy same-model synthetic exercise: the truth fixture and the candidate predictions use the same solver and network. Successful identification is not evidence of robustness to model mismatch or field performance.

## Troubleshooting

- **`No module named wntr`:** select your `.venv` interpreter and rerun installation using that interpreter.
- **Python 3.13/3.14 install errors:** recreate the virtual environment with Python 3.12. Do not reuse a venv made with another version.
- **`No module named pkg_resources`:** reinstall `setuptools==80.9.0`. WNTR 1.3.2 uses this legacy API. A deprecation warning may still appear; this was present in successful tests.
- **Missing data:** run `python generate_data.py`. Sample data is already included in the ZIP.
- **401/403 from provider:** check API key and permissions. **404/model error:** check region, model ID, and catalog access. **429:** check quota/balance. Avoid repeated retries while troubleshooting.
- **Model produces no final answer:** check `status` in the JSON trace. An incomplete or budget-exhausted run is not a diagnosis.
- **Tool-calling rejected:** choose a provider model/endpoint that supports function tools; do not assume all models do.
- **Edited observations rejected:** this learning demo expects the original columns and ten timestamps. General CSV import and real telemetry validation are future work.

## Suggested next experiments

1. Inspect normal and leak CSVs side by side.
2. Change hole size in a separate simulation and observe the pressure changes.
3. Compare scripted and LLM investigations on identical inputs.
4. Add an independently generated observation scenario to expose model mismatch.
5. Add flushing as an explicit supported hydraulic scenario, then sensor bias as an observation model.
6. Replace the separation heuristic with a calibrated uncertainty model and expected information gain.

## Sources

- WNTR overview: https://usepa.github.io/WNTR/
- Hydraulic simulation: https://usepa.github.io/WNTR/hydraulics.html
- Pipe splitting: https://usepa.github.io/WNTR/apidoc/wntr.morph.link.split_pipe.html
- Junction leaks: https://usepa.github.io/WNTR/apidoc/wntr.network.elements.Junction.html
- Nebius Nemotron example: https://github.com/nebius/token-factory-cookbook/blob/main/models/nemotron/nemotron3-super-120B.md

Dependencies keep their respective licenses. No third-party dataset is redistributed; included fixtures are generated locally by this example.
