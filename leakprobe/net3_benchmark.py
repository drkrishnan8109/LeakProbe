"""Reproducible synthetic cases on the EPA WNTR Net3 example network."""
import json
import math

import numpy as np
import pandas as pd
import wntr
from .paths import ROOT, DATA

NET3_FILE = DATA / "networks" / "Net3.inp"
OUT = DATA / "net3"
DURATION_HOURS = 6
STEP_SECONDS = 900
MEASUREMENT_HOUR = 3
N_HYPOTHESES = 24
N_MONITOR_PRESSURE = 12
N_FLOW_SENSORS = 8
N_MEASUREMENT_POINTS = 12
PRESSURE_SIGMA_M = 0.08
DEFAULT_PATTERNS_PER_SCENARIO = 200
LEAK_HYPOTHESIS_RANGES = {
    "leak_diameter_mm": (8.0, 25.0),
    "start_hour": (0.5, 1.5),
    "leak_duration_hours": (3.0, 4.5),
    "demand_scale": (0.85, 1.15),
}
NORMAL_HYPOTHESIS_RANGES = {"demand_scale": (0.85, 1.15)}


def load_network():
    if not NET3_FILE.exists():
        raise FileNotFoundError(f"Net3 input file not found: {NET3_FILE}")
    wn = wntr.network.WaterNetworkModel(str(NET3_FILE))
    wn.options.time.duration = DURATION_HOURS * 3600
    wn.options.time.hydraulic_timestep = STEP_SECONDS
    wn.options.time.report_timestep = STEP_SECONDS
    wn.options.hydraulic.demand_model = "PDD"
    wn.options.hydraulic.minimum_pressure = 0
    wn.options.hydraulic.required_pressure = 15
    wn.options.hydraulic.pressure_exponent = 0.5
    return wn


def choose_sensors(wn, seed=2026):
    """Choose fixed monitoring nodes and distributed optional gauge locations."""
    graph = wn.to_graph()
    demand_nodes = [n for n in wn.junction_name_list if wn.get_node(n).base_demand > 0]
    coords = {n: np.asarray(wn.get_node(n).coordinates, dtype=float) for n in demand_nodes}

    def spread(nodes, count, first):
        remaining = set(nodes)
        selected = []
        while remaining and len(selected) < count:
            if not selected:
                pick = first(remaining)
            else:
                pick = max(remaining, key=lambda n: (min(np.linalg.norm(coords[n]-coords[s]) for s in selected), n))
            selected.append(pick)
            remaining.remove(pick)
        return selected

    fixed_pressure = spread(demand_nodes, N_MONITOR_PRESSURE,
                            lambda ns: max(ns, key=lambda n: (graph.degree(n), n)))
    measurement_points = spread([n for n in demand_nodes if n not in fixed_pressure], N_MEASUREMENT_POINTS,
                                lambda ns: max(ns, key=lambda n: (graph.degree(n), n)))

    pipes = [n for n in wn.pipe_name_list if wn.get_link(n).diameter <= 0.9144]
    pipe_coords = {}
    for name in pipes:
        link = wn.get_link(name)
        a = np.asarray(wn.get_node(link.start_node_name).coordinates, dtype=float)
        b = np.asarray(wn.get_node(link.end_node_name).coordinates, dtype=float)
        pipe_coords[name] = (a+b)/2
    first_pipe = max(pipes, key=lambda n: (wn.get_link(n).diameter, n))
    candidates = [first_pipe]
    remaining_pipes = set(pipes) - {first_pipe}
    while remaining_pipes and len(candidates) < min(N_HYPOTHESES, len(pipes)):
        pick = max(remaining_pipes, key=lambda n: (
            min(np.linalg.norm(pipe_coords[n]-pipe_coords[s]) for s in candidates), n))
        candidates.append(pick)
        remaining_pipes.remove(pick)
    rng = np.random.default_rng(seed)
    rng.shuffle(candidates)
    n_train = max(2, round(len(candidates) * 0.7))
    split_pipes = {"train": sorted(candidates[:n_train]), "test": sorted(candidates[n_train:])}

    flow_sensors = sorted(wn.pipe_name_list, key=lambda n: (-wn.get_link(n).diameter, n))[:N_FLOW_SENSORS]
    return {"monitor_pressure_nodes": fixed_pressure,
            "measurement_points": measurement_points,
            "flow_sensors": flow_sensors,
            "candidate_pipes": split_pipes}


