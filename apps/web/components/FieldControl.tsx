"use client";

/**
 * Control de un campo diario.
 *
 * Reglas que este componente respeta literalmente (CONVENTIONS 10):
 *
 * - La sugerencia se renderiza como ayuda, con estilo distinto de un valor
 *   confirmado, y **nunca** como valor precargado del control.
 * - Aceptarla exige una acción explícita.
 * - "No sé" persiste sin valor y es una respuesta distinta de dejar vacío.
 * - Las anclas ordinales se conservan; nada se convierte en una escala inventada.
 * - El navegador solo envía campos tocados.
 */

import { useId, useState } from "react";

import { FIELD_SPECS, type AnswerInteraction, type PlannedQuestion } from "@/lib/contracts";
import { ORDINAL_ANCHORS_ES, TEXTS, fieldLabel, optionLabel } from "@/lib/texts";
import { formatValue } from "@/lib/format";

export interface AnswerPayload {
  fieldCode: string;
  interaction: AnswerInteraction;
  value?: unknown;
  defaultPresentationId?: string;
}

interface Props {
  question: PlannedQuestion;
  answered: boolean;
  disabled?: boolean;
  onAnswer: (payload: AnswerPayload) => void;
}

export function FieldControl({ question, answered, disabled = false, onAnswer }: Props) {
  const spec = FIELD_SPECS[question.field_code];
  const [draft, setDraft] = useState<string>("");
  const [tags, setTags] = useState<string[]>([]);
  const controlId = useId();
  const helpId = `${controlId}-help`;

  if (spec === undefined) {
    return null;
  }

  const suggestion = question.default;

  function submitManual(value: unknown) {
    onAnswer({
      fieldCode: question.field_code,
      // El servidor deriva `entry_mode`: si el campo tuvo presentación vigente,
      // esto se convierte en `default_edited` aunque aquí se llame `manual`.
      interaction: suggestion ? "edit_default" : "manual",
      value,
      ...(suggestion ? { defaultPresentationId: suggestion.presentation_id } : {}),
    });
  }

  const controls = (() => {
    switch (spec.fieldType) {
      case "bool":
        return (
          <div className="flex flex-wrap gap-2">
            {[true, false].map((value) => (
              <button
                key={String(value)}
                type="button"
                className="faro-button"
                disabled={disabled}
                onClick={() => submitManual(value)}
              >
                {value ? "Sí" : "No"}
              </button>
            ))}
          </div>
        );
      case "enum":
        return (
          <div className="flex flex-wrap gap-2">
            {(spec.values ?? []).map((value) => (
              <button
                key={value}
                type="button"
                className="faro-button"
                disabled={disabled}
                onClick={() => submitManual(value)}
              >
                {optionLabel(question.field_code, value)}
              </button>
            ))}
          </div>
        );
      case "ordinal": {
        const anchors = ORDINAL_ANCHORS_ES[question.field_code] ?? [];
        return (
          <div className="flex flex-wrap gap-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                type="button"
                className="faro-button flex-col !gap-0"
                disabled={disabled}
                onClick={() => submitManual(value)}
              >
                <span className="text-base font-semibold">{value}</span>
                <span className="text-xs text-muted">{anchors[value - 1] ?? ""}</span>
              </button>
            ))}
          </div>
        );
      }
      case "enum_set":
        return (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {(spec.values ?? []).map((value) => {
                const checked = tags.includes(value);
                return (
                  <label
                    key={value}
                    className="faro-button cursor-pointer"
                    data-selected={checked}
                  >
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={checked}
                      disabled={disabled}
                      onChange={() =>
                        setTags((current) =>
                          current.includes(value)
                            ? current.filter((item) => item !== value)
                            : [...current, value],
                        )
                      }
                    />
                    {optionLabel(question.field_code, value)}
                  </label>
                );
              })}
            </div>
            <button
              type="button"
              className="faro-button"
              disabled={disabled || tags.length === 0}
              onClick={() => submitManual(tags)}
            >
              Guardar conductas
            </button>
          </div>
        );
      case "text":
        return (
          <div className="space-y-2">
            <textarea
              id={controlId}
              className="faro-input"
              rows={3}
              maxLength={spec.max ?? 500}
              value={draft}
              disabled={disabled}
              aria-describedby={helpId}
              onChange={(event) => setDraft(event.target.value)}
            />
            <button
              type="button"
              className="faro-button"
              disabled={disabled || draft.trim() === ""}
              onClick={() => submitManual(draft)}
            >
              Guardar
            </button>
          </div>
        );
      default:
        return (
          <div className="flex flex-wrap items-center gap-2">
            <input
              id={controlId}
              className="faro-input max-w-[10rem]"
              type="number"
              inputMode="decimal"
              min={spec.min}
              max={spec.max}
              step={spec.fieldType === "float" ? 0.5 : 1}
              value={draft}
              disabled={disabled}
              aria-describedby={helpId}
              onChange={(event) => setDraft(event.target.value)}
            />
            <button
              type="button"
              className="faro-button"
              disabled={disabled || draft === ""}
              onClick={() =>
                submitManual(
                  spec.fieldType === "float" ? Number(draft) : Number.parseInt(draft, 10),
                )
              }
            >
              Guardar
            </button>
          </div>
        );
    }
  })();

  return (
    <fieldset
      className="faro-card space-y-3"
      data-field={question.field_code}
      data-answered={answered}
    >
      <legend className="faro-label">
        {fieldLabel(question.field_code)}
        {answered ? (
          <span className="ml-2 text-xs font-normal text-accent">
            <span aria-hidden="true">✓ </span>respondido
          </span>
        ) : null}
      </legend>

      {suggestion ? (
        <div
          className="rounded-md border border-dashed border-accent/60 bg-[#f2f7fb] p-3"
          data-suggestion="true"
        >
          <p className="text-sm font-semibold text-accent">
            <span aria-hidden="true">◇ </span>
            {TEXTS.suggestionBadge}: {formatValue(suggestion.value)}
          </p>
          <p id={helpId} className="faro-hint mt-1">
            {TEXTS.suggestionHelp}
          </p>
          <button
            type="button"
            className="faro-button-primary mt-2"
            disabled={disabled}
            onClick={() =>
              onAnswer({
                fieldCode: question.field_code,
                interaction: "accept_default",
                defaultPresentationId: suggestion.presentation_id,
              })
            }
          >
            {TEXTS.suggestionAccept}
          </button>
        </div>
      ) : null}

      {controls}

      <button
        type="button"
        className="faro-button"
        disabled={disabled}
        onClick={() =>
          onAnswer({ fieldCode: question.field_code, interaction: "unknown" })
        }
      >
        {TEXTS.unknownAnswer}
      </button>
    </fieldset>
  );
}
