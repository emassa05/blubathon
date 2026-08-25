"use client";

/**
 * Bloque de resultado pendiente (SPEC 6.9 y 11.4).
 *
 * Es un bloque aparte y no consume cupos de campos diarios. "No sé" es una
 * respuesta explícita: deja la resolución pending y no inventa un negativo.
 */

import { useState } from "react";

import { ConflictedState, ExpiredState } from "@/components/States";
import type { OutcomeReportValue } from "@/lib/contracts";
import { formatMoment } from "@/lib/format";
import { OUTCOME_REQUEST_STATUS_ES, RESOLUTION_STATUS_ES, TEXTS } from "@/lib/texts";

export interface OutcomePendingCardProps {
  questionEs: string;
  anchorsEs: readonly string[];
  targetEndAt: string;
  captureDeadlineAt: string;
  state: string;
  resolutionStatus?: string;
  disabled?: boolean;
  onReport: (value: OutcomeReportValue, occurredAt?: string) => void;
}

export function OutcomePendingCard(props: OutcomePendingCardProps) {
  const [occurredAt, setOccurredAt] = useState<string>("");

  if (props.state === "conflicted") {
    return <ConflictedState />;
  }

  return (
    <section
      aria-labelledby="outcome-pending-title"
      data-state={props.state}
      className="faro-card space-y-3"
    >
      <div>
        <h2 id="outcome-pending-title" className="text-base font-semibold text-ink">
          {TEXTS.pendingOutcomeTitle}
        </h2>
        <p className="faro-hint">
          {OUTCOME_REQUEST_STATUS_ES[props.state] ?? props.state}
          {props.resolutionStatus
            ? ` · ${RESOLUTION_STATUS_ES[props.resolutionStatus] ?? props.resolutionStatus}`
            : ""}
        </p>
      </div>

      <p className="text-base text-ink">{props.questionEs}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
        {props.anchorsEs.map((anchor) => (
          <li key={anchor}>{anchor}</li>
        ))}
      </ul>
      <p className="faro-hint">
        Ventana hasta {formatMoment(props.targetEndAt)}; se puede responder hasta{" "}
        {formatMoment(props.captureDeadlineAt)}.
      </p>

      {props.state === "missing" ? <ExpiredState /> : null}

      <div className="space-y-2">
        <label className="faro-label" htmlFor="occurred-at">
          ¿Cuándo ocurrió? (solo si respondes que sí)
        </label>
        <input
          id="occurred-at"
          className="faro-input"
          type="datetime-local"
          value={occurredAt}
          disabled={props.disabled}
          onChange={(event) => setOccurredAt(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="faro-button-primary"
            disabled={props.disabled || occurredAt === ""}
            onClick={() => props.onReport("yes", new Date(occurredAt).toISOString())}
          >
            Sí, ocurrió
          </button>
          <button
            type="button"
            className="faro-button"
            disabled={props.disabled}
            onClick={() => props.onReport("no")}
          >
            No ocurrió
          </button>
          <button
            type="button"
            className="faro-button"
            disabled={props.disabled}
            onClick={() => props.onReport("unknown")}
          >
            {TEXTS.unknownAnswer}
          </button>
        </div>
        <p className="faro-hint">
          Responder “{TEXTS.unknownAnswer}” deja el resultado sin resolver. Faro no lo
          convierte en un “no ocurrió”.
        </p>
      </div>
    </section>
  );
}
