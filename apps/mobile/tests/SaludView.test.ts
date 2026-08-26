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

  it("abre en el día de hoy y navega a los adyacentes", async () => {
    // La pantalla abre en hoy desde que los datos vienen de la API: el día es el
    // que decide qué historial y qué variables críticas se miran.
    const formato = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric" });
    const etiquetaDe = (dias: number): string => {
      const fecha = new Date();
      fecha.setDate(fecha.getDate() + dias);
      const texto = formato.format(fecha);
      return texto.charAt(0).toUpperCase() + texto.slice(1);
    };

    const wrapper = mount(SaludView);
    const etiqueta = () => wrapper.get(".fecha__etiqueta").text();

    expect(etiqueta()).toBe(etiquetaDe(0));

    await wrapper.get('[aria-label="Día anterior"]').trigger("click");
    expect(etiqueta()).toBe(etiquetaDe(-1));

    await wrapper.get('[aria-label="Día siguiente"]').trigger("click");
    await wrapper.get('[aria-label="Día siguiente"]').trigger("click");
    expect(etiqueta()).toBe(etiquetaDe(1));
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

  it("el 'ver más' de los formularios lleva al historial", async () => {
    const wrapper = mount(SaludView);

    await wrapper.get('[aria-label="Ver todos los formularios"]').trigger("click");
    expect(wrapper.emitted("verHistorial")).toHaveLength(1);
  });

  it("el aviso pendiente abre el cuestionario del día que se está mirando", async () => {
    const wrapper = mount(SaludView);
    const hoy = new Date();
    const mes = String(hoy.getMonth() + 1).padStart(2, "0");
    const iso = `${hoy.getFullYear()}-${mes}-${String(hoy.getDate()).padStart(2, "0")}`;

    await wrapper.get(".aviso").trigger("click");
    expect(wrapper.emitted("abrirCuestionario")).toEqual([[iso]]);
  });

  it("cada fila de formulario abre el cuestionario de su día", async () => {
    const wrapper = mount(SaludView);

    const fila = wrapper.findAll(".formulario__fila")[0];
    await fila?.trigger("click");
    // Sin API la tarjeta sigue enseñando el mock, cuyo id ya es la fecha ISO.
    expect(wrapper.emitted("abrirCuestionario")).toEqual([["2026-08-24"]]);
  });
});
