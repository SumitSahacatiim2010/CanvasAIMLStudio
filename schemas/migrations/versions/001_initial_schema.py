"""Initial metadata schema — data platform, IAM, ML skeleton.

Revision ID: 001_initial
Revises: None
Create Date: 2026-05-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── IAM ──────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("permissions", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("sso_provider", sa.String(50)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255)),
        sa.Column("old_value", JSONB),
        sa.Column("new_value", JSONB),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("session_id", sa.String(255)),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_resource", "audit_log", ["resource_type", "resource_id"])

    # ── Data Platform Metadata ───────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),  # postgres, oracle, s3, csv, api
        sa.Column("config_encrypted", sa.Text),  # encrypted connection config
        sa.Column("status", sa.String(20), server_default="inactive"),  # active, inactive, error
        sa.Column("last_connected_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("schema_json", JSONB),
        sa.Column("row_count", sa.BigInteger),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("source_id", "name", name="uq_dataset_source_name"),
    )

    op.create_table(
        "fields",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dtype", sa.String(50), nullable=False),
        sa.Column("nullable", sa.Boolean, server_default="true"),
        sa.Column("pii_classification", sa.String(50)),  # none, quasi, direct, sensitive
        sa.Column("stats", JSONB),  # min, max, mean, null_pct, unique_count, etc.
        sa.UniqueConstraint("dataset_id", "name", name="uq_field_dataset_name"),
    )

    op.create_table(
        "lineage_edges",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("upstream_dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("downstream_dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("transform_type", sa.String(50)),  # etl, federation, derived
        sa.Column("transform_config", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lineage_upstream", "lineage_edges", ["upstream_dataset_id"])
    op.create_index("ix_lineage_downstream", "lineage_edges", ["downstream_dataset_id"])

    # ── ML Platform Metadata ─────────────────────────────
    op.create_table(
        "ml_projects",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "ml_experiments",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("ml_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="created"),  # created, running, completed, failed
        sa.Column("config", JSONB),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "ml_models",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("ml_experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("algorithm", sa.String(100)),
        sa.Column("artifact_path", sa.String(500)),  # S3/MinIO path
        sa.Column("metrics", JSONB),  # accuracy, f1, auc, etc.
        sa.Column("hyperparameters", JSONB),
        sa.Column("feature_schema", JSONB),  # input feature names and types
        sa.Column("status", sa.String(20), server_default="trained"),  # trained, validated, deployed, retired
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ml_models_status", "ml_models", ["status"])

    # ── Seed default roles ───────────────────────────────
    op.execute("""
        INSERT INTO roles (name, description, permissions) VALUES
        ('PlatformAdmin',  'Full platform access',                          '{"admin": true}'),
        ('DataEngineer',   'Manage data sources, pipelines, federation',    '{"data": ["read", "write", "admin"]}'),
        ('DataScientist',  'Create experiments, train models, view data',   '{"data": ["read"], "ml": ["read", "write"]}'),
        ('RiskOfficer',    'Review models, approve deployments, view XAI',  '{"ml": ["read", "approve"], "agentic": ["read", "approve"]}'),
        ('BusinessUser',   'View dashboards, submit applications',          '{"dashboard": ["read"], "agentic": ["submit"]}'),
        ('Auditor',        'Read-only access to all platform data',         '{"audit": true}')
    """)


def downgrade() -> None:
    op.drop_table("ml_models")
    op.drop_table("ml_experiments")
    op.drop_table("ml_projects")
    op.drop_table("lineage_edges")
    op.drop_table("fields")
    op.drop_table("datasets")
    op.drop_table("sources")
    op.drop_table("audit_log")
    op.drop_table("users")
    op.drop_table("roles")
