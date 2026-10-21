"""Build a full-instrumentation companion dataset paired to data/net3."""
import json

import numpy as np
import pandas as pd

from .net3_benchmark import (
    OUT as SPARSE_DATA,
    PRESSURE_SIGMA_M,
    _serialize_hypothesis,
    load_network,
    simulate_net3,
)
from .paths import ROOT, DATA

OUTPUT = DATA / "net3_full_pipes_data"


def observation_columns(network):
    """Return timestamp plus pressure at every junction and flow in every pipe."""
    return ["timestamp_utc"] + [f"pressure_{node}_m" for node in network.junction_name_list] + [
        f"flow_{pipe}_lps" for pipe in network.pipe_name_list
    ]


def generate_full_dataset():
    required = ["metadata.json", "cases.json", "truth_labels.json", "hypotheses.json"]
    missing = [name for name in required if not (SPARSE_DATA / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"The paired dataset is missing {', '.join(missing)}. "
            "Generate data/net3 first with python generate_data.py --network net3 --cases 500."
        )

    source_metadata = json.loads((SPARSE_DATA / "metadata.json").read_text(encoding="utf-8"))
    cases = json.loads((SPARSE_DATA / "cases.json").read_text(encoding="utf-8"))
    labels = json.loads((SPARSE_DATA / "truth_labels.json").read_text(encoding="utf-8"))
    source_hypotheses = json.loads((SPARSE_DATA / "hypotheses.json").read_text(encoding="utf-8"))

    network = load_network()
    all_pressures = list(network.junction_name_list)
    all_flows = list(network.pipe_name_list)
    columns = observation_columns(network)
    sensors = {
        "monitor_pressure_nodes": all_pressures,
        "measurement_points": [],
        "flow_sensors": all_flows,
        "candidate_pipes": source_metadata["candidate_pipes_by_split"],
    }
    pressure_columns = [f"pressure_{node}_m" for node in all_pressures]
    flow_columns = [f"flow_{pipe}_lps" for pipe in all_flows]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    rng_by_case = {
        row["case_id"]: np.random.default_rng(source_metadata["seed"] + int(row["case_id"][-3:]) * 1009)
        for row in cases
    }
    fixtures = {row["case_id"]: {} for row in cases}
    for row in cases:
        case_id = row["case_id"]
        label = labels[case_id]
        if label["incident"] == "normal":
            truth = simulate_net3(demand_scale=label["demand_scale"], sensors=sensors)
        else:
            truth = simulate_net3(
                label["leak_pipe"], label["leak_diameter_mm"], label["start_hour"],
                label["leak_duration_hours"], label["demand_scale"], sensors=sensors,
            )
        observed = truth[columns].copy()
        rng = rng_by_case[case_id]
        for column in pressure_columns:
            observed[column] += rng.normal(0, PRESSURE_SIGMA_M, len(observed))
        for column in flow_columns:
            sigma = max(0.15, float(truth[column].abs().median()) * 0.02)
            observed[column] += rng.normal(0, sigma, len(observed))
        missing = rng.random(observed[pressure_columns + flow_columns].shape) < 0.01
        observed.loc[:, pressure_columns + flow_columns] = observed[
            pressure_columns + flow_columns
        ].mask(missing)
        sparse_observed = pd.read_csv(SPARSE_DATA / row["observations_file"])
        # Keep every existing channel byte-for-byte comparable; only newly
        # introduced sensors receive fresh, independent noise and dropouts.
        for column in sparse_observed.columns:
            observed[column] = sparse_observed[column]
        observed.to_csv(OUTPUT / row["observations_file"], index=False)

    # Use precisely the sparse dataset's parameter samples, but simulate and
    # retain each reference profile across all pressure and pipe-flow channels.
    hypotheses = {}
    for pipe, variants in source_hypotheses.items():
        full_variants = []
        for variant in variants:
            params = variant["parameters"]
            if pipe == "normal":
                prediction = simulate_net3(demand_scale=params["demand_scale"], sensors=sensors)
            else:
                prediction = simulate_net3(
                    pipe, params["leak_diameter_mm"], params["start_hour"],
                    params["leak_duration_hours"], params["demand_scale"], sensors=sensors,
                )
            full_variants.append(_serialize_hypothesis(
                prediction, params, pressure_columns, [], flow_columns
            ))
        hypotheses[pipe] = full_variants

    metadata = dict(source_metadata)
    metadata.pop("rejection_threshold", None)
    metadata.pop("rejection_threshold_calibration", None)
    metadata.update({
        "dataset_kind": "full_observation_companion",
        "paired_dataset": "data/net3",
        "observation_coverage": "Pressure at every junction and flow in every pipe.",
        "monitor_pressure_nodes": all_pressures,
        "flow_sensors": all_flows,
        "measurement_points": [],
        "measurement_fixtures_note": "No extra gauge points: every junction pressure is already in the observation CSV.",
        "observation_columns": len(columns),
        "pressure_column_count": len(pressure_columns),
        "flow_column_count": len(flow_columns),
        "reference_patterns_per_leak_pipe": len(next(
            variants for pipe, variants in source_hypotheses.items() if pipe != "normal"
        )),
        "normal_reference_patterns": len(source_hypotheses["normal"]),
        "reference_profile_total": sum(len(variants) for variants in source_hypotheses.values()),
        "noise_and_dropout": "Existing sensor columns are copied exactly from data/net3. Newly added channels use the same noise model and 1% sparse dropouts.",
        "limitations": "Full-observation paired benchmark; same case labels, split, candidate pipes, and reference parameter samples as data/net3. This is a best-case instrumentation comparison, not field validation.",
    })
    leak_profile_counts = {len(profiles) for pipe, profiles in source_hypotheses.items()
                           if pipe != "normal"}
    case_counts = source_metadata.get("case_counts", {})
    if (case_counts.get("total") == 500 and case_counts.get("train") == 400
            and case_counts.get("test") == 100
            and source_metadata.get("seed") == 2026
            and len(source_hypotheses.get("normal", [])) == 3
            and leak_profile_counts == {24}):
        metadata.update({
            "rejection_threshold": 64.29576260826462,
            "rejection_threshold_calibration": (
                "Calibrated for this 500-case full-observation benchmark on its 400 "
                "development cases by maximizing balanced accuracy. A weak top leak fit "
                "above this normalized_rmse is rejected as uncertain; the score is not a probability."),
        })
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (OUTPUT / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    (OUTPUT / "truth_labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    (OUTPUT / "measurement_fixtures.json").write_text(json.dumps(fixtures, indent=2), encoding="utf-8")
    (OUTPUT / "hypotheses.json").write_text(json.dumps(hypotheses, separators=(",", ":")), encoding="utf-8")
    print(f"Generated paired full-observation dataset: {len(cases)} cases, "
          f"{len(all_pressures)} junction pressures + {len(all_flows)} pipe flows per timestep.")
    print(f"Output: {OUTPUT.relative_to(ROOT)}/")


def main():
    generate_full_dataset()


if __name__ == "__main__":
    main()
