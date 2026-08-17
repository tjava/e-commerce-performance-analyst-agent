"""Application use case for ingesting uploaded datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecommerce_analyst.domain.interfaces import DatasetReader
from ecommerce_analyst.domain.models import DatasetIngestionLimits, IngestedDataset


@dataclass(frozen=True, slots=True)
class IngestDatasetUseCase:
    """Load an uploaded dataset through a configured reader."""

    reader: DatasetReader
    limits: DatasetIngestionLimits

    def execute(self, file_path: Path) -> IngestedDataset:
        """Ingest a dataset file without domain-specific semantic validation."""

        return self.reader.read(file_path, self.limits)
