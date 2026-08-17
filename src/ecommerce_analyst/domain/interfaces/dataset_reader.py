"""Dataset reader interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ecommerce_analyst.domain.models.dataset import DatasetIngestionLimits, IngestedDataset


class DatasetReader(Protocol):
    """Provider-neutral interface for loading uploaded dataset files."""

    def read(self, file_path: Path, limits: DatasetIngestionLimits) -> IngestedDataset:
        """Read a supported dataset file into the internal representation."""
