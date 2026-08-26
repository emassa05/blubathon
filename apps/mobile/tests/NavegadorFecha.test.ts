import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import NavegadorFecha from "@/components/salud/NavegadorFecha.vue";

describe("NavegadorFecha", () => {
  it("muestra el día en una región viva", () => {
    const wrapper = mount(NavegadorFecha, { props: { etiqueta: "Martes 25" } });

    const etiqueta = wrapper.get(".fecha__etiqueta");
    expect(etiqueta.text()).toBe("Martes 25");
    expect(etiqueta.attributes("aria-live")).toBe("polite");
  });

  it("los chevrons son botones con nombre accesible", () => {
    const wrapper = mount(NavegadorFecha, { props: { etiqueta: "Martes 25" } });

    const botones = wrapper.findAll("button");
    expect(botones).toHaveLength(2);
    expect(botones.map((boton) => boton.attributes("aria-label"))).toEqual([
      "Día anterior",
      "Día siguiente",
    ]);
  });

  it("emite un evento por cada dirección", async () => {
    const wrapper = mount(NavegadorFecha, { props: { etiqueta: "Martes 25" } });
    const [anterior, siguiente] = wrapper.findAll("button");

    await anterior?.trigger("click");
    await siguiente?.trigger("click");

    expect(wrapper.emitted("diaAnterior")).toHaveLength(1);
    expect(wrapper.emitted("diaSiguiente")).toHaveLength(1);
  });
});
