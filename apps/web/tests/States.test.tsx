/**
 * Estados obligatorios y límite de emergencia (CONVENTIONS 14, SPEC 13.2).
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmergencyNotice } from "@/components/EmergencyNotice";
import {
  AbstainedState,
  ConflictedState,
  EmptyState,
  ErrorState,
  ExpiredState,
  LoadingState,
} from "@/components/States";

describe("estados obligatorios", () => {
  it("loading anuncia el progreso de forma accesible", () => {
    render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando");
  });

  it("empty se distingue de un error", () => {
    render(<EmptyState />);
    expect(screen.getByText(/No hay nada que mostrar/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("error muestra el ID de solicitud sin payload clínico", () => {
    render(<ErrorState message="No se pudo guardar" requestId="req-1" />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("No se pudo guardar");
    expect(alert).toHaveTextContent("req-1");
  });

  it("la abstención no se presenta como error y explica su razón", () => {
    render(<AbstainedState reasons={["insufficient_verified_outcomes"]} />);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText(/Faro se abstiene/)).toBeInTheDocument();
    expect(
      screen.getByText(/Aún no hay suficientes resultados verificados/),
    ).toBeInTheDocument();
  });

  it("conflicto y expiración tienen su propio estado", () => {
    const { unmount } = render(<ConflictedState />);
    expect(screen.getByText(/Reportes incompatibles/)).toBeInTheDocument();
    unmount();
    render(<ExpiredState />);
    expect(screen.getByText(/ventana de captura ya cerró/)).toBeInTheDocument();
  });

  it("cada estado lleva texto y símbolo, no solo color", () => {
    render(<AbstainedState reasons={[]} />);
    const card = screen.getByText(/Faro se abstiene/);
    expect(card.textContent).toMatch(/◻/);
  });
});

describe("límite de emergencia", () => {
  it("es visible y dice que no hay que esperar una alerta", () => {
    render(<EmergencyNotice />);
    const note = screen.getByRole("note");
    expect(note).toHaveTextContent("Faro no monitorea emergencias");
    expect(note).toHaveTextContent(/no esperes una alerta/i);
  });
});
