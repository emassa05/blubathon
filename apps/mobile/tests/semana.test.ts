import { describe, expect, it } from "vitest";

import { desplazarSemana, etiquetaDiaLargo, lunesDe, semanaDe } from "@/dominio/semana";

describe("semana", () => {
  it("empieza en lunes, también cuando la fecha cae en domingo", () => {
    expect(lunesDe("2026-08-26")).toBe("2026-08-24");
    expect(lunesDe("2026-08-24")).toBe("2026-08-24");
    // El domingo cierra la semana que empezó seis días antes, no abre una nueva.
    expect(lunesDe("2026-08-30")).toBe("2026-08-24");
  });

  it("trae siete días seguidos con su inicial y su número", () => {
    const semana = semanaDe("2026-08-26", "2026-08-26");

    expect(semana.dias).toHaveLength(7);
    expect(semana.inicio).toBe("2026-08-24");
    expect(semana.fin).toBe("2026-08-30");
    expect(semana.dias.map((dia) => dia.numero)).toEqual([24, 25, 26, 27, 28, 29, 30]);
    expect(semana.dias[0]?.nombre).toBe("Lunes");
  });

  it("marca el día de hoy y deja el resto de la semana como futuro", () => {
    const semana = semanaDe("2026-08-26", "2026-08-26");

    expect(semana.dias.filter((dia) => dia.esHoy).map((dia) => dia.iso)).toEqual(["2026-08-26"]);
    expect(semana.dias.filter((dia) => dia.esFuturo).map((dia) => dia.numero)).toEqual([
      27, 28, 29, 30,
    ]);
  });

  it("no repite el mes en el rótulo si la semana no cambia de mes", () => {
    expect(semanaDe("2026-08-26", "2026-08-26").etiqueta).toBe("24 – 30 de agosto");
    // Y sí lo repite cuando la semana se parte entre dos meses.
    expect(semanaDe("2026-09-30", "2026-09-30").etiqueta).toBe("28 de septiembre – 4 de octubre");
  });

  it("sabe si es la semana en curso", () => {
    expect(semanaDe("2026-08-26", "2026-08-26").esSemanaActual).toBe(true);
    expect(semanaDe("2026-08-19", "2026-08-26").esSemanaActual).toBe(false);
  });

  it("se mueve de semana en semana en los dos sentidos", () => {
    expect(desplazarSemana("2026-08-24", -1)).toBe("2026-08-17");
    expect(desplazarSemana("2026-08-24", 1)).toBe("2026-08-31");
    expect(desplazarSemana("2026-08-24", -5)).toBe("2026-07-20");
  });

  it("titula un día con su nombre completo", () => {
    // La coma la pone el propio formato de `es-ES`; no se retoca a mano.
    expect(etiquetaDiaLargo("2026-08-25")).toBe("Martes, 25 de agosto");
  });
});
