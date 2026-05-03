from sqlalchemy import Column, String, Integer, JSON, DateTime, Float, Text
from sqlalchemy.sql import func
from services.gateway.app.database import Base

class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String(100), nullable=False, index=True)  # Can be service name or model_id
    severity = Column(String(20), default="info")  # info, warning, critical
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)
    resolved = Column(Integer, default=0)  # 0: no, 1: yes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DriftReport(Base):
    __tablename__ = "drift_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(50), nullable=False)
    drift_score = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    p_value = Column(Float)
    is_drifted = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(100), nullable=False, index=True)
    metrics = Column(JSON, default=dict)
    prediction_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
