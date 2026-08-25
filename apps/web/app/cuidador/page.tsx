"use client";

/**
 * Pantalla del cuidador (TAREAS P2.6).
 *
 * 1. Resultado pendiente.  2. Formulario destacado + cola completa.
 * 3. Sugerencia con aceptar/editar/no sé.  4. Confirmación de envío.
 * 5. Score de simulación etiquetado.  6. Baseline o abstención.
 * 7. Estrategias solo después de aprobación profesional.
 */

import { useCallback, useEffect, useState } from "react";

import { FieldControl, type AnswerPayload } from "@/components/FieldControl";
import { OutcomePendingCard } from "@/components/OutcomePendingCard";
import { PredictionOutputCard } from "@/components/PredictionOutputCard";
import { RecommendationList } from "@/components/RecommendationList";
import { EmergencyNotice } from "@/components/EmergencyNotice";
import { EmptyState, ErrorState, LoadingState } from "@/components/States";
import { ApiError, api } from "@/lib/api";
import type {
  FormSessionView,
  OutcomeValue,
  PredictionEpisodeView,
  RecommendationsView,
  SessionContextView,
  SubmitFormSessionView,
} from "@/lib/contracts";
import { readToken } from "@/lib/session";
import { abstentionReason, TEXTS } from "@/lib/texts";
import { DEMO_ACCOUNTS } from "@/lib/session";

type Status = "loading" | "ready" | "error";

