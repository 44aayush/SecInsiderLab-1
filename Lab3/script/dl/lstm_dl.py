"""LSTM over the feature sequence (Task 2), trained with the shared PyTorch loop of dl_common."""
from __future__ import annotations

import torch
from torch import nn

import common
from dl.dl_common import DEFAULT_DEVICE, TrainSettings, run_dl, set_seed

KEY = "lstm"
NAME = "LSTM"
# The LSTM's val loss oscillates with the shared lr 1e-3 / patience 3 (CLAUDE.md 9), so it has
# its own settings, chosen by lowest val loss among three grid configs (2026-11-15, clip 1.0):
# lr 5e-4/patience 5/cap 30 -> 0.00567 (best epoch 29, hit the cap); lr 3e-4/p5/cap 40 -> 0.00720;
# lr 5e-4/patience 7/cap 40 -> 0.00529 (best epoch 31, early stop at 38) = chosen.
MAX_EPOCHS = 40  # cap 30 was hit at best epoch 29, so 40 gives headroom
LEARNING_RATE = 5e-4  # smaller steps damp the oscillation
PATIENCE = 7  # rides out the oscillation before declaring the minimum found
HIDDEN_SIZE = 32
# Max total gradient L2 norm per step. The LSTM loss spikes on CPU and GPU (exploding
# gradients, CLAUDE.md 9); 1.0 is the common default for RNNs. Only the LSTM clips.
GRAD_CLIP_NORM = 1.0


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
    # Constants are read here, at call time, so experiments can monkeypatch them.
    settings = TrainSettings(lr=LEARNING_RATE, patience=PATIENCE, grad_clip_norm=GRAD_CLIP_NORM)
    return run_dl(model, KEY, NAME, splits, limit, device, settings)
