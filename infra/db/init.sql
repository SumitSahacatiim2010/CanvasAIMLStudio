-- CanvasML Studio Database Initialization
-- Creates schemas, tables, and roles for the platform services.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. SCHEMAS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS agentic;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS observability;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. CATALOG SCHEMA
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS catalog.sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    connection_details JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS catalog.datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES catalog.sources(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    schema JSONB,
    row_count BIGINT,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. AGENTIC SCHEMA
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agentic.applications (
    application_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applicant_name VARCHAR(255) NOT NULL,
    product_type VARCHAR(100) NOT NULL,
    loan_amount NUMERIC(15, 2) NOT NULL,
    annual_income NUMERIC(15, 2) NOT NULL,
    credit_score INTEGER,
    employment_status VARCHAR(50),
    decision VARCHAR(50),
    risk_grade VARCHAR(10),
    reasoning TEXT,
    workflow_state JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS agentic.decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES agentic.applications(application_id) ON DELETE CASCADE,
    decision_type VARCHAR(50) NOT NULL,
    result VARCHAR(50) NOT NULL,
    confidence_score NUMERIC(5, 4),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. RAG SCHEMA
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rag.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag.chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES rag.documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    -- We'd use pgvector here in a real deployment, but keeping it simple for now
    embedding JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. ML SCHEMA
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml.models (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    algorithm VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'trained',
    metrics JSONB,
    drift VARCHAR(50) DEFAULT 'none',
    hyperparameters JSONB,
    model_artifact_path VARCHAR(512),
    tags JSONB,
    trained_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml.experiments (
    experiment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    algorithms JSONB NOT NULL,
    cv_folds INTEGER DEFAULT 5,
    results JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS ml.prediction_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml.models(model_id) ON DELETE CASCADE,
    prediction_id VARCHAR(100) UNIQUE NOT NULL,
    input_features JSONB NOT NULL,
    prediction JSONB NOT NULL,
    ground_truth JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml.model_schemas (
    model_id UUID PRIMARY KEY REFERENCES ml.models(model_id) ON DELETE CASCADE,
    schema_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. OBSERVABILITY SCHEMA
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS observability.logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observability.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    baseline NUMERIC(10, 4),
    recent NUMERIC(10, 4),
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. INITIAL DATA (SEEDING)
-- ─────────────────────────────────────────────────────────────────────────────

-- Seed some catalog sources
INSERT INTO catalog.sources (name, type, connection_details, status) VALUES
('Core Banking System', 'postgresql', '{"host": "core-db", "port": 5432}', 'active'),
('Credit Bureau API', 'rest', '{"endpoint": "https://api.equifax.com/v1"}', 'active'),
('Salesforce CRM', 'salesforce', '{"domain": "canvasml.my.salesforce.com"}', 'active');

-- Seed some ML models
INSERT INTO ml.models (name, version, algorithm, status, metrics, drift) VALUES
('credit_risk_v1', 1, 'random_forest', 'retired', '{"f1": 0.82, "auc": 0.85, "accuracy": 0.81}', 'high'),
('credit_risk_v2', 2, 'gradient_boosting', 'deployed', '{"f1": 0.88, "auc": 0.91, "accuracy": 0.87}', 'none'),
('fraud_detection_xgb', 1, 'xgboost', 'deployed', '{"f1": 0.92, "auc": 0.96, "accuracy": 0.94}', 'low');

-- Seed observability alerts
INSERT INTO observability.alerts (model_name, metric, baseline, recent, severity) VALUES
('credit_risk_v1', 'f1_score', 0.82, 0.65, 'high');
