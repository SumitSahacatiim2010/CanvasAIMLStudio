# TransLab / Tantor AI Platform – Technical Blueprint

> This blueprint is intended as a living, implementation-facing document that engineering, data, and product teams can use throughout the product development lifecycle. It complements the PRD by going a level deeper into architecture, technology choices, algorithms, interfaces, and non‑functional constraints.

---

## 1. Architecture Overview

### 1.1 Core Architectural Style

- **Overall style**: Modular, service-oriented architecture with a strong data platform core and pluggable AI services.
- **Deployment options**: Kubernetes-based deployment supporting:
  - Bank‑hosted (on‑prem or VPC on hyperscalers) for regulated environments.
  - Managed SaaS for less-regulated use cases.
- **Foundational patterns**:
  - Hexagonal/ports-and-adapters around the data platform and agentic engine to isolate external systems.
  - Event-driven components (Kafka or equivalent) for ingestion and asynchronous orchestration.
  - Clear separation of concerns between:
    - Data platform (connectors, ingestion, federation, governance).
    - ML platform (feature engineering, training, deployment, XAI).
    - Agentic orchestration (credit decisioning, workflows).
    - Experience layer (UI, API, SDKs).

### 1.2 High‑Level Component Map

- **Gateway & API Layer**
  - API Gateway (e.g., Kong, NGINX, Apigee) for routing, authN/Z, rate limiting.
  - REST/GraphQL interfaces for admin, data, ML and agentic operations.

- **Identity & Access Management (IAM)**
  - Integration with bank SSO/IDP (OIDC/SAML).
  - Tenant, role and permission management for datasets, projects, models, workflows.

- **Data Platform**
  - Connector services (microservices per connector type family).
  - Ingestion & ETL/ELT engine (batch + microbatch streaming).
  - Data federation/virtualization engine.
  - Metadata, catalog, lineage, and governance services.

- **ML Platform (AutoML + XAI)**
  - Feature store (optional) for re‑usable features.
  - Profiling and data quality engine.
  - AutoML orchestration engine.
  - Model registry & deployment engine.
  - XAI and fairness analysis engine.

- **Agentic Platform**
  - Agent Studio (workflow designer & configuration).
  - Agent runtime (agent graph execution engine).
  - Tooling integrations (RAG, OCR, scoring models, external APIs).

- **Observability & Governance**
  - Metrics, tracing, and logging stack (Prometheus, Grafana, OpenTelemetry, ELK).
  - Governance reporting and export services.

- **Storage**
  - Operational store (PostgreSQL or equivalent) for metadata and configurations.
  - Object storage (S3-compatible) for artefacts, documents, model binaries.
  - Analytical stores (warehouse/lakehouse) via customer’s data platform or bundled (e.g., DuckDB/Trino/Presto for federation; optionally Snowflake/BigQuery/Redshift connectors).

---

## 2. Data Platform Blueprint

### 2.1 Connectors & Ingestion

#### 2.1.1 Connector Framework

- **Design**
  - Connector SDK for building new connectors with a standard lifecycle:
    - `validate_config()`
    - `test_connectivity()`
    - `discover_schemas()`
    - `extract()` (batch/stream)
  - Connector metadata stored in central catalog (type, capabilities, limits).

- **Technology Choices**
  - Base framework: Python/Go microservices with gRPC/REST.
  - Use JDBC/ODBC for relational DBs; native drivers for NoSQL where available.
  - Message bus: Kafka/Pulsar for streaming connectors.

- **Key Functional Details**
  - Support incremental extraction using:
    - High‑watermark columns (timestamp, numeric IDs).
    - Change data capture (CDC) where available (Debezium, native DB logs).
  - Support full-load with chunking based on PK ranges.
  - Configurable retry/backoff and dead‑letter queues for failed records.

#### 2.1.2 ETL/ELT Engine

- **Orchestration**: Directed acyclic graph (DAG) based, similar to Airflow/Prefect.
- **Transforms**
  - SQL-based transforms for pushdown to warehouses.
  - Python-based transforms for complex operations.
- **Scheduling**
  - Cron-like schedules stored per pipeline.
  - Event-triggered runs (on file arrival, Kafka topic events).

