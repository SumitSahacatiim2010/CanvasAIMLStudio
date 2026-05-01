"""Hybrid Search Engine — pgvector + keyword + Reciprocal Rank Fusion.

Blueprint §5: Three retrieval strategies combined via RRF:
1. Dense (vector similarity via pgvector or in-memory)
2. Sparse (BM25-style keyword matching)
3. Reranking (cross-encoder or score-based fusion)
"""

from dataclasses import dataclass, field
from typing import Any
import math
import re

from services.rag.chunking import Chunk


@dataclass
class SearchResult:
    """A single search result with source attribution."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    rank: int
    retrieval_method: str  # dense, sparse, hybrid
    metadata: dict[str, Any] = field(default_factory=dict)
    heading: str | None = None
    section: str | None = None
    page_number: int | None = None


@dataclass
class SearchResponse:
    """Complete search response with results and diagnostics."""

    query: str
    results: list[SearchResult]
    total_results: int
    retrieval_methods_used: list[str]
    fusion_method: str
    search_time_ms: float = 0.0


class VectorIndex:
    """In-memory vector index using numpy (pgvector adapter in production).

    Stores chunk embeddings and supports cosine similarity search.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._embeddings: list[list[float]] = []
        self._embed_model: Any = None

    def _get_embed_model(self) -> Any:
        """Lazy-load the embedding model."""
        if self._embed_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                self._embed_model = "stub"
        return self._embed_model

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using the model or stub."""
        model = self._get_embed_model()
        if model == "stub":
            # Deterministic stub embeddings for dev
            import hashlib
            result = []
            for text in texts:
                h = hashlib.sha256(text.encode()).hexdigest()
                vec = [int(h[i:i+2], 16) / 255.0 for i in range(0, min(len(h), 768 * 2), 2)]
                while len(vec) < 384:
                    vec.append(0.0)
                result.append(vec[:384])
            return result
        return model.encode(texts).tolist()

    def add_chunks(self, chunks: list[Chunk]) -> int:
        """Add chunks to the index."""
        texts = [c.text for c in chunks]
        embeddings = self._embed(texts)
        self._chunks.extend(chunks)
        self._embeddings.extend(embeddings)
        return len(chunks)

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        """Search by vector similarity."""
        import numpy as np

        if not self._embeddings:
            return []

        query_emb = np.array(self._embed([query])[0])
        scores = []
        for emb in self._embeddings:
            emb_arr = np.array(emb)
            norm_q = np.linalg.norm(query_emb)
            norm_e = np.linalg.norm(emb_arr)
            if norm_q > 0 and norm_e > 0:
                cos_sim = float(np.dot(query_emb, emb_arr) / (norm_q * norm_e))
            else:
                cos_sim = 0.0
            scores.append(cos_sim)

        ranked = sorted(enumerate(scores), key=lambda x: -x[1])[:top_k]
        return [(self._chunks[idx], score) for idx, score in ranked]

    @property
    def size(self) -> int:
        return len(self._chunks)


class KeywordIndex:
    """BM25-style keyword search index."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._doc_freqs: dict[str, int] = {}
        self._total_docs: int = 0
        self._avg_dl: float = 0.0

    def add_chunks(self, chunks: list[Chunk]) -> int:
        """Index chunks for keyword search."""
        self._chunks.extend(chunks)
        self._total_docs = len(self._chunks)

        # Update document frequencies
        for chunk in chunks:
            terms = set(self._tokenize(chunk.text))
            for term in terms:
                self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1

        # Update average document length
        total_len = sum(len(self._tokenize(c.text)) for c in self._chunks)
        self._avg_dl = total_len / max(self._total_docs, 1)

        return len(chunks)

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        """BM25 keyword search."""
        query_terms = self._tokenize(query)
        if not query_terms or not self._chunks:
            return []

        k1, b = 1.5, 0.75
        scores: list[tuple[int, float]] = []

        for i, chunk in enumerate(self._chunks):
            doc_terms = self._tokenize(chunk.text)
            dl = len(doc_terms)
            score = 0.0

            term_freq: dict[str, int] = {}
            for t in doc_terms:
                term_freq[t] = term_freq.get(t, 0) + 1

            for qt in query_terms:
                if qt not in term_freq:
                    continue
                tf = term_freq[qt]
                df = self._doc_freqs.get(qt, 0)
                idf = math.log((self._total_docs - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(self._avg_dl, 1)))
                score += idf * tf_norm

            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: -x[1])
        return [(self._chunks[idx], score) for idx, score in scores[:top_k]]

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + punctuation tokenizer."""
        return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 1]


# ── Reciprocal Rank Fusion ───────────────────────────────


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[Chunk, float]]],
    k: int = 60,
    top_n: int = 10,
) -> list[tuple[Chunk, float]]:
    """Fuse multiple ranked lists using Reciprocal Rank Fusion.

    RRF score = Σ 1 / (k + rank_i) across all lists.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}

    for ranked_list in ranked_lists:
        for rank, (chunk, _original_score) in enumerate(ranked_list, 1):
            cid = chunk.chunk_id
            if cid not in scores:
                scores[cid] = 0.0
                chunk_map[cid] = chunk
            scores[cid] += 1.0 / (k + rank)

    sorted_items = sorted(scores.items(), key=lambda x: -x[1])[:top_n]
    return [(chunk_map[cid], score) for cid, score in sorted_items]


# ── Hybrid Search Engine ─────────────────────────────────


class HybridSearchEngine:
    """Combines dense vector search, sparse keyword search, and RRF fusion."""

    def __init__(self) -> None:
        self.vector_index = VectorIndex()
        self.keyword_index = KeywordIndex()

    def index_chunks(self, chunks: list[Chunk]) -> dict[str, int]:
        """Index chunks in both vector and keyword indices."""
        v_count = self.vector_index.add_chunks(chunks)
        k_count = self.keyword_index.add_chunks(chunks)
        return {"vector_indexed": v_count, "keyword_indexed": k_count}

    def search(
        self,
        query: str,
        top_k: int = 10,
        methods: list[str] | None = None,
        rrf_k: int = 60,
    ) -> SearchResponse:
        """Execute hybrid search with configurable retrieval methods."""
        import time
        start = time.time()

        if methods is None:
            methods = ["dense", "sparse"]

        ranked_lists: list[list[tuple[Chunk, float]]] = []

        if "dense" in methods:
            dense_results = self.vector_index.search(query, top_k * 2)
            ranked_lists.append(dense_results)

        if "sparse" in methods:
            sparse_results = self.keyword_index.search(query, top_k * 2)
            ranked_lists.append(sparse_results)

        # Fuse results
        if len(ranked_lists) > 1:
            fused = reciprocal_rank_fusion(ranked_lists, k=rrf_k, top_n=top_k)
            fusion_method = "rrf"
        elif ranked_lists:
            fused = ranked_lists[0][:top_k]
            fusion_method = "single"
        else:
            fused = []
            fusion_method = "none"

        # Build response
        results: list[SearchResult] = []
        for rank, (chunk, score) in enumerate(fused, 1):
            results.append(SearchResult(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                text=chunk.text,
                score=round(score, 6),
                rank=rank,
                retrieval_method=fusion_method,
                metadata=chunk.metadata,
                heading=chunk.heading,
                section=chunk.section,
                page_number=chunk.page_number,
            ))

        elapsed_ms = (time.time() - start) * 1000

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            retrieval_methods_used=methods,
            fusion_method=fusion_method,
            search_time_ms=round(elapsed_ms, 2),
        )

    @property
    def index_size(self) -> int:
        return self.vector_index.size
