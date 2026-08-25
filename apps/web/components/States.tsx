/**
 * Estados obligatorios de la UI (CONVENTIONS 10 y TAREAS P2.6):
 * loading, empty, error, abstained, conflicted y expired.
 *
 * Ninguno depende solo del color: todos llevan texto y un símbolo.
 */

import { TEXTS, abstentionReason } from "@/lib/texts";

export function LoadingState({ label }: { label?: string }) {
  return (
    <p role="status" aria-live="polite" className="faro-card text-muted">
      {label ?? TEXTS.loading}
    </p>
  );
}

export function EmptyState({ label }: { label?: string }) {
  return (
    <p data-state="empty" className="faro-card text-muted">
      {label ?? TEXTS.empty}
    </p>
  );
}

export function ErrorState({
  message,
  requestId,
  onRetry,
}: {
  message: string;
  requestId?: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" data-state="error" className="faro-card border-alert/40">
      <p className="font-semibold text-alert">
        <span aria-hidden="true">✕ </span>
        {TEXTS.errorTitle}
      </p>
      <p className="mt-1 text-sm text-ink">{message}</p>
      {requestId ? (
        <p className="mt-1 text-xs text-muted">ID de solicitud: {requestId}</p>
      ) : null}
      {onRetry ? (
        <button type="button" className="faro-button mt-3" onClick={onRetry}>
          {TEXTS.retry}
        </button>
      ) : null}
    </div>
  );
}

/** Una abstención es una salida válida, no un error (CONVENTIONS 14). */
export function AbstainedState({ reasons }: { reasons: readonly string[] }) {
  return (
    <div data-state="abstained" className="faro-card border-caution/40 bg-[#fdfaf3]">
      <p className="font-semibold text-caution">
        <span aria-hidden="true">◻ </span>
        {TEXTS.abstainedTitle}
      </p>
      <p className="mt-1 text-sm text-ink">{TEXTS.abstainedBody}</p>
      {reasons.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
          {reasons.map((reason) => (
            <li key={reason}>{abstentionReason(reason)}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ConflictedState() {
  return (
    <div data-state="conflicted" className="faro-card border-alert/40">
      <p className="font-semibold text-alert">
        <span aria-hidden="true">⇄ </span>
        {TEXTS.conflictedTitle}
      </p>
      <p className="mt-1 text-sm text-ink">{TEXTS.conflictedBody}</p>
    </div>
  );
}

export function ExpiredState() {
  return (
    <div data-state="expired" className="faro-card border-caution/40">
      <p className="font-semibold text-caution">
        <span aria-hidden="true">⌛ </span>
        {TEXTS.expiredTitle}
      </p>
      <p className="mt-1 text-sm text-ink">{TEXTS.expiredBody}</p>
    </div>
  );
}
