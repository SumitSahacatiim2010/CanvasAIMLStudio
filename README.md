# CanvasML Studio / TransLab

> AI-powered data platform, ML playground, agentic credit decisioning, and multimodal RAG for BFSI.

## Architecture

| Layer | Components | Tech |
|-------|-----------|------|
| **Data Platform** | Connectors, ETL/ELT, Federation, Governance | Python/FastAPI, Go |
| **ML Platform** | AutoML, Profiling, Registry, XAI, Fairness | scikit-learn, XGBoost, SHAP, AIF360 |
| **Agentic** | Credit Decisioning, Policy Engine, Workflow | LangGraph, FastAPI |
| **RAG** | Document Ingestion, Hybrid Search, Generation | pgvector, OpenSearch, LLMs |
| **Console** | Platform UI, Agent Studio, Dashboards | React, TypeScript, ReactFlow |
| **Observability** | Metrics, Drift, Tracing | Prometheus, OpenTelemetry |

## Quick Start

```bash
# Start local infrastructure
docker compose -f deploy/docker-compose.yml up -d

# Run database migrations
cd schemas/migrations && alembic upgrade head

# Start gateway service
cd services/gateway && uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
services/          Backend microservices (Python/FastAPI)
console/           React/TypeScript frontend
schemas/           DB migrations & shared API schemas
deploy/            Docker Compose, Helm, Terraform
docs/              Architecture docs & ADRs
tests/             Integration & E2E tests
```

## Documentation

- [Product Requirements (PRD)](oorequirements/CanvasML%20Studio%20AI%20Platform%20–%20Product%20Requirements%20Document.md)
- [Technical Blueprint](CanvasML%20Studio-blueprint_v1.md)
- [Execution Prompts](CanvasML%20Studio_antigravity-translab-prompts.md)
