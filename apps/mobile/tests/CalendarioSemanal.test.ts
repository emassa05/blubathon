import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CalendarioSemanal from "@/components/historial/CalendarioSemanal.vue";
import { resumenDeDia, type CeldaCalendario } from "@/dominio/dia";
import { semanaDe } from "@/dominio/semana";

const HOY = "2026-08-26";

function celdas(): CeldaCalendario[] {
  return semanaDe(HOY, HOY).dias.map((dia) => ({
    dia,
    resumen: resumenDeDia(
      dia.iso,
      HOY,
      dia.iso === "2026-08-24"
        ? { local_date: dia.iso, submission_id: "s1", prediction_episode_id: "e1" }
        : undefined,
      dia.iso === "2026-08-25" ? { sleep_hours: 5 } : undefined,
    ),
  }));
}

describe("CalendarioSemanal", () => {
  it("pinta los siete días de la semana", () => {
    const wrapper = mount(CalendarioSemanal, {
      props: { celdas: celdas(), seleccionado: HOY },
    });

    expect(wrapper.findAll("li")).toHaveLength(7);
  });

  it("dice en palabras lo que la celda dice en color", () => {
    const wrapper = mount(CalendarioSemanal, {
      props: { celdas: celdas(), seleccionado: HOY },
    });

    const botones = wrapper.findAll("button");
    expect(botones[0]?.attributes("aria-label")).toBe("Lunes 24, cuestionario respondido");
    expect(botones[1]?.attributes("aria-label")).toBe(
      "Martes 25, cuestionario respondido, 1 variable crítica",
    );
    expect(botones[2]?.attributes("aria-label")).toBe("Miércoles 26, sin cuestionario, hoy");
    expect(botones[6]?.attributes("aria-label")).toBe("Domingo 30, todavía no ha llegado");
  });

  it("no deja pulsar un día que todavía no ha llegado", () => {
    const wrapper = mount(CalendarioSemanal, {
      props: { celdas: celdas(), seleccionado: HOY },
    });

    const botones = wrapper.findAll("button");
    expect(botones[2]?.attributes("disabled")).toBeUndefined();
    expect(botones[6]?.attributes("disabled")).toBeDefined();
  });

  it("marca el día abierto y emite el que se elige", async () => {
    const wrapper = mount(CalendarioSemanal, {
      props: { celdas: celdas(), seleccionado: HOY },
    });

    const botones = wrapper.findAll("button");
    expect(botones[2]?.classes()).toContain("dia--elegido");
    expect(botones[2]?.attributes("aria-pressed")).toBe("true");

    await botones[0]?.trigger("click");
    expect(wrapper.emitted("seleccionar")).toEqual([["2026-08-24"]]);
  });

  it("señala aparte los días con variables críticas", () => {
    const wrapper = mount(CalendarioSemanal, {
      props: { celdas: celdas(), seleccionado: HOY },
    });

    expect(wrapper.findAll(".dia__critica")).toHaveLength(1);
  });
});
