# Net3 evaluation runs: all 500 cases

Both datasets were evaluated using `evaluate_net3.py --split all`, so each run covers 500 cases (400 leak cases and 100 normal cases). Detection uses the configured rejection threshold; uncertain cases are counted as no leak alarm in the confusion matrix. Pipe localization is reported separately from leak detection.

| Dataset | Observations per case | Cases | TP | FN | FP | TN | Accuracy | Precision | Recall | Specificity | Balanced accuracy | F1 | Uncertain | Exact pipe among predicted leak cases | Exact pipe among all actual leak cases |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sparse Net3 | 12 pressure junctions + 8 pipe flows | 500 | 157 | 243 | 29 | 71 | 45.6% | 84.4% | 39.2% | 71.0% | 55.1% | 53.6% | 238 | 33/157 = 21.0% | 33/400 = 8.2% |
| Full-observation Net3 | All 92 pressure junctions + all 117 pipe flows | 500 | 153 | 247 | 24 | 76 | 45.8% | 86.4% | 38.2% | 76.0% | 57.1% | 53.0% | 292 | 66/153 = 43.1% | 66/400 = 16.5% |

**How to read the location columns:** “among predicted leak cases” asks how often the exact leaking pipe was named when the detector raised a leak alarm. “among all actual leak cases” also counts missed leaks as not localized, giving the end-to-end exact-pipe rate.

**Interpretation:** More observations improved exact-pipe localization (21.0% to 43.1% among predicted leak cases), but did not improve leak detection on this run: recall was 39.2% sparse and 38.2% full. Thus the current bottleneck is detecting leaks; once detected, full observations help identify the pipe. The all-500 result is descriptive, not an independent final test score, because it includes the 400 development cases along with the 100 held-out cases. It measures performance on these generated benchmark cases, not field performance.

## Raw run outputs

- [`net3_sparse_all500.txt`](net3_sparse_all500.txt): includes before/after optional pressure-reading metrics.
- [`net3_full_all500.txt`](net3_full_all500.txt): full-observation metrics.
- [`metrics_all500.csv`](metrics_all500.csv): machine-readable side-by-side metrics.
