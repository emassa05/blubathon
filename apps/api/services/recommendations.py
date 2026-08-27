"""Live retrieval, grounded drafting and recommendation feedback."""

from __future__ import annotations

import difflib
import logging
import re
import sqlite3
from dataclasses import dataclass
from uuid import UUID, uuid4

from apps.api.contracts.models import (
    AnswerItem,
    FeedbackRequest,
    FeedbackResponse,
    RecommendationCitation,
    RecommendationInstanceView,
    RecommendationListResponse,
    TodayRecommendationResponse,
)
from apps.api.errors import not_found
from apps.api.services.base import Services
from apps.api.services.recommendation_query import query_for, risk_band_for
from apps.api.store import history
from apps.api.store import recommendations as store
from apps.api.store.json_columns import load_list
from packages.shared.domain.rag import DocumentChunk, StrategyCitation
from rag.authoring.bm25 import Bm25Index
from rag.authoring.drafting import DraftRequest, DraftUnavailableError, request_draft
from rag.authoring.retrieval import RetrievalPlan, retrieve
from rag.domain.citations import verify_citation

logger = logging.getLogger("blubathon.api")

# Un modelo local chico rara vez cita palabra por palabra. `rag/domain/citations.py`
# (INV-24) exige literalidad exacta y eso no se toca: es la única barrera antes de
# que un cuidador vea la recomendación, porque este flujo no tiene revisión humana.
# Esto corre ANTES de esa verificación, para no descartar un intento del modelo por
# una diferencia menor — nunca reemplaza la verificación, solo decide si vale la
# pena intentarla con una subcadena que sí es literal.
CITATION_SNAP_THRESHOLD = 0.80


def _snap_to_literal(
    quote: str, chunk_text: str, *, threshold: float = CITATION_SNAP_THRESHOLD
) -> str | None:
    """La subcadena literal de `chunk_text` más parecida a `quote`, o `None`.

    El resultado es siempre un slice real de `chunk_text` — nunca el texto que
    propuso el modelo — así que sigue siendo una cita verificable byte a byte.
    Si la similitud contra `quote` no alcanza el umbral, no hay snap: el
    llamador debe abstenerse igual que si no hubiera match exacto.
    """

    if not quote or not chunk_text:
        return None
    matcher = difflib.SequenceMatcher(None, chunk_text, quote, autojunk=False)
    blocks = [block for block in matcher.get_matching_blocks() if block.size > 0]
    if not blocks:
        return None
    start = blocks[0].a
    end = blocks[-1].a + blocks[-1].size
    if end <= start:
        return None
    candidate = chunk_text[start:end]
    ratio = difflib.SequenceMatcher(None, candidate, quote, autojunk=False).ratio()
    return candidate if ratio >= threshold else None


# `render_fragments` (rag/authoring/drafting.py) marca cada fragmento del
# prompt como "[document_version_id | locator]" para que el modelo sepa de
# dónde citar. Un modelo chico a veces copia esa etiqueta en la prosa en vez
# de solo usarla como guía; esto la saca de `action_text_es`/`purpose_es`
# antes de persistir. No toca `quoted_text`: eso ya es un slice literal.
_FRAGMENT_TAG_RE = re.compile(
    r"\[[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"\s*\|[^\]]*\]"
)


def _strip_fragment_tags(text: str) -> str:
    cleaned = _FRAGMENT_TAG_RE.sub("", text)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _first_literal_snap(
    quote: str, chunks: tuple[DocumentChunk, ...]
) -> tuple[DocumentChunk, str] | None:
    """El primer chunk con un snap válido para `quote`, o `None` si ninguno alcanza."""

    for chunk in chunks:
        literal = _snap_to_literal(quote, chunk.text)
        if literal is not None:
            return chunk, literal
    return None


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    recommendation_instance_id: str
    child_id: str
    prediction_episode_id: str
    status: str
    abstention_reason: str | None
    attempt: int


