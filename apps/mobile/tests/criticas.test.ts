import { describe, expect, it } from "vitest";

import { variablesCriticas, zRobusta } from "@/dominio/criticas";

const HOY = "2026-08-26";

describe("variables críticas", () => {
  it("no destaca un día sin nada fuera de lo normal", () => {
    const criticas = variablesCriticas(
      { sleep_hours: 9, daily_regulation_state: "excellent", dysregulation_event_count: 0 },
      HOY,
    );

    expect(criticas).toEqual([]);
  });

  it("destaca el sueño corto y la desregulación frecuente como graves", () => {
    const criticas = variablesCriticas(
      { sleep_hours: 5.5, daily_regulation_state: "frequent_dysregulation" },
      HOY,
    );

    expect(criticas.map((critica) => critica.campo)).toEqual([
      "sleep_hours",
      "daily_regulation_state",
    ]);
    expect(criticas.every((critica) => critica.severidad === "alta")).toBe(true);
    expect(criticas[0]?.valor).toBe("5.5 h");
    expect(criticas[0]?.motivo).toBe("Muy poco sueño");
  });

  it("pone las graves delante y el resto en orden canónico", () => {
    const criticas = variablesCriticas(
      { alertness: "high", medication_adherence: "missed", sleep_quality: "interrupted" },
      HOY,
    );

    expect(criticas.map((critica) => critica.campo)).toEqual([
      "medication_adherence",
      "sleep_quality",
      "alertness",
    ]);
  });

  it("da luna a lo que habla del sueño y rombo al resto", () => {
    const criticas = variablesCriticas({ night_awakenings: 6, routine_changes: true }, HOY);

    expect(criticas.find((critica) => critica.campo === "night_awakenings")?.icono).toBe("luna");
    expect(criticas.find((critica) => critica.campo === "routine_changes")?.icono).toBe("rombo");
  });

  it("sin historial suficiente no calcula desviación personal", () => {
    const anteriores = [
      { fecha: "2026-08-25", respuestas: { sleep_hours: 7 } },
      { fecha: "2026-08-24", respuestas: { sleep_hours: 7.5 } },
    ];

    // 10 h no dispara ningún corte de nivel, y con dos observaciones tampoco
    // hay desviación que medir.
    expect(variablesCriticas({ sleep_hours: 10 }, HOY, anteriores)).toEqual([]);
  });

  it("con historial suficiente destaca lo que se sale de lo habitual", () => {
    const anteriores = [
      { fecha: "2026-08-25", respuestas: { sleep_hours: 7 } },
      { fecha: "2026-08-24", respuestas: { sleep_hours: 7.5 } },
      { fecha: "2026-08-23", respuestas: { sleep_hours: 8 } },
      { fecha: "2026-08-22", respuestas: { sleep_hours: 7 } },
      { fecha: "2026-08-21", respuestas: { sleep_hours: 7.5 } },
    ];

    const criticas = variablesCriticas({ sleep_hours: 10 }, HOY, anteriores);

    expect(criticas).toHaveLength(1);
    expect(criticas[0]?.severidad).toBe("media");
    expect(criticas[0]?.motivo).toBe("Sobre lo habitual, suele ser 7.5 h");
  });

  it("no mira días fuera de la ventana ni el día que se está evaluando", () => {
    const fuera = Array.from({ length: 6 }, (_, indice) => ({
      fecha: `2026-06-${String(10 + indice).padStart(2, "0")}`,
      respuestas: { sleep_hours: 7 + (indice % 2) / 2 },
    }));

    expect(variablesCriticas({ sleep_hours: 10 }, HOY, fuera)).toEqual([]);
  });

  it("la z robusta se calla cuando el historial no tiene dispersión", () => {
    expect(zRobusta(10, [7, 7, 7, 7, 7])).toBeNull();
    expect(zRobusta(10, [7, 7.5])).toBeNull();
    expect(zRobusta(10, [7, 7.5, 8, 7, 7.5])).toBeCloseTo(3.37, 2);
  });
});
