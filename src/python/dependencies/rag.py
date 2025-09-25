'''
Retrieval pipeline with:
 - Dense retrieval (Chroma)
 - Sparse retrieval (BM25, optional)
 - Hybrid retriever that merges dense + sparse results
 - SelfQueryRetriever for metadata filters / domain selection
 - Contextual compression applied as final stage before LLM

Notes:
 - BM25 uses `rank_bm25`. If not installed, sparse retrieval is skipped gracefully.
 - The HybridRetriever implements LangChain retriever interface (get_relevant_documents).
'''

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import math

from langchain.schema import Document, BaseRetriever
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.schema import AttributeInfo
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainFilter
from pydantic import Field

# runnable wrapper (some versions of LangChain provide this)
try:
    from langchain_core.runnables import RunnableLambda
except Exception:
    RunnableLambda = None

#* My Tools *#
from knowlage_base.chroma import ChromaStore
from knowlage_base.pinecone import PineconeStore
from models.mistaral import MistralLLM

# Optional BM25 import
try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None


##############
#! Immortal !#
##############

@dataclass
class RankConfig:
    w_semantic: float = 0.60
    w_bm25: float = 0.25
    w_meta: float = 0.15

    w_recency: float = 0.40
    w_section: float = 0.35
    w_source_priority: float = 0.25

    mmr_lambda: float = 0.35
    expand_neighbors: int = 1

    max_docs_initial: int = 24
    max_docs_final: int = 8


CRITICAL_SECTIONS = {"diagnosis", "management", "treatment", "assessment", "guideline", "summary"}


def _norm(x: float) -> float:
    if x is None:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _meta_score(md: Dict[str, Any], cfg: RankConfig) -> float:
    s = 0.0
    year = md.get("year") or md.get("published_year")
    if isinstance(year, (int, float)):
        s += cfg.w_recency * _norm((year - 2015) / 5.0)

    section = str(md.get("section", "")).lower()
    if section in CRITICAL_SECTIONS:
        s += cfg.w_section * 1.0
    elif section:
        s += cfg.w_section * 0.35

    prio = md.get("source_priority", 1)
    try:
        prio = float(prio)
    except Exception:
        prio = 1.0
    s += cfg.w_source_priority * _norm((prio - 1.0))
    return max(0.0, min(1.0, s))


def _doc_key(d: Document) -> str:
    md = getattr(d, "metadata", {}) or {}
    return str(md.get("doc_id") or md.get("source") or id(d))


def _neighbor_tag(md: Dict[str, Any]) -> Tuple[str, Optional[int]]:
    doc_id = str(md.get("doc_id") or md.get("source") or "unknown")
    idx = md.get("chunk_index") or md.get("chunk_id_index") or md.get("chunk_index_int")
    try:
        idx = int(idx) if idx is not None else None
    except Exception:
        idx = None
    return doc_id, idx


def _expand_neighbors(sorted_docs: List[Document], pool: Dict[Tuple[str, int], Document], cfg: RankConfig) -> List[Document]:
    seen = set()
    out: List[Document] = []
    for d in sorted_docs:
        md = getattr(d, "metadata", {}) or {}
        doc_id, idx = _neighbor_tag(md)
        k = (doc_id, idx if idx is not None else -1_000_000)
        if k not in seen:
            out.append(d); seen.add(k)
        if idx is None:
            continue
        for delta in range(1, cfg.expand_neighbors + 1):
            for nb in (idx - delta, idx + delta):
                kk = (doc_id, nb)
                if kk in pool and kk not in seen:
                    out.append(pool[kk]); seen.add(kk)
    return out

