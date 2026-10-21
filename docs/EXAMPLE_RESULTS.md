# Actual local example results

Generated and checked on Python 3.12.14 with WNTR 1.3.2 on macOS.
These are actual solver outputs for the supplied synthetic network, not field measurements.

## Predictions at 02:45

| Scenario | F01 flow L/s | P01 head m | MA head m | MB head m |
|---|---:|---:|---:|---:|
| normal | 10.000 | 41.471 | 39.888 | 39.888 |
| leak_A | 14.148 | 40.994 | 37.779 | 39.411 |
| leak_B | 14.148 | 40.994 | 39.411 | 37.779 |

## Scripted investigation

Before the portable-gauge measurement:

- Leak A normalized RMSE: 0.1237.
- Leak B normalized RMSE: 0.1237.
- Normal normalized RMSE: 11.4270.

The upstream sensors cannot distinguish the symmetric leak scenarios. The planner recommends MA, which costs 15 minutes versus a remaining budget of 20. MB would cost 30 minutes.

The synthetic MA fixture reports 37.809 m. After including it:

- Leak A normalized RMSE: 0.1251.
- Leak B normalized RMSE: 1.7522.
- Normal normalized RMSE: 11.3799.

Scores are not probabilities. A small increase in the best-fit score after adding a noisy measurement is normal; the important change is separation from the alternative. Rounding and package/platform differences can cause small numerical variation.

All 17 automated tests passed. Dependency consistency check passed. The real Nebius endpoint was not invoked; the API loop was tested with a fake provider client.

## Net3 held-out evaluation and rejection threshold

The current benchmark contains 500 cases: 400 development cases and 100 held-out cases. The detector is a physics-based reference-pattern matcher. It does not train a machine-learning model on the development cases. Those cases were used to select the dataset-specific rejection cutoff.

For the full-observation set (92 pressure junctions and 117 flow pipes), the 100 held-out cases contain 80 leaks and 20 normal cases. Before applying the rejection threshold, the confusion matrix was **61 TP, 19 FN, 12 FP, 8 TN**. With the **64.2958** normalized-RMSE threshold, it was **32 TP, 48 FN, 3 FP, 17 TN**. Specificity rose from 40% to 85%, while recall fell from 76.2% to 40%. The threshold rejected 38 cases as uncertain. Balanced accuracy changed from 58.1% to 62.5%.

The sparse set uses a separate **5.9836** cutoff because it has fewer observed channels. On its same held-out cases, the confusion matrix changed from **44 / 36 / 12 / 8** to **20 / 60 / 3 / 17** (TP / FN / FP / TN), rejecting 33 cases. The cutoff reduces false alarms but misses more leaks; it is not an across-the-board accuracy improvement. See [the detailed comparison](../outputs/evaluations/net3_full_pipes_comparison.md) for precision, F1, and pipe-location results.

Across all 500 full-observation cases with the threshold, the confusion matrix was **153 / 247 / 24 / 76** and 292 cases were uncertain. This includes the cases used for threshold selection, so it is descriptive rather than an independent test result.

The score is a normalized fit error, not a probability. These cutoffs apply to the current stored case and reference-pattern banks. They must be recalibrated if the data or reference profiles change. All Net3 cases are generated from a model and are not field-performance evidence.