### 2.2 Data Federation & Virtualization

#### 2.2.1 Federation Engine

- **Logical Layer**
  - Query planner that maps logical SQL to physical queries across sources.
  - Predicate pushdown and projection pruning where supported.
  - Join strategies:
    - Broadcast small tables.
    - Federated join with partial local materialization when required.

- **Technology Ideas**
  - Use Trino/Presto, Apache Calcite, or a bespoke thin federation layer.

#### 2.2.2 Caching & Materialized Views

- **Caching**
  - In‑memory cache (Redis) for small, frequently accessed dimension data.
  - TTL and invalidation policies configurable per dataset.
- **Materialized Views**
  - Physicalized tables in the bank’s warehouse/lake/lakehouse.
  - Refresh policies: on‑demand, scheduled, event‑driven.

### 2.3 Data Governance & Catalog

#### 2.3.1 Metadata & Catalog

- **Data Model**
  - Entities: `SourceSystem`, `Dataset`, `Field`, `PIIClassification`, `Owner`, `LineageEdge`.
  - Lineage graph representing flow from source -> ingestion pipelines -> datasets -> models -> dashboards.

- **Implementation**
  - Metadata store in PostgreSQL.
  - Graph representation via Neo4j or a graph extension for Postgres.

#### 2.3.2 Data Quality Engine

- **Rule Types**
  - Column-level: null percentage, uniqueness, value ranges, regex patterns.
  - Row-level: custom expressions (e.g., `loan_amount <= income * 50`).
- **Execution**
  - Rules attached to datasets and ETL jobs.
  - Evaluated as part of ingestion/transform jobs, with results stored in quality tables.

#### 2.3.3 Security & Privacy

- **RBAC**
  - Roles: `Admin`, `DataEngineer`, `DataScientist`, `RiskOfficer`, `BusinessUser`.
  - Permissions: dataset-level read/write, model-level deploy, policy-level edit.

- **PII Handling**
  - PII detection via regexes and ML classifier for column names & value patterns.
  - Masking policies applied at query-time (e.g., last‑4 only) or storage-time.
  - Hashing for irreversible pseudonymization of identifiers.

---

## 3. ML & AutoML Blueprint

### 3.1 Data Profiling & Preparation

#### 3.1.1 Profiling

- **Framework**: Use a profiling library (e.g., ydata-profiling or custom) integrated into the platform.
- **Statistics**
  - For numerical columns: mean, median, std, min/max, quantiles, skewness, kurtosis.
  - For categorical: unique count, frequency distribution, entropy.
  - Correlation matrices (Pearson, Spearman, Cramer’s V for categorical pairs).

#### 3.1.2 Data Cleaning Pipeline

- **Pipeline Structure**
  - Implemented as a sequence of configurable `transformer` components with metadata stored as JSON.
  - Each step corresponds to a UI element (toggle, parameter fields).

- **Transformers**
  - Missing value handlers: mean/median/mode/constant; category `Unknown`.
  - Outlier detection: z‑score, IQR filter, isolation forest.
  - Encoding:
    - One‑hot, target encoding (with leakage guard), ordinal encoding.
  - Scaling:
    - StandardScaler, MinMaxScaler, RobustScaler, PowerTransform (Box-Cox/Yeo-Johnson).
  - Variance & correlation filters: near‑zero variance removal, high‑correlation pruning.

### 3.2 Algorithm Catalog & Training Framework

#### 3.2.1 Supported Algorithm Families

- **Classification**
  - Logistic Regression (with L1/L2 regularization, liblinear/saga).
  - Random Forest, Gradient Boosted Trees (XGBoost/LightGBM/CatBoost).
  - Support Vector Machines (linear, RBF).
  - Naive Bayes (Gaussian, Multinomial).
  - Neural Networks (MLP, shallow architectures suitable for tabular data).

- **Regression**
  - Linear and Ridge/Lasso/ElasticNet regression.
  - Random Forest Regressor, Gradient Boosted Regression Trees.
  - SVR with kernels.
  - XGBoost/LightGBM/CatBoost regressors.

- **Others (Phase 2)**
  - Survival models (for time‑to‑default), time series models for sales volume forecasting.

