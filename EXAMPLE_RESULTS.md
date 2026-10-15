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

All eight automated tests passed. Dependency consistency check passed. The real Nebius endpoint was not invoked; the API loop was tested with a fake provider client.
