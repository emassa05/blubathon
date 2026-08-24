"""The concrete service composition behind the eight endpoints (SPEC 11).

This is the seam CONVENTIONS 2 describes: it reads SQLite, calls the pure ``ml``
domain, and serialises the result. No risk arithmetic happens here -- every
threshold, band and abstention rule lives in ``ml.engine.decision``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from apps.api.store import get_connection, get_history, init_db, insert_feedback, insert_logs
from ml.artifact import TrainedModel, load_model
from ml.engine.decision import build_risk_response, risk_band
from ml.engine.explain import compute_drivers
from ml.engine.pipeline import (
    PointInTimeFeatures,
    RiskAssessment,
    assess_risk,
    counterfactual_probabilities,
    make_override_scorer,
)
from ml.errors import InsufficientDataError, ModelNotReadyError
from ml.features import compute_icd
from ml.narrative import build_narrative_payload, generate_narrative
from ml.spec_constants import RISK_API_DECIMALS, VOI_MAX_REQUESTED_VARIABLES
from ml.strategies import strategy_label
from ml.voi import build_form, encode_answer, known_answers
from packages.shared import (
    CounterfactualRequest,
    CounterfactualResponse,
    DailyLog,
    EvaluationResponse,
    ExplainResponse,
    FeedbackRequest,
    IngestResponse,
    OkResponse,
    QualityResponse,
    RiskResponse,
    VoIResponse,
)

# SPEC 2 identifies children only by UUID; there is no name to show, and
# inventing one would be fabricating data (SPEC rule 0.11).
CHILD_PLACEHOLDER_ES = "tu hijo o hija"


def _encode_overrides(overrides: Mapping[str, Any]) -> dict[str, float | None]:
    """Turn contract-level answers into the numbers the feature row expects."""
    return {variable: encode_answer(variable, value) for variable, value in overrides.items()}


class FaroServices:
    """Wires the trained model and the database into the API contract."""

    def __init__(
        self,
        model_path: Path | str,
        db_path: Path | str,
        *,
        loader: Callable[[Path | str], TrainedModel] = load_model,
    ) -> None:
        self._model_path = Path(model_path)
        self._db_path = Path(db_path)
        self._loader = loader
        self._model: TrainedModel | None = None

    @property
    def model(self) -> TrainedModel:
        """Load the artifact once, and say plainly when there is none."""
        if self._model is None:
            self._model = self._loader(self._model_path)
        return self._model

    def warm_up(self) -> bool:
        """Try to load at start-up so the first request is not the slow one."""
        try:
            return self.model.ensemble.is_fitted
        except ModelNotReadyError:
            return False

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = get_connection(self._db_path)
        init_db(conn)
        try:
            yield conn
        finally:
            conn.close()

    def _history(self, conn: sqlite3.Connection, child_id: UUID, as_of: date) -> list[dict]:
        """Records up to and including the day, and never past it (SPEC rule 0.2)."""
        return get_history(conn, str(child_id), as_of_date=as_of.isoformat())

    def _assessment(
        self, history: list[dict], child_id: UUID, as_of: date
    ) -> tuple[RiskAssessment, PointInTimeFeatures]:
        context = PointInTimeFeatures(history, str(child_id), as_of)
        return (
            assess_risk(self.model.ensemble, history, str(child_id), as_of, context=context),
            context,
        )

    def _form(
        self,
        history: list[dict],
        child_id: UUID,
        as_of: date,
        icd: float,
        context: PointInTimeFeatures,
    ) -> dict[str, Any]:
        scorer = make_override_scorer(self.model.ensemble, context)
        return build_form(
            history,
            as_of,
            str(child_id),
            icd,
            scorer,
            self.model.population_prior,
        )

    # -- endpoints ---------------------------------------------------------

    def ingest(self, logs: list[DailyLog]) -> IngestResponse:
        if not logs:
            raise InsufficientDataError("ingest requires at least one daily log")
        payload = [log.model_dump(mode="json") for log in logs]
        with self._connection() as conn:
            insert_logs(conn, payload)
        last = logs[-1]
        return IngestResponse(ok=True, child_id=last.child_id, date=last.date)

    def predict(self, child_id: UUID, as_of: date) -> RiskResponse:
        """``as_of`` is the day being recorded; the answer is for the day after.

        Every endpoint takes the same ``date``: the day a person is filling in.
        Only the response carries ``t+1``, as SPEC 11.1 requires.
        """
        with self._connection() as conn:
            history = self._history(conn, child_id, as_of)
        assessment, context = self._assessment(history, child_id, as_of)
        form = self._form(history, child_id, as_of, assessment.quality["icd"], context)
        requested = [
            {
                "variable": item["variable"],
                "prompt_es": item["prompt_es"],
                "voi": round(item["voi"], RISK_API_DECIMALS),
            }
            for item in form["highlighted"][:VOI_MAX_REQUESTED_VARIABLES]
        ]
        return build_risk_response(
            child_id=child_id,
            prediction_date=assessment.target_date,
            probability=assessment.probability,
            interval=assessment.interval,
            icd=assessment.quality["icd"],
            history_days=assessment.history_days,
            requested_variables=requested,
        )

    def voi(self, child_id: UUID, target_date: date) -> VoIResponse:
        with self._connection() as conn:
            history = self._history(conn, child_id, target_date)
        context = PointInTimeFeatures(history, str(child_id), target_date)
        icd = compute_icd(history, target_date)["icd"]
        form = self._form(history, child_id, target_date, icd, context)
        return VoIResponse.model_validate({**form, "child_id": child_id})

    def explain(self, child_id: UUID, as_of: date) -> ExplainResponse:
        with self._connection() as conn:
            history = self._history(conn, child_id, as_of)
        assessment, context = self._assessment(history, child_id, as_of)
        answers = known_answers(history, as_of)
        drivers = compute_drivers(self.model.ensemble, context.base_row(), answers)
        payload = build_narrative_payload(
            child_name=CHILD_PLACEHOLDER_ES,
            risk_band=assessment.band or "verde",
            confidence=assessment.confidence,
            drivers=drivers,
        )
        narrative, source = generate_narrative(payload)
        return ExplainResponse.model_validate(
            {
                "drivers": [
                    {key: driver[key] for key in ("variable", "shap", "direction", "detail_es")}
                    for driver in drivers
                ],
                "narrative": narrative,
                "narrative_source": source,
                "strategies": [
                    {"id": strategy_id, "label_es": strategy_label(strategy_id)}
                    for strategy_id in payload["candidate_strategies"]
                ],
            }
        )

    def counterfactual(self, request: CounterfactualRequest) -> CounterfactualResponse:
        with self._connection() as conn:
            history = self._history(conn, request.child_id, request.date)
        before, after = counterfactual_probabilities(
            self.model.ensemble,
            history,
            str(request.child_id),
            request.date,
            _encode_overrides(request.overrides),
        )
        return CounterfactualResponse.model_validate(
            {
                "risk_before": before,
                "risk_after": after,
                "band_before": risk_band(before),
                "band_after": risk_band(after),
            }
        )

    def quality(self, child_id: UUID, target_date: date) -> QualityResponse:
        with self._connection() as conn:
            history = self._history(conn, child_id, target_date)
        metrics = compute_icd(history, target_date)
        return QualityResponse.model_validate(
            {key: round(value, RISK_API_DECIMALS) for key, value in metrics.items()}
        )

    def feedback(self, request: FeedbackRequest) -> OkResponse:
        with self._connection() as conn:
            insert_feedback(
                conn,
                {
                    "child_id": str(request.child_id),
                    "date": request.date.isoformat(),
                    "dysregulation_occurred": request.dysregulation_occurred,
                    "strategy_used": request.strategy_used,
                    "helped": request.helped,
                },
            )
        return OkResponse(ok=True)

    def evaluation(self) -> EvaluationResponse:
        report = self.model.evaluation
        if not report:
            raise ModelNotReadyError("the trained artifact carries no evaluation report")
        return EvaluationResponse.model_validate(
            {
                "metrics": report.get("metrics", {}),
                "baselines": report.get("baselines", {}),
                "ablations": {
                    **report.get("ablations", {}),
                    "disclaimer_es": report.get("disclaimer_es", ""),
                },
            }
        )