def simulate_net3(leak_pipe=None, leak_diameter_mm=16.0, start_hour=1.0,
                  leak_duration_hours=4.0, demand_scale=1.0, seed=0,
                  sensors=None):
    """Simulate normal operation or one leak; return all node pressures and pipe flows."""
    wn = load_network()
    if leak_pipe is not None:
        if leak_pipe not in wn.pipe_name_list:
            raise ValueError(f"Unknown Net3 pipe: {leak_pipe}")
        values = (leak_diameter_mm, start_hour, leak_duration_hours, demand_scale)
        if not all(math.isfinite(float(x)) for x in values):
            raise ValueError("Leak and demand parameters must be finite.")
        if not 4 <= leak_diameter_mm <= 40:
            raise ValueError("Leak diameter must be between 4 and 40 mm.")
        if not 0 <= start_hour < DURATION_HOURS or not 0 < leak_duration_hours <= DURATION_HOURS-start_hour:
            raise ValueError("Leak start and duration must fit inside the six-hour run.")
        if not 0.5 <= demand_scale <= 1.5:
            raise ValueError("Demand scale must be between 0.5 and 1.5.")

    if not math.isfinite(float(demand_scale)) or not 0.5 <= demand_scale <= 1.5:
        raise ValueError("Demand scale must be between 0.5 and 1.5.")
    if demand_scale != 1:
        for _, node in wn.junctions():
            for demand in node.demand_timeseries_list:
                demand.base_value *= demand_scale

    if leak_pipe is not None:
        leak_node = f"LP_LEAK_{leak_pipe}"
        new_pipe = f"LP_AFTER_{leak_pipe}"
        wn = wntr.morph.split_pipe(wn, leak_pipe, new_pipe, leak_node, split_at_point=0.5)
        wn.get_node(leak_node).add_leak(
            wn,
            area=math.pi * (leak_diameter_mm / 2000) ** 2,
            discharge_coeff=0.75,
            start_time=start_hour * 3600,
            end_time=(start_hour + leak_duration_hours) * 3600,
        )

    result = wntr.sim.WNTRSimulator(wn).run_sim(convergence_error=True)
    pressure = result.node["pressure"]
    flow = result.link["flowrate"]
    columns = {"timestamp_utc": pd.Timestamp("2026-01-01T00:00:00Z")
               + pd.to_timedelta(pressure.index, unit="s")}
    for node in wn.junction_name_list:
        if node in pressure:
            columns[f"pressure_{node}_m"] = pressure[node].to_numpy()
    for pipe in wn.pipe_name_list:
        if pipe in flow:
            columns[f"flow_{pipe}_lps"] = flow[pipe].to_numpy() * 1000
    return pd.DataFrame(columns)


def _sensor_columns(sensors):
    pressure_cols = [f"pressure_{n}_m" for n in sensors["monitor_pressure_nodes"]]
    flow_cols = [f"flow_{n}_lps" for n in sensors["flow_sensors"]]
    point_cols = [f"pressure_{n}_m" for n in sensors["measurement_points"]]
    return pressure_cols, flow_cols, point_cols


def _sample_hypothesis_parameters(pattern_count, parameter_ranges, rng):
    """Return reproducible stratified samples spanning each parameter range."""
    samples = {}
    for name, (low, high) in parameter_ranges.items():
        strata = (rng.permutation(pattern_count) + rng.random(pattern_count)) / pattern_count
        samples[name] = low + strata * (high - low)
    return [
        {name: float(values[index]) for name, values in samples.items()}
        for index in range(pattern_count)
    ]


def _serialize_hypothesis(prediction, parameters, pressure_cols, point_cols, flow_cols):
    return {
        "parameters": parameters,
        "pressure": {c.removeprefix("pressure_").removesuffix("_m"): prediction[c].round(5).tolist()
                     for c in pressure_cols + point_cols},
        "flow": {c.removeprefix("flow_").removesuffix("_lps"): prediction[c].round(5).tolist()
                 for c in flow_cols},
    }


