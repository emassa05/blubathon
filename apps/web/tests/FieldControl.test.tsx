/**
 * El control de campo respeta las reglas del formulario (CONVENTIONS 10).
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FARO_TEXTS_ES } from "@faro/contract";

import { FieldControl } from "@/components/FieldControl";
import { question, suggestedQuestion } from "./fixtures";

describe("FieldControl", () => {
  it("no precarga la sugerencia en el control y no envía nada si no se toca", () => {
    const onAnswer = vi.fn();
    render(
      <FieldControl question={suggestedQuestion()} answered={false} onAnswer={onAnswer} />,
    );
    // La sugerencia aparece como ayuda con estilo propio, no como valor elegido.
    expect(screen.getByText(/Sugerencia: No/)).toBeInTheDocument();
    expect(
      screen.getByText(FARO_TEXTS_ES.defaultSuggestionHintEs),
    ).toBeInTheDocument();
    expect(onAnswer).not.toHaveBeenCalled();
  });

  it("aceptar la sugerencia exige una acción explícita", async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    render(
      <FieldControl question={suggestedQuestion()} answered={false} onAnswer={onAnswer} />,
    );
    await user.click(screen.getByRole("button", { name: /Usar esta sugerencia/ }));
    expect(onAnswer).toHaveBeenCalledWith({
      fieldCode: "food_changes",
      interaction: "accept_default",
      // `AnswerSubmission` de P1 exige declarar el valor aceptado.
      value: false,
      defaultPresentationId: "00000000-0000-4000-8000-000000000701",
    });
  });

  it("escribir otro valor sobre un campo con sugerencia se envía como edición", async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    render(
      <FieldControl question={suggestedQuestion()} answered={false} onAnswer={onAnswer} />,
    );
    await user.click(screen.getByRole("button", { name: "Sí" }));
    expect(onAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ interaction: "edit_default", value: true }),
    );
  });

  it("«No sé» es una respuesta explícita sin valor", async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    render(<FieldControl question={question()} answered={false} onAnswer={onAnswer} />);
    await user.click(screen.getByRole("button", { name: "No sé" }));
    expect(onAnswer).toHaveBeenCalledWith({
      fieldCode: "sleep_quality",
      interaction: "unknown",
    });
  });

  it("conserva las anclas de una escala ordinal", () => {
    render(
      <FieldControl
        question={question({ field_code: "activity_participation" })}
        answered={false}
        onAnswer={vi.fn()}
      />,
    );
    expect(
      screen.getByText(FARO_TEXTS_ES.ordinalAnchorsEs.activity_participation[2]!),
    ).toBeInTheDocument();
    expect(
      screen.getByText(FARO_TEXTS_ES.ordinalAnchorsEs.activity_participation[4]!),
    ).toBeInTheDocument();
  });

  it("muestra las categorías del catálogo cerrado, sin inventar opciones", () => {
    render(<FieldControl question={question()} answered={false} onAnswer={vi.fn()} />);
    for (const label of Object.values(FARO_TEXTS_ES.sleepQualityLabelsEs)) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });
});
