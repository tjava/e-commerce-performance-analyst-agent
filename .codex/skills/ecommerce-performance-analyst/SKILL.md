---
name: ecommerce-performance-analyst
description: Persistent project source of truth for the E-commerce Performance Analyst Agent. Use whenever working in this repository, planning milestones, changing architecture, adding features, reviewing code, or making implementation decisions so the project remains a domain-constrained e-commerce analytics agent rather than a general-purpose data analyst.
---

# E-commerce Performance Analyst

## Core Product Goal

Build a domain-constrained AI analytics application for e-commerce transaction datasets. The system should accept CSV/XLSX uploads, validate that the dataset plausibly belongs to the e-commerce domain, profile schema and data quality, determine supported analyses from available columns, run deterministic computations, generate evidence-backed insights, validate those insights, create Plotly visualizations, and produce a structured business performance report.

Do not turn this project into a general-purpose data analyst. Reject irrelevant datasets, explain why they are unsupported, and allow legitimate but incomplete e-commerce datasets to continue with clear warnings.

## V1 Scope

Prioritize sales, product, customer, and pricing/discount performance. Adapt analyses to available columns and explicitly communicate unavailable analyses.

Non-goals unless explicitly requested:

- General-purpose arbitrary dataset analysis.
- Unsupported domains such as HR, finance-only ledgers, IoT telemetry, medical data, or generic survey analysis.
- Forecasting, inventory optimization, marketing attribution, recommendation engines, or anomaly detection beyond the stated V1 scope.
- Frontend/UI work before the relevant milestone.
- Speculative platform features, persistence, authentication, deployment, or integrations.

## Required Stack

Use Python 3.12+, uv, LangGraph, LangChain where useful for model/tool integration, Pydantic v2 structured outputs, Pandas, DuckDB, Plotly, pytest, Ruff, mypy, and python-dotenv or equivalent standard environment configuration.

Keep `pyproject.toml` as the central project configuration and use `uv.lock` for locked dependencies.

## LLM and Analytics Boundary

The LLM may reason about what to analyze, how to interpret computed results, how to phrase insights, and how to plan workflow steps. The LLM must not be trusted to perform numerical calculations.

All metrics, aggregations, joins, rankings, totals, rates, and chart data must come from deterministic Pandas and/or DuckDB computation. LangGraph nodes should coordinate services and engines, not embed Pandas/DuckDB business logic directly.

## Core Differentiators

Preserve these as defining project capabilities:

- Domain Validator: determine whether uploaded data is plausibly e-commerce transactional data; reject unrelated datasets with clear reasons; allow incomplete valid e-commerce datasets with warnings.
- Insight Validation Loop: verify generated insights against computed evidence before they reach the report; prevent unsupported claims, numerical inconsistencies, and conclusions beyond available evidence.

## Established Architecture

Maintain clear package boundaries:

- `domain`: core business concepts, value objects, enums, exceptions, and provider-neutral interfaces. Must not depend on LangChain, LangGraph, Plotly, Pandas, DuckDB, or UI frameworks.
- `application`: use cases and orchestration-level services. Coordinate domain operations and depend on abstractions where useful.
- `analytics`: deterministic analytical functionality using Pandas/DuckDB, independent of LLM reasoning.
- `agent`: LangGraph-specific workflow, graph, node, and state components. Keep orchestration separate from business logic and computation.
- `infrastructure`: concrete implementations for configuration, logging, LLM providers, filesystem/data loading, DuckDB, Pandas integrations, and future persistence.
- `interfaces`: entry points and adapters for future CLI, API, or web UI interaction.

Current foundation structure:

```text
src/ecommerce_analyst/
├── agent/
├── analytics/
├── application/
├── domain/
├── infrastructure/
├── interfaces/
└── main.py
tests/
├── fixtures/
├── integration/
└── unit/
data/
├── processed/
├── raw/
└── sample/
docs/
└── ARCHITECTURE.md
```

## Coding Principles

- Do not put business logic in `main.py`.
- Do not create giant `utils.py` or `agent.py` modules.
- Do not put Pandas/DuckDB logic inside LangGraph nodes directly.
- Do not make domain models depend on infrastructure libraries.
- Keep deterministic analytics independent from LLM reasoning.
- Keep LLM provider configuration behind replaceable abstractions.
- Use Pydantic models for structured application/agent data where appropriate.
- Prefer explicit types, small cohesive modules, and testable functions.
- Use dependency injection where it materially improves testability; avoid excessive abstractions.
- Avoid circular dependencies and unrelated restructuring.
- Never commit secrets or hardcoded API keys.

## Completed Milestone 1

Milestone 1 established foundation only:

- uv-managed Python package with `pyproject.toml` and `uv.lock`.
- Source package `ecommerce_analyst`.
- Typed environment settings in `infrastructure/config`.
- Centralized logging in `infrastructure/logging`.
- Minimal startup entry point in `main.py` that initializes settings/logging only.
- Initial domain/application/analytics/agent/infrastructure/interfaces boundaries.
- Test foundation under `tests/unit`, `tests/integration`, and `tests/fixtures`.
- Ruff and mypy configuration.
- `.env.example`, `.gitignore`, README, LICENSE, and `docs/ARCHITECTURE.md`.

Milestone 1 intentionally did not implement domain validation, data profiling, analysis engines, LangGraph nodes, insight generation, chart generation, report generation, or UI.

## Future Change Rule

Before making architectural or implementation decisions in this project, consult this skill and preserve these principles. Future milestones must build incrementally on the existing foundation. Do not broaden the product scope, bypass the established layer boundaries, collapse modules into catch-all files, or restructure the project unless the user explicitly instructs it or a clear technical need is identified and explained.
