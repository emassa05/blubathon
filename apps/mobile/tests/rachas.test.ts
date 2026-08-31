import { describe, expect, it } from "vitest";

import type { ChildHistoryDay } from "@/api/contrato";
import { rachaSinDesregulacion } from "@/dominio/rachas";

type Estado = ChildHistoryDay["outcome"] extends infer T
  ? T extends { status: infer S } | null | undefined
    ? S
    : never
  : never;

/** Un día del historial con solo lo que la racha mira. */
function dia(fecha: string, estado?: Estado): ChildHistoryDay {
  return {
    local_date: fecha,
    ...(estado === undefined ? {} : { outcome: { status: estado } }),
  } as ChildHistoryDay;
}

describe("rachaSinDesregulacion", () => {
  it("cuenta los 'no' seguidos desde el último día resuelto", () => {
    expect(
      rachaSinDesregulacion([
        dia("2026-08-26", "no"),
        dia("2026-08-25", "no"),
        dia("2026-08-24", "no"),
        dia("2026-08-23", "yes"),
      ]),
    ).toEqual({ dias: 3, hasta: "2026-08-26" });
  });

  it("los días sin contestar de arriba no cortan la racha ni la empiezan", () => {
    // La pregunta de hoy suele seguir abierta —la ventana de 24 h no ha
    // cerrado—, y arrancar ahí dejaría la racha en cero cada mañana.
    expect(
      rachaSinDesregulacion([
        dia("2026-08-27", "pending"),
        dia("2026-08-26", "no"),
        dia("2026-08-25", "no"),
      ]),
    ).toEqual({ dias: 2, hasta: "2026-08-26" });
  });

  it("un hueco sin contestar en medio corta: detrás no se sabe qué pasó", () => {
    expect(
      rachaSinDesregulacion([
        dia("2026-08-26", "no"),
        dia("2026-08-25", "pending"),
        dia("2026-08-24", "no"),
        dia("2026-08-23", "no"),
      ]),
    ).toEqual({ dias: 1, hasta: "2026-08-26" });
  });

  it("'unknown' y 'conflicted' tampoco cuentan como días limpios", () => {
    for (const estado of ["unknown", "conflicted"] as const) {
      expect(rachaSinDesregulacion([dia("2026-08-26", estado), dia("2026-08-25", "no")])).toEqual({
        dias: 1,
        hasta: "2026-08-25",
      });
    }
  });

  it("si el último confirmado fue un 'sí', la racha es cero y no null", () => {
    // Cero es informativo: dice que hubo episodio. `null` es no saber nada.
    expect(rachaSinDesregulacion([dia("2026-08-26", "yes"), dia("2026-08-25", "no")])).toEqual({
      dias: 0,
      hasta: "2026-08-26",
    });
  });

  it("sin ningún resultado confirmado no hay racha que enseñar", () => {
    expect(rachaSinDesregulacion([])).toBeNull();
    expect(rachaSinDesregulacion([dia("2026-08-27", "pending"), dia("2026-08-26")])).toBeNull();
  });
});
