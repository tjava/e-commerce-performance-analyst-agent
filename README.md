# E-commerce Performance Analyst Agent

The E-commerce Performance Analyst Agent is a domain-constrained AI analytics
application for uploaded e-commerce transaction datasets. The long-term system
will validate whether a CSV or XLSX file belongs to the supported e-commerce
domain, profile the dataset, determine which analyses are possible, run
deterministic analytics, generate evidence-backed insights, validate those
insights, create Plotly visualizations, and produce a structured business
performance report.

Current status: **Milestone 1 / foundation only**.

Analytics, domain validation, LangGraph workflows, insight generation, chart
generation, report generation, and UI functionality are not implemented yet.

## Domain Constraint

This project is intentionally not a general-purpose data analyst. Future
milestones will reject datasets that cannot reasonably be identified as
e-commerce transactional data. Legitimate e-commerce datasets with incomplete
optional fields should proceed with warnings, while unsupported datasets should
receive clear rejection reasons.

The LLM will reason about analysis planning and interpretation, but numerical
calculations must be performed by deterministic Python, Pandas, and DuckDB code.

## Architecture

The project is organized around clear package boundaries:

- `domain`: core concepts, value objects, enums, exceptions, and provider-neutral
  interfaces. This layer must not depend on Pandas, DuckDB, Plotly, LangGraph,
  LangChain, or UI frameworks.
- `application`: use cases and orchestration services that coordinate domain
  behavior.
- `analytics`: deterministic analytical functionality using Pandas and DuckDB.
- `agent`: LangGraph-specific workflow, graph, node, and state code.
- `infrastructure`: concrete adapters for configuration, logging, LLM providers,
  data loading, DuckDB, and future persistence.
- `interfaces`: external entry points such as CLI, API, or web adapters.

## Technology Stack

- Python 3.12+
- uv
- LangGraph
- LangChain
- Pydantic v2
- Pandas
- DuckDB
- Plotly
- python-dotenv
- pytest
- Ruff
- mypy

## Project Structure

```text
.
├── src/ecommerce_analyst/
│   ├── agent/
│   ├── analytics/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── interfaces/
│   └── main.py
├── tests/
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── data/
│   ├── processed/
│   ├── raw/
│   └── sample/
├── docs/
├── .env.example
├── pyproject.toml
└── README.md
```

## Local Development

Install dependencies with uv:

```bash
uv sync --dev
```

Run the foundation entry point:

```bash
uv run ecommerce-analyst
```

or:

```bash
uv run python -m ecommerce_analyst.main
```

## Environment Configuration

Copy `.env.example` to `.env` for local development and adjust values as needed.

Supported variables:

- `ECOMMERCE_ANALYST_ENV`
- `ECOMMERCE_ANALYST_LOG_LEVEL`
- `ECOMMERCE_ANALYST_LLM_PROVIDER`
- `ECOMMERCE_ANALYST_LLM_MODEL`
- `ECOMMERCE_ANALYST_LLM_API_KEY`
- `ECOMMERCE_ANALYST_RAW_DATA_DIR`
- `ECOMMERCE_ANALYST_PROCESSED_DATA_DIR`
- `ECOMMERCE_ANALYST_SAMPLE_DATA_DIR`

Use `ECOMMERCE_ANALYST_LLM_PROVIDER=none` for foundation checks that do not call
an LLM. If an actual provider is configured later, an API key must be supplied.

## Quality Checks

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Run formatting:

```bash
uv run ruff format .
```

Run type checking:

```bash
uv run mypy
```

## Future Milestones

- Domain validator for e-commerce dataset acceptance and rejection.
- Dataset schema and quality profiling.
- Analysis capability planning based on available columns.
- Deterministic sales, product, customer, and pricing analysis.
- LangGraph workflow orchestration.
- Evidence-backed insight generation and validation.
- Plotly visualization generation.
- Structured business report generation.
- CLI, API, or web interface.