#### 3.2.2 Training Orchestration

- **Engine**: Python ML backend using scikit-learn + XGBoost/LightGBM/CatBoost, optionally wrapped via MLflow.
- **Configuration Modes**
  - Baseline: auto‑selected hyperparameters per algorithm.
  - Hyperparameter tuning: random search, Bayesian optimization.
  - Grid search: exhaustive for small grids.

- **Search Strategy**
  - Apply early‑stopping and resource caps (max runs, max training time per algorithm).
  - Use cross‑validation (k‑fold) with stratification for classification.

### 3.3 Model Registry & Deployment

- **Model Registry**
  - Store: model artefacts (pickled/ONNX), metrics, training data schema signature, lineage.
  - Versioning per project and per use case.

- **Deployment Targets**
  - **Batch**: containerized scoring jobs reading from datasets and writing to target tables.
  - **Online**: REST/gRPC microservices or serverless functions.

- **Inference Contracts**
  - Strict input schema enforcement (feature names, types, pre-processing steps encoded in model metadata).
  - Backward compatibility rules for incremental schema evolution.

### 3.4 Explainability & Fairness

#### 3.4.1 XAI Implementation

- **Global Explanations**
  - Model‑agnostic SHAP (TreeSHAP for tree models, KernelSHAP otherwise).
  - Global feature importance charts.
  - PDP/ICE plots per feature.

- **Local Explanations**
  - Per‑prediction SHAP value plots.
  - Counterfactual instance generation using libraries like DiCE or custom search:
    - Objective: minimal perturbation to flip decision while respecting constraints.

- **Architecture**
  - Dedicated XAI service that loads models and generates explanation artefacts on demand or pre‑computes them for top features.

#### 3.4.2 Fairness Engine

- **Metrics**
  - Demographic parity difference/ratio.
  - Equal opportunity difference.
  - Equalized odds metrics.
  - Predictive parity where relevant.

- **Implementation**
  - Use fairness libraries (e.g., AIF360, fairlearn) under the hood.
  - Allow mapping from model features to protected group definitions.

- **Governance Reports**
  - Generate PDF/HTML reports summarizing metrics, charts, and threshold compliance.

---

## 4. Agentic Credit Decisioning Blueprint

### 4.1 Agent Model

- **Agent Types**
  - `DocumentIngestionAgent` – reads LOS payload and attached documents.
  - `DocumentVerificationAgent` – verifies integrity and basic authenticity (checksum, file type, signature placeholders).
  - `OCRAgent` – runs OCR on images/PDFs using Tesseract, AWS Textract, Azure Form Recognizer, or Google Document AI.
  - `IncomeAnalysisAgent` – parses salary slips, bank statements, computes income metrics (net salary, variability, bonuses).
  - `BankStatementAnalysisAgent` – detects EMI obligations, bounce counts, cash flow patterns.
  - `RiskScoringAgent` – calls ML models and rule engines for credit risk (PD, LGD, behavioural scores).
  - `CollateralAssessmentAgent` – hooks for property/asset valuation services.
  - `PolicyEvaluationAgent` – applies bank credit policies and product/segment rules.
  - `OrchestrationAgent` – coordinates all agents, aggregates outputs, and produces final decision + rationale.

- **Agent Interface**
  - Standardised interface:
    - `inputs`: schema describing required data.
    - `run(context) -> AgentResult` structure (data, metrics, logs, explanation snippets).
    - `tools`: callable utilities (RAG, models, external APIs).

### 4.2 Workflow Engine

- **Graph Representation**
  - Directed graph of nodes (agents, routers, decision nodes) stored in metadata.
  - Each node has:
    - ID, type, config.
    - Input mapping (from context or prior agent outputs).
    - Output contracts.

- **Execution**
  - Orchestrator executes graph with:
    - Parallelism where dependencies permit.
    - Timeouts, retries and circuit breakers for each agent.
  - Execution trace stored as a structured log (for audit and observability).

### 4.3 Policy & Rule Engine

- **Policy Representation**
  - Use a rule engine (e.g., Drools‑like DSL or JSON-based conditions) for bank credit policies.
  - Policies grouped by product, segment, geography.

