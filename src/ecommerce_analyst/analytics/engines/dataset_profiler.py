"""Pandas-backed dataset profiler and data quality analysis engine.

Computes dimensional overviews, per-column descriptive statistics,
data quality anomalies, and refined analytical capability assessments
for an accepted e-commerce dataset without calling any LLM.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from ecommerce_analyst.domain.models.dataset import IngestedDataset
from ecommerce_analyst.domain.profiling.enums import (
    ColumnRole,
    QualityIssueCode,
    QualityIssueSeverity,
)
from ecommerce_analyst.domain.profiling.result import (
    CapabilityAssessment,
    CategoricalStats,
    ColumnProfile,
    DatasetOverview,
    DatasetProfile,
    DateRangeStats,
    NumericStats,
    QualityIssue,
)
from ecommerce_analyst.domain.validation.enums import EcommerceCapability
from ecommerce_analyst.domain.validation.result import DomainValidationResult

logger = logging.getLogger(__name__)

_SIGNAL_TO_ROLE: dict[str, ColumnRole] = {
    "order_identifier": ColumnRole.ORDER_IDENTIFIER,
    "product_identifier": ColumnRole.PRODUCT_IDENTIFIER,
    "revenue_or_price": ColumnRole.REVENUE,
    "transaction_date": ColumnRole.DATE,
    "quantity": ColumnRole.QUANTITY,
    "customer_identifier": ColumnRole.CUSTOMER_IDENTIFIER,
    "product_category": ColumnRole.CATEGORY,
    "discount_or_promo": ColumnRole.DISCOUNT,
    "geographic": ColumnRole.GEOGRAPHIC,
    "payment_method": ColumnRole.PAYMENT_METHOD,
    "order_status": ColumnRole.STATUS,
}

_SEVERITY_ORDER: dict[QualityIssueSeverity, int] = {
    QualityIssueSeverity.BLOCKING: 0,
    QualityIssueSeverity.WARNING: 1,
    QualityIssueSeverity.INFO: 2,
}


class DatasetProfiler:
    """Profiles ingested datasets and evaluates data quality."""

    def profile(
        self,
        dataset: IngestedDataset,
        validation_result: DomainValidationResult,
    ) -> DatasetProfile:
        """Generate a complete DatasetProfile from an IngestedDataset."""
        profiled_at = datetime.now(UTC)
        df = _build_dataframe(dataset)
        total_rows = len(df)
        total_cols = len(df.columns)

        # 1. Dataset Overview
        duplicate_rows = int(df.duplicated().sum()) if total_rows > 0 else 0
        duplicate_pct = (
            round((duplicate_rows / total_rows) * 100.0, 2) if total_rows > 0 else 0.0
        )
        overview = DatasetOverview(
            filename=dataset.metadata.filename,
            row_count=total_rows,
            column_count=total_cols,
            duplicate_row_count=duplicate_rows,
            duplicate_row_pct=duplicate_pct,
            file_size_bytes=dataset.metadata.file_size_bytes,
        )

        # 2. Map Column Roles from detected signals
        column_roles = _resolve_column_roles(dataset, validation_result)

        # 3. Column Profiles & Issues
        column_profiles: list[ColumnProfile] = []
        quality_issues: list[QualityIssue] = []
        profiling_warnings: list[str] = list(dataset.metadata.parsing_warnings)

        # Dataset-level duplicate rows issue
        if duplicate_rows > 0:
            quality_issues.append(
                QualityIssue(
                    column=None,
                    code=QualityIssueCode.DUPLICATE_ROWS,
                    severity=QualityIssueSeverity.WARNING,
                    message=(
                        f"Dataset contains {duplicate_rows} duplicate rows ({duplicate_pct}%)."
                    ),
                    affected_row_count=duplicate_rows,
                    affected_pct=duplicate_pct,
                )
            )

        for col_meta in dataset.metadata.columns:
            col_name = col_meta.name
            role = column_roles.get(col_name, ColumnRole.UNKNOWN)
            series = df[col_name] if col_name in df.columns else pd.Series(dtype=object)

            col_profile, col_issues = _profile_column(
                series=series,
                col_meta_index=col_meta.index,
                col_meta_name=col_name,
                inferred_dtype=col_meta.inferred_dtype,
                role=role,
                total_rows=total_rows,
            )
            column_profiles.append(col_profile)
            quality_issues.extend(col_issues)

        # Sort quality issues by severity (BLOCKING first, then WARNING, then INFO)
        quality_issues.sort(key=lambda issue: _SEVERITY_ORDER[issue.severity])

        # 4. Refine Capability Assessments
        capability_assessments = _assess_capabilities(
            validation_result=validation_result,
            column_profiles=column_profiles,
            quality_issues=quality_issues,
        )

        # 5. Analytical Dimensions
        analytical_dimensions = _identify_analytical_dimensions(column_profiles)

        return DatasetProfile(
            overview=overview,
            column_profiles=tuple(column_profiles),
            quality_issues=tuple(quality_issues),
            capability_assessments=tuple(capability_assessments),
            analytical_dimensions=tuple(analytical_dimensions),
            profiling_warnings=tuple(profiling_warnings),
            profiled_at=profiled_at,
        )


def _build_dataframe(dataset: IngestedDataset) -> pd.DataFrame:
    """Reconstruct a pandas DataFrame from IngestedDataset."""
    if not dataset.records:
        cols = [c.name for c in dataset.metadata.columns]
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(dataset.records)


def _resolve_column_roles(
    dataset: IngestedDataset,
    validation_result: DomainValidationResult,
) -> dict[str, ColumnRole]:
    """Map dataset columns to ColumnRole using matched signals."""
    roles: dict[str, ColumnRole] = {}
    matched_map = {ms.matched_column: ms.signal_name for ms in validation_result.detected_signals}

    for col in dataset.metadata.columns:
        if col.name in matched_map:
            sig = matched_map[col.name]
            roles[col.name] = _SIGNAL_TO_ROLE.get(sig, ColumnRole.UNKNOWN)
        else:
            roles[col.name] = ColumnRole.UNKNOWN
    return roles


def _profile_column(
    series: pd.Series[Any],
    col_meta_index: int,
    col_meta_name: str,
    inferred_dtype: str,
    role: ColumnRole,
    total_rows: int,
) -> tuple[ColumnProfile, list[QualityIssue]]:
    """Profile an individual column and detect any anomalies."""
    null_count = int(series.isna().sum())
    null_pct = round((null_count / total_rows) * 100.0, 2) if total_rows > 0 else 0.0
    unique_count = int(series.nunique(dropna=True))
    is_constant = bool(unique_count == 1 and total_rows > 1 and null_count == 0)

    issues: list[QualityIssue] = []

    # Check null rates
    if null_pct > 80.0 and total_rows > 0:
        issues.append(
            QualityIssue(
                column=col_meta_name,
                code=QualityIssueCode.CRITICAL_NULL_RATE,
                severity=QualityIssueSeverity.BLOCKING,
                message=f"Column '{col_meta_name}' has critical null rate of {null_pct}%.",
                affected_row_count=null_count,
                affected_pct=null_pct,
            )
        )
    elif null_pct > 30.0 and total_rows > 0:
        issues.append(
            QualityIssue(
                column=col_meta_name,
                code=QualityIssueCode.HIGH_NULL_RATE,
                severity=QualityIssueSeverity.WARNING,
                message=f"Column '{col_meta_name}' has high null rate of {null_pct}%.",
                affected_row_count=null_count,
                affected_pct=null_pct,
            )
        )
    elif null_count > 0:
        issues.append(
            QualityIssue(
                column=col_meta_name,
                code=QualityIssueCode.MISSING_VALUES,
                severity=QualityIssueSeverity.INFO,
                message=f"Column '{col_meta_name}' has {null_count} missing values ({null_pct}%).",
                affected_row_count=null_count,
                affected_pct=null_pct,
            )
        )

    # Constant column check
    if is_constant:
        issues.append(
            QualityIssue(
                column=col_meta_name,
                code=QualityIssueCode.CONSTANT_COLUMN,
                severity=QualityIssueSeverity.INFO,
                message=f"Column '{col_meta_name}' contains a constant value across all rows.",
                affected_row_count=total_rows,
                affected_pct=100.0,
            )
        )

    # Check duplicate order IDs if order identifier
    if role == ColumnRole.ORDER_IDENTIFIER and total_rows > 0:
        duplicate_orders = int(series.duplicated().sum())
        if duplicate_orders > 0:
            dup_pct = round((duplicate_orders / total_rows) * 100.0, 2)
            issues.append(
                QualityIssue(
                    column=col_meta_name,
                    code=QualityIssueCode.DUPLICATE_ORDER_IDS,
                    severity=QualityIssueSeverity.WARNING,
                    message=(
                        f"Order identifier column '{col_meta_name}' has "
                        f"{duplicate_orders} non-unique entries ({dup_pct}%)."
                    ),
                    affected_row_count=duplicate_orders,
                    affected_pct=dup_pct,
                )
            )

    numeric_stats: NumericStats | None = None
    date_stats: DateRangeStats | None = None
    categorical_stats: CategoricalStats | None = None

    # Check if column should be profiled as numeric
    is_numeric_type = pd.api.types.is_numeric_dtype(series)
    should_be_numeric = is_numeric_type or role in (
        ColumnRole.REVENUE,
        ColumnRole.QUANTITY,
        ColumnRole.DISCOUNT,
    )

    if should_be_numeric:
        num_series = pd.to_numeric(series, errors="coerce")
        valid_nums = num_series.dropna()
        if len(valid_nums) > 0:
            zero_count = int((valid_nums == 0).sum())
            negative_count = int((valid_nums < 0).sum())
            mean_val = float(valid_nums.mean())
            std_val = float(valid_nums.std()) if len(valid_nums) > 1 else 0.0
            if np.isnan(std_val):
                std_val = 0.0

            numeric_stats = NumericStats(
                min_value=float(valid_nums.min()),
                max_value=float(valid_nums.max()),
                mean=round(mean_val, 4),
                median=float(valid_nums.median()),
                std=round(std_val, 4),
                p25=float(valid_nums.quantile(0.25)),
                p75=float(valid_nums.quantile(0.75)),
                zero_count=zero_count,
                negative_count=negative_count,
            )

            # Role-specific numeric quality checks
            if role == ColumnRole.QUANTITY:
                if negative_count > 0:
                    neg_pct = round((negative_count / total_rows) * 100.0, 2)
                    issues.append(
                        QualityIssue(
                            column=col_meta_name,
                            code=QualityIssueCode.NEGATIVE_QUANTITY,
                            severity=QualityIssueSeverity.WARNING,
                            message=(
                                f"Quantity column '{col_meta_name}' contains "
                                f"{negative_count} negative values."
                            ),
                            affected_row_count=negative_count,
                            affected_pct=neg_pct,
                        )
                    )
                if zero_count > 0:
                    zero_pct = round((zero_count / total_rows) * 100.0, 2)
                    issues.append(
                        QualityIssue(
                            column=col_meta_name,
                            code=QualityIssueCode.ZERO_QUANTITY,
                            severity=QualityIssueSeverity.WARNING,
                            message=(
                                f"Quantity column '{col_meta_name}' contains "
                                f"{zero_count} zero values."
                            ),
                            affected_row_count=zero_count,
                            affected_pct=zero_pct,
                        )
                    )

            elif role == ColumnRole.REVENUE:
                if negative_count > 0:
                    neg_pct = round((negative_count / total_rows) * 100.0, 2)
                    issues.append(
                        QualityIssue(
                            column=col_meta_name,
                            code=QualityIssueCode.NEGATIVE_PRICE,
                            severity=QualityIssueSeverity.WARNING,
                            message=(
                                f"Revenue/price column '{col_meta_name}' contains "
                                f"{negative_count} negative values."
                            ),
                            affected_row_count=negative_count,
                            affected_pct=neg_pct,
                        )
                    )
                if zero_count > 0:
                    zero_pct = round((zero_count / total_rows) * 100.0, 2)
                    issues.append(
                        QualityIssue(
                            column=col_meta_name,
                            code=QualityIssueCode.ZERO_PRICE,
                            severity=QualityIssueSeverity.WARNING,
                            message=(
                                f"Revenue/price column '{col_meta_name}' contains "
                                f"{zero_count} zero values."
                            ),
                            affected_row_count=zero_count,
                            affected_pct=zero_pct,
                        )
                    )
                if std_val > 0.0:
                    outlier_bound = mean_val + 5 * std_val
                    outlier_count = int((valid_nums > outlier_bound).sum())
                    if outlier_count > 0:
                        outlier_pct = round((outlier_count / total_rows) * 100.0, 2)
                        issues.append(
                            QualityIssue(
                                column=col_meta_name,
                                code=QualityIssueCode.IMPLAUSIBLE_PRICE,
                                severity=QualityIssueSeverity.INFO,
                                message=(
                                    f"Revenue column '{col_meta_name}' contains "
                                    f"{outlier_count} potential outlier values (> 5 std dev)."
                                ),
                                affected_row_count=outlier_count,
                                affected_pct=outlier_pct,
                            )
                        )

    # Check if column should be profiled as date
    is_datetime_type = pd.api.types.is_datetime64_any_dtype(series)
    should_be_date = is_datetime_type or role == ColumnRole.DATE

    if should_be_date:
        parsed_dates = pd.to_datetime(series, errors="coerce", format="mixed")
        non_null_count = int(series.notna().sum())
        valid_date_count = int(parsed_dates.notna().sum())
        unparseable_count = non_null_count - valid_date_count

        min_date_str: str | None = None
        max_date_str: str | None = None
        span_days: int | None = None
        future_count = 0

        if valid_date_count > 0:
            min_dt = parsed_dates.min()
            max_dt = parsed_dates.max()
            min_date_str = min_dt.isoformat()
            max_date_str = max_dt.isoformat()
            span_days = (max_dt - min_dt).days

            # Future date detection
            now_dt = pd.Timestamp.now()
            # Normalize timezone comparison if needed
            if parsed_dates.dt.tz is not None:
                now_dt = pd.Timestamp.now(tz=parsed_dates.dt.tz)
            future_count = int((parsed_dates > now_dt).sum())

        date_stats = DateRangeStats(
            min_date=min_date_str,
            max_date=max_date_str,
            date_span_days=span_days,
            unparseable_count=unparseable_count,
            future_date_count=future_count,
        )

        if unparseable_count > 0:
            is_all_unparseable = valid_date_count == 0
            sev = (
                QualityIssueSeverity.BLOCKING
                if is_all_unparseable
                else QualityIssueSeverity.WARNING
            )
            unp_pct = round((unparseable_count / total_rows) * 100.0, 2)
            issues.append(
                QualityIssue(
                    column=col_meta_name,
                    code=QualityIssueCode.UNPARSEABLE_DATE,
                    severity=sev,
                    message=(
                        f"Date column '{col_meta_name}' has "
                        f"{unparseable_count} unparseable values ({unp_pct}%)."
                    ),
                    affected_row_count=unparseable_count,
                    affected_pct=unp_pct,
                )
            )

        if future_count > 0:
            fut_pct = round((future_count / total_rows) * 100.0, 2)
            issues.append(
                QualityIssue(
                    column=col_meta_name,
                    code=QualityIssueCode.FUTURE_DATES,
                    severity=QualityIssueSeverity.WARNING,
                    message=(
                        f"Date column '{col_meta_name}' contains "
                        f"{future_count} future dates ({fut_pct}%)."
                    ),
                    affected_row_count=future_count,
                    affected_pct=fut_pct,
                )
            )

    # Categorical Stats (for string/object/categorical columns with unique_count > 0)
    if not is_numeric_type and not is_datetime_type and unique_count > 0:
        val_counts = series.dropna().astype(str).value_counts().head(5)
        top_tuples = tuple((str(k), int(v)) for k, v in val_counts.items())
        categorical_stats = CategoricalStats(
            unique_count=unique_count,
            null_count=null_count,
            top_values=top_tuples,
        )

        if role == ColumnRole.CATEGORY and unique_count == 1:
            issues.append(
                QualityIssue(
                    column=col_meta_name,
                    code=QualityIssueCode.SINGLE_CATEGORY_VALUE,
                    severity=QualityIssueSeverity.INFO,
                    message=(
                        f"Category column '{col_meta_name}' has only 1 distinct category value."
                    ),
                    affected_row_count=total_rows,
                    affected_pct=100.0,
                )
            )

    col_profile = ColumnProfile(
        name=col_meta_name,
        index=col_meta_index,
        inferred_dtype=inferred_dtype,
        role=role,
        null_count=null_count,
        null_pct=null_pct,
        unique_count=unique_count,
        is_constant=is_constant,
        numeric_stats=numeric_stats,
        date_stats=date_stats,
        categorical_stats=categorical_stats,
    )
    return col_profile, issues


def _assess_capabilities(
    validation_result: DomainValidationResult,
    column_profiles: list[ColumnProfile],
    quality_issues: list[QualityIssue],
) -> list[CapabilityAssessment]:
    """Refine capability assessments based on actual data quality findings."""
    assessments: list[CapabilityAssessment] = []
    profiles_by_role = {cp.role: cp for cp in column_profiles}

    for cap in EcommerceCapability:
        # If M3 already determined capability was unavailable, keep it unavailable
        if cap in validation_result.unavailable_capabilities:
            assessments.append(
                CapabilityAssessment(
                    capability=cap,
                    available=False,
                    limiting_issues=(),
                    confidence_note="Required signal for capability was not detected in dataset.",
                )
            )
            continue

        limiting: list[QualityIssueCode] = []
        is_available = True
        notes: list[str] = []

        if cap == EcommerceCapability.REVENUE_ANALYSIS:
            rev_prof = profiles_by_role.get(ColumnRole.REVENUE)
            if rev_prof is None or rev_prof.null_pct >= 80.0:
                is_available = False
                limiting.append(QualityIssueCode.CRITICAL_NULL_RATE)
                notes.append("Revenue data is missing or over 80% null.")
            elif rev_prof.null_pct > 30.0:
                limiting.append(QualityIssueCode.HIGH_NULL_RATE)
                notes.append(f"Revenue column has {rev_prof.null_pct}% nulls.")
            rev_issues = [
                i.code for i in quality_issues if i.column == (rev_prof.name if rev_prof else None)
            ]
            if QualityIssueCode.NEGATIVE_PRICE in rev_issues:
                limiting.append(QualityIssueCode.NEGATIVE_PRICE)
                notes.append("Negative prices present; totals may be affected.")

        elif cap == EcommerceCapability.TREND_ANALYSIS:
            date_prof = profiles_by_role.get(ColumnRole.DATE)
            if (
                date_prof is None
                or date_prof.date_stats is None
                or date_prof.date_stats.min_date is None
            ):
                is_available = False
                limiting.append(QualityIssueCode.UNPARSEABLE_DATE)
                notes.append("Dates are missing or cannot be parsed.")
            else:
                if (
                    date_prof.date_stats.unparseable_count > 0
                    and date_prof.null_pct + (date_prof.date_stats.unparseable_count) > 0
                ):
                    limiting.append(QualityIssueCode.UNPARSEABLE_DATE)
                    notes.append("Some date records are unparseable.")
                if date_prof.date_stats.future_date_count > 0:
                    limiting.append(QualityIssueCode.FUTURE_DATES)
                    notes.append("Future dates detected in trend range.")

        elif cap == EcommerceCapability.CUSTOMER_ANALYSIS:
            cust_prof = profiles_by_role.get(ColumnRole.CUSTOMER_IDENTIFIER)
            if cust_prof is None or cust_prof.null_pct >= 80.0:
                is_available = False
                limiting.append(QualityIssueCode.CRITICAL_NULL_RATE)
                notes.append("Customer identifier is missing or mostly null.")
            elif cust_prof.null_pct > 30.0:
                limiting.append(QualityIssueCode.HIGH_NULL_RATE)
                notes.append(f"Customer identifier has {cust_prof.null_pct}% nulls.")

        elif cap == EcommerceCapability.PRODUCT_ANALYSIS:
            prod_prof = profiles_by_role.get(ColumnRole.PRODUCT_IDENTIFIER)
            if prod_prof is None or prod_prof.null_pct >= 80.0:
                is_available = False
                limiting.append(QualityIssueCode.CRITICAL_NULL_RATE)
                notes.append("Product identifiers missing or mostly null.")

        note_str = " ".join(notes) if notes else "Data quality is sufficient for analysis."
        assessments.append(
            CapabilityAssessment(
                capability=cap,
                available=is_available,
                limiting_issues=tuple(limiting),
                confidence_note=note_str,
            )
        )

    return assessments


def _identify_analytical_dimensions(column_profiles: list[ColumnProfile]) -> list[str]:
    """Identify columns suitable as grouping dimensions in analysis."""
    dims: list[str] = []
    dimension_roles = {
        ColumnRole.CATEGORY,
        ColumnRole.GEOGRAPHIC,
        ColumnRole.PAYMENT_METHOD,
        ColumnRole.STATUS,
        ColumnRole.PRODUCT_IDENTIFIER,
        ColumnRole.CUSTOMER_IDENTIFIER,
    }

    for cp in column_profiles:
        # Exclude constant columns or columns with critical null rates
        if cp.is_constant or cp.null_pct >= 80.0:
            continue
        has_cardinality = (
            cp.categorical_stats is not None and 1 < cp.unique_count <= 100
        )
        if cp.role in dimension_roles or has_cardinality:
            dims.append(cp.name)

    return dims