class MetaAwareRetriever(BaseRetriever):
    """
    LangChain-compatible retriever wrapper.
    Inherits BaseRetriever and implements both sync and async hooks:
      - _get_relevant_documents
      - _aget_relevant_documents

    Accepts a base retriever that can be any of:
      - a BaseRetriever (recommended)
      - an object exposing get_relevant_documents / aget_relevant_documents
      - a Runnable-like object exposing invoke(...)
      - a plain callable that returns a list of Documents
    """
    base: Any = Field(..., description="Underlying retriever or callable")
    cfg: RankConfig = Field(default_factory=RankConfig)

    class Config:
        arbitrary_types_allowed = True  # allow non-pydantic types

    # ---- Factory so we don't fight with Pydantic's __init__
    @classmethod
    def from_retriever(cls, base, cfg: RankConfig = RankConfig()):
        return cls(base=base, cfg=cfg)

    # ---- Hooks for LangChain
    def _get_relevant_documents(self, query: str, run_manager=None) -> List[Document]:
        docs = self._call_base_sync(query)
        return self._rerank(docs)

    async def _aget_relevant_documents(self, query: str, run_manager=None) -> List[Document]:
        docs = await self._call_base_async(query)
        return self._rerank(docs)

    # ---- Internal helpers
    def _call_base_sync(self, query: str) -> List[Document]:
        if hasattr(self.base, "get_relevant_documents"):
            return self.base.get_relevant_documents(query) or []
        if hasattr(self.base, "invoke"):
            return self.base.invoke(query) or []
        if callable(self.base):
            return self.base(query) or []
        raise RuntimeError("Base retriever is not callable or doesn't expose get_relevant_documents()")

    async def _call_base_async(self, query: str) -> List[Document]:
        if hasattr(self.base, "aget_relevant_documents"):
            return await self.base.aget_relevant_documents(query) or []
        return self._call_base_sync(query)

    def _rerank(self, docs: List[Document]) -> List[Document]:
        # your scoring logic (same as you already wrote) ...
        # keep _norm, _meta_score, _expand_neighbors helpers as is
        if not docs:
            return []
        docs = docs[: max(self.cfg.max_docs_initial, len(docs))]
        scored = []
        for d in docs:
            md = getattr(d, "metadata", {}) or {}
            sem = md.get("semantic_score")
            bm25 = md.get("bm25_score")
            sem_n = _norm(sem if isinstance(sem, (int, float)) else 0.0)
            bm25_n = _norm(bm25 if isinstance(bm25, (int, float)) else 0.0)
            meta_n = _meta_score(md, self.cfg)
            fused = (self.cfg.w_semantic * sem_n) + (self.cfg.w_bm25 * bm25_n) + (self.cfg.w_meta * meta_n)
            scored.append((d, fused))
        scored.sort(key=lambda x: x[1], reverse=True)

        # MMR + neighbor expansion (same as before)
        selected, seen_keys = [], set()
        for d, score in scored:
            k = _doc_key(d)
            if k not in seen_keys:
                selected.append((d, score))
                seen_keys.add(k)
            if len(selected) >= self.cfg.max_docs_final:
                break

        pool = {}
        for d in docs:
            md = getattr(d, "metadata", {}) or {}
            doc_id, idx = _neighbor_tag(md)
            if idx is not None:
                pool[(doc_id, idx)] = d

        expanded = _expand_neighbors([d for d, _ in selected], pool, self.cfg)
        return expanded[: self.cfg.max_docs_final]


