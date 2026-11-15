# Figure index

Pick the figures for the report and the deck. Every figure also exists as PDF.

- Tier 1 Core (7 figures): short report. Slides: Tier 1 minus dl_history_grid.
- Tier 2 Recommended additions (+5): full report = Tier 1 + Tier 2 (12).
- Tier 3 Alternatives: swap in for a Tier 1/2 figure; not in addition.
- Tier 4 Appendix: one confusion matrix per model run.

## Tier 1 - Core (7 figures)

_a short report uses only these._

| Figure | Chart type | Purpose |
|---|---|---|
| [comparison_table](comparison_table.png) | table image | a slide-ready test table |
| [metrics_bar_grouped](metrics_bar_grouped.png) | grouped bars | Accuracy, Precision, Recall and F1 per model |
| [errors_bar](errors_bar.png) | grouped bars, log y-axis | FP and FN, where near-perfect models differ |
| [roc_test](roc_test.png) | ROC curves, full axes | the Task 3 ROC figure |
| [roc_test_zoom](roc_test_zoom.png) | ROC curves, FPR 0-0.05, TPR 0.95-1 | separates the near-perfect models |
| [confusion_grid_counts](confusion_grid_counts.png) | confusion heatmap grid, counts | all models side by side |
| [dl_history_grid](dl_history_grid.png) | line chart grid | train and val loss per DL model, best epoch marked |

## Tier 2 - Recommended additions (5 figures)

_a full 10-15 page report uses Tier 1 + Tier 2._

| Figure | Chart type | Purpose |
|---|---|---|
| [metrics_heatmap](metrics_heatmap.png) | annotated heatmap | everything at a glance |
| [roc_test_logx](roc_test_logx.png) | ROC curves, log-scale FPR | low false-alarm behaviour |
| [time_bar](time_bar.png) | horizontal bars, log x-axis | train and predict cost |
| [confusion_grid_normalized](confusion_grid_normalized.png) | confusion heatmap grid, row-normalised rates | rates (0-1, 4 decimals) instead of counts |
| [dl_history_overlay](dl_history_overlay.png) | line chart | validation loss of all DL models, convergence compared |

## Tier 3 - Alternatives (6 figures)

_swap one in for the Tier 1/2 figure named under 'alternative to'; not in addition._

| Figure | Chart type | Purpose |
|---|---|---|
| [metrics_small_multiples](metrics_small_multiples.png) | small multiples, sorted bars | ranking per metric; alternative to metrics_bar_grouped |
| [metrics_radar](metrics_radar.png) | radar chart | the profile of each model; alternative to metrics_heatmap |
| [metrics_dot](metrics_dot.png) | Cleveland dot plot | a compact comparison; alternative to metrics_bar_grouped |
| [roc_grid](roc_grid.png) | ROC small multiples | each curve on its own; alternative to roc_test |
| [roc_test_ml](roc_test_ml.png) | ROC curves, ML only | the family comparison; alternative to roc_test_zoom |
| [roc_test_dl](roc_test_dl.png) | ROC curves, DL only | the family comparison; alternative to roc_test_zoom |

## Tier 4 - Appendix (per-model detail) (8 figures)

_one confusion matrix per model run._

| Figure | Chart type | Purpose |
|---|---|---|
| [confusion_gnb](confusion_gnb.png) | single confusion heatmap | one model on one slide |
| [confusion_lr](confusion_lr.png) | single confusion heatmap | one model on one slide |
| [confusion_knn](confusion_knn.png) | single confusion heatmap | one model on one slide |
| [confusion_rf](confusion_rf.png) | single confusion heatmap | one model on one slide |
| [confusion_xgb](confusion_xgb.png) | single confusion heatmap | one model on one slide |
| [confusion_mlp](confusion_mlp.png) | single confusion heatmap | one model on one slide |
| [confusion_lstm](confusion_lstm.png) | single confusion heatmap | one model on one slide |
| [confusion_cnn](confusion_cnn.png) | single confusion heatmap | one model on one slide |

Total: 26 figures listed.
