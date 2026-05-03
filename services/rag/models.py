from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from services.gateway.app.database import Base
from services.rag.ingestion import IngestionStatus, DocumentType

class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(String(50), primary_key=True)  # DOC-hash
    title = Column(String(255), nullable=False)
    doc_type = Column(SQLEnum(DocumentType), nullable=False)
    source_path = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=False)
    raw_text = Column(Text, nullable=True)
    page_count = Column(Integer, default=1)
    metadata_json = Column(JSON, default=dict)
    status = Column(SQLEnum(IngestionStatus), default=IngestionStatus.COMPLETED)
    error = Column(Text, nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
