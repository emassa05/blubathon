import { describe, expect, it } from "vitest";

import type { CalibrationResponse } from "@/api/contrato";
import { DIAS_MINIMOS, bandaDeRiesgo, comprobacionDe } from "@/dominio/comprobacion";

function calibracion(
  tramos: Array<{ band: "low" | "medium" | "high"; days: number; observed: number; announced: number }>,
): CalibrationResponse {
  return {
    bands: tramos.map((tramo) => ({
      band: tramo.band,
      days: tramo.days,
      episodes: Math.round(tramo.days * tramo.observed),
      announced: tramo.announced,
      observed: tramo.observed,
      interval: [Math.max(0, tramo.observed - 0.07), Math.min(1, tramo.observed + 0.07)] as [
        number,
        number,
      ],
    })),
    brier: 0.21,
    days: tramos.reduce((total, tramo) => total + tramo.days, 0),
    episodes: 0,
    caveat_es: "aviso",
  } as CalibrationResponse;
}

describe("la comprobación de la cohorte", () => {
  it("usa los mismos cortes de banda que el servidor", () => {
    expect(bandaDeRiesgo(0)).toBe("low");
    expect(bandaDeRiesgo(19)).toBe("low");
    expect(bandaDeRiesgo(20)).toBe("medium");
    expect(bandaDeRiesgo(49)).toBe("medium");
    expect(bandaDeRiesgo(50)).toBe("high");
    expect(bandaDeRiesgo(100)).toBe("high");
  });

  it("trae el tramo que le toca a la cifra del día", () => {
    const datos = calibracion([
      { band: "low", days: 76, observed: 0.13, announced: 0.15 },
      { band: "medium", days: 226, observed: 0.36, announced: 0.37 },
      { band: "high", days: 170, observed: 0.59, announced: 0.61 },
    ]);

    expect(comprobacionDe(datos, 61)?.banda).toBe("high");
    expect(comprobacionDe(datos, 61)?.observado).toBe(59);
    expect(comprobacionDe(datos, 61)?.dias).toBe(170);
    expect(comprobacionDe(datos, 30)?.banda).toBe("medium");
    expect(comprobacionDe(datos, 5)?.banda).toBe("low");
  });

  it("dice si lo anunciado cae dentro de lo observado", () => {
    const concuerda = calibracion([{ band: "medium", days: 226, observed: 0.36, announced: 0.37 }]);
    expect(comprobacionDe(concuerda, 30)?.concuerda).toBe(true);

    // Anuncia 20% donde ocurre el 60%: el intervalo no lo cubre.
    const falla = calibracion([{ band: "medium", days: 226, observed: 0.6, announced: 0.2 }]);
    expect(comprobacionDe(falla, 30)?.concuerda).toBe(false);
  });

  it("calla mientras el tramo tenga pocos días", () => {
    const pocos = calibracion([
      { band: "medium", days: DIAS_MINIMOS - 1, observed: 0.36, announced: 0.37 },
    ]);
    expect(comprobacionDe(pocos, 30)).toBeNull();

    const justos = calibracion([
      { band: "medium", days: DIAS_MINIMOS, observed: 0.36, announced: 0.37 },
    ]);
    expect(comprobacionDe(justos, 30)).not.toBeNull();
  });

  it("sin cifra o sin calibración no hay nada que comprobar", () => {
    const datos = calibracion([{ band: "medium", days: 226, observed: 0.36, announced: 0.37 }]);
    expect(comprobacionDe(datos, null)).toBeNull();
    expect(comprobacionDe(null, 30)).toBeNull();
  });

  it("un tramo que el modelo nunca anunció no se inventa", () => {
    const datos = calibracion([{ band: "medium", days: 226, observed: 0.36, announced: 0.37 }]);
    expect(comprobacionDe(datos, 80)).toBeNull();
  });
});
