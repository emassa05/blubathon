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

  it("el icono de información es un botón con nombre propio que emite masInfo", async () => {
    const wrapper = mount(CabeceraRiesgo, { props: PROPS });

    const boton = wrapper.get(".riesgo__info");
    expect(boton.attributes("aria-label")).toBe("Qué significa el riesgo de desregulación");
    expect(boton.attributes("aria-hidden")).toBeUndefined();

    await boton.trigger("click");
    expect(wrapper.emitted("masInfo")).toHaveLength(1);
  });
});
