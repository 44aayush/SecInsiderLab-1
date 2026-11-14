"""Shared training and scoring helpers for the PyTorch models (Task 2).

Every ``*_dl.py`` module delegates to ``run_dl`` so that seeding contracts,
early stopping, timing and score extraction are identical for MLP, LSTM and
1D-CNN (CLAUDE.md 4.9 and 5). The default device is the CPU; pass ``device="cuda"``
to train on an NVIDIA GPU. GPU results can differ slightly from CPU results: the
CUDA/cuDNN kernels are not bit-identical to the CPU ones, even with cuDNN deterministic
mode on (set by ``configure_device``).
"""
from __future__ import annotations

import copy
import logging
import random
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

import common

log = logging.getLogger(__name__)

FAMILY = "DL"
DEFAULT_DEVICE = "cpu"


def resolve_device(requested: str) -> str:
    """Turn "auto" into "cuda" or "cpu"; pass explicit choices through.

    Args:
        requested: "auto", "cpu" or "cuda".

    Returns:
        "cuda" if requested (or auto and available), otherwise "cpu".

    Raises:
        RuntimeError: If "cuda" is requested but not available.
    """
    available = torch.cuda.is_available()
    if requested == "cuda" and not available:
        raise RuntimeError("--device cuda requested but torch.cuda.is_available() is False")
    if requested == "auto":
        return "cuda" if available else "cpu"
    return requested


def configure_device(device: str) -> None:
    """Make cuDNN as reproducible as it can be when running on CUDA.

    Args:
        device: "cpu" or "cuda".
    """
    if device == "cuda":
        # Benchmark mode picks kernels by timing, which varies per run; turn it off.
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def set_seed(seed: int) -> None:
    """Seed Python, NumPy and torch so weight initialisation is reproducible.

    Args:
        seed: Seed value, normally ``common.SEED``.
    """
    random.seed(seed)
    np.random.seed(seed)  # legacy global RNG, seeded in case a library still uses it
    torch.manual_seed(seed)


def make_loader(x: np.ndarray, y: np.ndarray, shuffle: bool) -> DataLoader:
    """Wrap arrays in a batched DataLoader.

    Args:
        x: Feature array, shape (n, f).
        y: Binary labels, shape (n,).
        shuffle: Shuffle every epoch (training) or keep the order (evaluation).

    Returns:
        DataLoader with batch size ``DL_BATCH_SIZE``.
    """
    dataset = TensorDataset(torch.as_tensor(x, dtype=torch.float32),
                            torch.as_tensor(y, dtype=torch.float32))  # BCE needs float labels
    # A dedicated seeded generator makes the shuffle order independent of global RNG use.
    generator = torch.Generator().manual_seed(common.SEED)
    return DataLoader(dataset, batch_size=common.DL_BATCH_SIZE, shuffle=shuffle,
                      generator=generator)


class EarlyStopper:
    """Track the best validation loss and keep a copy of the best weights.

    Attributes:
        patience: Epochs without improvement that trigger a stop.
        best_loss: Lowest validation loss seen so far.
        best_state: Deep copy of the state_dict at that loss.
        bad_epochs: Epochs since the last improvement.
    """

    def __init__(self, patience: int) -> None:
        """Create the stopper.

        Args:
            patience: Number of non-improving epochs tolerated before stopping.
        """
        self.patience = patience
        self.best_loss = float("inf")
        self.best_state: dict[str, torch.Tensor] | None = None
        self.bad_epochs = 0

    def update(self, val_loss: float, model: nn.Module) -> bool:
        """Record one epoch.

        Args:
            val_loss: Validation loss of this epoch.
            model: Model whose weights are snapshotted on improvement.

        Returns:
            True when training should stop.
        """
        if val_loss < self.best_loss:
            self.best_loss = val_loss
            # deepcopy: state_dict() returns live references that later steps overwrite.
            self.best_state = copy.deepcopy(model.state_dict())
            self.bad_epochs = 0
        else:
            self.bad_epochs += 1
        return self.bad_epochs >= self.patience

    def restore(self, model: nn.Module) -> None:
        """Load the best weights back into the model.

        Args:
            model: Model to restore; left unchanged if no epoch was recorded.
        """
        if self.best_state is not None:
            model.load_state_dict(self.best_state)


def _train_epoch(model: nn.Module, loader: DataLoader, loss_fn: nn.Module,
                 optimizer: torch.optim.Optimizer, device: str) -> float:
    """Run one optimisation pass over the training data.

    Args:
        model: Network returning logits of shape (batch, 1).
        loader: Shuffled training loader.
        loss_fn: BCEWithLogitsLoss.
        optimizer: Adam optimiser.
        device: Device the model lives on; each batch is moved there.

    Returns:
        Mean training loss per sample.
    """
    model.train()  # enables dropout
    total, count = 0.0, 0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)  # batches stay on the CPU until used
        optimizer.zero_grad()
        loss = loss_fn(model(xb).squeeze(1), yb)
        loss.backward()
        optimizer.step()
        total += loss.item() * len(yb)  # weight by batch size: the last batch is smaller
        count += len(yb)
    return total / count


