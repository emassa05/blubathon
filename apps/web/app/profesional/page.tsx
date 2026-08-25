"use client";

/**
 * Pantalla profesional (TAREAS P2.8).
 *
 * 1. Inbox de recomendaciones pendientes.
 * 2. Escenario sin datos identificables innecesarios.
 * 3. Estrategias y citas verificables.
 * 4. Aprobar, rechazar, sustituir, diferir o marcar no aplica.
 * 5. Registrar aplicación.
 * 6. Resultado pendiente y estado de conflicto.
 * 7. Historial de versiones, sin editarlo.
 */

import { useCallback, useEffect, useState } from "react";

import { RecommendationList } from "@/components/RecommendationList";
import { EmptyState, ErrorState, LoadingState } from "@/components/States";
import { ApiError, api } from "@/lib/api";
import type {
  RecommendationInstanceSummary,
  RecommendationsView,
  ReviewDecision,
} from "@/lib/contracts";
import { formatMoment } from "@/lib/format";
import { DEMO_ACCOUNTS, readToken } from "@/lib/session";
import { RESOLUTION_STATUS_ES, TEXTS, fieldLabel, optionLabel } from "@/lib/texts";

const DECISIONS: ReadonlyArray<{ value: ReviewDecision; label: string }> = [
  { value: "approved", label: TEXTS.approve },
  { value: "rejected", label: TEXTS.reject },
  { value: "deferred", label: TEXTS.defer },
  { value: "not_applicable", label: TEXTS.notApplicable },
];

