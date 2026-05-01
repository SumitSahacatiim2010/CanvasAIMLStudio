# Antigravity Prompt Pack for TransLab / CanvasML Studio AI Platform

> **Version 2.0** — Enhanced with full phase lifecycle, corrected GSD syntax for Antigravity, expanded prompts for all platform modules, and architecture decision records.

This file contains:
- GSD workflow prompts adapted for Antigravity (using workflow file references, not Claude Code `/gsd:` syntax).
- Phase-specific implementation prompts for all 9 platform phases.
- Skill-to-phase mapping for the 1,400+ installed Antigravity skills.
- Architecture Decision Records (ADRs) for resolved technology choices.
- Day-to-day execution workflow.

You can paste each prompt into Antigravity and iterate phase by phase.

---

## 1. Bootstrap the Project with GSD (Get Shit Done)

> **Prerequisites**: GSD framework available at `d:\00 WorkSpace\agentskillstest\gsd_workflow\`. PRD and Blueprint markdown files must be in the repo.
>
> **GSD for Antigravity**: Instead of Claude Code's `/gsd:command` syntax, reference the GSD workflow files directly. Antigravity reads these as skill instructions when you point it to the workflow `.md` file.

### 1.1 Initialize the TransLab Project

```
Read the GSD new-project workflow at:
  d:\00 WorkSpace\agentskillstest\gsd_workflow\get-shit-done\workflows\new-project.md

You are initializing a new project called "TransLab / CanvasML Studio AI Platform".

Context files already present in this repo:
- PRD: oorequirements/CanvasML Studio AI Platform – Product Requirements Document.md
- Technical Blueprint: CanvasML Studio-blueprint_v1.md

Instructions:
1. Read both documents end-to-end.
2. Extract the core vision, constraints, personas, and high-level architecture.
3. Create PROJECT.md, REQUIREMENTS.md, ROADMAP.md, and STATE.md that are strictly aligned with these docs.
4. Treat the PRD as the source of truth for WHAT and the Blueprint as the source of truth for HOW.
5. Use the 9-phase roadmap defined in section 1.5 of this prompt pack.
6. Explicitly separate:
   - v1 scope (must-have for first bank POC)
   - v1.1/v2 enhancements (nice-to-have or regulatory hardening)
   - Out of scope.

Ask me ONLY targeted clarification questions where the PRD/Blueprint has genuine ambiguity.
Otherwise, do not re-design the product.
```

### 1.2 Discuss Implementation Preferences for a Phase

```
Read the GSD discuss-phase workflow at:
  d:\00 WorkSpace\agentskillstest\gsd_workflow\get-shit-done\workflows\discuss-phase.md

Phase [N] title: [Phase title from §1.5].

Use these documents as your implementation contract:
- PRD: oorequirements/CanvasML Studio AI Platform – Product Requirements Document.md
- Blueprint: CanvasML Studio-blueprint_v1.md

Your tasks in this step:
1. Read the phase description and the corresponding Blueprint sections.
2. Identify gray areas and edge cases that affect the implementation.
3. Ask me focused questions where necessary.
4. Capture all decisions in CONTEXT.md for this phase.
5. Do NOT expand scope — new capabilities belong in other phases.
```

### 1.3 Plan a Phase (Atomic Tasks)

```
Read the GSD plan-phase workflow at:
  d:\00 WorkSpace\agentskillstest\gsd_workflow\get-shit-done\workflows\plan-phase.md

Plan Phase [N] for the TransLab platform as described in:
- PRD: oorequirements/CanvasML Studio AI Platform – Product Requirements Document.md
- Blueprint: CanvasML Studio-blueprint_v1.md

Constraints:
- Create 2-4 atomic plans that can be executed independently with clean git commits.
- Each plan must include:
  - Clear success criteria (how we know it is done).
  - Interfaces and contracts (APIs, message formats, DB schemas) documented in the repo.
  - Integration points with later phases clearly marked.

Make sure plans reference specific files to create (directories, schemas, docs).
```

### 1.4 Execute and Verify a Phase

```
Read the GSD execute-phase workflow at:
  d:\00 WorkSpace\agentskillstest\gsd_workflow\get-shit-done\workflows\execute-phase.md