def _eval_loss(model: nn.Module, loader: DataLoader, loss_fn: nn.Module, device: str) -> float:
    """Compute the mean loss without updating weights.

    Args:
        model: Network returning logits of shape (batch, 1).
        loader: Evaluation loader.
        loss_fn: BCEWithLogitsLoss.
        device: Device the model lives on; each batch is moved there.

    Returns:
        Mean loss per sample.
    """
    model.eval()  # disables dropout
    total, count = 0.0, 0
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            total += loss_fn(model(xb).squeeze(1), yb).item() * len(yb)
            count += len(yb)
    return total / count


def train_model(model: nn.Module, splits: common.DataSplits, max_epochs: int,
                device: str = DEFAULT_DEVICE) -> dict:
    """Train with Adam and BCE, early stopping on the validation loss.

    Args:
        model: Untrained network returning logits.
        splits: Scaled data splits; only train and validation are used.
        max_epochs: Upper bound on epochs.
        device: "cpu" or "cuda"; the model is moved there before the optimiser is built.

    Returns:
        History {"train_loss": [...], "val_loss": [...]}, one entry per epoch run.
        The best-epoch weights are restored into ``model``.
    """
    model.to(device)  # before Adam is created, so the optimiser state lives on the same device
    train_loader = make_loader(splits.x_train, splits.y_train, shuffle=True)
    val_loader = make_loader(splits.x_val, splits.y_val, shuffle=False)
    loss_fn = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=common.DL_LR)
    stopper = EarlyStopper(common.DL_PATIENCE)
    history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
    for epoch in range(1, max_epochs + 1):
        start = time.perf_counter()
        train_loss = _train_epoch(model, train_loader, loss_fn, optimizer, device)
        val_loss = _eval_loss(model, val_loader, loss_fn, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        log.info("epoch %d/%d: train_loss %.5f, val_loss %.5f (%.1f s)",
                 epoch, max_epochs, train_loss, val_loss, time.perf_counter() - start)
        if stopper.update(val_loss, model):
            log.info("early stop at epoch %d (best val_loss %.5f)", epoch, stopper.best_loss)
            break
    stopper.restore(model)  # report the best epoch, not the last one
    return history


def predict_scores(model: nn.Module, x: np.ndarray, device: str = DEFAULT_DEVICE) -> np.ndarray:
    """Compute P(DDoS) for every row.

    Args:
        model: Trained network returning logits.
        x: Feature array, shape (n, f).
        device: Device the model lives on.

    Returns:
        float32 array of shape (n,) with values in [0, 1].
    """
    model.eval()
    scores = []
    with torch.no_grad():
        for start in range(0, len(x), common.DL_BATCH_SIZE):  # batched to bound memory
            batch = torch.as_tensor(x[start:start + common.DL_BATCH_SIZE], dtype=torch.float32)
            # Sigmoid on the device, then back to CPU numpy for the metric code.
            scores.append(torch.sigmoid(model(batch.to(device)).squeeze(1)).cpu().numpy())
    return np.concatenate(scores)


# Six parameters: the contract signature (CLAUDE.md 5) plus the device; a wrapper object
# would only hide them.
def run_dl(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        model: nn.Module, key: str, name: str, splits: common.DataSplits,
        max_epochs: int, device: str = DEFAULT_DEVICE) -> common.ModelResult:
    """Train a network, then score the validation and test sets.

    Does not seed: callers seed before building the model (CLAUDE.md 4.9).

    Args:
        model: Untrained network.
        key: Registry key, e.g. "mlp".
        name: Display name.
        splits: Scaled data splits.
        max_epochs: Upper bound on epochs.
        device: "cpu" (default) or "cuda".

    Returns:
        ModelResult (family "DL") with P(DDoS) scores, timings and history.
    """
    configure_device(device)
    log.info("%s: training on device %s", name, device)
    log.info("%s architecture:\n%s", name, model)
    log.info("%s settings: batch %d, lr %g, max epochs %d, patience %d", name,
             common.DL_BATCH_SIZE, common.DL_LR, max_epochs, common.DL_PATIENCE)
    start = time.perf_counter()
    history = train_model(model, splits, max_epochs, device)
    train_time = time.perf_counter() - start
    # Validation scoring is not timed: only the test prediction is reported (CLAUDE.md 4.11).
    val_score = predict_scores(model, splits.x_val, device)
    start = time.perf_counter()
    test_score = predict_scores(model, splits.x_test, device)
    predict_time = time.perf_counter() - start
    log.info("%s: train %.2f s, test predict %.2f s", name, train_time, predict_time)
    return common.ModelResult(key, name, FAMILY, val_score, test_score, train_time,
                              predict_time, history)
