import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SaludView from "@/views/SaludView.vue";

describe("SaludView", () => {
  it("monta la pantalla completa con los datos del mock", () => {
    const wrapper = mount(SaludView);
    const texto = wrapper.text();

    expect(texto).toContain("86%");
    expect(texto).toContain("Mantener la rutina de sueño y un momento tranquilo antes de dormir.");
    expect(texto).toContain("Lo más importante hoy");
    expect(texto).toContain("Horas de sueño");
    expect(texto).toContain("Estrés percibido");
    expect(texto).toContain("Últimos formularios");
    expect(texto).toContain("Lunes 24");
    expect(texto).toContain("Domingo 23");
    expect(texto).toContain("Tienes un formulario este día");
  });

  it("abre en el día del resumen y navega a los adyacentes", async () => {
    const wrapper = mount(SaludView);
    const etiqueta = () => wrapper.get(".fecha__etiqueta").text();

    expect(etiqueta()).toBe("Martes 25");

    await wrapper.get('[aria-label="Día anterior"]').trigger("click");
    expect(etiqueta()).toBe("Lunes 24");

    await wrapper.get('[aria-label="Día siguiente"]').trigger("click");
    await wrapper.get('[aria-label="Día siguiente"]').trigger("click");
    expect(etiqueta()).toBe("Miércoles 26");
  });

  it("tiene un único h1 y un h2 por sección", () => {
    const wrapper = mount(SaludView);

    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.findAll("h2").map((h) => h.text())).toEqual([
      "Recomendación de hoy",
      "Lo más importante hoy",
      "Últimos formularios",
    ]);
  });
});
