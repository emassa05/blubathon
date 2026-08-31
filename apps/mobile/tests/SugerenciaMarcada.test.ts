import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { FieldCode, ValorCampo } from "@/api/contrato";
import CampoCuestionario from "@/components/cuestionario/CampoCuestionario.vue";

function montar(campo: FieldCode, sugerido: ValorCampo, mostrar = true) {
  return mount(CampoCuestionario, {
    props: {
      pregunta: { field_code: campo, highlighted: false, reason: "canonical_order", voi_nats: null },
      sugerencia: { field_code: campo, value: sugerido, window_days: 60, sample_size: 31 },
      mostrarSugerencia: mostrar,
    },
  });
}

/** Las opciones marcadas ahora mismo, por su etiqueta. */
function marcadas(wrapper: ReturnType<typeof montar>): string[] {
  return wrapper
    .findAll("button.opcion")
    .filter((boton) => boton.attributes("aria-pressed") === "true")
    .map((boton) => boton.text());
}

describe("la sugerencia en el repaso", () => {
  it("sale ya marcada, sin botón que aceptarla", () => {
    const wrapper = montar("food_changes", false);

    expect(marcadas(wrapper)).toEqual(["No"]);
    // El botón de aceptar desapareció: dejarla como está ya no pide un gesto.
    expect(wrapper.text()).not.toContain("Usar");
    // Y sigue diciendo de dónde sale, que es lo que la separa de una respuesta.
    expect(wrapper.get(".sugerencia").text()).toContain("Suele responder");
  });

  it("marcarla no la guarda: el borrador sigue sin tocarse", () => {
    const wrapper = montar("food_changes", false);

    // Nada emitido: lo que viaja lo decide `aplicarSugerencias` al guardar.
    expect(wrapper.emitted("responder")).toBeUndefined();
    expect(wrapper.get("fieldset").attributes("data-contestada")).toBe("false");
  });

  it("elegir otra cosa manda como edición de la sugerencia", async () => {
    const wrapper = montar("food_changes", false);

    await wrapper.findAll("button.opcion")[0]!.trigger("click");

    expect(wrapper.emitted("responder")).toEqual([[true, "edit_default"]]);
  });

  it("con escala, marca el punto sugerido y enseña su ancla", () => {
    const wrapper = montar("activity_participation", 4);

    const activo = wrapper.findAll(".escala__punto--activo");
    expect(activo).toHaveLength(1);
    expect(activo[0]!.text()).toBe("4");
    expect(wrapper.get(".escala__ancla").text().length).toBeGreaterThan(0);
  });

  it("mientras se contesta no se marca nada: la sugerencia no se ve", () => {
    const wrapper = montar("food_changes", false, false);

    expect(marcadas(wrapper)).toEqual([]);
    expect(wrapper.find(".sugerencia").exists()).toBe(false);
  });
});
