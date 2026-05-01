"""Chunking Pipeline — text segmentation strategies for RAG indexing.

Blueprint §5: Three chunking strategies:
1. Recursive character splitting (default, general purpose)
2. Semantic chunking (embedding-based topic boundaries)
3. Document-structure-aware chunking (header/section detection)
"""

from dataclasses import dataclass, field
from typing import Any
import hashlib
import re


@dataclass
class Chunk:
    """A single text chunk ready for embedding and indexing."""

    chunk_id: str
    doc_id: str
    text: str
    token_count: int  # Approximate
    chunk_index: int  # Position in document
    total_chunks: int
    metadata: dict[str, Any] = field(default_factory=dict)
    # Source attribution
    page_number: int | None = None
    section: str | None = None
    heading: str | None = None


def _approx_tokens(text: str) -> int:
    """Approximate token count (1 token ≈ 4 chars for English)."""
    return len(text) // 4


# ── Strategy 1: Recursive Character Splitting ────────────


def recursive_split(
    text: str,
    doc_id: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 128,
    separators: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Split text recursively by separators, falling back to character splits.

    Tries to split on paragraph breaks first, then sentences, then words.
    Produces overlapping chunks for context continuity.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    chunks: list[Chunk] = []
    segments = _recursive_split_impl(text, chunk_size, separators)

    # Apply overlap
    merged: list[str] = []
    for i, seg in enumerate(segments):
        if i > 0 and chunk_overlap > 0:
            # Prepend overlap from previous segment
            prev = segments[i - 1]
            overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            seg = overlap_text + seg
        merged.append(seg)

    for i, chunk_text in enumerate(merged):
        if not chunk_text.strip():
            continue
        chunk_id = f"{doc_id}_rc_{i:04d}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=chunk_text.strip(),
            token_count=_approx_tokens(chunk_text),
            chunk_index=i,
            total_chunks=len(merged),
            metadata=metadata or {},
        ))

    # Fix total_chunks
    for c in chunks:
        c.total_chunks = len(chunks)

    return chunks


