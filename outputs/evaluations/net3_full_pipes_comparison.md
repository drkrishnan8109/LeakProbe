# Net3 sparse versus full observation coverage

Both evaluations use the same 100 held-out case labels (80 leak, 20 normal), candidate-pipe split, and reference-pattern parameter samples. The full-observation dataset also reuses the original values for all 20 existing sensor channels. It adds pressure at the remaining junctions and flow in the remaining pipes.

| Metric | Sparse: 12 junctions + 8 pipes | Full: 92 junctions + 117 pipes |
|---|---:|---:|
| Leak-detection accuracy | 52.0% (52/100) | 69.0% (69/100) |
| Precision | 78.6% (44/56) | 83.6% (61/73) |
| Recall | 55.0% (44/80) | 76.2% (61/80) |
| Specificity | 40.0% (8/20) | 40.0% (8/20) |
| Balanced accuracy | 47.5% | 58.1% |
| F1 | 64.7% | 79.7% |
| Exact pipe, across all actual leak cases | 13/80 (16.2%) | 41/80 (51.2%) |
| Exact pipe, among detected leaks | 13/44 (29.5%) | 41/61 (67.2%) |

The wider coverage improved leak recall and pipe localization in this generated benchmark. Specificity stayed at 40%, so the detector still raises many false alarms on normal cases. This is a comparison of simulated full versus sparse sensor coverage; it is not evidence of field performance. The current detector is a physics-based reference-pattern matcher, not a model trained on the 400 development cases.

## Descriptive report over all 500 full-observation cases

This combines the 400 development and 100 held-out cases, so it is a summary of this dataset, not an independent test result. The overall set contains 400 leak cases and 100 normal cases.

| Metric | All 500 cases |
|---|---:|
| Confusion matrix (TP / FN / FP / TN) | 378 / 22 / 91 / 9 |
| Accuracy | 77.4% (387/500) |
| Precision | 80.6% (378/469) |
| Recall | 94.5% (378/400) |
| Specificity | 9.0% (9/100) |
| False-alarm rate | 91.0% (91/100) |
| Balanced accuracy | 51.7% |
| F1 | 87.0% |
| Exact pipe, across all actual leak cases | 104/400 (26.0%) |
| Exact pipe, among detected leaks | 104/378 (27.5%) |

The high recall and F1 come with a very high false-alarm rate on normal cases. Since this combined set contains 80% leak cases and includes development cases, use the held-out test report above for the separate test estimate.

## Rejection-threshold evaluation

The full-observation detector now rejects a case as **uncertain** when its top-ranked scenario is a leak but that fit has normalized RMSE above **64.2958**. This cutoff was selected on the 400 development cases to maximize balanced accuracy. For the binary alarm metrics below, a rejected case counts as no leak alarm. The score is a fit measure, not a probability.

| Held-out metric | Before threshold | With threshold |
|---|---:|---:|
| Confusion matrix (TP / FN / FP / TN) | 61 / 19 / 12 / 8 | 32 / 48 / 3 / 17 |
| Accuracy | 69.0% | 49.0% |
| Precision | 83.6% | 91.4% |
| Recall | 76.2% | 40.0% |
| Specificity | 40.0% | 85.0% |
| Balanced accuracy | 58.1% | 62.5% |
| F1 | 79.7% | 55.7% |
| Rejected as uncertain | 0 | 38/100 |
| Exact pipe across all 80 actual leaks | 41/80 (51.2%) | 26/80 (32.5%) |
| Exact pipe among accepted leak alarms | 41/61 (67.2%) | 26/32 (81.2%) |

On the held-out cases, the threshold cuts false alarms from 12 to 3 and raises specificity, while missing more leaks and lowering overall accuracy. It is a conservative operating point, not an across-the-board improvement. The train and test splits use different candidate-pipe groups and different leak parameter ranges, so the test result is the meaningful check of this threshold's transfer.

Across all 500 full-observation cases, the threshold produced **153 TP, 247 FN, 24 FP, and 76 TN**, with 292 cases rejected as uncertain. Accuracy was 45.8%, precision 86.4%, recall 38.2%, specificity 76.0%, balanced accuracy 57.1%, and F1 53.0%. Exact pipe identification was 66/153 (43.1%) among accepted leak alarms and 66/400 (16.5%) across all actual leaks. This combines development cases used to select the cutoff with the held-out cases, so it is descriptive rather than an independent estimate.

The default sparse dataset has its own calibrated threshold (**5.9836**) because its 20 measurement channels produce a different score scale. On the same 100 held-out cases, the sparse threshold changed the confusion matrix from **44 / 36 / 12 / 8** to **20 / 60 / 3 / 17** (TP / FN / FP / TN): specificity rose from 40.0% to 85.0%, while recall fell from 55.0% to 25.0%. It rejected 33/100 cases as uncertain. An extra pressure reading changed this to 21 / 59 / 3 / 17 and 32 uncertain cases. Both cutoffs were calibrated against the current stored 500-case datasets and their reference banks (24 leak profiles per candidate pipe, 3 normal profiles). Recalibrate if cases or reference patterns are regenerated with different settings.

Reproduce the held-out result with:

```bash
python evaluate_net3.py --split test --data-dir data/net3_full_pipes_data
```

To produce the descriptive result over all 500 cases, use `--split all`.