def generate_hypothesis_bank(sensors, patterns_per_scenario=DEFAULT_PATTERNS_PER_SCENARIO,
                             seed=2026):
    """Simulate a dense reference bank for every candidate pipe and normal operation."""
    if isinstance(patterns_per_scenario, bool) or patterns_per_scenario < 1:
        raise ValueError("patterns_per_scenario must be a positive integer.")
    pressure_cols, flow_cols, point_cols = _sensor_columns(sensors)
    candidate_pipes = sorted(set(sensors["candidate_pipes"]["train"] +
                                 sensors["candidate_pipes"]["test"]))
    rng = np.random.default_rng(seed + 1)
    hypotheses = {}

    for pipe in candidate_pipes:
        variants = []
        parameters_list = _sample_hypothesis_parameters(
            patterns_per_scenario, LEAK_HYPOTHESIS_RANGES, rng)
        for parameters in parameters_list:
            prediction = simulate_net3(
                pipe, parameters["leak_diameter_mm"], parameters["start_hour"],
                parameters["leak_duration_hours"], parameters["demand_scale"],
                sensors=sensors)
            variants.append(_serialize_hypothesis(
                prediction, {name: round(value, 5) for name, value in parameters.items()},
                pressure_cols, point_cols, flow_cols))
        hypotheses[pipe] = variants

    normal_variants = []
    parameters_list = _sample_hypothesis_parameters(
        patterns_per_scenario, NORMAL_HYPOTHESIS_RANGES, rng)
    for parameters in parameters_list:
        prediction = simulate_net3(demand_scale=parameters["demand_scale"], sensors=sensors)
        normal_variants.append(_serialize_hypothesis(
            prediction, {name: round(value, 5) for name, value in parameters.items()},
            pressure_cols, point_cols, flow_cols))
    hypotheses["normal"] = normal_variants
    return hypotheses


def _hypothesis_metadata(patterns_per_scenario):
    return {
        "hypothesis_patterns_per_leak_pipe": patterns_per_scenario,
        "normal_hypothesis_patterns": patterns_per_scenario,
        "hypothesis_parameter_sampling": "Seeded stratified sampling across the stated ranges.",
        "hypothesis_parameter_ranges": {
            "leak": {name: list(bounds) for name, bounds in LEAK_HYPOTHESIS_RANGES.items()},
            "normal": {name: list(bounds) for name, bounds in NORMAL_HYPOTHESIS_RANGES.items()},
        },
    }


def generate_hypotheses_only(patterns_per_scenario=DEFAULT_PATTERNS_PER_SCENARIO, seed=None):
    """Refresh only the reference pattern bank, preserving existing case observations."""
    metadata_path = OUT / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError("Generate a Net3 dataset before refreshing its hypothesis bank.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    seed = metadata.get("seed", 2026) if seed is None else seed
    sensors = choose_sensors(load_network(), seed)
    if sensors["candidate_pipes"] != metadata["candidate_pipes_by_split"]:
        raise ValueError("The selected seed does not match the existing dataset's candidate-pipe split.")
    hypotheses = generate_hypothesis_bank(sensors, patterns_per_scenario, seed)
    (OUT / "hypotheses.json").write_text(
        json.dumps(hypotheses, separators=(",", ":")), encoding="utf-8")
    metadata.pop("hypothesis_parameter_grid", None)
    metadata.update(_hypothesis_metadata(patterns_per_scenario))
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Updated reference patterns: {patterns_per_scenario} per each of "
          f"{len(hypotheses) - 1} candidate leak pipes and "
          f"{len(hypotheses['normal'])} normal-operation patterns.")
    print("Existing cases and observation files were preserved.")


