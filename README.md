# LeakProbe learning demo

A runnable Python project for the two-branch water-network example. Start locally, inspect the CSVs, then optionally connect NVIDIA Nemotron through Nebius Token Factory.

**This is an educational subset of the PRD, not the complete LeakProbe product.** All observations, measurements, and operational notes are synthetic. No sensors, utility accounts, or physical equipment are connected.

## Quick start in VS Code

1. Extract `leakprobe-demo.zip`.
2. Install **Python 3.12** (3.11 is also intended to work) and VS Code's Microsoft Python extension. Python 3.13/3.14 are not supported by this pinned demo dependency set.
3. In VS Code, choose **File → Open Folder** and select the extracted `leakprobe-demo` folder itself.
4. Open **Terminal → New Terminal**. Run the commands below for your operating system.
5. Select the virtual environment using **Python: Select Interpreter** in the command palette.

### macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_demo.py
```

### Windows PowerShell

Using the environment's executable directly avoids PowerShell activation-policy problems:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_demo.py
```

In the remaining commands, Windows users can replace `python` with `.\.venv\Scripts\python.exe` unless their environment is activated.

The local demo requires internet only for installing packages. It makes no inference API calls. It regenerates the files in `data/`, so copy edited data elsewhere before rerunning it.

If you use full Visual Studio rather than VS Code, install its Python workload, open this folder, select the same environment, and run `run_demo.py` as the startup file. The terminal commands remain the same. Only macOS/Python 3.12 execution was tested here; Windows/Linux instructions have not been executed.

## What happens when you run it

`python run_demo.py` performs this scripted sequence:

1. Build the network and simulate normal, leak A, and leak B scenarios.
2. Generate ten upstream observations with small reproducible noise.
3. Read the network and fictional maintenance notes.
4. Compare the three scenarios using upstream observations. A and B should be tied.
5. Recommend MA because it can distinguish A from B and fits the 20-minute budget.
6. Reveal one synthetic MA measurement from the fixture and consume 15 minutes.
7. Compare again. Branch A should fit the supplied fixture best.
8. Write the entire sequence to `outputs/scripted_trace.json`.

This local sequence is explicitly scripted; it is not an LLM transcript. The optional agent decides its own sequence through the same tool interface.

## Files to read first

| File | Purpose |
|---|---|
| `simulator.py` | Defines the physical network and runs WNTR |
| `generate_data.py` | Generates reproducible prediction and observation fixtures |
| `tools.py` | Local tools, scenario comparison, measurement choice, validation |
| `run_demo.py` | Complete local walkthrough without an API key |
| `agent.py` | Optional Nemotron tool-calling loop through Nebius |
| `data/observations.csv` | Ten noisy readings from F01 and P01 only |
| `data/prediction_normal.csv` | Ten normal-operation predictions |
| `data/prediction_leak_A.csv` | Ten branch A leak predictions |
| `data/prediction_leak_B.csv` | Ten branch B leak predictions |
| `data/demo_measurements.json` | Synthetic measurement fixtures revealed by the collection tool |
| `data/operations.json` | Fictional flushing schedule and cancellation records |
| `outputs/scripted_trace.json` | Example local investigation trace |
| `EXAMPLE_RESULTS.md` | Actual output recorded during local testing |
| `.env.example` | API configuration template; contains no real key |
| `.vscode/launch.json` | VS Code debug configurations |
| `tests/` | Hydraulic behavior, tool boundaries, and mocked agent-loop tests |
| `docs/LeakProbe-PRD.md` | Broader product specification; most of it is future scope |

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
from simulator import simulate

normal = simulate('normal')
leak = simulate('leak_A', hole_diameter_mm=12)
print(leak)
leak.to_csv('my_12mm_leak.csv', index=False)
```

Supported scenario names are `normal`, `leak_A`, and `leak_B`. Hole diameter must be finite and in (0, 30] mm. Every simulation starts from a fresh network so changes cannot contaminate another scenario.

## How comparison and measurement selection work

The comparison tool aligns timestamps and compares all ten upstream readings with each prediction. Flow and pressure errors are each divided by an illustrative scale of 0.2 in their respective units. It then calculates root mean squared normalized error. Once collected, a branch measurement adds one more residual against the scenario's final pressure prediction.

**A lower score means a better fit among the three predefined scenarios. It is not a probability, confidence interval, or proof of a leak.** The scaling values are demonstration settings, not fitted sensor uncertainty. There is no parameter estimation, calibrated posterior, or out-of-distribution abstention implementation here.

The measurement planner compares the A-versus-B predicted pressures at MA and MB. Among feasible, unmeasured locations, it selects the largest pressure separation per minute. This is a simple heuristic, not the PRD's expected-information-gain algorithm.

MA takes 10 minutes to travel/setup plus 5 minutes to measure. MB takes 25 plus 5. The initial budget is 20 minutes. The tool enforces the budget even if the LLM requests MB. Repeated requests for a measurement already collected return that observation without charging twice.

The demo measurement at 03:00 reuses the final predicted hydraulic state plus a small offset. This assumes the network stays steady after 02:20. A real application needs predictions at the true collection time and actual measured data.

## Connect an LLM through Nebius

The local demo works first. Live mode additionally requires a Nebius API key, an accessible tool-calling model, internet access, and sufficient account balance. ChatGPT Pro is not an API credential. Your reported Token Factory credits are not checked by this project.

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

A final answer and the tool results are saved to `outputs/llm_trace.json`. The trace stores tool calls/results and available usage counts; it does not capture private reasoning or API credentials. You can inspect exactly which evidence the model received.

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

Tests cover normal flow balance, pressure symmetry, leak onset, input validation, upstream ambiguity, evidence updating, time-budget enforcement, invalid tool requests, and provider-independent tool-call round trips with a fake client.

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
