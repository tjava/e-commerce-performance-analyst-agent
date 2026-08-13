# Architecture

Milestone 1 establishes package boundaries, configuration, logging, dependency
management, and test tooling. It intentionally does not implement analytics,
domain validation, LangGraph nodes, prompts, charting, reports, or UI behavior.

## Dependency Direction

The dependency direction should remain:

```text
interfaces -> application -> domain
agent      -> application -> domain
analytics  -> domain
infrastructure -> domain
```

The domain layer is the innermost layer. It contains project concepts,
interfaces, enums, and exceptions, and must remain independent of vendor and
framework libraries such as LangGraph, LangChain, Pandas, DuckDB, and Plotly.

Application code should coordinate use cases and depend on domain abstractions.
Infrastructure code provides concrete adapters for external technologies.
Agent code contains LangGraph-specific workflow details and should call
application services instead of embedding business or analytics logic directly.
Analytics code owns deterministic computation and should stay independent from
LLM reasoning.

## Configuration

Configuration is loaded through `ecommerce_analyst.infrastructure.config`.
Settings are typed with Pydantic and sourced from environment variables,
optionally loaded from `.env` via `python-dotenv`.

Secrets are represented with `SecretStr` and are not printed by the application.
The foundation supports `ECOMMERCE_ANALYST_LLM_PROVIDER=none` so local startup
and tests do not require an API key. When a real provider is configured, the API
key is required immediately so failures are clear and early.

## Logging

Logging is configured in one place:
`ecommerce_analyst.infrastructure.logging.configure`.

The current formatter is intentionally simple and consistent. It avoids logging
configuration objects or secret values. Future milestones can add structured
logging if deployment needs justify it.

## Entry Point

`ecommerce_analyst.main` initializes settings and logging, then exits. It does
not execute any analytics or agent workflow. This gives later milestones a
stable startup path without mixing business logic into `main.py`.

## Future Integration Points

- Domain validation should be introduced as application use cases backed by
  domain models and deterministic schema evidence.
- Pandas and DuckDB work should live in `analytics` or concrete infrastructure
  adapters, not inside LangGraph nodes.
- LangGraph state should be explicit and isolated under `agent/state`.
- LLM provider clients should implement provider-neutral interfaces rather than
  leaking provider SDK details into application or domain code.
