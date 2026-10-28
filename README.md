# LeakProbe

LeakProbe is a Streamlit workbench for comparing a water-network sensor feed with normal-operation and candidate-leak patterns. The repository uses one Net3 dataset: the **high-signal 500-case benchmark**, with pressure at all 92 junctions and flow in all 117 pipes.

The cases are generated from the EPA EPANET Example Network 3 model. They are useful for a controlled benchmark and do not establish performance on a utility network.

## Start the app

Use Python 3.12, create an environment, and install the pinned packages:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The investigation page lets you choose a case, inspect network-wide pressure and flow summaries, and compare the complete feed against normal and candidate-leak simulations. The benchmark page shows the baseline, class-weighted, and SMOTE classifier results. Opening the app does not call an LLM provider.

To run an offline investigation from the terminal:

```bash
python run_demo.py --scripted
```

To use the optional Nebius/Nemotron explanation, install `requirements-llm.txt`, configure `.env` from `.env.example`, and run:

```bash
python run_demo.py
```

The LLM receives the case observations and tool outputs. Provider requests can incur charges. ChatGPT Pro access is not an API credential.

## The only supported sensor layout

Every case must contain exactly:

- 92 pressure columns, one for every Net3 junction.
- 117 flow columns, one for every Net3 pipe.

Missing readings may occur within those columns. The channel definitions and columns must remain complete. The app, physics-based comparator, evaluator, high-signal generator, and classifier all reject a smaller or incomplete channel set.

The canonical dataset is `data/net3_full_high_signal/`. It contains 500 cases: 400 development cases (320 leaks and 80 normal) and 100 held-out cases (80 leaks and 20 normal). It also contains the per-case outcomes and a reference-pattern bank matched to its high-signal leak ranges.

## Evaluate and benchmark

Run the physics-based comparison on the held-out cases:

```bash
python evaluate_net3.py --split test
```

Run the recall-led classifier benchmark. SMOTE is applied only inside the training folds, and the alert threshold is selected using out-of-fold development predictions:

```bash
python -m leakprobe.smote_benchmark
```

Results and per-case predictions are written to `data/net3_full_high_signal_benchmark/`. The test split is reserved for final reporting. Use the held-out numbers to compare precision, recall, false alarms, and missed leaks.

The earlier sparse-channel reports and standard-range dataset are retired. Do not use them for app runs, comparisons, or new result claims.

## Regenerate the high-signal feed

The generator preserves the 500 case IDs, split, and pipe assignments, then regenerates full-channel observations and a matching reference bank:

```bash
python generate_data.py
```

The benchmark intentionally uses 28–35 mm leak openings lasting 4–4.5 hours. Leak and normal demand ranges are aligned across the development and test splits. This makes the detection task easier and is useful for comparing classifier behavior, but it can overstate performance relative to smaller or shorter leaks, unmodeled operating changes, or real sensor feeds. Re-run the classifier benchmark and physics-based evaluation after regenerating the data; saved metrics do not automatically transfer.

The included network file is `data/networks/Net3.inp`. Net3 has 92 junctions, 117 pipes, two pumps, and two reservoirs. WNTR uses meters, seconds, and cubic meters per second internally; saved pipe flow is in liters per second and pressure is in meters of water head.

## Reading the metrics

Leak is the positive class:

- **Precision**: of the cases flagged as leaks, how many are labeled leaks.
- **Recall**: of the leak cases, how many are flagged.
- **False alarm**: a normal case flagged as a leak.
- **Miss**: a leak case not flagged.

A high-recall operating point can catch more leaks while increasing false alarms. The 80/20 held-out class balance also means an always-leak classifier would have 100% recall, 80% precision, and 0% specificity; that would not be a useful detector. Review the confusion matrix and balanced accuracy alongside precision and recall.

The physics-based matcher ranks reference simulations by normalized fit error. The error is not a probability. Classifier scores and results on these generated cases are not field validation.

## Project layout

```text
leakprobe/                         Python implementation
data/net3_full_high_signal/        Sole active 500-case, 92/117-channel dataset
data/net3_full_high_signal_benchmark/ Classifier reports and per-case predictions
data/networks/Net3.inp             EPANET network model
docs/                              Product and Streamlit documentation
outputs/evaluations/               Current full-channel evaluation report
streamlit_app.py                   Streamlit entry point
```

See [PITCH.md](PITCH.md), [the product requirements](docs/LeakProbe-PRD.md), and [the Streamlit guide](docs/STREAMLIT_FRONTEND_README.md) for product scope and hosting notes.
