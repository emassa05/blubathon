import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";

const TEXTO = "Mantener la rutina de sueño y un momento tranquilo antes de dormir.";

describe("TarjetaRecomendacion", () => {
  it("muestra el sobretítulo y la recomendación", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO } },
    });

    expect(wrapper.get("h2").text()).toBe("Recomendación de hoy");
    expect(wrapper.get(".recomendacion__frase").text()).toBe(TEXTO);
  });

  it("ni el fondo ilustrado ni el destello llegan al lector de pantalla", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO } },
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
});
