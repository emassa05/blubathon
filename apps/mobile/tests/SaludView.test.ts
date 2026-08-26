import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { RIESGO_DE_PRUEBA } from "@/theme/riesgo";
import SaludView from "@/views/SaludView.vue";

describe("SaludView", () => {
  it("monta la pantalla completa con los datos del mock", () => {
    const wrapper = mount(SaludView);
    const texto = wrapper.text();

    expect(texto).toContain("Riesgo de desregulación");
    expect(texto).toContain("18%");
    expect(texto).toContain("Nivel de confianza 85%");
    expect(texto).toContain("Mantener la rutina de sueño y un momento tranquilo antes de dormir.");
    expect(texto).toContain("Lo más importante hoy");
    expect(texto).toContain("Horas de sueño");
    expect(texto).toContain("Estrés percibido");
    expect(texto).toContain("Últimos formularios");
    expect(texto).toContain("Lunes 24");
    expect(texto).toContain("Domingo 23");
    expect(texto).toContain("Tienes un formulario este día");
  });

  it("la columna lleva la clase de la banda que le toca al riesgo del mock", () => {
    const wrapper = mount(SaludView);

    expect(wrapper.get(".pantalla__columna").classes()).toContain("faro-banda--bajo");
  });

  it("el botón de prueba recorre las tres bandas y vuelve a empezar", async () => {
    const wrapper = mount(SaludView);
    const columna = () => wrapper.get(".pantalla__columna").classes();
    const boton = wrapper.get(".pantalla__prueba");

    await boton.trigger("click");
    expect(columna()).toContain("faro-banda--medio");
    expect(wrapper.text()).toContain(`${RIESGO_DE_PRUEBA.medio}%`);

    await boton.trigger("click");
    expect(columna()).toContain("faro-banda--alto");
    expect(wrapper.text()).toContain(`${RIESGO_DE_PRUEBA.alto}%`);

    await boton.trigger("click");
    expect(columna()).toContain("faro-banda--bajo");
    expect(wrapper.text()).toContain(`${RIESGO_DE_PRUEBA.bajo}%`);
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