Execute all approved plans for Phase [N] ([Phase title]) for the TransLab project.

Guidelines:
- Follow the tasks exactly as defined in PLAN.md for this phase.
- Prefer small, composable modules and clear interfaces over big monoliths.
- Every task should result in:
  - Working, compilable code.
  - Minimal but clear documentation (README or ARCHITECTURE section).
  - Unit tests or at least scaffolding for tests.
- Use conventional commit messages and keep each plan as an atomic commit.

After execution, run the verification protocol and summarise:
- What was built.
- What tests were run.
- Any deviations from the PRD/Blueprint and why.
```

```
Read the GSD verify-work workflow at:
  d:\00 WorkSpace\agentskillstest\gsd_workflow\get-shit-done\workflows\verify-work.md

Run verification for Phase [N] ([Phase title]) of the TransLab project.

Check explicitly against:
- The relevant PRD sections for this phase.
- The relevant Blueprint sections for this phase.

Ensure that:
- The implemented code satisfies the described behaviour.
- All APIs and schemas are documented.
- Any gaps are captured as todos and ROADMAP updates.
```

### 1.5 Full Phase Lifecycle & Dependency Graph

The platform build follows this 9-phase roadmap. For each phase, cycle through: **discuss → plan → execute → verify**.

```
Phase 0: Project Skeleton & Infrastructure Setup
  Dependencies: None
  Blueprint: §7, §8
  Deliverables: Repo structure, Docker Compose, CI/CD pipeline, IAM skeleton,
                Postgres schema migrations framework, S3/MinIO setup

Phase 1: Data Platform Foundations (Connectors, Ingestion, Federation, Governance)
  Dependencies: Phase 0
  Blueprint: §2
  Deliverables: Connector framework + 4 connectors (Postgres, Oracle, S3, CSV),
                ETL/ELT engine with DAGs, federation/virtual views, metadata catalog

Phase 2: ML Platform (Profiling, AutoML, Model Registry)
  Dependencies: Phase 1 (datasets)
  Blueprint: §3.1–3.3
  Deliverables: Profiling service, 7-step cleaning pipeline, training engine
                (scikit-learn + XGBoost/LightGBM), model registry + deployment

Phase 3: XAI & Fairness Engine
  Dependencies: Phase 2 (models)
  Blueprint: §3.4
  Deliverables: SHAP/PDP global explanations, per-prediction explanations,
                counterfactual generation, fairness assessment (AIF360/fairlearn),
                governance report PDF export

Phase 4: Agentic Credit Decisioning Studio
  Dependencies: Phase 1 + Phase 2 + Phase 3
  Blueprint: §4, §12
  Deliverables: LangGraph agent graph, 9 agent types, workflow engine,
                policy/rule engine, maker-checker flow, decision cards,
                mock LOS integration

Phase 5: Multimodal RAG & Knowledge Assistants
  Dependencies: Phase 1 (ingestion pipelines)
  Blueprint: §5
  Deliverables: Document ingestion + OCR, chunking pipeline, hybrid search
                (pgvector + OpenSearch), retrieval API, generation API with
                citation enforcement, guardrails

Phase 6: Observability, Drift & Monitoring
  Dependencies: Phase 2 + Phase 4
  Blueprint: §6
  Deliverables: Metrics exporters, drift detection (PSI/K-S), alerting,
                distributed tracing, operational dashboards backend

Phase 7: Platform Console UI
  Dependencies: All backend phases (1-6)
  Blueprint: §10, §11
  Deliverables: React/TypeScript console, workflow builder (ReactFlow),
                data pipeline builder, executive dashboards, operational views

Phase 8: Security Hardening, Compliance & UAT
  Dependencies: All prior phases
  Blueprint: §7
  Deliverables: mTLS enforcement, Vault integration, RBAC enforcement,
                audit logging pipeline, BFSI compliance controls,
                penetration testing, UAT with synthetic bank data