class RecommendationService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def generate(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        prediction_episode_id: str,
        probability: float | None,
        answers: tuple[AnswerItem, ...],
        now: str,
        exclude_chunk_ids: frozenset[UUID] = frozenset(),
        increment_attempt: bool = False,
    ) -> RecommendationResult:
        query_es = query_for(probability, answers)
        return self._generate_from_query(
            tenant_id=tenant_id,
            subject_id=subject_id,
            prediction_episode_id=prediction_episode_id,
            risk_band=risk_band_for(probability),
            query_es=query_es,
            now=now,
            exclude_chunk_ids=exclude_chunk_ids,
            increment_attempt=increment_attempt,
        )

    def probability_for_episode(self, prediction_episode_id: str) -> float | None:
        with self._services.database.read() as connection:
            # La misma cifra que ve la pantalla: si el challenger estimó, la
            # banda de riesgo y la consulta del RAG tienen que salir de ahí y no
            # de la tasa base, o el consejo hablaría de otro día.
            row = history.operational_output(connection, prediction_episode_id)
        return None if row is None else row["probability"]

    def redraft(self, recommendation_instance_id: str, *, now: str) -> RecommendationResult:
        with self._services.database.read() as connection:
            row = store.instance(connection, recommendation_instance_id)
            if row is None:
                raise not_found()
            excluded = frozenset(UUID(item) for item in store.citation_chunk_ids(row))
            payload = dict(row)
        return self._generate_from_query(
            tenant_id=payload["tenant_id"],
            subject_id=payload["subject_id"],
            prediction_episode_id=payload["prediction_episode_id"],
            risk_band=payload["risk_band"],
            query_es=payload["query_es"],
            now=now,
            exclude_chunk_ids=excluded,
            increment_attempt=True,
        )

    def _generate_from_query(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        prediction_episode_id: str,
        risk_band: str,
        query_es: str,
        now: str,
        exclude_chunk_ids: frozenset[UUID],
        increment_attempt: bool,
    ) -> RecommendationResult:
        with self._services.database.read() as connection:
            instance = store.instance_for_episode(connection, prediction_episode_id)
            if instance is None or instance["tenant_id"] != tenant_id:
                raise not_found()
            recommendation_instance_id = instance["recommendation_instance_id"]
            rows = [
                row
                for row in store.indexed_chunk_rows(connection)
                if UUID(row["document_chunk_id"]) not in exclude_chunk_ids
            ]

        chunks = tuple(_chunk(row) for row in rows)
        by_id = {chunk.document_chunk_id: chunk for chunk in chunks}
        retrieval = retrieve(
            query_es,
            index=Bm25Index(chunks),
            plan=RetrievalPlan.lexical_only(),
        )
        selected = tuple(by_id[UUID(chunk_id)] for chunk_id in retrieval.chunk_ids)
        if not selected:
            return self._persist_abstention(
                recommendation_instance_id,
                subject_id,
                prediction_episode_id,
                risk_band,
                query_es,
                "no_indexed_match",
                now,
                increment_attempt,
            )
        try:
            draft = request_draft(
                DraftRequest(generalized_question_es=query_es, chunks=selected),
                transport=self._services.draft_transport,
                authorised_document_version_ids=frozenset(
                    chunk.document_version_id for chunk in selected
                ),
            ).payload()
        except (DraftUnavailableError, ValueError):
            return self._persist_abstention(
                recommendation_instance_id,
                subject_id,
                prediction_episode_id,
                risk_band,
                query_es,
                "draft_unavailable",
                now,
                increment_attempt,
            )

        action_text_es = draft.get("action_text_es")
        purpose_es = draft.get("purpose_es")
        claims = draft.get("claims")
        if isinstance(action_text_es, str):
            action_text_es = _strip_fragment_tags(action_text_es)
        if isinstance(purpose_es, str):
            purpose_es = _strip_fragment_tags(purpose_es)
        if (
            not isinstance(action_text_es, str)
            or not action_text_es.strip()
            or not isinstance(purpose_es, str)
            or not purpose_es.strip()
            or not isinstance(claims, list)
            or not claims
        ):
            return self._persist_abstention(
                recommendation_instance_id,
                subject_id,
                prediction_episode_id,
                risk_band,
                query_es,
                "draft_not_grounded",
                now,
                increment_attempt,
            )

        persisted_citations = []
        for claim in claims:
            quote = claim.get("quoted_text", "") if isinstance(claim, dict) else ""
            candidates = [chunk for chunk in selected if quote and quote in chunk.text]
            if candidates:
                chunk = candidates[0]
            else:
                snapped = _first_literal_snap(quote, selected)
                if snapped is None:
                    return self._persist_abstention(
                        recommendation_instance_id,
                        subject_id,
                        prediction_episode_id,
                        risk_band,
                        query_es,
                        "draft_not_grounded",
                        now,
                        increment_attempt,
                    )
                chunk, quote = snapped
            citation = StrategyCitation(
                citation_id=uuid4(),
                claim_id=uuid4(),
                document_chunk_id=chunk.document_chunk_id,
                locator=chunk.locator,
                quoted_text=quote,
                chunk_sha256=chunk.chunk_sha256,
                canonical_url=next(
                    row["canonical_url"]
                    for row in rows
                    if row["document_chunk_id"] == str(chunk.document_chunk_id)
                ),
            )
            if not verify_citation(citation, by_id).verified:
                return self._persist_abstention(
                    recommendation_instance_id,
                    subject_id,
                    prediction_episode_id,
                    risk_band,
                    query_es,
                    "draft_not_grounded",
                    now,
                    increment_attempt,
                )
            row = next(
                row for row in rows if row["document_chunk_id"] == str(chunk.document_chunk_id)
            )
            persisted_citations.append(
                {
                    "document_chunk_id": str(chunk.document_chunk_id),
                    "document_title_es": row["document_title"],
                    "locator": chunk.locator,
                    "quote_es": quote,
                }
            )

        if not persisted_citations:
            return self._persist_abstention(
                recommendation_instance_id,
                subject_id,
                prediction_episode_id,
                risk_band,
                query_es,
                "draft_not_grounded",
                now,
                increment_attempt,
            )
        logger.info(
            "recomendacion emparejada recommendation_instance_id=%s citas=%d",
            recommendation_instance_id,
            len(persisted_citations),
        )
        with self._services.database.write() as connection:
            store.update_result(
                connection,
                recommendation_instance_id=recommendation_instance_id,
                risk_band=risk_band,
                query_es=query_es,
                status="matched",
                action_text_es=action_text_es,
                purpose_es=purpose_es,
                citations=persisted_citations,
                abstention_reason=None,
                now=now,
                increment_attempt=increment_attempt,
            )
            refreshed = store.instance(connection, recommendation_instance_id)
            assert refreshed is not None
            attempt = refreshed["attempt"]
        return RecommendationResult(
            recommendation_instance_id,
            subject_id,
            prediction_episode_id,
            "matched",
            None,
            attempt,
        )

    def _persist_abstention(
        self,
        recommendation_instance_id: str,
        subject_id: str,
        prediction_episode_id: str,
        risk_band: str,
        query_es: str,
        reason: str,
        now: str,
        increment_attempt: bool,
    ) -> RecommendationResult:
        logger.info(
            "recomendacion abstencion recommendation_instance_id=%s reason=%s",
            recommendation_instance_id,
            reason,
        )
        with self._services.database.write() as connection:
            store.update_result(
                connection,
                recommendation_instance_id=recommendation_instance_id,
                risk_band=risk_band,
                query_es=query_es,
                status="abstained",
                action_text_es=None,
                purpose_es=None,
                citations=[],
                abstention_reason=reason,
                now=now,
                increment_attempt=increment_attempt,
            )
            refreshed = store.instance(connection, recommendation_instance_id)
            assert refreshed is not None
            attempt = refreshed["attempt"]
        return RecommendationResult(
            recommendation_instance_id,
            subject_id,
            prediction_episode_id,
            "abstained",
            reason,
            attempt,
        )

    def for_episode(
        self, connection: sqlite3.Connection, *, tenant_id: str, prediction_episode_id: str
    ) -> RecommendationInstanceView:
        row = store.instance_for_episode(connection, prediction_episode_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise not_found()
        return _view(connection, row)

    def list(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        status: str | None,
        child_id: str | None,
        limit: int,
    ) -> RecommendationListResponse:
        return RecommendationListResponse(
            items=[
                _view(connection, row)
                for row in store.list_instances(
                    connection,
                    tenant_id=tenant_id,
                    status=status,
                    subject_id=child_id,
                    limit=limit,
                )
            ]
        )

    def today(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        child_id: str,
        local_date: str,
    ) -> TodayRecommendationResponse:
        row = connection.execute(
            "SELECT i.* FROM recommendation_instances AS i"
            " JOIN prediction_episodes AS e ON e.prediction_episode_id = i.prediction_episode_id"
            " JOIN form_sessions AS f ON f.form_session_id = e.form_session_id"
            " WHERE i.tenant_id = ? AND i.subject_id = ? AND f.local_date = ?"
            " ORDER BY i.created_at DESC LIMIT 1",
            (tenant_id, child_id, local_date),
        ).fetchone()
        if row is None:
            return TodayRecommendationResponse(status="no_submission_today")
        view = _view(connection, row)
        return TodayRecommendationResponse(
            status=view.status,
            risk_band=view.risk_band,
            recommendation_instance_id=view.recommendation_instance_id,
            action_text_es=view.action_text_es,
            purpose_es=view.purpose_es,
            citations=view.citations,
            abstention_reason=view.abstention_reason,
            rating=view.rating,
        )

    def feedback(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        recommendation_instance_id: str,
        request: FeedbackRequest,
        now: str,
    ) -> FeedbackResponse:
        row = store.instance(connection, recommendation_instance_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise not_found()
        feedback_id = store.add_feedback(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            rating=request.rating,
            note_es=request.note_es,
            now=now,
        )
        return FeedbackResponse(
            feedback_id=feedback_id,
            rating=request.rating,
            attempt=row["attempt"],
        )


def _chunk(row: sqlite3.Row) -> DocumentChunk:
    return DocumentChunk(
        document_chunk_id=row["document_chunk_id"],
        document_version_id=row["document_version_id"],
        locator=row["locator"],
        text=row["text"],
        chunk_sha256=row["chunk_sha256"],
        chunker_version=row["chunker_version"],
    )


def _view(connection: sqlite3.Connection, row: sqlite3.Row) -> RecommendationInstanceView:
    feedback = store.latest_feedback(connection, row["recommendation_instance_id"])
    citations = [
        RecommendationCitation(
            document_title_es=item["document_title_es"],
            locator=item["locator"],
            quote_es=item["quote_es"],
        )
        for item in load_list(row["citations"])
    ]
    keys = set(row.keys())
    return RecommendationInstanceView(
        recommendation_instance_id=row["recommendation_instance_id"],
        child_id=row["subject_id"],
        child_label=row["child_label"] if "child_label" in keys else None,
        prediction_episode_id=row["prediction_episode_id"],
        local_date=row["local_date"] if "local_date" in keys else None,
        created_at=row["created_at"],
        risk_band=row["risk_band"],
        query_es=row["query_es"],
        status=row["status"],
        action_text_es=row["action_text_es"],
        purpose_es=row["purpose_es"],
        citations=citations,
        abstention_reason=row["abstention_reason"],
        attempt=row["attempt"],
        rating=None if feedback is None else feedback["rating"],
    )
