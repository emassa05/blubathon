import { describe, expect, it } from "vitest";

import {
  MINIMO_RESULTADOS,
  adherencia,
  pendientesDeCierre,
  serieRiesgo,
  tasaObservada,
  ultimoRiesgo,
} from "@/dominio/serieRiesgo";

import { diaFalso } from "./servidorFalso";

/** Un día con el resultado ya confirmado, que `diaFalso` deja siempre en `pending`. */
function conResultado(dia: unknown, estado: "yes" | "no"): unknown {
  return { ...(dia as object), outcome: { status: estado, reported_at: "2026-08-25T12:00:00Z" } };
}

describe("serieRiesgo", () => {
  it("devuelve los días en orden cronológico, no como los da la API", () => {
    // El contrato entrega del más reciente al más antiguo; una línea de tiempo
    // se lee al revés, y si el orden no se invirtiera aquí el gráfico dibujaría
    // el pasado a la derecha.
    const serie = serieRiesgo([
      diaFalso({ fecha: "2026-08-25", probabilidad: 0.4 }),
      diaFalso({ fecha: "2026-08-24", probabilidad: 0.1 }),
    ] as never);

    expect(serie.map((punto) => punto.fecha)).toEqual(["2026-08-24", "2026-08-25"]);
  });

  it("pasa la probabilidad de 0-1 a 0-100", () => {
    const [punto] = serieRiesgo([diaFalso({ fecha: "2026-08-25", probabilidad: 0.183 })] as never);
    expect(punto?.riesgo).toBe(18.3);
  });

  it("deja la abstención como hueco y no la convierte en cero", () => {
    // Un cero diría "hoy no hay riesgo". La abstención dice "no lo sabemos", y
    // pintar lo segundo como lo primero es afirmar algo que nadie estimó.
    const [punto] = serieRiesgo([diaFalso({ fecha: "2026-08-25", probabilidad: null })] as never);
    expect(punto?.riesgo).toBeNull();
  });

  it("descarta un intervalo con los extremos cambiados", () => {
    const [punto] = serieRiesgo([
      diaFalso({ fecha: "2026-08-25", probabilidad: 0.4, intervalo: [0.6, 0.2] }),
    ] as never);
    expect(punto?.banda).toBeNull();
  });
});

describe("ultimoRiesgo", () => {
  it("se salta las abstenciones más recientes y devuelve la última cifra", () => {
    const serie = serieRiesgo([
      diaFalso({ fecha: "2026-08-25", probabilidad: null }),
      diaFalso({ fecha: "2026-08-24", probabilidad: 0.31 }),
    ] as never);
    expect(ultimoRiesgo(serie)).toBe(31);
  });

  it("es null cuando el modelo se abstuvo todos los días", () => {
    const serie = serieRiesgo([diaFalso({ fecha: "2026-08-25", probabilidad: null })] as never);
    expect(ultimoRiesgo(serie)).toBeNull();
  });
});

describe("tasaObservada", () => {
  it("se abstiene por debajo del mínimo de resultados confirmados", () => {
    // "1 de 2" se leería como un 50 % de riesgo de fondo, y no es nada
    // parecido a eso: es el mismo corte con el que se abstiene el backend.
    const dias = [
      conResultado(diaFalso({ fecha: "2026-08-25", probabilidad: 0.4 }), "yes"),
      conResultado(diaFalso({ fecha: "2026-08-24", probabilidad: 0.4 }), "no"),
    ];
    expect(tasaObservada(serieRiesgo(dias as never))).toBeNull();
  });

  it("cuenta episodios sobre confirmados en cuanto hay base", () => {
    const dias = Array.from({ length: MINIMO_RESULTADOS }, (_, indice) =>
      conResultado(
        diaFalso({ fecha: `2026-08-${20 + indice}`, probabilidad: 0.4 }),
        indice === 0 ? "yes" : "no",
      ),
    );
    expect(tasaObservada(serieRiesgo(dias as never))).toEqual({
      episodios: 1,
      confirmados: MINIMO_RESULTADOS,
    });
  });

  it("no cuenta como limpio un día sin contestar", () => {
    // `pending` no es un "no": es silencio, y contarlo bajaría la tasa con días
    // de los que nadie dijo nada.
    const dias = Array.from({ length: MINIMO_RESULTADOS }, (_, indice) =>
      diaFalso({ fecha: `2026-08-${20 + indice}`, probabilidad: 0.4 }),
    );
    expect(tasaObservada(serieRiesgo(dias as never))).toBeNull();
  });
});

describe("adherencia", () => {
  it("mide días con registro sobre días que abarca el historial", () => {
    // Del 20 al 24 son 5 días de calendario; hay 2 registrados.
    const serie = serieRiesgo([
      diaFalso({ fecha: "2026-08-24", probabilidad: 0.4 }),
      diaFalso({ fecha: "2026-08-20", probabilidad: 0.4 }),
    ] as never);
    expect(adherencia(serie)).toBeCloseTo(2 / 5);
  });

  it("es 1 cuando no falta ningún día", () => {
    const serie = serieRiesgo([
      diaFalso({ fecha: "2026-08-21", probabilidad: 0.4 }),
      diaFalso({ fecha: "2026-08-20", probabilidad: 0.4 }),
    ] as never);
    expect(adherencia(serie)).toBe(1);
  });

  it("es 0 sin historial, y no una división por cero", () => {
    expect(adherencia([])).toBe(0);
  });
});

describe("pendientesDeCierre", () => {
  it("cuenta lo que sigue sin resolverse, incluido lo que entró en conflicto", () => {
    const dias = [
      diaFalso({ fecha: "2026-08-25", probabilidad: 0.4 }),
      conResultado(diaFalso({ fecha: "2026-08-24", probabilidad: 0.4 }), "no"),
      {
        ...(diaFalso({ fecha: "2026-08-23", probabilidad: 0.4 }) as object),
        outcome: { status: "conflicted", reported_at: null },
      },
    ];
    expect(pendientesDeCierre(dias as never)).toBe(2);
  });
});