```

### 1.6 Additional GSD Workflows (Available but Optional)

These GSD workflows are available and useful at specific points:

| Workflow | File | When to Use |
|----------|------|-------------|
| Discovery | `workflows/discovery-phase.md` | Phase 0 — tech research before committing to stack |
| Map Codebase | `workflows/map-codebase.md` | When resuming after a break |
| Diagnose Issues | `workflows/diagnose-issues.md` | Debugging failures during execution |
| Add Tests | `workflows/add-tests.md` | After each phase for explicit test generation |
| Audit Milestone | `workflows/audit-milestone.md` | Quality gates between major phases |
| Transition | `workflows/transition.md` | Handoff between phases or team members |
| Progress | `workflows/progress.md` | Check overall project status |

---

## 2. Phase-Specific Antigravity Prompts

> Use these directly in Antigravity inside the repo.

### 2.0 Phase 0: Project Skeleton & Infrastructure

```
You are a platform engineer setting up the TransLab project infrastructure.

Using the Blueprint (§7, §8), implement:

1. Repository structure:
   - `services/` — backend microservices (Python/FastAPI, one dir per service)
   - `console/` — React/TypeScript frontend
   - `schemas/` — shared DB migrations, API schemas (OpenAPI/Protobuf)
   - `deploy/` — Docker Compose, Helm charts, Terraform
   - `docs/` — architecture docs, ADRs
   - `tests/` — integration and E2E test suites

2. Docker Compose for local development:
   - PostgreSQL 16 with pgvector extension
   - MinIO (S3-compatible object storage)
   - Redis (caching and job queues)
   - Kafka/Redpanda (message bus)
   - OpenSearch (keyword index)

3. CI/CD pipeline skeleton (GitHub Actions or GitLab CI):
   - Lint + type check + unit test on PR
   - Build Docker images on merge to main
   - Helm deploy to dev namespace

4. Database migrations framework:
   - Alembic (Python) for service-specific schemas
   - Shared metadata schema: `sources`, `datasets`, `fields`, `lineage_edges`, `users`, `roles`, `permissions`

5. IAM skeleton:
   - FastAPI auth middleware with JWT validation
   - RBAC role definitions: PlatformAdmin, DataEngineer, DataScientist, RiskOfficer, BusinessUser, Auditor

Document in `docs/ARCHITECTURE-infrastructure.md`.
```

### 2.1 Phase 1: Data Platform (Connectors, Ingestion, Federation, Governance)

```
You are an expert backend + data platform engineer working inside Antigravity.

Repository context:
- PRD: oorequirements/CanvasML Studio AI Platform – Product Requirements Document.md
- Blueprint: CanvasML Studio-blueprint_v1.md (§2)

Deliverables:

1. Connector framework:
   - Directory structure under `services/connectors/`
   - Base abstract connector class with methods: validate_config, test_connectivity, discover_schemas, extract
   - Implement concrete connectors for: Postgres, Oracle, S3, CSV
   - Support incremental extraction (high-watermark, CDC where available)
   - Unit tests and minimal docs

2. Ingestion/ETL engine:
   - `services/ingestion/` with DAG-based pipeline definitions
   - Support for full-load and incremental (high-watermark) jobs
   - YAML/JSON config format for pipelines
   - Configurable retry/backoff and dead-letter queues

3. Data federation:
   - `services/federation/` that exposes a logical SQL endpoint mapped to underlying sources
   - Predicate pushdown and projection pruning
   - Basic join support across two sources (broadcast small tables strategy)

4. Metadata & catalog:
   - Postgres schema and migrations for: SourceSystem, Dataset, Field, PIIClassification, Owner, LineageEdge
   - REST API to register, query, and search datasets
   - Data quality rules engine: column-level (null %, uniqueness, ranges) and row-level (custom expressions)

Work style:
- Propose folder structure and high-level design in markdown first.
- Then implement step by step, keeping code idiomatic and testable.
```

### 2.2 Phase 2: ML/AutoML & XAI + Fairness

```
You are an ML platform engineer working in Antigravity.

Using the TransLab PRD and Blueprint (§3), implement the AI Playground + AutoML backend.

