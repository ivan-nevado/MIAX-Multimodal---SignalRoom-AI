"""Multimodal semantic search over a user's investigations.

Each completed investigation gets a small private index (``.../output/index/search.json``):
passages from the summary, drivers, claims, news, PDF facts and pages, transcript windows of
calls and videos, video slides, and uploaded images. Text passages are embedded with the
multimodal embedding model; uploaded images are embedded natively (same vector space), so a
text query can find a chart and an image query can find the call where it was discussed.

Scoring is hybrid (cosine + small lexical boost). Without an embedding model, or for indexes
built with a different model, it falls back to keyword scoring. Indexing is best-effort and
never fails an investigation. The index sits under the investigation prefix, so deleting the
investigation deletes it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from typing import Any, Literal

from pydantic import Field

from app.integrations.ai.base import AIError
from app.integrations.ai.gateway import AIGateway
from app.integrations.storage.base import StorageBackend, investigation_output_key, key_belongs_to
from app.repositories.base import Repositories
from app.schemas.agents import Transcript, TranscriptSegment
from app.schemas.common import Model
from app.schemas.investigations import InvestigationRecord
from app.services.errors import UpstreamUnavailable, ValidationFailed
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)

ChunkModality = Literal["summary", "driver", "claim", "news", "document", "image", "audio", "video"]
SearchModality = Literal["all", "analysis", "news", "document", "image", "audio", "video"]

MODALITY_GROUPS: dict[str, set[str]] = {
    "all": {"summary", "driver", "claim", "news", "document", "image", "audio", "video"},
    "analysis": {"summary", "driver", "claim"},
    "news": {"news"},
    "document": {"document"},
    "image": {"image"},
    "audio": {"audio"},
    "video": {"video"},
}
MAX_CHUNKS = 160
WINDOW_CHARS = 700
MAX_INDEXES = 100
MIN_SEMANTIC_SCORE = 0.3
MAX_HITS_PER_INVESTIGATION = 3
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.%$-]*")
_STOP = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "or",
    "to",
    "in",
    "on",
    "for",
    "is",
    "was",
    "what",
    "why",
    "did",
    "how",
    "with",
    "about",
    "de",
    "la",
    "el",
    "y",
    "en",
    "que",
}


class IndexChunk(Model):
    chunk_id: str
    modality: ChunkModality
    title: str
    text: str
    ref: str | None = None
    location: str | None = None  # "02:15" in a call/video, "p. 3" in a PDF
    vector: list[float] | None = None


class InvestigationIndex(Model):
    investigation_id: str
    symbol: str | None = None
    asset_name: str | None = None
    question: str = ""
    created_at: str = ""
    embedding_model: str | None = None
    indexed_at: str = ""
    chunks: list[IndexChunk] = Field(default_factory=list)


class SearchHit(Model):
    investigation_id: str
    symbol: str | None
    asset_name: str | None
    question: str
    created_at: str
    modality: ChunkModality
    title: str
    snippet: str
    ref: str | None = None
    location: str | None = None
    score: float


class SearchResponse(Model):
    query: str
    mode: Literal["semantic", "keyword", "image"]
    indexed_investigations: int
    hits: list[SearchHit]


def index_key(user_id: str, investigation_id: str) -> str:
    return investigation_output_key(user_id, investigation_id, "index", "search.json")


# ---------------------------------------------------------------------------- chunking
def _windows(segments: list[TranscriptSegment]) -> list[tuple[str | None, str]]:
    """Group transcript turns into ~WINDOW_CHARS passages, keeping the start timestamp."""
    out: list[tuple[str | None, str]] = []
    start: str | None = None
    buf: list[str] = []
    size = 0
    for seg in segments:
        if not buf:
            start = seg.start
        line = f"{seg.speaker}: {seg.text}"
        buf.append(line)
        size += len(line)
        if size >= WINDOW_CHARS:
            out.append((start, "\n".join(buf)))
            buf, size = [], 0
    if buf:
        out.append((start, "\n".join(buf)))
    return out


def _load_transcript(
    storage: StorageBackend, key: str | None, user_id: str, fallback: list[TranscriptSegment]
) -> list[TranscriptSegment]:
    if key and key_belongs_to(key, user_id):
        try:
            return Transcript.model_validate(json.loads(storage.get_bytes(key))).segments
        except Exception:
            logger.info("search_transcript_unavailable")
    return fallback


def build_chunks(record: InvestigationRecord, storage: StorageBackend) -> list[IndexChunk]:
    r = record.result
    if r is None:
        return []
    chunks: list[IndexChunk] = []

    def add(
        modality: ChunkModality, title: str, text: str, ref: str | None = None, location: str | None = None
    ) -> None:
        text = " ".join(text.split())
        if text:
            chunks.append(
                IndexChunk(
                    chunk_id=f"k{len(chunks)}",
                    modality=modality,
                    title=title,
                    text=text[:2000],
                    ref=ref,
                    location=location,
                )
            )

    add("summary", "Executive summary", f"{r.executive_summary} {r.what_happened}")
    for d in r.drivers:
        add("driver", f"Driver: {d.name}", f"{d.name}. {d.explanation}")
    for c in r.claims[:15]:
        add("claim", "Claim", c.claim)
    if r.news is not None:
        for cl in r.news.clusters[:10]:
            add(
                "news",
                f"News: {cl.theme}",
                cl.theme
                + ". "
                + " ".join(a.title for a in r.news.articles if a.id in set(cl.article_ids))[:1500],
            )
    for doc in r.documents:
        add("document", f"{doc.filename} - summary", doc.summary, doc.upload_id)
        for i in range(0, len(doc.key_facts), 5):
            facts = doc.key_facts[i : i + 5]
            page = facts[0].page
            add(
                "document",
                f"{doc.filename} - key facts",
                "; ".join(f"{f.fact}: {f.value}" if f.value else f.fact for f in facts),
                doc.upload_id,
                f"p. {page}" if page else None,
            )
        for vp in doc.visual_pages:
            figs = "; ".join(f"{f.fact}: {f.value}" for f in vp.extracted_figures[:6])
            add(
                "document",
                f"{doc.filename} - page {vp.page}",
                f"{vp.description} {figs}",
                doc.upload_id,
                f"p. {vp.page}",
            )
        if doc.risks or doc.guidance:
            add(
                "document",
                f"{doc.filename} - guidance & risks",
                " ".join(doc.guidance + doc.risks),
                doc.upload_id,
            )
    for img in r.images:
        add(
            "image",
            f"{img.filename} - {img.image_type.replace('_', ' ')}",
            " ".join([*img.observations, img.interpretation or ""]),
            img.upload_id,
        )
    for clip in r.audio:
        if clip.analysis is not None:
            a = clip.analysis
            add(
                "audio",
                f"{clip.filename} - summary",
                " ".join([a.summary, *a.key_points, *a.guidance]),
                clip.upload_id,
            )
        for start, text in _windows(
            _load_transcript(storage, clip.transcript_key, record.user_id, clip.transcript_preview)
        ):
            add("audio", f"{clip.filename} - transcript", text, clip.upload_id, start)
    for vid in r.videos:
        add(
            "video",
            f"{vid.filename} - summary",
            " ".join([vid.summary, *vid.key_points, *vid.guidance]),
            vid.upload_id,
        )
        for s in vid.slides:
            figs = "; ".join(f"{f.fact}: {f.value}" for f in s.figures)
            add(
                "video",
                f"{vid.filename} - slide: {s.title or 'untitled'}",
                f"{s.title}. {s.description} {figs}",
                vid.upload_id,
                s.timestamp,
            )
        for start, text in _windows(
            _load_transcript(storage, vid.transcript_key, record.user_id, vid.transcript_preview)
        ):
            add("video", f"{vid.filename} - transcript", text, vid.upload_id, start)
    return chunks[:MAX_CHUNKS]


# ---------------------------------------------------------------------------- scoring
def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1}


def lexical_score(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    words = _tokens(text)
    hits = sum(1 for q in query_tokens if q in words or any(w.startswith(q) for w in words if len(q) >= 4))
    return hits / len(query_tokens)


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------------------- service
class SearchIndexService:
    def __init__(self, repos: Repositories, storage: StorageBackend, ai: AIGateway) -> None:
        self._repos = repos
        self._storage = storage
        self._ai = ai

    @property
    def semantic_enabled(self) -> bool:
        return self._ai.available("embedding")

    # ------------------------------------------------------------------ indexing
    async def index(self, record: InvestigationRecord) -> InvestigationIndex | None:
        if record.result is None:
            return None
        chunks = await asyncio.to_thread(build_chunks, record, self._storage)
        model: str | None = None
        if self.semantic_enabled and chunks:
            try:
                vectors = await self._ai.embed_texts([f"{c.title}\n{c.text}" for c in chunks], agent="search")
                for c, v in zip(chunks, vectors, strict=True):
                    c.vector = v
                await self._embed_images(record, chunks)
                model = self._ai.model_for("embedding")
            except (AIError, ValueError) as exc:
                logger.warning("search_embedding_failed", extra={"error_type": type(exc).__name__})
                for c in chunks:
                    c.vector = None
        index = InvestigationIndex(
            investigation_id=record.investigation_id,
            symbol=record.symbol,
            asset_name=record.asset_name,
            question=record.question,
            created_at=record.created_at,
            embedding_model=model,
            indexed_at=utc_now_iso(),
            chunks=chunks,
        )
        await asyncio.to_thread(
            self._storage.put_bytes,
            index_key(record.user_id, record.investigation_id),
            index.model_dump_json().encode("utf-8"),
            "application/json",
        )
        return index

    async def _embed_images(self, record: InvestigationRecord, chunks: list[IndexChunk]) -> None:
        """Native image embeddings, so pictures are searchable by what they look like."""
        for att in record.attachments:
            if att.kind != "image" or not key_belongs_to(att.storage_key, record.user_id):
                continue
            data = await asyncio.to_thread(self._storage.get_bytes, att.storage_key)
            vector = await self._ai.embed_image(data, att.content_type, agent="search")
            chunks.append(
                IndexChunk(
                    chunk_id=f"k{len(chunks)}",
                    modality="image",
                    title=f"{att.filename} - image",
                    text=f"Uploaded image {att.filename}",
                    ref=att.upload_id,
                    vector=vector,
                )
            )

    async def index_safely(self, record: InvestigationRecord) -> None:
        try:
            await self.index(record)
        except Exception as exc:
            logger.warning("search_index_failed", extra={"error_type": type(exc).__name__})

    # ------------------------------------------------------------------ loading
    def _load(self, user_id: str, investigation_id: str) -> InvestigationIndex | None:
        try:
            return InvestigationIndex.model_validate(
                json.loads(self._storage.get_bytes(index_key(user_id, investigation_id)))
            )
        except Exception:
            return None

    async def _indexes(self, user_id: str, investigation_id: str | None = None) -> list[InvestigationIndex]:
        if investigation_id:
            ids = [investigation_id]
        else:
            records = await asyncio.to_thread(self._repos.investigations.list_by_user, user_id, MAX_INDEXES)
            ids = [r.investigation_id for r in records if r.status == "completed"]
        loaded = await asyncio.gather(*(asyncio.to_thread(self._load, user_id, i) for i in ids))
        return [x for x in loaded if x is not None]

    # ------------------------------------------------------------------ querying
    async def search(
        self,
        user_id: str,
        query: str,
        modality: SearchModality = "all",
        limit: int = 20,
        investigation_id: str | None = None,
    ) -> SearchResponse:
        query = " ".join(query.split())
        if len(query) < 2:
            raise ValidationFailed("Type at least 2 characters.")
        indexes = await self._indexes(user_id, investigation_id)
        current = self._ai.model_for("embedding") if self.semantic_enabled else None
        q_vec: list[float] | None = None
        if current and any(ix.embedding_model == current for ix in indexes):
            try:
                q_vec = (await self._ai.embed_texts([query], agent="search"))[0]
            except AIError as exc:
                logger.warning("search_query_embedding_failed", extra={"error_type": type(exc).__name__})
        q_tokens = _tokens(query)

        def score(ix: InvestigationIndex, c: IndexChunk) -> float | None:
            lex = lexical_score(q_tokens, f"{c.title} {c.text}")
            if q_vec is not None and c.vector is not None and ix.embedding_model == current:
                sem = cosine(q_vec, c.vector) + 0.15 * lex
                return sem if sem >= MIN_SEMANTIC_SCORE else None
            return lex if lex >= 0.5 else None

        cap = limit if investigation_id else MAX_HITS_PER_INVESTIGATION
        hits = self._rank(indexes, modality, score, limit, cap)
        return SearchResponse(
            query=query,
            mode="semantic" if q_vec is not None else "keyword",
            indexed_investigations=len(indexes),
            hits=hits,
        )

    async def search_by_image(
        self, user_id: str, data: bytes, mime_type: str, modality: SearchModality = "all", limit: int = 20
    ) -> SearchResponse:
        if not self.semantic_enabled:
            raise UpstreamUnavailable("Image search needs the embedding model, which is not configured.")
        try:
            q_vec = await self._ai.embed_image(data, mime_type, agent="search")
        except AIError as exc:
            raise UpstreamUnavailable("The embedding model is unavailable right now. Please retry.") from exc
        indexes = await self._indexes(user_id)
        current = self._ai.model_for("embedding")

        def score(ix: InvestigationIndex, c: IndexChunk) -> float | None:
            if c.vector is None or ix.embedding_model != current:
                return None
            s = cosine(q_vec, c.vector)
            return s if s >= MIN_SEMANTIC_SCORE else None

        return SearchResponse(
            query="(image)",
            mode="image",
            indexed_investigations=len(indexes),
            hits=self._rank(indexes, modality, score, limit, MAX_HITS_PER_INVESTIGATION),
        )

    @staticmethod
    def _rank(
        indexes: list[InvestigationIndex],
        modality: SearchModality,
        score: Any,
        limit: int,
        per_investigation: int,
    ) -> list[SearchHit]:
        allowed = MODALITY_GROUPS[modality]
        scored: list[tuple[float, InvestigationIndex, IndexChunk]] = []
        for ix in indexes:
            for c in ix.chunks:
                if c.modality not in allowed:
                    continue
                s = score(ix, c)
                if s is not None:
                    scored.append((s, ix, c))
        scored.sort(key=lambda t: t[0], reverse=True)
        per_inv: dict[str, int] = {}
        seen: set[tuple[str, str]] = set()
        hits: list[SearchHit] = []
        for s, ix, c in scored:
            dedup = (ix.investigation_id, c.text[:120])
            if per_inv.get(ix.investigation_id, 0) >= per_investigation or dedup in seen:
                continue
            seen.add(dedup)
            per_inv[ix.investigation_id] = per_inv.get(ix.investigation_id, 0) + 1
            hits.append(
                SearchHit(
                    investigation_id=ix.investigation_id,
                    symbol=ix.symbol,
                    asset_name=ix.asset_name,
                    question=ix.question,
                    created_at=ix.created_at,
                    modality=c.modality,
                    title=c.title,
                    snippet=c.text[:420],
                    ref=c.ref,
                    location=c.location,
                    score=round(min(max(s, 0.0), 1.0), 3),
                )
            )
            if len(hits) >= limit:
                break
        return hits

    async def passages(
        self, user_id: str, investigation_id: str, question: str, k: int = 6
    ) -> list[dict[str, Any]]:
        """Top passages of one investigation for a follow-up question (retrieval-augmented answer)."""
        try:
            res = await self.search(user_id, question, investigation_id=investigation_id, limit=k)
        except Exception:
            return []
        return [{"title": h.title, "location": h.location, "text": h.snippet, "ref": h.ref} for h in res.hits]
