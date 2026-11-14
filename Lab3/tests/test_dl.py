"""Unit tests for the PyTorch models and their shared helpers (Task 2)."""
from __future__ import annotations

import numpy as np
import pytest
import torch
from torch import nn

import common
from dl import cnn_dl, dl_common, lstm_dl, mlp_dl
from dl.dl_common import EarlyStopper

MODULES = [mlp_dl, lstm_dl, cnn_dl]
NET_CLASSES = {"mlp": mlp_dl.MlpNet, "lstm": lstm_dl.LstmNet, "cnn": cnn_dl.CnnNet}
BATCH = 4
TINY_EPOCHS = 2
PATIENCE = 3
VAL_LOSSES = [1.0, 0.8, 0.9, 0.85, 0.95]
EXPECTED_STOPS = [False, False, False, False, True]
BEST_EPOCH_INDEX = 1  # the 0.8 epoch


@pytest.mark.parametrize("n_features", [10, 59])
@pytest.mark.parametrize("key", sorted(NET_CLASSES))
def test_forward_shape(key: str, n_features: int) -> None:
    """Each network maps (batch, n_features) to (batch, 1) logits."""
    model = NET_CLASSES[key](n_features)
    out = model(torch.zeros(BATCH, n_features))
    assert out.shape == (BATCH, 1)


def _assert_scores(scores: np.ndarray, n_rows: int) -> None:
    """Check score shape and the [0, 1] range.

    Args:
        scores: Predicted probabilities.
        n_rows: Expected length.
    """
    assert scores.shape == (n_rows,)
    assert np.all((scores >= 0.0) & (scores <= 1.0))


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.KEY)
def test_run_returns_valid_result(module, splits: common.DataSplits) -> None:
    """A short run gives a well-formed DL ModelResult."""
    result = module.run(splits, max_epochs=TINY_EPOCHS)
    assert result.family == "DL"
    assert (result.key, result.name) == (module.KEY, module.NAME)
    _assert_scores(result.y_val_score, len(splits.y_val))
    _assert_scores(result.y_test_score, len(splits.y_test))
    assert result.train_time_s > 0 and result.predict_time_s >= 0
    assert result.history is not None
    assert len(result.history["val_loss"]) <= TINY_EPOCHS
    assert len(result.history["train_loss"]) == len(result.history["val_loss"])


def test_early_stopper_stops_and_restores() -> None:
    """Patience 3 stops on the 5th epoch and restores the 0.8-epoch weights."""
    model = nn.Linear(1, 1, bias=False)
    stopper = EarlyStopper(patience=PATIENCE)
    stops = []
    for epoch, loss in enumerate(VAL_LOSSES):
        with torch.no_grad():
            model.weight.fill_(float(epoch))  # distinct weight per epoch
        stops.append(stopper.update(loss, model))
    assert stops == EXPECTED_STOPS
    stopper.restore(model)
    assert model.weight.item() == float(BEST_EPOCH_INDEX)


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.KEY)
def test_run_is_deterministic(module, splits: common.DataSplits) -> None:
    """Two runs with the same seed give identical scores."""
    first = module.run(splits, max_epochs=TINY_EPOCHS)
    second = module.run(splits, max_epochs=TINY_EPOCHS)
    np.testing.assert_array_equal(first.y_test_score, second.y_test_score)


def test_explicit_cpu_device_matches_default(splits: common.DataSplits) -> None:
    """Passing device="cpu" gives the same scores as the default."""
    default = mlp_dl.run(splits, max_epochs=TINY_EPOCHS)
    explicit = mlp_dl.run(splits, max_epochs=TINY_EPOCHS, device="cpu")
    np.testing.assert_array_equal(default.y_test_score, explicit.y_test_score)


def test_resolve_device_auto_and_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    """auto picks cpu without CUDA; an explicit cuda request then fails loudly."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert dl_common.resolve_device("auto") == "cpu"
    assert dl_common.resolve_device("cpu") == "cpu"
    with pytest.raises(RuntimeError):
        dl_common.resolve_device("cuda")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert dl_common.resolve_device("auto") == "cuda"


def test_default_epoch_limit_is_module_constant(splits: common.DataSplits,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """max_epochs=None falls back to the module's MAX_EPOCHS."""
    monkeypatch.setattr(mlp_dl, "MAX_EPOCHS", TINY_EPOCHS)
    result = mlp_dl.run(splits)
    assert result.history is not None
    assert len(result.history["val_loss"]) <= TINY_EPOCHS
