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

- **Pipelines**
  - Convert documents (PDF, Word, images) to text using OCR where needed.
  - Chunk into semantically meaningful units (e.g., 512–2048 tokens) with overlap.

- **Metadata**
  - Capture source, document type, date, section headers, regulatory references.

- **Indexing**
  - Use vector database (e.g., pgvector, Pinecone, Weaviate) for embeddings.
  - Use keyword index (e.g., OpenSearch/Elasticsearch) for exact term queries.

### 5.2 Retrieval & Generation

- **Embeddings**
  - Use domain‑appropriate embedding model (e.g., multilingual for Indian languages if needed).

- **Retrieval Strategies**
  - Hybrid retrieval: BM25 + vector similarity, reranking with a cross‑encoder.
  - Filters on metadata (jurisdiction, product, date).

- **Generation**
  - LLM-based answer generator with:
    - Prompt templates enforcing citation and policy compliance.
    - System prompts tuned for regulatory QA and internal knowledge use.

- **Guardrails**
  - Content filters, refusal patterns for out‑of‑scope questions.
  - Redaction of PII in generated responses where necessary.

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

### 7.1 Security

- TLS everywhere, mutual TLS for internal services in regulated deployments.
- Secrets management via Vault or cloud KMS.
- Fine‑grained audits of all user actions (view, edit, deploy, override).

### 7.2 Performance & Scalability

- Horizontal scaling of stateless services.
- Asynchronous job queues for heavy workloads (training, XAI, document OCR).
- Performance targets:
  - Real‑time decisioning APIs: P95 latency upper bounds defined per client (e.g., 500–1000 ms for scoring only, longer when document processing is included).

### 7.3 Reliability

- Multi‑AZ deployments where available.
- Backup and disaster recovery plans for metadata DBs and artefact storage.

---

## 8. Development, Testing & Tooling

### 8.1 Codebase & Language Choices

- Backend services: primarily Python (for ML-centric services) and Go/Java (for high‑throughput connectors and federation engine).
- Frontend: React/TypeScript UI for platform console and Studio.

### 8.2 Testing Strategy

- Unit tests for all transformers, policy rules, and agent logic.
- Integration tests for connectors, ETL pipelines, and external API integrations.
- Model validation suites for credit models (performance, stability, fairness tests).
- Synthetic data generators for dev/test aligned with domain constraints.

### 8.3 CI/CD

- Container-based pipelines (Docker + Kubernetes).
- Automated tests and quality gates (linting, security scans).
- Promotion workflows from dev → UAT → prod with approvals, especially for credit models.

---

## 9. Mapping to PRD Modules

- **Source & Ingestion Layer** → Sections 2.1–2.1.2.
- **Data Federation & Virtualization** → Section 2.2.
- **Data Governance & Catalog** → Section 2.3.
- **AI Playground & AutoML** → Sections 3.1–3.3.
- **Explainability & Fairness** → Section 3.4.
- **Scheduling, Drift & Orchestration** → Sections 3.3, 6.2, 6.3.
- **Agentic Credit Decisioning Studio** → Section 4.
- **Multimodal RAG & Assistants** → Section 5.
- **Executive & Operational Dashboards** → Sections 4.4, 6.1.