ML Platform deliverables:
- Profiling service (`services/ml/profiling/`): statistics, correlations, alerts for high correlation/missing values/skewness.
- Data cleaning pipeline (`services/ml/pipeline/`): modular transformers matching the 7-step flow (unique ratio, low-info removal, missing values, outliers, encoding, transformations/scaling, near-zero variance).
- Model training service (`services/ml/training/`): wrappers around scikit-learn + XGBoost/LightGBM/CatBoost with configs for classification (binary/multiclass) and regression.
- Model comparison: accuracy, precision, recall, F1, ROC AUC, confusion matrices.
- Model registry (`services/ml/registry/`): artefact storage (pickled/ONNX), metrics, training data schema signature, versioning.

XAI deliverables:
- XAI service (`services/ml/xai/`):
  - Global feature importance endpoint (TreeSHAP for tree models, KernelSHAP otherwise).
  - PDP/ICE plots per feature.
  - Per-prediction SHAP value explanation endpoint.
  - Counterfactual instance generation using DiCE (minimal perturbation to flip decision).

Fairness deliverables:
- Fairness engine (`services/ml/fairness/`):
  - Protected attributes configuration per model (gender, age bands, etc.).
  - Metrics: demographic parity difference/ratio, equal opportunity difference, equalized odds, predictive parity.
  - Implementation via AIF360 or fairlearn under the hood.
  - Fair/unfair classification based on configured thresholds.
  - Governance report generation (PDF/HTML): performance metrics + fairness metrics + XAI summary.

APIs:
- Create project and attach datasets.
- Launch training run with configuration (baseline / hyperparameter tuning / grid search).
- Retrieve metrics, artefacts, XAI reports, fairness assessments.
```

### 2.3 Phase 4: Agentic Credit Decisioning Studio

```
You are an agentic systems engineer designing the Credit Decisioning Studio for TransLab.

Using the PRD (§4.6, §5.7) and Blueprint (§4, §12), implement:

1. LangGraph agent graph under `services/agentic/`:
   - StateGraph with typed AgentState (application_id, documents, extracted_data, risk_scores, policy_results, decision, confidence, trace, human_override).
   - Agent nodes: DocumentIngestionAgent, DocumentVerificationAgent, OCRAgent, IncomeAnalysisAgent, BankStatementAnalysisAgent, RiskScoringAgent, CollateralAssessmentAgent, PolicyEvaluationAgent, OrchestrationAgent.
   - Conditional edges for routing (e.g., risk_score > threshold → manual review).
   - Interrupt points for human-in-the-loop (interrupt_before on OrchestrationAgent for maker review).

2. Tool definitions under `services/agentic/tools/`:
   - score_credit_risk → ML model scoring API
   - run_ocr → OCR service
   - query_bureau → bureau API with caching (stubbed for now)
   - evaluate_policy → policy engine
   - search_knowledge_base → RAG retrieval API

3. Policy engine under `services/policy/`:
   - JSON/DSL-based rule definitions grouped by product, segment, geography.
   - Evaluates conditions on raw data + ML-derived features.
   - Outputs: hard rejections (violations) and soft recommendations.

4. API endpoints:
   - Submit loan application payload + documents.
   - Run configured agentic workflow for a given product/segment.
   - Return decision card (decision, confidence, key risk drivers, trace IDs).
   - Maker-checker endpoints: accept/override with justification, checker validate/finalize.
   - Immutable audit log per application.

5. LangGraph checkpointer:
   - PostgreSQL-backed persistence for workflow state.
   - Supports pause/resume for human review steps.

Start with a mock LOS payload schema and stubbed bureau/collateral calls.
Document in `docs/agentic-credit-decisioning.md`.
```

### 2.4 Phase 5: Multimodal RAG & Knowledge Assistants

```
You are an AI engineer implementing multimodal RAG for TransLab.

Using the Blueprint (§5), build:

