/**
 * Lista de recomendaciones ya filtrada por el servidor (SPEC 11.6).
 *
 * El frontend no decide qué se muestra: solo dibuja lo que el serializer
 * autorizó. Un plan humano nunca aparece con citas del RAG.
 */

import { AbstainedState } from "@/components/States";
import { isHumanPlan, reviewStatusOf } from "@/lib/contracts";
import type { RecommendationItemView, RecommendationsView } from "@/lib/contracts";
import { REVIEW_STATUS_ES, TEXTS } from "@/lib/texts";

function Citations({ item }: { item: RecommendationItemView }) {
  const citations = item.citations ?? [];
  if (citations.length === 0) {
    return (
      <p className="faro-hint">
        {isHumanPlan(item)
          ? "Un plan propio del equipo no hereda citas del catálogo."
          : "Sin citas registradas."}
      </p>
    );
  }
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-sm font-semibold text-accent">
        {TEXTS.citationsTitle} ({citations.length})
      </summary>
      <ul className="mt-2 space-y-2">
        {citations.map((citation) => (
          <li key={citation.citation_id} className="rounded border border-line p-2 text-sm">
            <p className="italic text-ink">“{citation.quoted_text}”</p>
            <p className="faro-hint mt-1">{citation.locator}</p>
            <a
              className="text-sm text-accent underline"
              href={citation.canonical_url}
              rel="noreferrer noopener"
              target="_blank"
            >
              Abrir la fuente citada
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function RecommendationList({
  view,
  children,
}: {
  view: RecommendationsView;
  children?: (item: RecommendationItemView) => React.ReactNode;
}) {
  if (view.status === "abstained") {
    return <AbstainedState reasons={view.reasons ?? []} />;
  }
  if (view.status === "awaiting_professional_review") {
    return (
      <div data-state="awaiting-review" className="faro-card border-caution/40">
        <p className="font-semibold text-caution">
          <span aria-hidden="true">◷ </span>
          {TEXTS.awaitingReviewTitle}
        </p>
        <p className="mt-1 text-sm text-ink">{TEXTS.awaitingReviewBody}</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {view.items.map((item) => (
        <li
          key={isHumanPlan(item) ? item.human_plan_version_id : item.strategy_version_id}
          className="faro-card space-y-2"
          data-item-type={item.item_type}
          data-review-status={reviewStatusOf(item)}
        >
          <p className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
            <span>
              {isHumanPlan(item) ? "Plan del equipo" : "Estrategia del catálogo"}
            </span>
            <span>·</span>
            <span>{REVIEW_STATUS_ES[reviewStatusOf(item)] ?? reviewStatusOf(item)}</span>
            {item.non_actionable ? (
              <span className="text-alert">
                <span aria-hidden="true">⊘ </span>no accionable
              </span>
            ) : null}
          </p>
          <p className="text-base text-ink">{item.action_text_es}</p>
          <Citations item={item} />
          {children ? children(item) : null}
        </li>
      ))}
    </ul>
  );
}
