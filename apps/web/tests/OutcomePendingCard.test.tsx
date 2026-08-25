/**
 * Bloque de resultado pendiente: «No sé» no fabrica un negativo (SPEC 4.4).
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OutcomePendingCard } from "@/components/OutcomePendingCard";

const base = {
  questionEs: "¿Ocurrió una desregulación mayor en las últimas 24 horas?",
  anchorsEs: ["No ocurrió: día habitual.", "Ocurrió: requirió apoyo sostenido."],
  targetEndAt: "2026-08-26T12:00:00.000Z",
  captureDeadlineAt: "2026-08-27T12:00:00.000Z",
  state: "open",
};

describe("OutcomePendingCard", () => {
  it("conserva las anclas de severidad tal como fueron aprobadas", () => {
    render(<OutcomePendingCard {...base} onReport={vi.fn()} />);
    expect(screen.getByText(/día habitual/)).toBeInTheDocument();
    expect(screen.getByText(/apoyo sostenido/)).toBeInTheDocument();
  });

  it("«No sé» envía unknown y avisa que no se convierte en un no", async () => {
    const onReport = vi.fn();
    const user = userEvent.setup();
    render(<OutcomePendingCard {...base} onReport={onReport} />);
    await user.click(screen.getByRole("button", { name: "No sé" }));
    expect(onReport).toHaveBeenCalledWith("unknown");
    expect(screen.getByText(/no lo convierte en un “no ocurrió”/)).toBeInTheDocument();
  });

  it("«Sí, ocurrió» exige declarar cuándo", async () => {
    render(<OutcomePendingCard {...base} onReport={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Sí, ocurrió/ })).toBeDisabled();
  });

  it("un estado de conflicto reemplaza el formulario", () => {
    render(<OutcomePendingCard {...base} state="conflicted" onReport={vi.fn()} />);
    expect(screen.getByText(/Reportes incompatibles/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "No sé" })).toBeNull();
  });
});
