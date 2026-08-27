import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";

const TEXTO = "Mantener la rutina de sueño y un momento tranquilo antes de dormir.";

describe("TarjetaRecomendacion", () => {
  it("muestra el sobretítulo y la recomendación", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, estado: "lista" as const } },
    });

    expect(wrapper.get("h2").text()).toBe("Recomendación de hoy");
    expect(wrapper.get(".recomendacion__frase").text()).toBe(TEXTO);
  });

  it("ni el fondo ilustrado ni el destello llegan al lector de pantalla", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, estado: "lista" as const } },
    });

    // Da igual si el `aria-hidden` está en el propio SVG o en el envoltorio:
    // lo que se comprueba es que ningún dibujo quede expuesto.
    const svgs = [...wrapper.element.querySelectorAll("svg")];
    expect(svgs.length).toBeGreaterThan(0);
    for (const svg of svgs) {
      expect(svg.closest('[aria-hidden="true"]')).not.toBeNull();
      expect(svg.getAttribute("focusable")).toBe("false");
    }
  });

  it("mientras el RAG redacta enseña los renglones, y al llegar el texto los quita", async () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: "Estamos preparando…", estado: "pendiente" as const } },
    });

    // Tres renglones con la forma del párrafo que viene, y decorativos: lo que
    // se anuncia es la frase de estado, no el hueco.
    expect(wrapper.findAll(".cargando__renglon")).toHaveLength(3);
    expect(wrapper.get(".cargando").attributes("aria-hidden")).toBe("true");
    expect(wrapper.get(".recomendacion__frase").attributes("role")).toBe("status");

    await wrapper.setProps({ recomendacion: { texto: TEXTO, estado: "lista" as const } });

    expect(wrapper.find(".cargando").exists()).toBe(false);
    expect(wrapper.get(".recomendacion__frase").text()).toBe(TEXTO);
  });

  it("una abstención se pinta quieta: no hay nada en camino", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: "No se muestra.", estado: "abstenida" as const } },
    });

    expect(wrapper.find(".cargando").exists()).toBe(false);
  });
});
