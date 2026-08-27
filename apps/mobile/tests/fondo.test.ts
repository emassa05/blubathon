import { describe, expect, it } from "vitest";

import { VARIABLE_FONDO, VARIANTES, aplicarFondo, varianteAlAzar } from "@/theme/fondo";

describe("varianteAlAzar", () => {
  it("reparte el sorteo por todas las variantes, sin salirse", () => {
    const salidas = new Set<string>();
    for (let i = 0; i < 1000; i += 1) {
      salidas.add(varianteAlAzar(i / 1000).id);
    }
    expect(salidas.size).toBe(VARIANTES.length);
  });

  it("aguanta los extremos del sorteo", () => {
    // `Math.random()` devuelve [0, 1). El 1 no deberia llegar, pero un
    // desbordamiento del indice dejaria la pantalla sin fondo.
    expect(varianteAlAzar(0).id).toBe(VARIANTES[0]?.id);
    expect(varianteAlAzar(0.999999999).id).toBe(VARIANTES[VARIANTES.length - 1]?.id);
    expect(varianteAlAzar(1)).toBeDefined();
    expect(varianteAlAzar(-1)).toBeDefined();
  });
});

describe("aplicarFondo", () => {
  it("escribe las capas en la raiz y deja a la vista cual salio", () => {
    const raiz = document.createElement("div");
    const variante = aplicarFondo(raiz, VARIANTES[2]);

    expect(variante.id).toBe(VARIANTES[2]?.id);
    expect(raiz.style.getPropertyValue(VARIABLE_FONDO)).toBe(VARIANTES[2]?.capas);
    expect(raiz.dataset.fondo).toBe(VARIANTES[2]?.id);
  });
});

describe("las variantes", () => {
  it("todas traen las tres burbujas sobre un degradado", () => {
    for (const variante of VARIANTES) {
      const burbujas = variante.capas.match(/radial-gradient/g) ?? [];
      expect(burbujas).toHaveLength(3);
      expect(variante.capas).toContain("linear-gradient");
    }
  });

  it("ninguna se sale de la familia de la marca ni sube el croma", () => {
    for (const variante of VARIANTES) {
      for (const [, luz, croma, tono] of variante.capas.matchAll(
        /oklch\(([\d.]+) ([\d.]+) ([\d.]+)/g,
      )) {
        // Fuera de 200-280 el fondo empezaria a leerse como una banda de riesgo.
        expect(Number(tono)).toBeGreaterThanOrEqual(200);
        expect(Number(tono)).toBeLessThanOrEqual(280);
        // Ambiente, no color: por encima de esto la tarjeta blanca deja de
        // separarse del fondo.
        expect(Number(croma)).toBeLessThanOrEqual(0.06);
        // Y muy claras: por debajo de esto dejaria de ser ambiente.
        expect(Number(luz)).toBeGreaterThanOrEqual(0.93);
      }
    }
  });

  it("cada variante tiene un id propio", () => {
    const ids = VARIANTES.map((variante) => variante.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
