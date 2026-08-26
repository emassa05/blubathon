import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TarjetaFormularios from "@/components/salud/TarjetaFormularios.vue";
import type { RegistroFormulario } from "@/types/salud";

const REGISTROS: readonly RegistroFormulario[] = [
  { id: "2026-08-24", dia: "Lunes 24", estado: "respondido" },
  { id: "2026-08-23", dia: "Domingo 23", estado: "sin-responder" },
];

describe("TarjetaFormularios", () => {
  it("lista cada día con su estado escrito, no solo con el color", () => {
    const wrapper = mount(TarjetaFormularios, { props: { registros: REGISTROS } });

    const filas = wrapper.findAll("li");
    expect(filas).toHaveLength(2);
    expect(filas[0]?.text()).toContain("Lunes 24");
    expect(filas[0]?.text()).toContain("Respondido");
    expect(filas[1]?.text()).toContain("Domingo 23");
    expect(filas[1]?.text()).toContain("Sin responder");
  });

  it("distingue el punto por estado", () => {
    const wrapper = mount(TarjetaFormularios, { props: { registros: REGISTROS } });

    const puntos = wrapper.findAll(".formulario__punto");
    expect(puntos[0]?.classes()).toContain("formulario__punto--respondido");
    expect(puntos[1]?.classes()).toContain("formulario__punto--sin-responder");
  });

  it("la acción es un botón con nombre accesible y emite verMas", async () => {
    const wrapper = mount(TarjetaFormularios, { props: { registros: REGISTROS } });

    const accion = wrapper.get("button");
    expect(accion.text()).toBe("ver más");
    expect(accion.attributes("aria-label")).toBe("Ver todos los formularios");

    await accion.trigger("click");
    expect(wrapper.emitted("verMas")).toHaveLength(1);
  });
});
