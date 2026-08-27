import { describe, expect, it } from "vitest";

import { confianzaDelIntervalo } from "@/dominio/incertidumbre";

describe("confianzaDelIntervalo", () => {
  it("pasa el ancho del intervalo a confianza", () => {
    // 0.15 de ancho: 85%.
    expect(confianzaDelIntervalo([0.09, 0.24])).toBe(85);
  });

  it("sin intervalo no inventa una confianza", () => {
    // El challenger logístico no publica intervalo, y el contrato deja el campo
    // opcional: ausente, mal formado o con algo que no es un número es lo mismo,
    // y lo que se devuelve es "no hay", no un número por defecto.
    for (const valor of [null, undefined, [], [0.1], [0.1, 0.2, 0.3], ["a", "b"], [0.1, "b"]]) {
      expect(confianzaDelIntervalo(valor)).toBeNull();
    }
  });

  it("un intervalo del revés se descarta, no se da la vuelta", () => {
    expect(confianzaDelIntervalo([0.6, 0.2])).toBeNull();
  });

  it("acota al 0-1 antes de convertir", () => {
    expect(confianzaDelIntervalo([-0.2, 1.4])).toBe(0);
  });

  /*
   * El rango que la cifra puede tomar de verdad. Con la ventana de 60 días (C18)
   * y el mínimo de 5 resultados (C19), el ancho del posterior Beta va de ~0.58 a
   * ~0.18: el número vive entre el 42% y el 82% y el 100% es inalcanzable.
   */
  it("no llega al 100 ni con la ventana llena", () => {
    expect(confianzaDelIntervalo([0.24, 0.42])).toBe(82);
    expect(confianzaDelIntervalo([0.13, 0.71])).toBe(42);
  });
});
