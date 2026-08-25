/**
 * Serialización visible de recomendaciones (SPEC 11.6, INV-29).
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FARO_TEXTS_ES } from "@faro/contract";

import { RecommendationList } from "@/components/RecommendationList";
import {
  abstainedRecommendations,
  awaitingReview,
  matchedRecommendations,
} from "./fixtures";

describe("RecommendationList", () => {
  it("mientras todo esté pendiente no muestra ninguna acción", () => {
    render(<RecommendationList view={awaitingReview()} />);
    expect(screen.getByText(/Esperando revisión profesional/)).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).toBeNull();
  });

  it("una abstención muestra su razón y ninguna estrategia", () => {
    render(<RecommendationList view={abstainedRecommendations()} />);
    expect(screen.getByText(FARO_TEXTS_ES.recommendationAbstentionEs.clinical_review_unavailable)).toBeInTheDocument();
    // La abstención lista razones, nunca estrategias.
    expect(screen.queryByRole("listitem")).toHaveTextContent(
      FARO_TEXTS_ES.recommendationAbstentionEs.clinical_review_unavailable,
    );
    expect(screen.queryByText(/Revisen luz, ruido/)).toBeNull();
  });

  it("una estrategia aprobada trae citas abribles y verificables", () => {
    render(<RecommendationList view={matchedRecommendations()} />);
    expect(screen.getByText(/Revisen luz, ruido y temperatura/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Abrir la fuente citada/ });
    expect(link).toHaveAttribute("href", "https://example.invalid/faro/fixture-doc-001/v1");
  });

  it("un plan humano no muestra citas del RAG", () => {
    render(<RecommendationList view={matchedRecommendations()} />);
    const planItem = screen
      .getAllByRole("listitem")
      .find((item) => item.dataset.itemType === "human_plan");
    expect(planItem).toBeDefined();
    expect(planItem?.textContent).toMatch(/no hereda citas del catálogo/);
    expect(planItem?.querySelector("a")).toBeNull();
  });

  it("una dependencia suspendida se marca como no accionable", () => {
    const view = matchedRecommendations();
    const suspended = {
      ...view,
      items: view.items.map((item) => ({ ...item, non_actionable: "dependency_suspended" as const })),
    };
    render(<RecommendationList view={suspended} />);
    expect(screen.getAllByText(/no accionable/)).toHaveLength(2);
  });
});
