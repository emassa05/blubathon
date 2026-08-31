import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CabeceraRiesgo from "@/components/salud/CabeceraRiesgo.vue";

const COMPROBACION = {
  banda: "low" as const,
  dias: 76,
  observado: 13,
  intervalo: [7, 23] as readonly [number, number],
  concuerda: true,
};

const PROPS = { riesgo: 18, comprobacion: COMPROBACION };

describe("CabeceraRiesgo", () => {
  it("pinta el sobretítulo, la cifra y lo que ocurrió en días así", () => {
    const wrapper = mount(CabeceraRiesgo, { props: PROPS });

    expect(wrapper.get(".riesgo__sobretitulo").text()).toBe("Riesgo de desregulación");
    expect(wrapper.get(".riesgo__cifra").text()).toBe("18%");
    // El margen y los días van con la cifra: un porcentaje sin saber sobre
    // cuántos días se midió no se puede leer.
    const comprobacion = wrapper.get(".riesgo__confianza").text();
    expect(comprobacion).toContain("En días así ocurrió el");
    expect(comprobacion).toContain("13%");
    expect(comprobacion).toContain("7–23%");
    expect(comprobacion).toContain("76");
  });

  it("lee el riesgo como una sola etiqueta bajo un encabezado de nivel 1", () => {
    const wrapper = mount(CabeceraRiesgo, { props: PROPS });

    const etiqueta = "Riesgo de desregulación: 18 por ciento";
    expect(wrapper.get('[role="group"]').attributes("aria-label")).toBe(etiqueta);
    expect(wrapper.get("h1").attributes("aria-label")).toBe(etiqueta);
    expect(wrapper.get(".riesgo__cifra").attributes("aria-hidden")).toBe("true");
  });

  it("el icono de información abre la explicación y se cierra sola", async () => {
    const wrapper = mount(CabeceraRiesgo, { props: PROPS });

    const boton = wrapper.get(".ayuda__disparador");
    expect(boton.attributes("aria-label")).toBe("Qué significa el riesgo de desregulación");
    expect(boton.attributes("aria-hidden")).toBeUndefined();
    expect(boton.attributes("aria-expanded")).toBe("false");

    await boton.trigger("click");
    expect(boton.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(".ayuda__globo").text()).toContain("proporción de días parecidos a hoy");

    // No exige nada: el mismo botón la vuelve a cerrar.
    await boton.trigger("click");
    expect(wrapper.find(".ayuda__globo").exists()).toBe(false);
  });

  it("sin estimación no escribe un cero ni deja la pastilla", () => {
    const wrapper = mount(CabeceraRiesgo, { props: { riesgo: null, comprobacion: null } });

    expect(wrapper.get(".riesgo__cifra").text()).toBe("—");
    expect(wrapper.find(".riesgo__porciento").exists()).toBe(false);
    expect(wrapper.find(".riesgo__confianza").exists()).toBe(false);
    expect(wrapper.get("h1").attributes("aria-label")).toBe(
      "Riesgo de desregulación: sin estimación todavía",
    );
  });
});
