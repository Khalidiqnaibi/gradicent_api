from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import math
import traceback
import time

from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.chains import RetrievalQA
from pydantic import BaseModel

# * MY TOOLS * #
from dependencies.rag import RetrievalPipeline
from dependencies.rag import MetaAwareRetriever


DEFAULT_PROMPT = """You are a clinical decision support assistant. Use ONLY the information in **YOUR KNOWLEDGE**. If the knowledge is insufficient, say you do not know and list what evidence is missing.

Rules (be detailed):
- Answer in the same language as the question, in clear full sentences.
- Start with a short **Summary** (2-5 lines).
- Always provide **Reasoning** (detailed, stepwise) and cite supporting passages inline using [^S#].
- **Only include** a **Most likely diagnosis** and/or **Management / Treatment** section if the user's question explicitly asks for them or clearly implies them (e.g., asks for diagnosis, differentials, treatment, management, or next steps). Otherwise omit those headers.
- If sources conflict, state the conflict and why you prioritize one, with citations.
- Do NOT invent facts or use information outside **YOUR KNOWLEDGE**.
- Do NOT output JSON, YAML, or machine-only formats.

YOUR KNOWLEDGE:
{context}

QUESTION:
{question}

Answer (use inline citations like [^S1]; finish with a short Sources list):
Sources:
- [^S1] {s1_meta}
- [^S2] {s2_meta}
- [^S3] {s3_meta}
- [^S4] {s4_meta}
""".strip()


class RankConfig(BaseModel):
    # weights for fusion of base retriever score and metadata features
    w_semantic: float = 0.60
    w_bm25: float = 0.25
    w_meta: float = 0.15

    # metadata feature weights (sum doesn't have to be 1.0)
    w_recency: float = 0.40         # boost newer materials if dates exist
    w_section: float = 0.35         # boost clinically critical sections e.g., diagnosis/management
    w_source_priority: float = 0.25 # boost authoritative books/guidelines

    # MMR diversification (0 => none, 1 => max novelty)
    mmr_lambda: float = 0.35

    # adjacency expansion
    expand_neighbors: int = 1       # include +/- N neighbor chunks if available to improve continuity

    # caps
    max_docs_initial: int = 24
    max_docs_final: int = 8

CRITICAL_SECTIONS = {"diagnosis", "management", "treatment", "assessment", "guideline", "summary"}

