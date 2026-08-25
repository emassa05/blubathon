/**
 * Límite de uso urgente, visible de forma permanente (SPEC 2.27 y 13.2).
 *
 * Aparece en entrada, abstención, resultados y recomendaciones. Nunca sugiere
 * esperar una alerta de Faro.
 */

import { TEXTS } from "@/lib/texts";

export function EmergencyNotice({ body }: { body?: string }) {
  return (
    <aside
      role="note"
      aria-label={TEXTS.emergencyTitle}
      className="faro-card border-alert/40 bg-[#fdf6f6]"
    >
      <p className="flex items-start gap-2 text-sm font-semibold text-alert">
        <span aria-hidden="true">⚠</span>
        <span>{TEXTS.emergencyTitle}</span>
      </p>
      <p className="mt-1 text-sm text-ink">{body ?? TEXTS.emergencyBody}</p>
    </aside>
  );
}
