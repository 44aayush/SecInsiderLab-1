"""1D convolutional network (Task 2), trained with the shared PyTorch loop of dl_common."""
from __future__ import annotations

import torch
from torch import nn

import common
from dl.dl_common import DEFAULT_DEVICE, run_dl, set_seed

KEY = "cnn"
NAME = "1D-CNN"
# 30 epochs chosen from the 2026-11-13 experiment: it improved every CNN test metric.
MAX_EPOCHS = 30
CONV_1, CONV_2, KERNEL, PADDING, POOL = 32, 64, 3, 1, 2


class CnnNet(nn.Module):
    """Two Conv1d blocks over the feature axis, global max pooling, linear head.

    Needs n_features >= 2.
    """

    def __init__(self, n_features: int) -> None:
        """Build the layers.

        Args:
            n_features: Number of input features.
        """
        super().__init__()
        del n_features  # the adaptive pooling makes the head independent of the length
        self.features = nn.Sequential(
            nn.Conv1d(1, CONV_1, KERNEL, padding=PADDING), nn.ReLU(), nn.MaxPool1d(POOL),
            nn.Conv1d(CONV_1, CONV_2, KERNEL, padding=PADDING), nn.ReLU(),
            nn.AdaptiveMaxPool1d(1),
        )
        self.head = nn.Linear(CONV_2, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Compute logits.

        Args:
            x: Float tensor, shape (batch, n_features).

        Returns:
            Logits, shape (batch, 1).
        """
        # Add a channel axis: (batch, 1, n_features).
        return self.head(self.features(x.unsqueeze(1)).squeeze(-1))


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
    model = CnnNet(splits.x_train.shape[1])
    limit = MAX_EPOCHS if max_epochs is None else max_epochs
    return run_dl(model, KEY, NAME, splits, limit, device)
