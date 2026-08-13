# E-commerce Performance Analyst Agent

The E-commerce Performance Analyst Agent is a domain-constrained AI analytics
application for uploaded e-commerce transaction datasets. It is designed to
validate whether uploaded CSV or XLSX files belong to the e-commerce domain,
profile data quality and schema, determine which analyses are supported by the
available columns, run deterministic calculations with Pandas and DuckDB, and
produce evidence-backed insights, Plotly visualizations, and structured business
reports through a LangGraph workflow.

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