1. Document ingestion service (`services/rag/ingestion/`):
   - OCR pipeline: Tesseract (on-prem) or cloud API, with layout-aware parsing via unstructured.io.
   - Chunking pipeline:
     - Recursive character splitting (default, 512-2048 tokens, 100 token overlap).
     - Semantic chunking (embedding similarity for topic boundaries) for regulatory documents.
     - Document-structure-aware chunking using detected headers/sections.
   - Metadata extraction: document type classification, named entity extraction, regulatory reference tagging.

2. Hybrid search index:
   - Vector store (pgvector) for embeddings using text-embedding-3-large or BGE-large for on-prem.
   - Keyword index (OpenSearch) for BM25 exact term queries.
   - Dual-write pipeline: every chunk indexed in both stores.

3. Retrieval API (`services/rag/retrieval/`):
   - Hybrid retrieval: BM25 + vector similarity combined via Reciprocal Rank Fusion (RRF).
   - Cross-encoder reranker (ms-marco-MiniLM) on top-50 → top-5.
   - Multi-query retrieval: generate 3-5 query variants via LLM.
   - Metadata filters: jurisdiction, product, date range, document type.

4. Generation API (`services/rag/generation/`):
   - LLM answer generator with citation enforcement: every claim includes [Source: doc_id, page, section].
   - System prompts per use case (regulatory QA vs internal knowledge).
   - Streaming responses for chat interface.
   - Guardrails: content filters, PII redaction, hallucination detection (compare claims vs passages).
   - Token budget enforcement per query.

Place code under `services/rag/` and create `docs/rag-architecture.md`.
```

### 2.5 Phase 6: Observability, Drift & Governance

```
You are a platform SRE/ML engineer.

Implement the observability and drift layer for TransLab as per Blueprint (§6).

Scope:
- Metrics exporters for:
  - Platform services (CPU, memory, queue depths, error rates) via Prometheus.
  - ML model inference (latency, throughput, accuracy, AUC, F1).
  - Agentic workflows (per-agent and end-to-end latency, success rates, override frequency, token usage).

- Drift detection jobs (`services/drift/`):
  - PSI (Population Stability Index) for categorical and binned continuous features.
  - K-S test for continuous variables.
  - Configurable thresholds per feature and composite index.
  - Compare current distributions vs training baseline stored in model registry.

- Alerting integration:
  - Email and webhook alerts when thresholds are breached.
  - Configurable actions: alert only, block predictions for certain segments, automatic traffic shaping.

- Distributed tracing:
  - OpenTelemetry instrumentation across all services.
  - Trace ID propagation from API gateway through agentic workflow to model inference.
  - Span data stored with configurable retention.

Organize under `services/monitoring/` and `services/drift/`.
Document threshold configuration per deployment in `docs/observability.md`.
```

### 2.6 Phase 7: Platform Console UI

```
You are a senior frontend engineer building the TransLab platform console.

Using Blueprint (§10, §11), implement:

1. Project setup (`console/`):
   - React 18 + TypeScript 5 + Vite
   - Zustand for global state (auth, user preferences, active project)
   - TanStack Query for server-state caching
   - React Router v6 with lazy-loaded routes
   - Radix UI + custom design system tokens (or shadcn/ui)

2. Layout shell:
   - Persistent sidebar with navigation: Data Platform, AI Playground, Agent Studio, RAG Assistant, Monitoring, Governance, Admin.
   - Top bar with breadcrumbs, user menu, notification tray.

3. Shared components:
   - DataTable (sortable, filterable, paginated with column pinning)
   - FormWizard (multi-step with validation and draft saving)
   - MetricCard (KPI with sparkline and trend indicator)
   - StatusBadge (running, completed, failed, pending review)
   - AuditTimeline (chronological event log)

4. Agent Studio — Workflow Builder:
   - ReactFlow-based drag-and-drop directed graph editor.
   - Custom node types: DataInputNode, AgentNode, PolicyNode, DecisionNode, OutputNode.
   - Edge validation (output schema ↔ input schema compatibility).
   - Slide-out configuration panels per node.
   - Live execution trace overlay during workflow runs.