def generate_dataset(case_count=32, seed=2026, train_fraction=0.8,
                    patterns_per_scenario=DEFAULT_PATTERNS_PER_SCENARIO):
    """Create train/test cases with pipe-disjoint truth labels and hidden readings."""
    if isinstance(case_count, bool) or case_count < 4:
        raise ValueError("case_count must be an integer of at least 4.")
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be greater than 0 and less than 1.")
    train_count = round(case_count * train_fraction)
    test_count = case_count - train_count
    if min(train_count, test_count) < 2:
        raise ValueError("The requested split must provide at least 2 cases in each split.")
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    base = load_network()
    sensors = choose_sensors(base, seed)
    candidate_by_split = sensors["candidate_pipes"]
    all_candidates = sorted(set(candidate_by_split["train"] + candidate_by_split["test"]))
    hypotheses = generate_hypothesis_bank(sensors, patterns_per_scenario, seed)

    case_rows = []
    labels = {}
    fixtures = {}
    case_index = 0
    for split, split_count in (("train", train_count), ("test", test_count)):
        pipes = candidate_by_split[split]
        for local_index in range(split_count):
            case_id = f"case_{case_index:03d}"
            case_index += 1
            is_normal = (local_index == 1 if split_count < 5 else local_index % 5 == 4)
            if split == "train":
                demand_scale = float(rng.uniform(0.85, 1.0))
            else:
                demand_scale = float(rng.uniform(1.0, 1.15))
            if is_normal:
                pipe, diameter, start, leak_duration = None, None, None, None
                truth = simulate_net3(demand_scale=demand_scale, sensors=sensors)
            else:
                pipe = str(rng.choice(pipes))
                if split == "train":
                    diameter = float(rng.uniform(8, 16))
                    start = float(rng.uniform(0.5, 1.0))
                    leak_duration = float(rng.uniform(3.0, 3.75))
                else:
                    diameter = float(rng.uniform(17, 25))
                    start = float(rng.uniform(1.0, 1.5))
                    leak_duration = float(rng.uniform(3.75, 4.5))
                truth = simulate_net3(pipe, diameter, start, leak_duration, demand_scale, sensors=sensors)

            observed = truth[["timestamp_utc", *pressure_cols, *flow_cols]].copy()
            for col in pressure_cols:
                observed[col] += rng.normal(0, PRESSURE_SIGMA_M, len(observed))
            flow_sigmas = {}
            for col in flow_cols:
                sigma = max(0.15, float(truth[col].abs().median()) * 0.02)
                flow_sigmas[col] = sigma
                observed[col] += rng.normal(0, sigma, len(observed))
            # Deterministic, sparse telemetry dropouts.
            missing = rng.random(observed[pressure_cols + flow_cols].shape) < 0.01
            observed.loc[:, pressure_cols + flow_cols] = observed[pressure_cols + flow_cols].mask(missing)
            observed.to_csv(OUT / f"{case_id}_observations.csv", index=False)

            measure_idx = int(MEASUREMENT_HOUR * 3600 / STEP_SECONDS)
            fixtures[case_id] = {
                point: {"pressure_head_m": round(float(truth.at[measure_idx, f"pressure_{point}_m"] + rng.normal(0, PRESSURE_SIGMA_M)), 5),
                        "timestamp_utc": truth.at[measure_idx, "timestamp_utc"].isoformat(),
                        "provenance": "synthetic Net3 simulation with sensor noise"}
                for point in sensors["measurement_points"]
            }
            labels[case_id] = {"split": split, "incident": "normal" if is_normal else "single_leak",
                               "leak_pipe": pipe,
                               "leak_diameter_mm": round(diameter, 3) if diameter is not None else None,
                               "start_hour": round(start, 3) if start is not None else None,
                               "leak_duration_hours": round(leak_duration, 3) if leak_duration is not None else None,
                               "demand_scale": round(demand_scale, 4)}
            case_rows.append({"case_id": case_id, "split": split,
                              "observations_file": f"{case_id}_observations.csv"})

    metadata = {
        "network": "EPA EPANET Example Network 3 (Net3)",
        "source": "https://github.com/USEPA/WNTR/blob/main/examples/networks/Net3.inp",
        "nodes": len(base.node_name_list), "links": len(base.link_name_list),
        "junctions": len(base.junction_name_list), "pipes": len(base.pipe_name_list),
        "duration_hours": DURATION_HOURS, "timestep_minutes": STEP_SECONDS // 60,
        "measurement_hour": MEASUREMENT_HOUR,
        "pressure_noise_sigma_m": PRESSURE_SIGMA_M,
        "flow_noise_sigma": "max(0.15 L/s, 2% of median absolute flow)",
        "monitor_pressure_nodes": sensors["monitor_pressure_nodes"],
        "flow_sensors": sensors["flow_sensors"],
        "measurement_points": sensors["measurement_points"],
        "candidate_pipes_by_split": candidate_by_split,
        "truth_parameter_ranges_by_split": {
            "train": {"diameter_mm": [8, 16], "start_hour": [0.5, 1.0], "duration_hours": [3.0, 3.75], "demand_scale": [0.85, 1.0]},
            "test": {"diameter_mm": [17, 25], "start_hour": [1.0, 1.5], "duration_hours": [3.75, 4.5], "demand_scale": [1.0, 1.15]},
        },
        "seed": seed,
        "case_counts": {"total": case_count, "train": train_count, "test": test_count},
        **_hypothesis_metadata(patterns_per_scenario),
        "limitations": "Synthetic benchmark; train/test leak pipe sets are disjoint. The dense hypothesis bank is a physics-based reference library; scenario rankings are fit scores, not probabilities or field validation.",
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (OUT / "cases.json").write_text(json.dumps(case_rows, indent=2), encoding="utf-8")
    (OUT / "truth_labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    (OUT / "measurement_fixtures.json").write_text(json.dumps(fixtures, indent=2), encoding="utf-8")
    (OUT / "hypotheses.json").write_text(json.dumps(hypotheses, separators=(",", ":")), encoding="utf-8")
    print(f"Generated Net3 dataset: {case_count} cases (normal + leak), {len(all_candidates)} candidate pipes, "
          f"{len(sensors['measurement_points'])} optional pressure measurement points.")
    print(f"Train/test cases use disjoint pipe sets. Files: {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    generate_dataset()