- **Execution**
  - Policy engine evaluates conditions on:
    - Raw data (income, age, tenure, bureau scores).
    - Derived features from ML agents (PD, risk segments).
  - Outputs include:
    - Hard rejections (policy violations).
    - Soft recommendations (e.g., reduce loan amount, increase collateral).

### 4.4 Human-in-the-Loop & Governance

- **Decision Cards**
  - Data model includes:
    - Application ID, current status, decision, confidence.
    - Key risk factors, pros/cons, policy triggers.
    - Links to XAI artefacts and execution trace.

- **Override Flow**
  - Maker can override AI/policy suggestion with reason.
  - Checker validates; both actions logged with timestamp and user.
  - Immutable audit records stored in append-only log (e.g., WORM store).

### 4.5 Integration Points

- **LOS/LMS**
  - REST/Message-based integration for application intake and decision outputs.
  - Status callbacks and decision events published to integration bus.

- **Bureau & External APIs**
  - Encapsulated as tools/agents with retry, idempotency and response caching.

---

## 5. Multimodal RAG & Knowledge Assistant Blueprint

### 5.1 Document Ingestion & Indexing

- **Ingestion Pipelines**
  - Convert documents (PDF, Word, images) to text using OCR where needed.
  - OCR stack: Tesseract for on-prem, AWS Textract / Azure Document Intelligence / Google Document AI for cloud.
  - Layout-aware parsing for tables, headers, footers, and multi-column documents using `unstructured.io` or equivalent.

- **Chunking Strategies**
  - **Recursive character splitting** (default): split on paragraph → sentence → word with configurable `chunk_size` (512–2048 tokens) and `chunk_overlap` (50–200 tokens).
  - **Semantic chunking**: use embedding similarity to detect topic boundaries; preferred for regulatory documents with distinct sections.
  - **Document-structure-aware chunking**: leverage detected headers/sections from layout parsing to create contextually complete chunks.
  - Each chunk retains: `chunk_id`, `document_id`, `section_path` (e.g., "Chapter 3 > Section 3.2"), `page_numbers`, `char_offsets`.

- **Metadata Extraction**
  - Capture source, document type, date, section headers, regulatory references.
  - Auto-classify document type (circular, guideline, internal policy, financial statement) using a lightweight classifier.
  - Extract named entities (regulation IDs, dates, amounts) for structured metadata.

- **Indexing**
  - Use vector database (pgvector for on-prem, Pinecone/Weaviate for managed) for embeddings.
  - Use keyword index (OpenSearch/Elasticsearch) for exact term queries and BM25.
  - Dual-write pipeline: every ingested chunk is indexed in both vector and keyword stores.

### 5.2 Embedding & Retrieval

- **Embedding Model Selection**
  - Primary: `text-embedding-3-large` (OpenAI) or Gemini embeddings for cloud deployments.
  - On-prem / air-gapped: `BAAI/bge-large-en-v1.5` or `intfloat/multilingual-e5-large` (HuggingFace) for Indian language support.
  - Dimensionality: 1024–3072 depending on model; use Matryoshka embeddings where supported for flexible dim reduction.
  - Re-embed on model upgrade with versioned embedding columns.

- **Retrieval Strategies**
  - **Hybrid retrieval**: BM25 (keyword) + dense vector similarity, combined via Reciprocal Rank Fusion (RRF).
  - **Reranking**: cross-encoder reranker (`ms-marco-MiniLM-L-12-v2` or Cohere Rerank) applied to top-50 candidates to produce final top-5.
  - Metadata filters on jurisdiction, product, date range, document type applied pre-retrieval.
  - **Multi-query retrieval**: generate 3–5 query variants via LLM to improve recall on ambiguous questions.

### 5.3 Generation & Citation

- **Generation Pipeline**
  - LLM-based answer generator (Gemini / GPT-4o / Claude) with structured prompt templates.
  - **Citation enforcement**: every claim in the generated answer must include `[Source: doc_id, page, section]` references.
  - System prompts tuned per use case:
    - Regulatory QA: strict citation, no speculation, flag when answer is uncertain.
    - Internal knowledge: allow synthesis across documents, summarize when appropriate.
  - Streaming responses for chat-style interface.

