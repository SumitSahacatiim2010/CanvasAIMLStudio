from sqlalchemy import Column, String, Integer, JSON, DateTime, Float
from sqlalchemy.sql import func
from services.gateway.app.database import Base

class Agent(Base):
    """Registry of available agents and their metadata."""
    __tablename__ = "agents"

    id = Column(String(50), primary_key=True)  # e.g., "OCRAgent"
    name = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0.0")
    description = Column(String(512))
    config_schema = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkflowExecution(Base):
    """Trace of a workflow execution for a credit application."""
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String(50), nullable=False, index=True)
    product_type = Column(String(50))
    status = Column(String(20), default="running")  # running, completed, error, human_review
    state = Column(JSON, nullable=False)  # Full AgentState
    result = Column(JSON, nullable=True)  # Final decision card
    duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
