"""Multi-layer perceptron (Task 2), trained with the shared PyTorch loop of dl_common."""
from __future__ import annotations

import torch
from torch import nn

import common
from dl.dl_common import DEFAULT_DEVICE, run_dl, set_seed

KEY = "mlp"
NAME = "MLP"
# Chosen on validation evidence only: with cap 15 the MLP never early-stopped; with cap 30 its best
# validation epoch was 29 (cap hit); with cap 40 it early-stops at epoch 32, best epoch still 29
# (val loss 0.00167), so the cap no longer ends training and the restored model is identical.
MAX_EPOCHS = 40
HIDDEN_1, HIDDEN_2, DROPOUT = 128, 64, 0.2


class MlpNet(nn.Module):
    """Fully connected network n_features -> 128 -> 64 -> 1 with ReLU and dropout."""

    def __init__(self, n_features: int) -> None:
        """Build the layers.

        Args:
            n_features: Number of input features.
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, HIDDEN_1), nn.ReLU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN_1, HIDDEN_2), nn.ReLU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN_2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Compute logits.

        Args:
            x: Float tensor, shape (batch, n_features).

        Returns:
            Logits, shape (batch, 1).
        """
        return self.net(x)


def run(splits: common.DataSplits, max_epochs: int | None = None,
        device: str = DEFAULT_DEVICE) -> common.ModelResult:
    """Seed, build and train the model.

    Args:
        splits: Scaled data splits.
        max_epochs: Upper bound on epochs; None uses the module's ``MAX_EPOCHS``.
        device: "cpu" (default) or "cuda".

    Returns:
        ModelResult with family "DL".
    """
    set_seed(common.SEED)  # before the model is built, so the initial weights are reproducible
    model = MlpNet(splits.x_train.shape[1])
    limit = MAX_EPOCHS if max_epochs is None else max_epochs
    return run_dl(model, KEY, NAME, splits, limit, device)