5. Data Pipeline Builder:
   - Visual DAG editor for ETL/ELT pipelines.
   - SQL editor with syntax highlighting and schema browser.
   - Data preview panel (sample rows at each pipeline stage).

6. Executive dashboards:
   - Portfolio overview, risk exposure, AI performance, operational efficiency, cost tracking.
   - Recharts-based visualizations with auto-refresh.
   - PDF export via headless rendering.
   - Role-based dashboard views per Blueprint §11.4.

Make it look premium — use dark mode, smooth transitions, glassmorphism cards.
```

### 2.7 Phase 8: Security & Compliance

```
You are a security engineer hardening the TransLab platform for BFSI deployment.

Using Blueprint (§7), implement:

1. Transport security:
   - TLS 1.3 for all external endpoints.
   - Mutual TLS for internal service-to-service communication.
   - API Gateway TLS termination, rate limiting, IP whitelisting.
   - WAF rules for public-facing endpoints.

2. Secrets management:
   - HashiCorp Vault integration for all credentials.
   - Automatic secret rotation (30/60/90 day configurable).
   - Encryption at rest: AES-256 for PostgreSQL (TDE), S3/MinIO (SSE-KMS).
   - Remove any hardcoded secrets from codebase.

3. RBAC enforcement:
   - Permission checks at API gateway AND service level (defense in depth).
   - Dataset-level, model-level, workflow-level access control with inheritance.
   - Integration with bank SSO/IDP (OIDC/SAML 2.0).

4. Audit logging pipeline:
   - Every user action logged: timestamp, user_id, role, action, resource, old/new values, IP, session.
   - Append-only store (WORM-compliant).
   - 7-year retention for financial services.
   - Audit log search and export API.

5. Compliance controls:
   - RBI IT Framework: data residency controls, BCP/DR documentation.
   - MAS TRM/FEAT: model risk governance report templates.
   - SOC 2 Type II: control mapping to Trust Services Criteria.
   - DPDP Act / PDPA: consent management hooks, data subject request handling.

6. Security testing:
   - Container image scanning (Trivy).
   - Python code security scanning (Bandit).
   - Dependency vulnerability scanning (Snyk).
   - API security testing (OWASP ZAP).