export default function ProfessionalPage() {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [items, setItems] = useState<RecommendationInstanceSummary[]>([]);
  const [selected, setSelected] = useState<RecommendationInstanceSummary | null>(null);
  const [detail, setDetail] = useState<RecommendationsView | null>(null);
  const [planText, setPlanText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(readToken() ?? DEMO_ACCOUNTS[1]!.token);
  }, []);

  const load = useCallback(async () => {
    if (token === null) return;
    setLoading(true);
    setError(null);
    try {
      const inbox = await api.inbox(token);
      setItems(inbox.items);
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const openInstance = useCallback(
    async (instance: RecommendationInstanceSummary) => {
      if (token === null) return;
      setSelected(instance);
      setBusy(true);
      try {
        setDetail(await api.recommendations(token, instance.prediction_episode_id));
      } catch (caught) {
        setError(caught as ApiError);
      } finally {
        setBusy(false);
      }
    },
    [token],
  );

  async function review(strategyVersionId: string, decision: ReviewDecision) {
    if (token === null || selected === null || detail === null) return;
    setBusy(true);
    setError(null);
    try {
      await api.review(
        token,
        selected.recommendation_instance_id,
        decision === "human_plan_substituted"
          ? {
              strategyVersionId,
              decision,
              humanPlan: { actionTextEs: planText, allowedExecutorRoles: ["caregiver"] },
            }
          : { strategyVersionId, decision },
        detail.revision,
      );
      setPlanText("");
      setDetail(await api.recommendations(token, selected.prediction_episode_id));
      await load();
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }

  async function recordExecution(item: {
    strategy_version_id: string | null;
    human_plan_version_id: string | null;
  }) {
    if (token === null || selected === null || detail === null) return;
    setBusy(true);
    setError(null);
    try {
      await api.execution(
        token,
        selected.recommendation_instance_id,
        {
          status: "applied",
          appliedAt: new Date().toISOString(),
          ...(item.strategy_version_id !== null
            ? { strategyVersionId: item.strategy_version_id }
            : {}),
          ...(item.human_plan_version_id !== null
            ? { humanPlanVersionId: item.human_plan_version_id }
            : {}),
        },
        detail.revision,
      );
      setDetail(await api.recommendations(token, selected.prediction_episode_id));
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4">
      {error !== null ? (
        <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
      ) : null}

      <section aria-labelledby="inbox-title" className="space-y-3">
        <h1 id="inbox-title" className="text-lg font-semibold text-ink">
          {TEXTS.inboxTitle}
        </h1>
        {items.length === 0 ? (
          <EmptyState label="No hay recomendaciones pendientes de revisión." />
        ) : (
          <ul className="space-y-2">
            {items.map((instance) => (
              <li key={instance.recommendation_instance_id}>
                <button
                  type="button"
                  className="faro-card w-full text-left hover:bg-canvas"
                  aria-pressed={
                    selected?.recommendation_instance_id ===
                    instance.recommendation_instance_id
                  }
                  disabled={busy}
                  onClick={() => void openInstance(instance)}
                >
                  <p className="font-semibold text-ink">{instance.subject_label}</p>
                  <p className="faro-hint">
                    {formatMoment(instance.created_at)} ·{" "}
                    {instance.pending_strategy_version_ids.length} por revisar
                  </p>
                  <p className="faro-hint">
                    Catálogo {instance.catalog_version ?? "no disponible"}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {selected !== null ? (
        <section aria-labelledby="scenario-title" className="faro-card space-y-2">
          <h2 id="scenario-title" className="text-base font-semibold text-ink">
            {TEXTS.scenarioTitle}
          </h2>
          {selected.scenario === null ? (
            <EmptyState label="El escenario mínimo no está disponible para esta instancia." />
          ) : (
            <dl className="grid grid-cols-2 gap-1 text-sm">
              {Object.entries(selected.scenario.field_values).map(([code, value]) => (
                <div key={code} className="contents">
                  <dt className="text-muted">{fieldLabel(code)}</dt>
                  <dd className="text-ink">{optionLabel(code, value)}</dd>
                </div>
              ))}
              <dt className="text-muted">Contexto</dt>
              <dd className="text-ink">{selected.scenario.context_tags.join(", ") || "—"}</dd>
              <dt className="text-muted">Perfil</dt>
              <dd className="text-ink">{selected.scenario.profile_tags.join(", ") || "—"}</dd>
              <dt className="text-muted">Contraindicaciones</dt>
              <dd className="text-ink">
                {selected.scenario.contraindication_tags.join(", ") || "ninguna registrada"}
              </dd>
            </dl>
          )}
          <p className="faro-hint">
            El escenario no incluye identidad, notas ni historial: solo los valores cerrados
            necesarios para el match.
          </p>
        </section>
      ) : null}

      {detail !== null ? (
        <section aria-labelledby="review-title" className="space-y-3">
          <h2 id="review-title" className="text-base font-semibold text-ink">
            Estrategias de esta instancia
          </h2>
          <RecommendationList view={detail}>
            {(item) => (
              <div className="space-y-2 border-t border-line pt-2">
                {item.item_type === "strategy" && item.strategy_version_id !== null ? (
                  <>
                    <div className="flex flex-wrap gap-2">
                      {DECISIONS.map((decision) => (
                        <button
                          key={decision.value}
                          type="button"
                          className="faro-button"
                          disabled={busy || item.non_actionable !== null}
                          onClick={() =>
                            void review(item.strategy_version_id!, decision.value)
                          }
                        >
                          {decision.label}
                        </button>
                      ))}
                    </div>
                    <label className="faro-label" htmlFor={`plan-${item.strategy_version_id}`}>
                      {TEXTS.substitute}
                    </label>
                    <textarea
                      id={`plan-${item.strategy_version_id}`}
                      className="faro-input"
                      rows={2}
                      value={planText}
                      disabled={busy || item.non_actionable !== null}
                      onChange={(event) => setPlanText(event.target.value)}
                    />
                    <button
                      type="button"
                      className="faro-button"
                      disabled={busy || planText.trim() === "" || item.non_actionable !== null}
                      onClick={() =>
                        void review(item.strategy_version_id!, "human_plan_substituted")
                      }
                    >
                      {TEXTS.substitute}
                    </button>
                  </>
                ) : null}

                {item.review_status === "approved" ||
                item.review_status === "human_plan_substituted" ? (
                  <button
                    type="button"
                    className="faro-button-primary"
                    disabled={busy || item.non_actionable !== null}
                    onClick={() => void recordExecution(item)}
                  >
                    {item.execution_status === "applied"
                      ? "Aplicación registrada"
                      : TEXTS.recordExecution}
                  </button>
                ) : null}
              </div>
            )}
          </RecommendationList>

          <section aria-labelledby="history-title" className="faro-card">
            <h3 id="history-title" className="text-sm font-semibold text-ink">
              {TEXTS.historyTitle}
            </h3>
            <dl className="mt-2 grid grid-cols-2 gap-1 text-xs text-muted">
              <dt>Instancia</dt>
              <dd>{detail.recommendation_instance_id}</dd>
              <dt>Catálogo</dt>
              <dd>{detail.catalog_version ?? "—"}</dd>
              <dt>Corpus</dt>
              <dd>{detail.corpus_version ?? "—"}</dd>
              <dt>Disponibilidad</dt>
              <dd>{detail.availability_reason}</dd>
              <dt>Revisión</dt>
              <dd className="break-all">{detail.revision}</dd>
            </dl>
            <p className="faro-hint mt-2">
              El historial no se edita: una corrección crea otra versión.{" "}
              {RESOLUTION_STATUS_ES.pending}
            </p>
          </section>
        </section>
      ) : null}
    </div>
  );
}
