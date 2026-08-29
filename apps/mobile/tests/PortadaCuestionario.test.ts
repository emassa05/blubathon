import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import PortadaCuestionario from "@/components/cuestionario/PortadaCuestionario.vue";
import { ANIMOS_BUENOS } from "@/components/icons/mood/animos";

/** Los rellenos de las caras que **no** pueden salir: triste, mareada y neutra. */
const CARAS_MALAS = ["#D96848", "#7B7EC8", "#A89080"];

const BASE = { idTitulo: "titulo-1", titulo: "Martes, 25 de agosto" };

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PortadaCuestionario", () => {
  it("dibuja un punto por paso y alarga el que toca", () => {
    const wrapper = mount(PortadaCuestionario, { props: { ...BASE, paso: 2, pasos: 4 } });

    const puntos = wrapper.findAll(".portada__punto");
    expect(puntos).toHaveLength(4);
    expect(puntos.filter((punto) => punto.classes("portada__punto--actual"))).toHaveLength(1);
    expect(puntos[1]?.classes()).toContain("portada__punto--actual");

    // Los puntos no se cuentan con lector: por dónde vas se dice con palabras.
    expect(wrapper.text()).toContain("Paso 2 de 4");
  });

  it("el título lleva el id con el que el diálogo se nombra", () => {
    const wrapper = mount(PortadaCuestionario, {
      props: { ...BASE, sobretitulo: "Cuestionario diario", pasos: 3 },
    });

    const titulo = wrapper.get("#titulo-1");
    expect(titulo.text()).toBe("Martes, 25 de agosto");
    expect(wrapper.text()).toContain("Cuestionario diario");
  });

  it("sin pasos no hay progreso que enseñar", () => {
    const wrapper = mount(PortadaCuestionario, { props: { ...BASE, pasos: 0 } });

    expect(wrapper.findAll(".portada__punto")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("Paso");
    // Pero la cara sigue: la portada no desaparece en el repaso ni al guardar.
    expect(wrapper.find(".portada__cara").exists()).toBe(true);
  });

  it("la cara sale al azar y nunca es una de las malas", () => {
    // Se barre el sorteo entero: cualquier valor de `Math.random` tiene que
    // caer en una de las buenas, no solo el primero y el último.
    for (let cual = 0; cual < ANIMOS_BUENOS.length; cual += 1) {
      vi.spyOn(Math, "random").mockReturnValue(cual / ANIMOS_BUENOS.length);

      const cara = mount(PortadaCuestionario, { props: BASE }).get(".portada__cara").html();
      for (const mala of CARAS_MALAS) expect(cara).not.toContain(mala);
    }
  });

  it("cambia de cara al cambiar de paso, y nunca repite la que había", async () => {
    const wrapper = mount(PortadaCuestionario, { props: { ...BASE, paso: 1, pasos: 3 } });
    const primera = wrapper.get(".portada__cara").html();

    await wrapper.setProps({ paso: 2 });
    const segunda = wrapper.get(".portada__cara").html();
    expect(segunda).not.toBe(primera);

    // Y volver atrás también sortea: lo que cambia es el paso, no la dirección.
    await wrapper.setProps({ paso: 1 });
    expect(wrapper.get(".portada__cara").html()).not.toBe(segunda);
  });
});