def _recursive_split_impl(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    """Recursive implementation of text splitting."""
    if len(text) <= chunk_size:
        return [text]

    if not separators:
        # Last resort: character split
        result = []
        for i in range(0, len(text), chunk_size):
            result.append(text[i:i + chunk_size])
        return result

    sep = separators[0]
    remaining_seps = separators[1:]

    if sep == "":
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(sep)
    result: list[str] = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                result.append(current)
            if len(part) > chunk_size:
                # Part itself is too large — recurse with next separator
                sub_parts = _recursive_split_impl(part, chunk_size, remaining_seps)
                result.extend(sub_parts)
                current = ""
            else:
                current = part

    if current:
        result.append(current)

    return result


# ── Strategy 2: Semantic Chunking ────────────────────────


def semantic_split(
    text: str,
    doc_id: str,
    similarity_threshold: float = 0.5,
    min_chunk_size: int = 200,
    max_chunk_size: int = 2048,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Split text at semantic topic boundaries.

    Computes sentence-level embeddings and splits where
    cosine similarity drops below the threshold.

    Falls back to recursive splitting if embeddings are unavailable.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 1:
        return recursive_split(text, doc_id, max_chunk_size, 128, metadata=metadata)

    try:
        # Try to compute embeddings for boundary detection
        from sentence_transformers import SentenceTransformer
        import numpy as np

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(sentences)

        # Find semantic boundaries
        boundaries: list[int] = [0]
        for i in range(1, len(embeddings)):
            sim = float(np.dot(embeddings[i - 1], embeddings[i]) /
                        (np.linalg.norm(embeddings[i - 1]) * np.linalg.norm(embeddings[i]) + 1e-8))
            if sim < similarity_threshold:
                boundaries.append(i)
        boundaries.append(len(sentences))

        # Build chunks from boundaries
        chunks: list[Chunk] = []
        for b in range(len(boundaries) - 1):
            chunk_sentences = sentences[boundaries[b]:boundaries[b + 1]]
            chunk_text = " ".join(chunk_sentences)

            # Enforce size limits
            if len(chunk_text) > max_chunk_size:
                sub_chunks = recursive_split(chunk_text, doc_id, max_chunk_size, 128, metadata=metadata)
                chunks.extend(sub_chunks)
            elif len(chunk_text) >= min_chunk_size:
                chunk_id = f"{doc_id}_sem_{b:04d}"
                chunks.append(Chunk(
                    chunk_id=chunk_id, doc_id=doc_id, text=chunk_text,
                    token_count=_approx_tokens(chunk_text),
                    chunk_index=b, total_chunks=len(boundaries) - 1,
                    metadata={"strategy": "semantic", **(metadata or {})},
                ))

        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.total_chunks = len(chunks)

        return chunks if chunks else recursive_split(text, doc_id, max_chunk_size, 128, metadata=metadata)

    except ImportError:
        # Fallback if sentence-transformers not available
        return recursive_split(text, doc_id, max_chunk_size, 128, metadata=metadata)


# ── Strategy 3: Structure-Aware Chunking ─────────────────


def structure_aware_split(
    text: str,
    doc_id: str,
    max_chunk_size: int = 2048,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Split text based on document structure (headers, sections).

    Detects markdown-style headers, numbered sections, and page breaks.
    Preserves section hierarchy in chunk metadata.
    """
    # Detect section boundaries
    header_patterns = [
        (r'^(#{1,4})\s+(.+)$', 'markdown'),
        (r'^(\d+\.[\d.]*)\s+(.+)$', 'numbered'),
        (r'^(Section|Article|Part|Chapter)\s+(\d+[.\d]*)\s*[:\-–]?\s*(.*)$', 'formal'),
        (r'^---\s*Page Break\s*---$', 'page_break'),
    ]

    lines = text.split("\n")
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] = {"heading": "Introduction", "level": 0, "lines": []}
    current_page = 1

    for line in lines:
        is_header = False
        for pattern, ptype in header_patterns:
            match = re.match(pattern, line.strip(), re.IGNORECASE)
            if match:
                if ptype == "page_break":
                    current_page += 1
                    continue

                # Save current section
                if current_section["lines"]:
                    sections.append(current_section)

                if ptype == "markdown":
                    level = len(match.group(1))
                    heading = match.group(2).strip()
                elif ptype == "numbered":
                    level = match.group(1).count(".")
                    heading = match.group(2).strip()
                else:
                    level = 1
                    heading = f"{match.group(1)} {match.group(2)} {match.group(3) if match.lastindex >= 3 else ''}".strip()

                current_section = {"heading": heading, "level": level, "lines": [], "page": current_page}
                is_header = True
                break

        if not is_header:
            current_section["lines"].append(line)

    if current_section["lines"]:
        sections.append(current_section)

    # Build chunks from sections
    chunks: list[Chunk] = []
    for i, section in enumerate(sections):
        section_text = "\n".join(section["lines"]).strip()
        if not section_text:
            continue

        if len(section_text) > max_chunk_size:
            sub_chunks = recursive_split(section_text, doc_id, max_chunk_size, 128, metadata=metadata)
            for sc in sub_chunks:
                sc.heading = section["heading"]
                sc.section = section["heading"]
                sc.page_number = section.get("page")
            chunks.extend(sub_chunks)
        else:
            chunk_id = f"{doc_id}_sec_{i:04d}"
            chunks.append(Chunk(
                chunk_id=chunk_id, doc_id=doc_id, text=section_text,
                token_count=_approx_tokens(section_text),
                chunk_index=i, total_chunks=len(sections),
                heading=section["heading"], section=section["heading"],
                page_number=section.get("page"),
                metadata={"strategy": "structure", **(metadata or {})},
            ))

    for i, c in enumerate(chunks):
        c.chunk_index = i
        c.total_chunks = len(chunks)

    return chunks if chunks else recursive_split(text, doc_id, max_chunk_size, 128, metadata=metadata)


# ── Chunking Pipeline Orchestrator ───────────────────────


def chunk_document(
    text: str,
    doc_id: str,
    strategy: str = "recursive",
    chunk_size: int = 1024,
    chunk_overlap: int = 128,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Chunk a document using the specified strategy.

    Args:
        text: Document text to chunk.
        doc_id: Document identifier for chunk attribution.
        strategy: "recursive" | "semantic" | "structure"
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.
        metadata: Additional metadata to attach to chunks.

    Returns:
        List of Chunk objects ready for embedding.
    """
    if strategy == "semantic":
        return semantic_split(text, doc_id, metadata=metadata, max_chunk_size=chunk_size)
    elif strategy == "structure":
        return structure_aware_split(text, doc_id, max_chunk_size=chunk_size, metadata=metadata)
    else:
        return recursive_split(text, doc_id, chunk_size, chunk_overlap, metadata=metadata)