- **Guardrails**
  - Content filters: block out-of-scope questions, profanity, prompt injection attempts.
  - Refusal patterns for questions outside the knowledge base with confidence scoring.
  - PII redaction in generated responses using regex + NER-based detection.
  - **Hallucination detection**: compare generated claims against retrieved passages; flag unsupported statements.
  - Token budget enforcement per query (configurable per deployment).

---

## 6. Observability, Monitoring & Drift Blueprint

### 6.1 Metrics & Tracing

- **Metrics**
  - Platform: CPU, memory, queue depths, error rates.
  - ML: latencies, throughput, model‑specific metrics (accuracy, AUC, F1, etc.).
  - Agentic workflows: end‑to‑end latency, step latencies, success/failure per agent.

- **Tracing**
  - Distributed tracing with trace IDs propagated across services.
  - Span data stored for a defined retention period.

### 6.2 Drift Detection

- **Data Drift**
  - Monitor feature distributions over time vs. training baseline:
    - Population Stability Index (PSI).
    - K‑S test for continuous variables.
  - Thresholds per feature and composite index.

- **Model Drift**
  - Monitor performance metrics on labelled back‑test data or delayed labels.
  - Use early warning thresholds triggering retraining workflows.

### 6.3 Alerting & Guardrails

- **Actions on Drift**
  - Alert only, or stop predictions for certain segments.
  - Automatic traffic shaping (reduce reliance on model and increase manual review).

---

## 7. Security, Compliance & Non‑Functional Requirements

### 7.1 Network & Transport Security

- TLS 1.3 everywhere; mutual TLS for internal service-to-service communication in regulated deployments.
- API Gateway enforces TLS termination, rate limiting, and IP whitelisting for bank-hosted deployments.
- Network segmentation: data platform, ML platform, agentic engine, and UI tier in separate network zones.
- Web Application Firewall (WAF) for public-facing API endpoints.

### 7.2 Secrets & Key Management

- Secrets management via HashiCorp Vault (on-prem) or cloud KMS (AWS KMS / Azure Key Vault / GCP KMS).
- Database credentials, API keys, and service tokens stored exclusively in Vault; never in config files or environment variables.
- Automatic secret rotation with configurable intervals (30/60/90 days).
- Encryption at rest: AES-256 for all persistent stores (PostgreSQL TDE, S3 SSE-KMS, MinIO server-side encryption).

### 7.3 Identity, Access & Audit

- **RBAC Enforcement**
  - Roles: `PlatformAdmin`, `DataEngineer`, `DataScientist`, `RiskOfficer`, `BusinessUser`, `Auditor` (read-only).
  - Permissions enforced at API gateway AND service level (defense in depth).
  - Dataset-level, model-level, and workflow-level access control with inheritance.
  - Integration with bank SSO/IDP (OIDC/SAML 2.0); support for AD/LDAP.

- **Audit Logging Pipeline**
  - Every user action (view, create, edit, deploy, override, delete) logged with: `timestamp`, `user_id`, `role`, `action`, `resource`, `old_value`, `new_value`, `ip_address`, `session_id`.
  - Audit logs written to append-only store (immutable); WORM-compliant for regulatory retention.
  - Retention: minimum 7 years for financial services; configurable per deployment.
  - Audit log search and export API for compliance teams.

### 7.4 BFSI Regulatory Compliance

- **RBI IT Framework**: data residency controls, outsourcing risk assessment documentation, BCP/DR requirements.
- **MAS TRM / FEAT Guidelines**: model risk governance reports, fairness assessment artefacts, explainability documentation.
- **SOC 2 Type II**: controls mapped to Trust Services Criteria (security, availability, processing integrity, confidentiality).
- **ISO 27001**: ISMS alignment with Annex A controls; asset inventory, risk treatment plans.
- **Data Privacy**: DPDP Act (India) / PDPA (Singapore) compliance hooks; consent management, data subject request handling.

### 7.5 Performance & Scalability

