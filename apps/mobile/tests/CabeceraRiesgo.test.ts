import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CabeceraRiesgo from "@/components/salud/CabeceraRiesgo.vue";

const PROPS = { riesgo: 18, confianza: 85 };

describe("CabeceraRiesgo", () => {
  it("pinta el sobretítulo, la cifra y el nivel de confianza", () => {
    const wrapper = mount(CabeceraRiesgo, { props: PROPS });

    expect(wrapper.get(".riesgo__sobretitulo").text()).toBe("Riesgo de desregulación");
    expect(wrapper.get(".riesgo__cifra").text()).toBe("18%");
    expect(wrapper.get(".riesgo__confianza").text()).toBe("Nivel de confianza 85%");
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

  it("sin estimación no escribe un cero ni deja la pastilla de confianza", () => {
    const wrapper = mount(CabeceraRiesgo, { props: { riesgo: null, confianza: null } });

    expect(wrapper.get(".riesgo__cifra").text()).toBe("—");
    expect(wrapper.find(".riesgo__porciento").exists()).toBe(false);
    expect(wrapper.find(".riesgo__confianza").exists()).toBe(false);
    expect(wrapper.get("h1").attributes("aria-label")).toBe(
      "Riesgo de desregulación: sin estimación todavía",
    );
  });
});
