"""Evaluate Net3 scenario rankings against the separated synthetic truth labels."""
import argparse
import json
from pathlib import Path

from .net3_tools import DATA, Net3Investigation


def classification_metrics(actual, predicted):
    """Summarize binary leak/normal predictions; "leak" is the positive class."""
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must contain the same number of cases.")
    allowed = {"leak", "normal"}
    if any(value not in allowed for value in (*actual, *predicted)):
        raise ValueError("Class labels must be 'leak' or 'normal'.")

    tp = sum(a == "leak" and p == "leak" for a, p in zip(actual, predicted))
    fn = sum(a == "leak" and p == "normal" for a, p in zip(actual, predicted))
    fp = sum(a == "normal" and p == "leak" for a, p in zip(actual, predicted))
    tn = sum(a == "normal" and p == "normal" for a, p in zip(actual, predicted))
    total = tp + fn + fp + tn
    recall = tp / (tp + fn) if tp + fn else None
    precision = tp / (tp + fp) if tp + fp else None
    specificity = tn / (tn + fp) if tn + fp else None
    balanced = ((recall + specificity) / 2
                if recall is not None and specificity is not None else None)
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and precision + recall else 0.0
          if precision is not None and recall == 0 else None)
    return {
        "confusion_matrix": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "total": total,
        "accuracy": (tp + tn) / total if total else None,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
        "balanced_accuracy": balanced,
        "f1": f1,
    }


def select_cases(cases, split):
    """Select one split, or every case for a descriptive whole-dataset report."""
    if split not in {"train", "test", "all"}:
        raise ValueError("split must be 'train', 'test', or 'all'.")
    return [row["case_id"] for row in cases if split == "all" or row["split"] == split]


def _print_classification_report(stage, actual, predicted):
    metrics = classification_metrics(actual, predicted)
    matrix = metrics["confusion_matrix"]
    actual_leaks = matrix["tp"] + matrix["fn"]
    actual_normals = matrix["tn"] + matrix["fp"]
    print(f"\n{stage} leak detection (positive = leak):")
    print("                 Predicted leak  Predicted normal")
    print(f"Actual leak      {matrix['tp']:>13}  {matrix['fn']:>16}  (n={actual_leaks})")
    print(f"Actual normal    {matrix['fp']:>13}  {matrix['tn']:>16}  (n={actual_normals})")

    def show(name, value, numerator=None, denominator=None, detail=None):
        if value is None:
            print(f"  {name}: undefined{f' ({detail})' if detail else ''}")
        elif numerator is not None and denominator is not None:
            print(f"  {name}: {value:.1%} ({numerator}/{denominator})")
        else:
            print(f"  {name}: {value:.1%}")

    show("Accuracy", metrics["accuracy"], matrix["tp"] + matrix["tn"], metrics["total"])
    show("Precision", metrics["precision"], matrix["tp"], matrix["tp"] + matrix["fp"],
         "no cases predicted as leak" if matrix["tp"] + matrix["fp"] == 0 else None)
    show("Recall", metrics["recall"], matrix["tp"], actual_leaks)
    show("Specificity", metrics["specificity"], matrix["tn"], actual_normals)
    show("False-alarm rate", metrics["false_alarm_rate"], matrix["fp"], actual_normals)
    show("Balanced accuracy", metrics["balanced_accuracy"])
    show("F1", metrics["f1"])
    return metrics


def _binary_prediction(decision):
    """Treat an abstention as no leak alarm for binary alarm metrics."""
    return "normal" if decision["prediction"] == "uncertain" else decision["prediction"]


