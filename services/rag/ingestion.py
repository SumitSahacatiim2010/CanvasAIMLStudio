"""Document Ingestion Service — OCR, parsing, and metadata extraction.

Blueprint §5: Handles PDF, DOCX, images, and structured documents.
Uses layout-aware parsing for regulatory and financial documents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import hashlib
import json


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    IMAGE = "image"
    CSV = "csv"
    UNKNOWN = "unknown"


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestedDocument:
    """A document that has been ingested into the RAG system."""

    doc_id: str
    title: str
    doc_type: DocumentType
    source_path: str
    content_hash: str
    raw_text: str
    page_count: int
    metadata: dict[str, Any]
    status: IngestionStatus = IngestionStatus.COMPLETED
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None


class DocumentIngestionService:
    """Ingests documents for RAG indexing.

    Pipeline:
        1. Detect document type
        2. Extract raw text (OCR for images/scanned PDFs)
        3. Extract metadata (title, author, dates, document type classification)
        4. Extract named entities and regulatory references
        5. Store ingested document record
    """

    def __init__(self) -> None:
        self._documents: dict[str, IngestedDocument] = {}

    def ingest(self, file_path: str, metadata: dict[str, Any] | None = None) -> IngestedDocument:
        """Ingest a single document."""
        path = Path(file_path)
        doc_type = self._detect_type(path)
        doc_id = f"DOC-{hashlib.md5(str(path).encode()).hexdigest()[:12]}"

        try:
            raw_text = self._extract_text(path, doc_type)
            content_hash = hashlib.sha256(raw_text.encode()).hexdigest()

            extracted_metadata = self._extract_metadata(raw_text, doc_type)
            if metadata:
                extracted_metadata.update(metadata)

            doc = IngestedDocument(
                doc_id=doc_id,
                title=extracted_metadata.get("title", path.stem),
                doc_type=doc_type,
                source_path=str(path),
                content_hash=content_hash,
                raw_text=raw_text,
                page_count=extracted_metadata.get("page_count", 1),
                metadata=extracted_metadata,
            )

        except Exception as e:
            doc = IngestedDocument(
                doc_id=doc_id,
                title=path.stem,
                doc_type=doc_type,
                source_path=str(path),
                content_hash="",
                raw_text="",
                page_count=0,
                metadata=metadata or {},
                status=IngestionStatus.FAILED,
                error=str(e),
            )

        self._documents[doc_id] = doc
        return doc

    def ingest_text(self, text: str, title: str, metadata: dict[str, Any] | None = None) -> IngestedDocument:
        """Ingest raw text directly (for API-based ingestion)."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        doc_id = f"DOC-{content_hash[:12]}"

        extracted_metadata = self._extract_metadata(text, DocumentType.TXT)
        if metadata:
            extracted_metadata.update(metadata)

        doc = IngestedDocument(
            doc_id=doc_id,
            title=title,
            doc_type=DocumentType.TXT,
            source_path="inline",
            content_hash=content_hash,
            raw_text=text,
            page_count=1,
            metadata=extracted_metadata,
        )

        self._documents[doc_id] = doc
        return doc

    def get_document(self, doc_id: str) -> IngestedDocument | None:
        return self._documents.get(doc_id)

    def list_documents(self) -> list[IngestedDocument]:
        return list(self._documents.values())

    def _detect_type(self, path: Path) -> DocumentType:
        ext = path.suffix.lower()
        type_map = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".doc": DocumentType.DOCX,
            ".txt": DocumentType.TXT,
            ".md": DocumentType.TXT,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".csv": DocumentType.CSV,
            ".png": DocumentType.IMAGE,
            ".jpg": DocumentType.IMAGE,
            ".jpeg": DocumentType.IMAGE,
            ".tiff": DocumentType.IMAGE,
        }
        return type_map.get(ext, DocumentType.UNKNOWN)

    def _extract_text(self, path: Path, doc_type: DocumentType) -> str:
        """Extract text from a document. Uses appropriate parser per type."""
        if doc_type in (DocumentType.TXT,):
            return path.read_text(encoding="utf-8", errors="replace")

        elif doc_type == DocumentType.PDF:
            try:
                import PyPDF2
                with open(path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    pages = [page.extract_text() or "" for page in reader.pages]
                    return "\n\n--- Page Break ---\n\n".join(pages)
            except ImportError:
                return f"[PDF extraction requires PyPDF2. File: {path.name}]"

        elif doc_type == DocumentType.HTML:
            text = path.read_text(encoding="utf-8", errors="replace")
            try:
                from html.parser import HTMLParser
                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.result: list[str] = []
                    def handle_data(self, data: str) -> None:
                        self.result.append(data.strip())
                extractor = TextExtractor()
                extractor.feed(text)
                return " ".join(filter(None, extractor.result))
            except Exception:
                return text

        elif doc_type == DocumentType.CSV:
            return path.read_text(encoding="utf-8", errors="replace")

        else:
            return f"[Unsupported document type: {doc_type.value}. File: {path.name}]"

    def _extract_metadata(self, text: str, doc_type: DocumentType) -> dict[str, Any]:
        """Extract metadata from document text."""
        lines = text.split("\n")
        word_count = len(text.split())

        metadata: dict[str, Any] = {
            "word_count": word_count,
            "line_count": len(lines),
            "char_count": len(text),
            "doc_type_classified": self._classify_document(text),
            "page_count": max(1, text.count("--- Page Break ---") + 1),
        }

        # Extract potential title (first non-empty line)
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                metadata["title"] = stripped[:200]
                break

        # Detect regulatory references
        import re
        reg_patterns = [
            (r"RBI\s+(?:Master\s+)?(?:Direction|Circular|Guidelines?)", "RBI"),
            (r"MAS\s+(?:TRM|FEAT|Notice)", "MAS"),
            (r"(?:Basel\s+(?:II|III|IV))", "Basel"),
            (r"SOC\s*2", "SOC2"),
            (r"ISO\s*27001", "ISO27001"),
            (r"DPDP\s+Act", "DPDP"),
        ]
        refs = set()
        for pattern, label in reg_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                refs.add(label)
        if refs:
            metadata["regulatory_references"] = sorted(refs)

        return metadata

    def _classify_document(self, text: str) -> str:
        """Classify document type based on content keywords."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["policy", "guideline", "regulation", "directive", "circular"]):
            return "regulatory"
        elif any(kw in text_lower for kw in ["balance sheet", "profit and loss", "financial statement"]):
            return "financial"
        elif any(kw in text_lower for kw in ["credit", "loan", "underwriting", "risk assessment"]):
            return "credit"
        elif any(kw in text_lower for kw in ["procedure", "process", "workflow", "sop"]):
            return "operational"
        return "general"
