import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from services.gateway.app.database import Base

class Source(Base):
    __tablename__ = "catalog_sources"
    
    id = Column(String, primary_key=True, default=lambda: f"src-{uuid.uuid4().hex[:8]}")
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="inactive")
    description = Column(String, nullable=False, default="")
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Dataset(Base):
    __tablename__ = "catalog_datasets"
    
    id = Column(String, primary_key=True, default=lambda: f"ds-{uuid.uuid4().hex[:8]}")
    source_id = Column(String, ForeignKey("catalog_sources.id"), nullable=False)
    name = Column(String(255), nullable=False)
    row_count = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    fields = Column(JSONB, nullable=False, default=list)
    field_count = Column(Integer, nullable=False, default=0)
    tags = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LineageEdge(Base):
    __tablename__ = "catalog_lineage_edges"
    
    id = Column(String, primary_key=True, default=lambda: f"lin-{uuid.uuid4().hex[:8]}")
    upstream_dataset_id = Column(String, ForeignKey("catalog_datasets.id"), nullable=False)
    downstream_dataset_id = Column(String, ForeignKey("catalog_datasets.id"), nullable=False)
    transform_type = Column(String(50), nullable=False, default="derived")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
