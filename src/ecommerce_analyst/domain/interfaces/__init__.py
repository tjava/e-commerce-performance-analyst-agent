"""Domain-level protocols and interfaces."""

from ecommerce_analyst.domain.interfaces.dataset_reader import DatasetReader
from ecommerce_analyst.domain.interfaces.llm import LLMClient

__all__ = ["DatasetReader", "LLMClient"]
