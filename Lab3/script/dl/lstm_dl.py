"""LSTM over the feature sequence (Task 2), trained with the shared PyTorch loop of dl_common."""
from __future__ import annotations

import torch
from torch import nn

import common
from dl.dl_common import DEFAULT_DEVICE, run_dl, set_seed

KEY = "lstm"
NAME = "LSTM"
# Stays at 15 (the default): the 2026-11-13 experiment showed 30 epochs worsened the
# LSTM's precision and FP.
MAX_EPOCHS = common.DL_DEFAULT_MAX_EPOCHS
HIDDEN_SIZE = 32


class LstmNet(nn.Module):
    """LSTM reading the features as a sequence of length n_features with 1 channel."""

    def __init__(self, n_features: int) -> None:
        """Build the layers.

        Args:
            n_features: Number of input features.
        """
        super().__init__()
        del n_features  # the LSTM is length-agnostic; kept for the shared constructor contract
        # batch_first=True: input is (batch, time, channel); without it the batch is read as time.
        self.lstm = nn.LSTM(input_size=1, hidden_size=HIDDEN_SIZE, batch_first=True)
        self.head = nn.Linear(HIDDEN_SIZE, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Compute logits.

        Args:
            x: Float tensor, shape (batch, n_features).

        Returns:
            Logits, shape (batch, 1).
        """
        # One scalar per time step; n_features is the sequence length.
        _, (h_n, _) = self.lstm(x.unsqueeze(-1))
        return self.head(h_n[-1])  # last layer hidden state, shape (batch, 32)


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
    model = LstmNet(splits.x_train.shape[1])
    limit = MAX_EPOCHS if max_epochs is None else max_epochs
    return run_dl(model, KEY, NAME, splits, limit, device)