Document in `docs/security-architecture.md`.
```

---

## 3. Antigravity Skills Mapping (Phase-Specific)

> From the 1,424 installed skills, load only the relevant ones per phase to avoid context noise.

### Phase 0: Infrastructure
- `@aws-skills` or `@azure-skills` — cloud infrastructure patterns
- `@docker-expert` — container best practices
- `@github-actions-templates` — CI/CD pipeline patterns
- `@database` — database setup and migrations
- `@secrets-management` — Vault integration

### Phase 1: Data Platform
- `@database-design` — schema design, indexing strategy
- `@backend-architect` — service architecture
- `@api-patterns` — REST/GraphQL design
- `@sql-pro` — query optimization

### Phase 2: ML Platform
- `@ml-pipeline-workflow` — MLOps pipeline orchestration
- `@mlops-engineer` — experiment tracking, model registries
- `@python-pro` — Python best practices

### Phase 3: XAI & Fairness
- `@ml-pipeline-workflow` — model evaluation pipelines
- `@documentation` — governance report generation

### Phase 4: Agentic Credit Decisioning
- `@langgraph` — LangGraph agent patterns (if available)
- `@crewai` — multi-agent framework patterns
- `@backend-architect` — service design

### Phase 5: RAG
- `@rag-engineer` — RAG implementation patterns
- `@rag-implementation` — retrieval strategies
- `@embedding-strategies` — embedding model selection
- `@vector-database-engineer` — vector index tuning

### Phase 6: Observability
- `@grafana-dashboards` — dashboard creation
- `@prometheus-configuration` — metrics setup
- `@distributed-tracing` — OpenTelemetry instrumentation

### Phase 7: UI Console
- `@react-patterns` — React best practices
- `@frontend-design` — UI/interaction quality
- `@shadcn` — component library
- `@design-spells` — micro-interactions and polish

### Phase 8: Security
- `@security-auditor` — security review
- `@aws-security-audit` or `@azure-security-audit` — cloud security
- `@gdpr-data-handling` — privacy compliance

---

## 4. GitHub Frameworks & Repos

| Resource | Repo | Status | Use For |
|----------|------|--------|---------|
| **GSD Framework** | `gsd-build/get-shit-done` | ✅ Cloned locally | Spec-driven development, PROJECT/REQUIREMENTS/ROADMAP, atomic plans |
| **Antigravity Awesome Skills** | `sickn33/antigravity-awesome-skills` | ✅ Installed (1,424 skills) | Phase-specific skills per §3 above |
| **Anthropic Skills** | `anthropics/skills` | ✅ Cloned locally | Official skill reference |
| **Superpowers** | `obra/superpowers` | ✅ Cloned locally | Multi-agent plugin patterns |
| **GSD Antigravity Fork** | `toonight/get-shit-done-for-antigravity` | ❌ Optional | Antigravity-native `.agent`/`.gsd`/`.gemini` skeleton |

---

## 5. Architecture Decision Records (ADRs)

### ADR-001: LLM Orchestration Framework → LangGraph

**Status**: Decided  
**Decision**: Use LangGraph (LangChain ecosystem) for agentic workflow orchestration.  
**Rationale**:
- Stateful multi-step agent graphs with cycles (required for HITL credit decisioning).
- Built-in checkpointing for long-running workflows that pause for human review.
- Native tool-calling for ML models, OCR, bureau APIs, policy engines.
- Streaming support for real-time decision card updates.
- Production deployment via LangGraph Platform.

**Alternatives considered**:
- CrewAI — simpler role-based agents, but lacks fine-grained graph control and interrupt points.
- Custom framework — maximum flexibility, but high development/maintenance cost.
- AutoGen — strong for multi-agent conversations, weaker for structured workflow graphs.

### ADR-002: Embedding Model → text-embedding-3-large (cloud) / BGE-large (on-prem)

**Status**: Decided  
**Decision**: Use OpenAI text-embedding-3-large for cloud deployments; BAAI/bge-large-en-v1.5 or intfloat/multilingual-e5-large for on-prem/air-gapped deployments.  
**Rationale**: Best accuracy-to-cost ratio for financial/regulatory text. Multilingual support for Indian languages with the HuggingFace option.

### ADR-003: Workflow State Store → PostgreSQL (via LangGraph Checkpointer)

**Status**: Decided  
**Decision**: Use PostgreSQL as the persistence backend for LangGraph's checkpointer.  
**Rationale**: Already the primary metadata store; avoids introducing a separate event store for v1. LangGraph's checkpointer handles serialization and state versioning. Append-only audit logs kept in a separate table for WORM compliance.

### ADR-004: Message Bus → Redpanda

**Status**: Proposed  
**Decision**: Use Redpanda instead of Apache Kafka.  
**Rationale**: Kafka-compatible API (zero code changes), but simpler operations (single binary, no ZooKeeper), lower resource footprint for development and small deployments. Can switch to managed Kafka (MSK/Confluent) for large production deployments.

---

## 6. Day-to-Day Execution Workflow

1. **Start every phase** with GSD:
   - Discuss (read `workflows/discuss-phase.md`) → Plan (read `workflows/plan-phase.md`) → Execute (read `workflows/execute-phase.md`) → Verify (read `workflows/verify-work.md`).

2. **Inside each phase**, use the phase-specific prompt from §2 above.

3. **Keep PRD + Blueprint open** in the repo and explicitly reference them so the agent never drifts.

4. **Use skills selectively** per §3 mapping:
   - Data tasks → load data/ETL/federation skills.
   - ML tasks → load ML/AutoML/XAI skills.
   - Agentic tasks → load LangGraph/agent skills.
   - UI tasks → load React/frontend/design skills.
   - Security tasks → load security/compliance skills.

5. **Commit early, commit often** — let GSD handle atomic planning and verification.

6. **Between phases**, run the audit-milestone workflow (`workflows/audit-milestone.md`) to verify quality before advancing.

7. **When resuming after a break**, run `workflows/resume-project.md` to restore context.
