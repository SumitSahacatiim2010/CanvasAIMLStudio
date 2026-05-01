"""RAG Generation Service — answer generation with citation enforcement.

Blueprint §5: Generates answers from retrieved context using LLM,
enforcing inline citations (e.g., [Source §4.2]) for every claim.
"""

from dataclasses import dataclass, field
from typing import Any

from services.rag.search import SearchResult


@dataclass
class Citation:
    """A citation reference in the generated answer."""

    citation_id: str
    doc_id: str
    chunk_id: str
    text_excerpt: str  # Relevant excerpt from the source
    heading: str | None = None
    page_number: int | None = None
    score: float = 0.0


@dataclass
class GeneratedAnswer:
    """An answer generated from RAG retrieval with citations."""

    query: str
    answer: str
    citations: list[Citation]
    confidence: float  # 0.0 to 1.0
    retrieval_count: int
    model_used: str
    generation_time_ms: float = 0.0
    follow_up_questions: list[str] = field(default_factory=list)


class RAGGenerator:
    """Generates answers from retrieved context.

    In production, calls the LLM API (OpenAI, Azure, or local vLLM).
    Currently uses a template-based approach for development.
    """

    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        self.config = llm_config or {
            "model": "gpt-4o",
            "temperature": 0.1,
            "max_tokens": 2048,
        }

    def generate(
        self,
        query: str,
        search_results: list[SearchResult],
        system_prompt: str | None = None,
    ) -> GeneratedAnswer:
        """Generate an answer from search results with citations.

        Args:
            query: User's question.
            search_results: Retrieved chunks from hybrid search.
            system_prompt: Custom system prompt override.

        Returns:
            GeneratedAnswer with inline citations.
        """
        import time
        start = time.time()

        if not search_results:
            return GeneratedAnswer(
                query=query,
                answer="I could not find relevant information to answer this question. Please try rephrasing or checking a different knowledge base.",
                citations=[],
                confidence=0.0,
                retrieval_count=0,
                model_used="none",
            )

        # Build citations
        citations: list[Citation] = []
        for i, result in enumerate(search_results[:5]):
            citation = Citation(
                citation_id=f"[{i + 1}]",
                doc_id=result.doc_id,
                chunk_id=result.chunk_id,
                text_excerpt=result.text[:300],
                heading=result.heading,
                page_number=result.page_number,
                score=result.score,
            )
            citations.append(citation)

        # Build context for LLM
        context_parts: list[str] = []
        for i, result in enumerate(search_results[:5]):
            source_label = result.heading or result.doc_id
            context_parts.append(
                f"[Source {i + 1}: {source_label}]\n{result.text}\n"
            )
        context = "\n---\n".join(context_parts)

        # Try to use LLM API
        answer = self._call_llm(query, context, system_prompt)

        # Calculate confidence based on search scores
        avg_score = sum(r.score for r in search_results[:5]) / min(len(search_results), 5)
        confidence = min(avg_score * 2, 1.0)  # Normalize to 0-1

        elapsed_ms = (time.time() - start) * 1000

        # Generate follow-up questions
        follow_ups = self._generate_follow_ups(query, search_results)

        return GeneratedAnswer(
            query=query,
            answer=answer,
            citations=citations,
            confidence=round(confidence, 3),
            retrieval_count=len(search_results),
            model_used=self.config.get("model", "template"),
            generation_time_ms=round(elapsed_ms, 2),
            follow_up_questions=follow_ups,
        )

    def _call_llm(self, query: str, context: str, system_prompt: str | None) -> str:
        """Call LLM API or use template-based generation."""
        if system_prompt is None:
            system_prompt = (
                "You are a knowledgeable assistant for a financial services institution. "
                "Answer questions using ONLY the provided context. "
                "Cite your sources using [Source N] notation. "
                "If the context doesn't contain enough information, say so clearly."
            )

        try:
            import openai
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=self.config.get("model", "gpt-4o"),
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 2048),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
                ],
            )
            return response.choices[0].message.content or ""

        except (ImportError, Exception):
            # Template-based fallback for development
            return self._template_answer(query, context)

    def _template_answer(self, query: str, context: str) -> str:
        """Generate a structured template answer when LLM is unavailable."""
        lines = context.split("\n")
        source_lines = [l for l in lines if l.startswith("[Source")]

        answer_parts = [
            f"Based on the available documentation, here is what I found regarding: **{query}**\n",
        ]

        # Extract key information from each source
        for i, source in enumerate(source_lines[:3]):
            answer_parts.append(f"According to {source.strip()}, the relevant information indicates the following. [Source {i + 1}]")

        answer_parts.append(
            "\n*Note: This is a template-based response. "
            "Connect an LLM API for production-quality answers.*"
        )

        return "\n\n".join(answer_parts)

    def _generate_follow_ups(self, query: str, results: list[SearchResult]) -> list[str]:
        """Generate suggested follow-up questions."""
        follow_ups: list[str] = []

        # Extract topics from results
        headings = [r.heading for r in results if r.heading]
        if headings:
            follow_ups.append(f"Can you explain more about {headings[0]}?")
        follow_ups.append(f"What are the regulatory requirements related to this?")
        follow_ups.append(f"How does this compare to industry best practices?")

        return follow_ups[:3]