def evaluate(split="test", data_dir=DATA):
    data_dir = Path(data_dir)
    cases = json.loads((data_dir / "cases.json").read_text(encoding="utf-8"))
    labels = json.loads((data_dir / "truth_labels.json").read_text(encoding="utf-8"))
    selected = select_cases(cases, split)
    if not selected:
        raise ValueError(f"No cases in the {split} split. Generate the Net3 dataset first.")

    actual_classes = []
    predicted_before = []
    predicted_after = []
    rejected_before = rejected_after = 0
    leak_total = leak_pipe_correct_before = leak_pipe_correct_after = 0
    detected_leaks_before = detected_leaks_after = 0
    located_detected_before = located_detected_after = 0
    has_optional_measurements = bool(json.loads(
        (data_dir / "metadata.json").read_text(encoding="utf-8")
    ).get("measurement_points"))
    for index, case_id in enumerate(selected, start=1):
        truth = labels[case_id]
        session = Net3Investigation(case_id, data_dir=data_dir)
        before_result = session.compare_hypotheses()
        before = before_result["ranking"][0]
        before_decision = before_result["decision"]
        is_normal = truth["incident"] == "normal"
        actual_classes.append("normal" if is_normal else "leak")
        predicted_before.append(_binary_prediction(before_decision))
        rejected_before += before_decision["rejected"]
        if not is_normal:
            leak_total += 1
            leak_pipe_correct_before += (before_decision["prediction"] == "leak"
                                         and before["leak_pipe"] == truth["leak_pipe"])
            if before_decision["prediction"] == "leak":
                detected_leaks_before += 1
                located_detected_before += before["leak_pipe"] == truth["leak_pipe"]

        recommendation = session.recommend_measurement()["recommended"] if has_optional_measurements else None
        if recommendation:
            session.collect_demo_measurement(recommendation)
        after_result = session.compare_hypotheses() if recommendation else before_result
        after = after_result["ranking"][0]
        after_decision = after_result["decision"]
        predicted_after.append(_binary_prediction(after_decision))
        rejected_after += after_decision["rejected"]
        if not is_normal:
            leak_pipe_correct_after += (after_decision["prediction"] == "leak"
                                        and after["leak_pipe"] == truth["leak_pipe"])
            if after_decision["prediction"] == "leak":
                detected_leaks_after += 1
                located_detected_after += after["leak_pipe"] == truth["leak_pipe"]
        if index % 25 == 0 or index == len(selected):
            print(f"Progress: {index}/{len(selected)} cases evaluated", flush=True)

    print(f"Net3 {split} split: {len(selected)} cases ({leak_total} leaks, "
          f"{len(selected)-leak_total} normal)")
    before_stage = ("Before optional pressure reading" if has_optional_measurements
                    else "Full observation set")
    _print_classification_report(before_stage, actual_classes, predicted_before)
    if rejected_before:
        print(f"  Rejected as uncertain: {rejected_before}/{len(selected)} cases; counted as no leak alarm above.")
    if has_optional_measurements:
        _print_classification_report("After optional pressure reading", actual_classes, predicted_after)
        if rejected_after:
            print(f"  Rejected as uncertain: {rejected_after}/{len(selected)} cases; counted as no leak alarm above.")
    threshold = json.loads((data_dir / "metadata.json").read_text(encoding="utf-8")).get("rejection_threshold")
    if threshold is not None:
        print(f"Rejection threshold: best leak fit score > {threshold:.4f} becomes uncertain.")
    if leak_total:
        print("\nPipe location, conditional on the case being an actual leak:")
        if has_optional_measurements:
            print(f"  Before extra pressure measurement: "
                  f"{located_detected_before}/{detected_leaks_before} detected leaks had the exact pipe "
                  f"({located_detected_before/detected_leaks_before:.1%})" if detected_leaks_before else
                  "  Before extra pressure measurement: no leaks were detected")
            print(f"  After extra pressure measurement: "
                  f"{located_detected_after}/{detected_leaks_after} detected leaks had the exact pipe "
                  f"({located_detected_after/detected_leaks_after:.1%})" if detected_leaks_after else
                  "  After extra pressure measurement: no leaks were detected")
            print("  Exact pipe across all actual leak cases (missed leaks count as not located):")
            print(f"    Before extra measurement: {leak_pipe_correct_before/leak_total:.1%} "
                  f"({leak_pipe_correct_before}/{leak_total})")
            print(f"    After extra measurement: {leak_pipe_correct_after/leak_total:.1%} "
                  f"({leak_pipe_correct_after}/{leak_total})")
        else:
            print(f"  Using all observations in the CSV: "
                  f"{located_detected_before}/{detected_leaks_before} detected leaks had the exact pipe "
                  f"({located_detected_before/detected_leaks_before:.1%})" if detected_leaks_before else
                  "  Using all observations in the CSV: no leaks were detected")
            print("  Exact pipe across all actual leak cases (missed leaks count as not located):")
            print(f"    Using all observations in the CSV: {leak_pipe_correct_before/leak_total:.1%} "
                  f"({leak_pipe_correct_before}/{leak_total})")
    print("These are results on generated benchmark cases, not field performance.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "test", "all"), default="test",
                        help="Evaluate the held-out split, development split, or all cases.")
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="Net3 dataset directory (default: data/net3).")
    args = parser.parse_args()
    evaluate(args.split, args.data_dir)


if __name__ == "__main__":
    main()
