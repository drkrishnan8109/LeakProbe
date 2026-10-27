# Recall led SMOTE Net3 benchmark

Experimental case-level classifier; the existing detector remains physics based.
Positive class: leak. Target development recall: 90%. Synthetic source data only.

Thresholds maximize precision among those meeting target recall on out-of-fold development predictions.

| Variant | Threshold | Dev target met | Test leak precision | Test leak recall | Test leak F1 | Test balanced accuracy | TP / FN / FP / TN |
|---|---:|:---:|---:|---:|---:|---:|---:|
| baseline | 0.695 | yes | 0.800 | 1.000 | 0.889 | 0.500 | 80 / 0 / 20 / 0 |
| class_weight | 0.689 | yes | 0.800 | 1.000 | 0.889 | 0.500 | 80 / 0 / 20 / 0 |
| smote | 0.557 | yes | 0.800 | 1.000 | 0.889 | 0.500 | 80 / 0 / 20 / 0 |

A target marked ‘no’ could not be met by the selected thresholding procedure on development data. Test results are held out once and should not be used to tune the model.

## 400-case development set (in-sample diagnostic)

Each model below was fitted on all 400 development cases and scored on those same cases. These figures are expected to be optimistic and are not a generalization estimate.

| Variant | Leak precision | Leak recall | Leak F1 | Balanced accuracy | TP / FN / FP / TN |
|---|---:|---:|---:|---:|---:|
| baseline | 1.000 | 1.000 | 1.000 | 1.000 | 320 / 0 / 0 / 80 |
| class_weight | 1.000 | 1.000 | 1.000 | 1.000 | 320 / 0 / 0 / 80 |
| smote | 1.000 | 1.000 | 1.000 | 1.000 | 320 / 0 / 0 / 80 |
