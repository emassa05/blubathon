import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import BarraEstado from "@/components/salud/BarraEstado.vue";

describe("BarraEstado", () => {
  it("muestra la hora como un <time> con datetime", () => {
    const wrapper = mount(BarraEstado, { props: { hora: "18:09", bateria: 58 } });

    const hora = wrapper.get("time");
    expect(hora.text()).toBe("18:09");
    expect(hora.attributes("datetime")).toBe("18:09");
  });

  it("anuncia la batería con una etiqueta legible y rellena la pastilla", () => {
    const wrapper = mount(BarraEstado, { props: { hora: "18:09", bateria: 58 } });

    const bateria = wrapper.get('[role="img"]');
    expect(bateria.attributes("aria-label")).toBe("Batería al 58 por ciento");
    expect(bateria.text()).toBe("58");
    expect(wrapper.get(".barra__relleno").attributes("style")).toContain("width: 58%");
  });
});