class HybridRetriever:
    def __init__(
        self,
        vectorstore: ChromaStore,
        metadata_map: dict,
        sparse_texts: Optional[List[str]] = None,
        sparse_ids: Optional[List[str]] = None,
        top_k_dense: int = 5,
        top_k_sparse: int = 5,
    ):
        self.vectorstore = vectorstore
        self.metadata_map = metadata_map or {}
        self.top_k_dense = top_k_dense
        self.top_k_sparse = top_k_sparse

        if BM25Okapi and sparse_texts:
            tokenized = [t.split() for t in sparse_texts]
            self.bm25 = BM25Okapi(tokenized)
            self.sparse_ids = sparse_ids or list(range(len(sparse_texts)))
            self.sparse_texts = sparse_texts
        else:
            self.bm25 = None
            self.sparse_ids = []
            self.sparse_texts = []

    def _dense_search(self, query: str, k: int) -> List[Document]:
        try:
            store = getattr(self.vectorstore, "store", self.vectorstore)
            if hasattr(store, "similarity_search"):
                return store.similarity_search(query, k=k)
            if hasattr(store, "search"):
                return store.search(query, k)
            return []
        except Exception as e:
            print(f"Dense Chroma search error: {e}")
            return []

    def _bm25_search(self, query: str, k: int) -> List[Document]:
        if not self.bm25:
            return []
        q_tokens = query.split()
        scores = self.bm25.get_scores(q_tokens)
        top_n = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        docs = []
        for idx in top_n:
            doc_id = self.sparse_ids[idx]
            meta = self.metadata_map.get(str(doc_id), {})
            text = self.sparse_texts[idx]
            docs.append(Document(page_content=text, metadata=meta))
        return docs

    def _merge(self, dense: List[Document], sparse: List[Document], k: int) -> List[Document]:
        seen = set()
        merged = []
        for doc in dense + sparse:
            key = doc.metadata.get("chunk_id") or doc.metadata.get("source") or (doc.page_content or "")[:80]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
            if len(merged) >= k:
                break
        return merged

    def get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        dense_docs = self._dense_search(query, self.top_k_dense)
        sparse_docs = self._bm25_search(query, self.top_k_sparse)
        merged_docs = self._merge(dense_docs, sparse_docs, max(self.top_k_dense, self.top_k_sparse))
        return merged_docs

    def get_scores_for_query(self, query: str) -> dict:
        results = {"dense": [], "sparse": []}
        dense_docs = self._dense_search(query, self.top_k_dense)
        results["dense"] = [(doc.metadata, (doc.page_content or "")[:80]) for doc in dense_docs]
        if self.bm25:
            q_tokens = query.split()
            scores = self.bm25.get_scores(q_tokens)
            results["sparse"] = list(enumerate(scores))
        return results

class LengthLimitingRetriever:
    def __init__(self, base_retriever, max_docs: int = 5, max_chars_per_doc: int = 3500):
        self.base = base_retriever
        self.max_docs = max_docs
        self.max_chars_per_doc = max_chars_per_doc

    def get_relevant_documents(self, query: str, **kwargs):
        docs = []
        if hasattr(self.base, "get_relevant_documents"):
            docs = self.base.get_relevant_documents(query, **kwargs) or []
        else:
            try:
                docs = self.base.invoke(query) or []
            except Exception:
                try:
                    docs = self.base(query) or []
                except Exception:
                    docs = []
        out = []
        for d in docs[: self.max_docs]:
            md = getattr(d, "metadata", {}) or {}
            content = getattr(d, "page_content", b"") or ""
            if isinstance(content, (bytes, bytearray)):
                try:
                    content = content.decode("utf-8", errors="ignore")
                except Exception:
                    content = ""
            if len(content) > self.max_chars_per_doc:
                content = content[: self.max_chars_per_doc] + "\n... [truncated]"
            out.append(Document(page_content=content, metadata=md))
        return out


class _SelfQueryHybridRetriever:
    def __init__(self, selfquery_retriever, hybrid_retriever):
        self.selfquery = selfquery_retriever
        self.hybrid = hybrid_retriever

    def invoke(self, input_text: str):
        sq_docs = []
        try:
            sq_docs = self.selfquery.get_relevant_documents(input_text) or []
        except Exception:
            try:
                sq_docs = self.selfquery.invoke(input_text) or []
            except Exception:
                sq_docs = []

        hy_docs = []
        try:
            hy_docs = self.hybrid.get_relevant_documents(input_text) or []
        except Exception:
            hy_docs = []

        seen = set()
        merged = []
        for doc in sq_docs + hy_docs:
            key = doc.metadata.get("chunk_id") or doc.metadata.get("source") or (doc.page_content or "")[:80]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged

DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MISTRAL_MODE = "openrouter"
DEFAULT_MISTRAL_HF_MODEL = None

DEFAULT_FIELDS = [
    AttributeInfo(name="source", description="Source file name or origin", type="string"),
    AttributeInfo(name="page", description="Page number", type="integer"),
    AttributeInfo(name="chunk_id", description="Unique chunk identifier", type="string"),
    AttributeInfo(name="owner", description="Associated owner or entity", type="string"),
]


class RetrievalPipeline:
    def __init__(
        self,
        embed_model: str = DEFAULT_EMBED_MODEL,
        mistral_mode: str = DEFAULT_MISTRAL_MODE,
        mistral_hf_model: Optional[str] = DEFAULT_MISTRAL_HF_MODEL,
        metadata_fields: Optional[List[AttributeInfo]] = None,
    ):
        self.embed_model = embed_model
        self.metadata_fields = metadata_fields or DEFAULT_FIELDS

        # initialize ChromaStore (this expects ChromaStore to handle embeddings / persistence)
        self.embeddings = None  # optionally set by caller; ChromaStore handles fallback
        #self.vstore = ChromaStore(embeddings=self.embeddings)
        self.vstore = PineconeStore(embeddings=self.embeddings)
        self.metadata_map = self.vstore.get_metadata_map() or {}

        # initialize LLMs
        self.mistral_mode = mistral_mode
        self.mistral_hf_model = mistral_hf_model
        self.self_query_llm = MistralLLM(mode=self.mistral_mode, hf_model=self.mistral_hf_model, temperature=0.0, max_tokens=256)
        self.filter_llm = MistralLLM(mode=self.mistral_mode, hf_model=self.mistral_hf_model, temperature=0.0, max_tokens=256)
        self.answer_llm = MistralLLM(mode=self.mistral_mode, hf_model=self.mistral_hf_model, temperature=0.0, max_tokens=512)

        # build sparse corpus for BM25 (if available)
        sparse_texts, sparse_ids = [], []
        if isinstance(self.metadata_map, dict):
            for k, v in self.metadata_map.get("documents", {}).items():
                if isinstance(v, dict):
                    text = v.get("text") or v.get("page_content") or v.get("content") or ""
                    if text:
                        sparse_texts.append(text)
                        sparse_ids.append(k)

        # hybrid retriever
        self.hybrid_retriever = HybridRetriever(
            self.vstore,
            self.metadata_map.get("documents", {}),
            sparse_texts=sparse_texts,
            sparse_ids=sparse_ids,
        )

    def add_documents(self, docs: List[Document]):
        if not docs:
            return
        self.vstore.add_documents(docs)
        # update metadata map
        self.metadata_map = self.vstore.get_metadata_map()
        # optionally inform QA system if attached
        if hasattr(self, "qa_system") and getattr(self, "qa_system") is not None:
            try:
                self.qa_system.refresh_retriever()
            except Exception:
                pass

    def create_selfquery_retriever(self, doc_description: str = "Document chunks"):
        document_texts = []
        # construct texts array from metadata map if available
        for v in (self.metadata_map.get("documents", {}) or {}).values():
            if isinstance(v, dict):
                text = v.get("text") or v.get("page_content") or v.get("content")
                if text:
                    document_texts.append(text)
        return SelfQueryRetriever.from_llm(
            llm=self.self_query_llm,
            vectorstore=self.vstore.store,
            document_contents=document_texts,
            document_content_description=doc_description,
            metadata_field_info=self.metadata_fields,
        )

    def create_compression_retriever(self, base_retriever=None, max_docs=6, max_chars_per_doc=1500):
        if base_retriever is None:
            composite = _SelfQueryHybridRetriever(self.create_selfquery_retriever(), self.hybrid_retriever)
            if RunnableLambda is not None:
                base_runnable = RunnableLambda(lambda input_text: composite.invoke(input_text))
            else:
                # fallback: use an object with invoke
                base_runnable = composite
            base = base_runnable
        else:
            base = base_retriever

        limited = LengthLimitingRetriever(base, max_docs=max_docs, max_chars_per_doc=max_chars_per_doc)

        # wrap limited as runnable if RunnableLambda available
        base_runnable = RunnableLambda(lambda input_text: limited.get_relevant_documents(input_text)) if RunnableLambda is not None else limited

        base_compressor = LLMChainFilter.from_llm(self.filter_llm)
        return ContextualCompressionRetriever(base_retriever=base_runnable, base_compressor=base_compressor)

    def rebuild_hybrid_retriever(self, top_k_dense: int = 10, top_k_sparse: int = 10):
        sparse_texts, sparse_ids = [], []
        for k, v in (self.metadata_map.get("documents", {}) or {}).items():
            text = v.get("text") or v.get("page_content") or v.get("content")
            if text:
                sparse_texts.append(text)
                sparse_ids.append(k)
        self.hybrid_retriever = HybridRetriever(
            self.vstore,
            self.metadata_map.get("documents", {}),
            sparse_texts=sparse_texts,
            sparse_ids=sparse_ids,
            top_k_dense=top_k_dense,
            top_k_sparse=top_k_sparse,
        )

    def inspect_retrieval(self, query: str) -> dict:
        return self.hybrid_retriever.get_scores_for_query(query)

    def create_full_pipeline_retriever(self, doc_description: str = "Document chunks"):
        selfquery = self.create_selfquery_retriever(doc_description)
        composite = _SelfQueryHybridRetriever(selfquery, self.hybrid_retriever)
        base_runnable = RunnableLambda(lambda input_text: composite.invoke(input_text)) if RunnableLambda is not None else composite
        return self.create_compression_retriever(base_retriever=base_runnable)

    def switch_llm_model(self, mode: str = None, hf_model: Optional[str] = None):
        if mode:
            self.mistral_mode = mode
        if hf_model is not None:
            self.mistral_hf_model = hf_model
        # recreate instances
        self.self_query_llm = MistralLLM(mode=self.mistral_mode, hf_model=self.mistral_hf_model, temperature=0.0, max_tokens=256)
        self.filter_llm = MistralLLM(mode=self.mistral_mode, hf_model=self.mistral_hf_model, temperature=0.0, max_tokens=256)
        self.answer_llm = MistralLLM(mode=self.mistral_mode, hf_model=self.mistral_hf_model, temperature=0.0, max_tokens=512)

