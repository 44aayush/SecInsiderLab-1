"""Shared pytest fixtures for the Lab 4 unit tests (stdlib only).

``fixtures/sample_ddos.csv`` is a byte-for-byte copy of ``../Lab3/tests/fixtures/sample_ddos.csv``
(3,187 rows, 34 inf rows), sha256
``e11e365a1de7456954074532a1bd9c6583d7046d666b7a4ae8c360fcdd01db3f``.
Unit tests never read the 77 MB CSV.
"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(name="fixture_csv")
def _fixture_csv() -> Path:
    """Return the path of the small sample CSV.

    Returns:
        Path of tests/fixtures/sample_ddos.csv.
    """
    return FIXTURES / "sample_ddos.csv"


@pytest.fixture(name="always_malicious_path")
def _always_malicious_path() -> Path:
    """Return the path of the always-Malicious stub model (created by T3.2).

    Returns:
        Path of tests/fixtures/always_malicious.json.
    """
    return FIXTURES / "always_malicious.json"