- Horizontal scaling of stateless services via Kubernetes HPA (CPU/memory-based autoscaling).
- Asynchronous job queues (Celery + Redis / Kafka consumer groups) for heavy workloads (training, XAI, document OCR).
- Performance targets:
  - Real‑time scoring APIs: P95 ≤ 500 ms (scoring only), P95 ≤ 3 s (with document OCR).
  - Batch inference: process 100K records/hour per model.
  - Data federation queries: P95 ≤ 5 s for cross-source joins on datasets < 1M rows.
  - UI console: First Contentful Paint ≤ 1.5 s, Time to Interactive ≤ 3 s.

### 7.6 Reliability & DR

- Multi‑AZ deployments where available; active-passive failover for stateful services.
- RPO ≤ 1 hour, RTO ≤ 4 hours for metadata DBs and model registry.
- Backup and disaster recovery plans for metadata DBs, artefact storage, and audit logs.
- Health check endpoints for all services; Kubernetes liveness/readiness probes.
- Circuit breakers (Hystrix-pattern) for external API calls (bureau, LOS, LLM providers).

---

## 8. Development, Testing & Tooling

### 8.1 Codebase & Language Choices

- Backend services: primarily Python 3.11+ (for ML-centric services, FastAPI for APIs) and Go (for high‑throughput connectors and federation engine).
- Frontend: React 18+ / TypeScript 5+ for platform console and Studio.
- Monorepo structure using Turborepo or Nx for shared types, utilities, and build orchestration.

### 8.2 Branching & Version Strategy

- **Branching model**: Trunk-based development with short-lived feature branches.
  - `main` → always deployable; protected with required reviews.
  - `feature/*` → individual feature branches; merged via PR with CI checks.
  - `release/*` → cut from main for production releases; hotfixes cherry-picked.
