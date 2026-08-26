import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";

const TEXTO = "Mantener la rutina de sueño y un momento tranquilo antes de dormir.";

describe("TarjetaRecomendacion", () => {
  it("muestra el sobretítulo y la recomendación", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, imagen: null } },
    });

    expect(wrapper.get("h2").text()).toBe("Recomendación de hoy");
    expect(wrapper.get(".recomendacion__frase").text()).toBe(TEXTO);
  });

  it("marca el placeholder mientras no haya foto", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, imagen: null } },
    });

    expect(wrapper.get(".recomendacion__foto").classes()).toContain(
      "recomendacion__foto--placeholder",
    );
  });

  it("pinta la foto real cuando llega la URL", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, imagen: "/familia.jpg" } },
    });

    const foto = wrapper.get(".recomendacion__foto");
    expect(foto.classes()).not.toContain("recomendacion__foto--placeholder");
    expect(foto.attributes("style")).toContain("/familia.jpg");
  });
});
