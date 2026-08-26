import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CabeceraBienestar from "@/components/salud/CabeceraBienestar.vue";

describe("CabeceraBienestar", () => {
  it("pinta el sobretítulo y la cifra", () => {
    const wrapper = mount(CabeceraBienestar, { props: { porcentaje: 86 } });

    expect(wrapper.get(".bienestar__sobretitulo").text()).toBe("Bienestar de hoy");
    expect(wrapper.get(".bienestar__cifra").text()).toBe("86%");
  });

  it("las lee como una sola etiqueta bajo un encabezado de nivel 1", () => {
    const wrapper = mount(CabeceraBienestar, { props: { porcentaje: 86 } });

    const grupo = wrapper.get('[role="group"]');
    expect(grupo.attributes("aria-label")).toBe("Bienestar de hoy: 86 por ciento");
    expect(wrapper.get("h1").attributes("aria-label")).toBe("Bienestar de hoy: 86 por ciento");
    expect(wrapper.get(".bienestar__cifra").attributes("aria-hidden")).toBe("true");
  });
});