export default function CaregiverPage() {
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<ApiError | null>(null);
  const [context, setContext] = useState<SessionContextView | null>(null);
  const [session, setSession] = useState<FormSessionView | null>(null);
  const [submitted, setSubmitted] = useState<SubmitFormSessionView | null>(null);
  const [episode, setEpisode] = useState<PredictionEpisodeView | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationsView | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(readToken() ?? DEMO_ACCOUNTS[0]!.token);
  }, []);

  const load = useCallback(async () => {
    if (token === null) return;
    setStatus("loading");
    setError(null);
    try {
      const nextContext = await api.session(token);
      setContext(nextContext);
      setStatus("ready");
    } catch (caught) {
      setError(caught as ApiError);
      setStatus("error");
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function startSession(subjectId: string) {
    if (token === null) return;
    setBusy(true);
    try {
      setSubmitted(null);
      setEpisode(null);
      setRecommendations(null);
      setSession(await api.openFormSession(token, { subjectId, source: "home" }));
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }

  async function answer(payload: AnswerPayload) {
    if (token === null || session === null) return;
    setBusy(true);
    try {
      const accepted = await api.answer(token, session.form_session_id, {
        fieldCode: payload.fieldCode,
        interaction: payload.interaction,
        ...(payload.value !== undefined ? { value: payload.value } : {}),
        ...(payload.defaultPresentationId !== undefined
          ? { defaultPresentationId: payload.defaultPresentationId }
          : {}),
      });
      setSession(accepted.session);
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (token === null || session === null) return;
    setBusy(true);
    try {
      const result = await api.submit(token, session.form_session_id);
      setSubmitted(result);
      const episodeId = result.prediction_episode_id ?? result.linked_prediction_episode_id;
      if (episodeId !== null) {
        setEpisode(await api.episode(token, episodeId));
        setRecommendations(await api.recommendations(token, episodeId));
      }
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }

  async function report(value: OutcomeValue, occurredAt?: string) {
    if (token === null || session === null) return;
    const episodeId =
      session.outcome_pending?.prediction_episode_id ??
      submitted?.prediction_episode_id ??
      null;
    if (episodeId === null) return;
    setBusy(true);
    try {
      await api.reportOutcome(token, episodeId, {
        value,
        ...(occurredAt !== undefined ? { occurredAt } : {}),
      });
      setSession(await api.readFormSession(token, session.form_session_id));
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading") return <LoadingState />;
  if (status === "error" && context === null) {
    return (
      <ErrorState
        message={error?.message ?? "Sin conexión con la API"}
        requestId={error?.requestId}
        onRetry={() => void load()}
      />
    );
  }
  if (context !== null && context.subjects.length === 0) {
    return <EmptyState label="No tienes autorizaciones vigentes sobre ninguna persona." />;
  }

  const answered = new Set(session?.answered_field_codes ?? []);

  return (
    <div className="space-y-4">
      {error !== null ? (
        <ErrorState message={error.message} requestId={error.requestId} />
      ) : null}

      <section className="faro-card space-y-2">
        <h1 className="text-lg font-semibold text-ink">Registro del día</h1>
        <div className="flex flex-wrap gap-2">
          {context?.subjects.map((subject) => (
            <button
              key={subject.subject_id}
              type="button"
              className={
                session?.subject_id === subject.subject_id
                  ? "faro-button-primary"
                  : "faro-button"
              }
              disabled={busy}
              onClick={() => void startSession(subject.subject_id)}
            >
              {subject.display_label}
            </button>
          ))}
        </div>
        {session?.audit_mode ? (
          <p className="faro-hint">
            Esta sesión es de auditoría: hoy no verás sugerencias, para poder medir si son
            útiles.
          </p>
        ) : null}
      </section>

      {session === null ? (
        <EmptyState label="Elige a quién corresponde el registro para comenzar." />
      ) : (
        <>
          {session.outcome_pending !== null ? (
            <OutcomePendingCard
              questionEs={session.outcome_pending.question_es}
              anchorsEs={session.outcome_pending.severity_anchors_es}
              targetEndAt={session.outcome_pending.target_end_at}
              captureDeadlineAt={session.outcome_pending.capture_deadline_at}
              status={session.outcome_pending.status}
              disabled={busy}
              onReport={(value, occurredAt) => void report(value, occurredAt)}
            />
          ) : null}

          <section aria-labelledby="highlighted-title" className="space-y-3">
            <h2 id="highlighted-title" className="text-base font-semibold text-ink">
              {TEXTS.highlightedTitle}
            </h2>
            {session.highlighted.length === 0 ? (
              <EmptyState label="Nada destacado por ahora." />
            ) : (
              session.highlighted.map((question) => (
                <FieldControl
                  key={question.field_code}
                  question={question}
                  answered={answered.has(question.field_code)}
                  disabled={busy || session.status !== "draft"}
                  onAnswer={(payload) => void answer(payload)}
                />
              ))
            )}
          </section>

          <details className="faro-card">
            <summary className="cursor-pointer text-base font-semibold text-ink">
              {TEXTS.queueTitle} ({session.tail.length})
            </summary>
            <div className="mt-3 space-y-3">
              {session.tail.map((question) => (
                <FieldControl
                  key={question.field_code}
                  question={question}
                  answered={answered.has(question.field_code)}
                  disabled={busy || session.status !== "draft"}
                  onAnswer={(payload) => void answer(payload)}
                />
              ))}
            </div>
          </details>

          <button
            type="button"
            className="faro-button-primary w-full"
            disabled={busy || session.status !== "draft"}
            onClick={() => void submit()}
          >
            {session.status === "draft" ? TEXTS.submit : TEXTS.submitted}
          </button>
        </>
      )}

      {submitted !== null ? (
        <section aria-labelledby="submitted-title" className="space-y-3">
          <h2 id="submitted-title" className="text-base font-semibold text-ink">
            {TEXTS.submitted}
          </h2>
          {submitted.status === "target_definition_unavailable" ? (
            <div className="faro-card border-caution/40" data-state="abstained">
              <p className="font-semibold text-caution">
                <span aria-hidden="true">◻ </span>
                Se guardó tu registro, sin crear un objetivo
              </p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-ink">
                {submitted.reasons.map((reason) => (
                  <li key={reason}>{abstentionReason(reason)}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="faro-card text-sm text-ink">
              {submitted.status === "episode_linked"
                ? "Tu registro se sumó a la ventana de 24 horas que ya estaba abierta."
                : "Se abrió una ventana de 24 horas para registrar el resultado."}
            </p>
          )}
          <EmergencyNotice body={submitted.emergency_notice_es} />
        </section>
      ) : null}

      {episode !== null ? (
        <section aria-labelledby="episode-title" className="space-y-3">
          <h2 id="episode-title" className="text-base font-semibold text-ink">
            Estimaciones de este registro
          </h2>
          {episode.outputs.map((output) => (
            <PredictionOutputCard key={output.track_id} output={output} />
          ))}
        </section>
      ) : null}

      {recommendations !== null ? (
        <section aria-labelledby="recommendations-title" className="space-y-3">
          <h2 id="recommendations-title" className="text-base font-semibold text-ink">
            Apoyos revisados
          </h2>
          <RecommendationList view={recommendations} />
          <EmergencyNotice body={recommendations.emergency_notice_es} />
        </section>
      ) : null}
    </div>
  );
}
