"""Database configuration and models for ML service."""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Numeric, func, MetaData, TypeDecorator, CHAR
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
import os
from datetime import datetime

# Get DB URL from env or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://canvasml:canvasml_dev_2024@localhost:5432/canvasml")

# Handle schema for SQLite
SCHEMA = "ml" if not DATABASE_URL.startswith("sqlite") else None

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata = MetaData(schema=SCHEMA)
Base = declarative_base(metadata=metadata)

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)

class DBModel(Base):
    __tablename__ = "models"

    model_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    algorithm = Column(String(100), nullable=False)
    status = Column(String(50), default='trained')
    metrics = Column(JSON)
    drift = Column(String(50), default='none')
    hyperparameters = Column(JSON)
    model_artifact_path = Column(String(512))
    tags = Column(JSON)
    trained_at = Column(DateTime(timezone=True))

class DBExperiment(Base):
    __tablename__ = "experiments"

    experiment_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    experiment_name = Column(String(255), nullable=False)
    task_type = Column(String(100), nullable=False)
    status = Column(String(50), default='queued')
    algorithms = Column(JSON, nullable=False)
    cv_folds = Column(Integer, default=5)
    results = Column(JSON)
    error = Column(String)
    reasoning = Column(String)
    trace = Column(JSON)
    created_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

class DBPredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    model_id = Column(GUID(), nullable=False)
    prediction_id = Column(String(100), unique=True, nullable=False)
    input_features = Column(JSON, nullable=False)
    prediction = Column(JSON, nullable=False)
    ground_truth = Column(JSON, nullable=True)
    latency_ms = Column(Numeric(10, 2), nullable=True)
    error = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class DBModelSchema(Base):
    __tablename__ = "model_schemas"

    model_id = Column(GUID(), primary_key=True)
    schema_json = Column(JSON, nullable=False)
    reference_stats = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