def build_context_snippets(docs: List[Document], char_budget: int = 7000) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Produce a compact context with labeled sources [^S#] for inline citation.
    Returns (context_text, source_cards)
    - source_cards[i] has fields: id, book, file, page, line, source, doc_id
    """
    pieces: List[str] = []
    cards: List[Dict[str, Any]] = []
    total = 0

    def meta_line(md: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        book = md.get("book") or md.get("title") or md.get("source_book") or "Unknown Book"
        file = md.get("source_file") or md.get("file_name") or md.get("source") or "unknown"
        page = md.get("page") or md.get("page_number") or "?"
        line = md.get("line") or md.get("line_number") or "?"
        return f"{book}, {file}, p.{page}, line {line}", {
            "book": book, "file": file, "page": page, "line": line,
            "source": md.get("source"), "doc_id": md.get("doc_id")
        }

    s_index = 1
    for d in docs:
        text = (getattr(d, "page_content", "") or "").strip()
        if not text:
            continue
        md = getattr(d, "metadata", {}) or {}
        evid_str, meta = meta_line(md)
        tag = f"[^S{s_index}]"
        snippet = f"--- {tag} ---\n{text}\n"
        remaining = max(0, char_budget - total)
        if remaining <= 0:
            break
        if len(snippet) > remaining:
            snippet = snippet[:remaining] + "\n... [truncated]"
        pieces.append(snippet)
        total += len(snippet)
        cards.append({"id": tag, **meta})
        s_index += 1

    return "\n".join(pieces), cards

def evidence_block(cards: List[Dict[str, Any]]) -> Dict[str, str]:
    """Map up to 4 cards into s1_meta..s4_meta replacements for the prompt."""
    lines = []
    for c in cards[:4]:
        lines.append(f"{c['book']}, {c['file']}, p.{c['page']}, line {c['line']}")
    # pad to 4 so the prompt variables exist
    while len(lines) < 4:
        lines.append("—")
    return {
        "s1_meta": lines[0],
        "s2_meta": lines[1],
        "s3_meta": lines[2],
        "s4_meta": lines[3],
    }

class QASystem:
    def __init__(self,
                 pipeline: RetrievalPipeline,
                 prompt_template: Optional[str] = None,
                 chain_type: str = "stuff",
                 rank_cfg: RankConfig = RankConfig()):
        self.pipeline = pipeline
        self.prompt_template = prompt_template or DEFAULT_PROMPT
        self.chain_type = chain_type
        self.rank_cfg = rank_cfg

        # base retrievers from your pipeline
        self.hybrid = self.pipeline.hybrid_retriever
        self.compressor = self.pipeline.create_compression_retriever(base_retriever=self.hybrid)

        # meta-aware re-ranker wrapper on top of compression retriever
        self.retriever = MetaAwareRetriever.from_retriever(self.compressor, cfg=dict(self.rank_cfg))

        self.qa_chain = self._build_qa_chain()

    def _build_qa_chain(self):
        prompt = PromptTemplate(
            input_variables=["context", "question", "s1_meta", "s2_meta", "s3_meta", "s4_meta"],
            template=self.prompt_template
        )
        # We use RetrievalQA primarily for its interface; we still prebuild context ourselves for control.
        return RetrievalQA.from_chain_type(
            llm=self.pipeline.answer_llm,
            retriever=self.retriever,
            chain_type=self.chain_type,
            chain_type_kwargs={"prompt": prompt}
        )


    # ---- Dynamic controls
    def refresh_retriever(self, doc_description: Optional[str] = None):
        # maintain your pipeline’s self-query retriever to generate filters,
        # but keep hybrid as main search for breadth
        self.hybrid = self.pipeline.hybrid_retriever
        self.compressor = self.pipeline.create_compression_retriever(base_retriever=self.hybrid)
        self.retriever = MetaAwareRetriever(self.compressor, cfg=self.rank_cfg)
        self.qa_chain = self._build_qa_chain()

    def update_prompt(self, new_template: str):
        self.prompt_template = new_template
        self.qa_chain = self._build_qa_chain()

    def switch_retriever_mode(self, mode: str = "meta-aware"):
        if mode == "hybrid":
            self.retriever = self.hybrid
        elif mode == "compression":
            self.retriever = self.compressor
        elif mode in ("meta", "meta-aware", "rerank"):
            self.retriever = MetaAwareRetriever(self.compressor, cfg=self.rank_cfg)
        else:
            raise ValueError(f"Unknown retriever mode: {mode}")
        self.qa_chain = self._build_qa_chain()

    # ---- Internal prompt assembly to guarantee metadata usage + citations
    def _assemble_prompt(self, question: str, docs: List[Document]) -> str:
        context_text, cards = build_context_snippets(docs)
        ev = evidence_block(cards)
        prompt = PromptTemplate(
            input_variables=["context", "question", "s1_meta", "s2_meta", "s3_meta", "s4_meta"],
            template=self.prompt_template
        ).format(
            context=context_text,
            question=question,
            **ev
        )
        return prompt

    # ---- Public APIs
    def ask(self, question: str) -> str:
        """Grounded answer with inline citations. Safe fallbacks included."""
        try:
            # Pull docs directly so we can control context packing
            docs = self.retriever.get_relevant_documents(question)
            prompt_text = self._assemble_prompt(question, docs)
            return self.pipeline.answer_llm(prompt_text)
        except Exception as e:
            print("ask() primary failed:", e)
            print(traceback.format_exc())
            # small-payload fallback
            try:
                docs = self.hybrid.get_relevant_documents(question)[:6]
            except Exception:
                docs = []
            prompt_text = self._assemble_prompt(question, docs)
            try:
                # Some LLM classes expose ._call(), others are callable
                if hasattr(self.pipeline.answer_llm, "_call"):
                    return self.pipeline.answer_llm._call(prompt_text)
                return self.pipeline.answer_llm(prompt_text)
            except Exception as e2:
                return f"Unable to generate an answer at this time. Details: {e2}"

    def ask_with_metadata(self, question: str, return_sources: bool = True) -> Dict[str, Any] | str:
        """
        Returns {'answer', 'source_documents'} by default.
        source_documents contain page_content and metadata (as retrieved after rerank+expand).
        """
        try:
            docs = self.retriever.get_relevant_documents(question)
            prompt_text = self._assemble_prompt(question, docs)
            answer = self.pipeline.answer_llm(prompt_text)
            if not return_sources:
                return answer
            return {
                "answer": answer,
                "source_documents": [
                    {"page_content": d.page_content, "metadata": getattr(d, "metadata", {}) or {}}
                    for d in docs
                ]
            }
        except Exception as e:
            print("ask_with_metadata() failed:", e)
            print(traceback.format_exc())
            return {
                "answer": f"Retrieval or generation failed: {e}",
                "source_documents": []
            }

    def ask_structured(self, question: str) -> Dict[str, Any]:
        """
        Returns a structured payload you can log/trace:
        - answer (str)
        - citations (list of {id, book, file, page, line})
        - used_filters (from self-query retriever if available)
        - timing
        """
        t0 = time.time()
        try:
            # If your pipeline exposes the last self-query filters, include them:
            used_filters = getattr(self.pipeline, "last_filters", None)

            docs = self.retriever.get_relevant_documents(question)
            ctx, cards = build_context_snippets(docs)
            prompt_text = PromptTemplate(
                input_variables=["context", "question", "s1_meta", "s2_meta", "s3_meta", "s4_meta"],
                template=self.prompt_template
            ).format(context=ctx, question=question, **evidence_block(cards))

            if hasattr(self.pipeline.answer_llm, "_call"):
                answer = self.pipeline.answer_llm._call(prompt_text)
            else:
                answer = self.pipeline.answer_llm(prompt_text)

            return {
                "answer": answer,
                "citations": cards,
                "used_filters": used_filters,
                "timing_ms": int((time.time() - t0) * 1000)
            }
        except Exception as e:
            return {
                "answer": f"Failed to answer: {e}",
                "citations": [],
                "used_filters": None,
                "timing_ms": int((time.time() - t0) * 1000)
            }