- **Versioning**: Semantic versioning (SemVer) for platform releases; independent versioning for ML models.
- **Commit conventions**: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`) for automated changelogs.

### 8.3 Environment Topology

- **Local dev**: Docker Compose with all services; MinIO for S3, local PostgreSQL, mock Kafka.
- **Dev/Integration**: shared Kubernetes cluster; ephemeral namespaces per branch for CI.
- **Staging/UAT**: production-mirror environment; bank-specific configs; used for client acceptance testing.
- **Production**: bank-hosted K8s cluster or managed SaaS; blue-green or canary deployments.
- Environment parity enforced via Helm charts with environment-specific value overrides.

### 8.4 Testing Strategy

- **Unit tests**: all transformers, policy rules, agent logic, API handlers. Coverage target: ≥ 80%.
- **Integration tests**: connectors against real DB instances (via Testcontainers), ETL pipelines, external API stubs.
- **Contract tests**: Pact or equivalent for service-to-service API contracts (data platform ↔ ML platform ↔ agentic engine).
- **Model validation suites**: performance (AUC, F1, Gini), stability (PSI on hold-out), fairness tests per model.
- **E2E tests**: Playwright for UI console; API test suites for critical workflows (submit application → decision card).
- **Synthetic data generators**: Faker-based generators for dev/test aligned with domain constraints (loan applications, bank statements, salary slips).

### 8.5 CI/CD

- Container-based pipelines (Docker + Kubernetes); GitHub Actions or GitLab CI.
- Automated quality gates: linting (ruff/eslint), type checking (mypy/tsc), security scans (Trivy for containers, Bandit for Python, Snyk for dependencies).
- Promotion workflows: dev → staging → UAT → prod with required approvals, especially for credit models.
- ML model promotion: separate pipeline with model validation suite as gate; model registry approval workflow.
- Infrastructure as Code: Terraform/Pulumi for cloud resources; Helm for K8s manifests.

---

## 9. Mapping to PRD Modules

- **Source & Ingestion Layer** (PRD §4.1, §5.1) → Blueprint §2.1–2.1.2.
- **Data Federation & Virtualization** (PRD §4.2, §5.2) → Blueprint §2.2.
- **Data Governance & Catalog** (PRD §4.3, §5.3) → Blueprint §2.3.
- **AI Playground & AutoML** (PRD §4.4, §5.4) → Blueprint §3.1–3.3.
- **Explainability & Fairness** (PRD §5.5) → Blueprint §3.4.
- **Scheduling, Drift & Orchestration** (PRD §4.5, §5.6) → Blueprint §3.3, 6.2, 6.3.
- **Agentic Credit Decisioning Studio** (PRD §4.6, §5.7) → Blueprint §4, §12.
- **Multimodal RAG & Assistants** (PRD §5.8) → Blueprint §5.
- **Executive & Operational Dashboards** (PRD §5.9) → Blueprint §11, §6.1.
- **Platform Console & UI** (PRD §4.4 UI, §4.6 Studio) → Blueprint §10.
- **Security & Compliance** (PRD §6) → Blueprint §7.

---

## 10. Platform Console & UI Architecture

### 10.1 Technology Stack

- **Framework**: React 18+ with TypeScript 5+; Vite for build tooling.
- **State Management**: Zustand for global state (auth, user preferences, active project); React Query / TanStack Query for server-state caching and synchronization.
- **Routing**: React Router v6 with lazy-loaded route modules per platform area.
- **Component Library**: Radix UI primitives + custom design system tokens (spacing, color, typography); alternatively, shadcn/ui for rapid scaffolding.
- **Visualization**: Recharts for dashboards and metric charts; D3.js for custom lineage graphs.
- **Forms**: React Hook Form + Zod for schema-validated forms (connector setup, model configs, policy definitions).

### 10.2 Component Architecture

- **Layout Shell**: persistent sidebar navigation + top bar with breadcrumbs, user menu, and notification tray.
- **Module Pages**: Data Platform, AI Playground, Agent Studio, RAG Assistant, Monitoring, Governance, Admin.
- **Shared Components**:
  - `DataTable` — sortable, filterable, paginated table with column pinning and row selection.
  - `FormWizard` — multi-step form with validation, back/forward navigation, and draft saving.
  - `MetricCard` — KPI display widget with sparkline, trend indicator, and drill-down link.
  - `StatusBadge` — consistent status indicators across platform (running, completed, failed, pending review).
  - `AuditTimeline` — chronological event log with expandable detail rows.

### 10.3 Workflow Builder (Agent Studio)

- **Engine**: ReactFlow for the drag-and-drop directed graph editor.
  - Custom node types: `DataInputNode`, `AgentNode`, `PolicyNode`, `DecisionNode`, `OutputNode`.
  - Edge validation: enforce type-compatible connections (output schema ↔ input schema).
  - Minimap, zoom controls, and auto-layout (dagre algorithm).
- **Configuration Panels**: slide-out panels for node configuration (agent parameters, policy rules, output mappings).
- **Live Preview**: execution trace overlay showing real-time status per node during workflow runs.

### 10.4 Data Pipeline Builder (ETL/ELT)

- **Visual DAG editor** (similar to Airflow Graph View) for defining ingestion and transform pipelines.
- **SQL editor** with syntax highlighting, auto-complete, and schema browser for federation queries.
- **Data preview** panel showing sample rows at each pipeline stage.

---

## 11. Executive & Operational Dashboards

### 11.1 Dashboard Architecture

- **Rendering**: server-side data aggregation via API endpoints; client-side rendering with Recharts/D3.
- **Refresh**: configurable auto-refresh (30s / 1m / 5m / manual); WebSocket push for critical alerts.
- **Export**: PDF report generation (via Puppeteer/Playwright headless rendering) and CSV export for all data tables.
- **Embedding**: dashboards embeddable in bank intranet portals via iframe with SSO passthrough.

### 11.2 Executive Dashboard KPIs

- **Portfolio Overview**: total applications processed, approval/rejection rates, average processing time, STP rate.
- **Risk Exposure**: portfolio-level PD distribution, concentration by segment/product, top risk factors.
- **AI Performance**: model accuracy trends, drift status, retraining frequency, XAI report completion rate.
- **Operational Efficiency**: automation coverage (% decisions via agentic workflow), override frequency, human-in-the-loop queue depth.
- **Cost Tracking**: LLM token usage and cost per workflow, compute cost per model training run, storage growth.

### 11.3 Operational Dashboard Views

- **Per-Workflow View**: end-to-end latency (P50/P95/P99), success rate, failure breakdown by agent, active applications in pipeline.
- **Per-Agent View**: availability, task success rate, output consistency score, safety compliance flags, latency distribution, token usage.
- **Per-Model View**: inference throughput, latency, drift metrics (PSI/K-S), last retrain date, current vs. baseline performance.
- **Data Platform View**: connector health, ingestion job status, data quality scores, federation query performance.

### 11.4 Role-Based Dashboard Access

| Role | Dashboard Views | Export |
|------|----------------|--------|
| Executive | Portfolio, Risk, AI Performance, Cost | PDF summary |
| Risk Officer | Portfolio, Risk (detailed), Model drift | PDF + CSV |
| Data Scientist | Model performance, Drift, XAI reports | CSV |
| Business User | Application status, Decision cards | PDF |
| Platform Admin | All views + system health | All formats |

---

## 12. LLM Orchestration Architecture (LangGraph)

### 12.1 Framework Decision

- **Chosen framework**: LangGraph (LangChain ecosystem) for agentic workflow orchestration.
- **Rationale**:
  - First-class support for stateful, multi-step agent graphs with cycles (critical for credit decisioning with human-in-the-loop).
  - Built-in persistence (checkpointing) for long-running workflows that pause for human review.
  - Native tool-calling support for integrating ML models, OCR services, bureau APIs, and policy engines.
  - Streaming support for real-time decision card updates.
  - Production-grade with LangGraph Platform for deployment, monitoring, and scaling.

### 12.2 Agent Graph Architecture

- **Graph Definition**:
  - Each agentic workflow (e.g., credit underwriting) defined as a `StateGraph` with typed state schema.
  - Nodes: individual agents (DocumentIngestion, OCR, IncomeAnalysis, RiskScoring, PolicyEvaluation, Orchestration).
  - Edges: conditional routing based on agent outputs (e.g., if `risk_score > threshold` → route to manual review).
  - Interrupt points: `interrupt_before` / `interrupt_after` for human-in-the-loop nodes.

- **State Management**:
  - `AgentState` TypedDict containing: `application_id`, `documents`, `extracted_data`, `risk_scores`, `policy_results`, `decision`, `confidence`, `trace`, `human_override`.
  - State persisted via LangGraph checkpointer (PostgreSQL-backed) for durability across service restarts.
  - State transitions logged for complete audit trail.

### 12.3 Tool Integration

- **Tool Definitions**:
  - `score_credit_risk(features) → PD, LGD, risk_segment` — calls ML model scoring API.
  - `run_ocr(document) → extracted_text, tables, metadata` — calls OCR service.
  - `query_bureau(applicant_id) → bureau_score, enquiries, accounts` — calls bureau API with caching.
  - `evaluate_policy(application, segment, product) → violations, recommendations` — calls policy engine.
  - `search_knowledge_base(query) → passages, citations` — calls RAG retrieval API.

- **Tool Execution**:
  - Tools wrapped with retry logic, circuit breakers, and timeout enforcement.
  - Tool call results cached where idempotent (bureau lookups, OCR results).
  - All tool invocations logged with input/output for audit.

### 12.4 Model Routing & Cost Management

- **Model Selection**:
  - Primary LLM: Gemini 2.0 Flash for orchestration reasoning (cost-effective, fast).
  - Fallback: GPT-4o or Claude for complex reasoning tasks (policy interpretation, counterfactual generation).
  - Local models (Llama 3 / Mistral via vLLM) for air-gapped / on-prem deployments.

- **Cost Controls**:
  - Token budget per workflow execution (configurable per product/segment).
  - Token usage tracked per agent, per tool call, and per workflow.
  - Cost dashboards in monitoring (§11.2).
  - Model routing rules: use cheapest model that meets quality threshold for each task.

### 12.5 Prompt Management

- **Prompt Registry**: versioned prompt templates stored in database (not hardcoded).
- **Prompt Structure**: system prompt + task prompt + context injection (retrieved documents, extracted data, prior agent outputs).
- **A/B Testing**: support for prompt variant testing with performance comparison (accuracy, latency, cost).
- **Guardrails**: output parsers (Pydantic models) enforcing structured agent responses; fallback to retry on parse failure.