def build_context_snippets(docs: List[Document], char_budget: int = 7000):
    pieces = []
    cards = []
    total = 0
    s_index = 1
    for d in docs:
        text = (getattr(d, "page_content", "") or "").strip()
        if not text:
            continue
        md = getattr(d, "metadata", {}) or {}
        book = md.get("book") or md.get("title") or md.get("source_book") or "Unknown Book"
        file = md.get("source_file") or md.get("file_name") or md.get("source") or "unknown"
        page = md.get("page") or md.get("page_number") or "?"
        line = md.get("line") or md.get("line_number") or "?"
        tag = f"[^S{s_index}]"
        snippet = f"--- {tag} ---\n{text}\n"
        remaining = max(0, char_budget - total)
        if remaining <= 0:
            break
        if len(snippet) > remaining:
            snippet = snippet[:remaining] + "\n... [truncated]"
        pieces.append(snippet)
        total += len(snippet)
        cards.append({"id": tag, "book": book, "file": file, "page": page, "line": line, "source": md.get("source"), "doc_id": md.get("doc_id")})
        s_index += 1
    return "\n".join(pieces), cards


def evidence_block(cards: List[Dict[str, Any]]) -> Dict[str, str]:
    lines = []
    for c in cards[:4]:
        lines.append(f"{c['book']}, {c['file']}, p.{c['page']}, line {c['line']}")
    while len(lines) < 4:
        lines.append("—")
    return {"s1_meta": lines[0], "s2_meta": lines[1], "s3_meta": lines[2], "s4_meta": lines[3]}
