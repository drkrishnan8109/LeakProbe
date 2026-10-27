"""Generate a high signal synthetic Net3 leak-detection dataset.

This keeps the source dataset's 500 case IDs, labels, split, and pipe assignments,
but uses large, long leaks and matching operating ranges across train and test.
It is a classifier smoke-test dataset, not a representative benchmark.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .net3_benchmark import PRESSURE_SIGMA_M, simulate_net3
from .paths import DATA

SOURCE = DATA / "net3"
OUT = DATA / "net3_high_signal"
LEAK_DIAMETER_MM = (28.0, 35.0)
LEAK_START_HOUR = (0.5, 1.5)
LEAK_DURATION_HOURS = (4.0, 5.0)
DEMAND_SCALE = (0.85, 1.15)
FLOW_NOISE_FRACTION = 0.02
FLOW_NOISE_FLOOR_LPS = 0.15
MISSING_FRACTION = 0.01


def generate(source=SOURCE, output=OUT, seed=2026):
    source = Path(source)
    output = Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Output directory must be separate from the original dataset.")

    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    cases = json.loads((source / "cases.json").read_text(encoding="utf-8"))
    original_labels = json.loads((source / "truth_labels.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)

    pressure_columns = [f"pressure_{node}_m" for node in metadata["monitor_pressure_nodes"]]
    flow_columns = [f"flow_{pipe}_lps" for pipe in metadata["flow_sensors"]]
    observed_columns = [*pressure_columns, *flow_columns]
    rng = np.random.default_rng(seed)
    labels = {}

    for case in cases:
        case_id = case["case_id"]
        truth_label = original_labels[case_id]
        demand_scale = float(rng.uniform(*DEMAND_SCALE))
        if truth_label["incident"] == "normal":
            diameter = start = duration = None
            truth = simulate_net3(demand_scale=demand_scale)
        else:
            diameter = float(rng.uniform(*LEAK_DIAMETER_MM))
            start = float(rng.uniform(*LEAK_START_HOUR))
            duration = float(rng.uniform(*LEAK_DURATION_HOURS))
            truth = simulate_net3(
                leak_pipe=truth_label["leak_pipe"],
                leak_diameter_mm=diameter,
                start_hour=start,
                leak_duration_hours=duration,
                demand_scale=demand_scale,
            )

        observed = truth[["timestamp_utc", *observed_columns]].copy()
        for column in pressure_columns:
            observed[column] += rng.normal(0, PRESSURE_SIGMA_M, len(observed))
        for column in flow_columns:
            sigma = max(FLOW_NOISE_FLOOR_LPS,
                        float(truth[column].abs().median()) * FLOW_NOISE_FRACTION)
            observed[column] += rng.normal(0, sigma, len(observed))
        missing = rng.random(observed[observed_columns].shape) < MISSING_FRACTION
        observed.loc[:, observed_columns] = observed[observed_columns].mask(missing)
        observed.to_csv(output / case["observations_file"], index=False)

        labels[case_id] = {
            "split": truth_label["split"],
            "incident": truth_label["incident"],
            "leak_pipe": truth_label["leak_pipe"],
            "leak_diameter_mm": round(diameter, 3) if diameter is not None else None,
            "start_hour": round(start, 3) if start is not None else None,
            "leak_duration_hours": round(duration, 3) if duration is not None else None,
            "demand_scale": round(demand_scale, 4),
        }

    (output / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    (output / "truth_labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    high_signal_metadata = {
        "dataset_variant": "intentionally high-signal synthetic classifier diagnostic",
        "source_dataset": str(source.relative_to(DATA) if source.is_relative_to(DATA) else source),
        "network": metadata["network"],
        "case_counts": metadata["case_counts"],
        "candidate_pipes_by_split": metadata["candidate_pipes_by_split"],
        "monitor_pressure_nodes": metadata["monitor_pressure_nodes"],
        "flow_sensors": metadata["flow_sensors"],
        "duration_hours": metadata["duration_hours"],
        "timestep_minutes": metadata["timestep_minutes"],
        "pressure_noise_sigma_m": PRESSURE_SIGMA_M,
        "flow_noise_sigma": "max(0.15 L/s, 2% of median absolute flow)",
        "telemetry_missing_fraction": MISSING_FRACTION,
        "generation_seed": seed,
        "parameters": {
            "leak_diameter_mm": list(LEAK_DIAMETER_MM),
            "leak_start_hour": list(LEAK_START_HOUR),
            "leak_duration_hours": list(LEAK_DURATION_HOURS),
            "demand_scale_for_both_splits": list(DEMAND_SCALE),
        },
        "limitations": (
            "Leaks are intentionally large and long, and train/test operating ranges are aligned. "
            "Use this only to smoke-test the classifier pipeline."
        ),
    }
    (output / "metadata.json").write_text(
        json.dumps(high_signal_metadata, indent=2), encoding="utf-8"
    )
    counts = {
        split: {label: sum(row["split"] == split and row["incident"] == label
                           for row in labels.values())
                for label in ("normal", "single_leak")}
        for split in ("train", "test")
    }
    print(f"Generated {len(cases)} high-signal cases at {output}")
    print(f"Split counts: {json.dumps(counts, sort_keys=True)}")
    print("Original Net3 dataset was read only and remains unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    generate(source=args.source, output=args.output, seed=args.seed)
