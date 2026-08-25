"""Application use case for validating an ingested dataset."""

from __future__ import annotations

from dataclasses import dataclass, field

from ecommerce_analyst.application.services.domain_validator import EcommerceDomainValidator
from ecommerce_analyst.domain.models.dataset import IngestedDataset
from ecommerce_analyst.domain.validation.result import DomainValidationResult


@dataclass(frozen=True, slots=True)
class ValidateDatasetUseCase:
    """Determine whether an ingested dataset belongs to the e-commerce domain.

    This use case is a thin coordinator: it delegates all classification logic
    to ``EcommerceDomainValidator`` and returns the structured result directly.

    Example usage::

        validator = EcommerceDomainValidator()
        use_case = ValidateDatasetUseCase(validator=validator)
        result = use_case.execute(dataset)
        if result.is_accepted:
            ...
    """

    validator: EcommerceDomainValidator = field(
        default_factory=EcommerceDomainValidator
    )

    def execute(self, dataset: IngestedDataset) -> DomainValidationResult:
        """Run domain validation on a technically loaded dataset.

        Parameters
        ----------
        dataset:
            A fully ingested dataset produced by ``IngestDatasetUseCase``.

        Returns
        -------
        DomainValidationResult
            Fully structured result — never raises for valid input regardless
            of whether the dataset passes or fails domain validation.
        """
        return self.validator.validate(dataset)
