import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TarjetaFactores from "@/components/salud/TarjetaFactores.vue";
import type { FactorRiesgo } from "@/types/salud";

const FACTORES: readonly FactorRiesgo[] = [
  {
    id: "horas-de-sueno",
    icono: "luna",
    titulo: "Horas de sueño",
    detalle: "6.2 h · Bajo lo habitual",
    prioridad: "alta",
  },
  {
    id: "estres-percibido",
    icono: "rombo",
    titulo: "Estrés percibido",
    detalle: "4/5 · Elevado",
    prioridad: "alta",
  },
];

describe("TarjetaFactores", () => {
  it("titula la tarjeta con un h2 y su subtítulo", () => {
    const wrapper = mount(TarjetaFactores, { props: { factores: FACTORES } });

    expect(wrapper.get("h2").text()).toBe("Lo más importante hoy");
    expect(wrapper.get(".factores__subtitulo").text()).toBe(
      "Variables que más pueden influir en el riesgo de hoy.",
    );
  });

  it("lista un elemento por factor con su icono y su etiqueta de prioridad", () => {
    const wrapper = mount(TarjetaFactores, { props: { factores: FACTORES } });

    const filas = wrapper.findAll("li");
    expect(filas).toHaveLength(2);
    expect(filas[0]?.text()).toContain("Horas de sueño");
    expect(filas[0]?.text()).toContain("6.2 h · Bajo lo habitual");
    expect(filas[1]?.text()).toContain("Estrés percibido");
    expect(wrapper.findAll(".factor__prioridad").map((e) => e.text())).toEqual([
      "Alta prioridad",
      "Alta prioridad",
    ]);
    expect(wrapper.findAll("svg")).toHaveLength(2);
  });

  it("oculta los iconos a los lectores de pantalla", () => {
    const wrapper = mount(TarjetaFactores, { props: { factores: FACTORES } });

    for (const svg of wrapper.findAll("svg")) {
      expect(svg.attributes("aria-hidden")).toBe("true");
      expect(svg.attributes("focusable")).toBe("false");
    }
  });
});
