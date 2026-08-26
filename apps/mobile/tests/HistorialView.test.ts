import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { hoyIso, semanaDe } from "@/dominio/semana";
import { olvidarRespuestas } from "@/estado/respuestas";
import HistorialView from "@/views/HistorialView.vue";

const NINO = "00000000-0000-4000-8000-000000000101";
const HOY = hoyIso();

const CHILDREN = { children: [{ child_id: NINO, display_label: "Ana" }] };

const HISTORIAL = {
  child_id: NINO,
  days: [
    {
      local_date: HOY,
      submission_id: "11111111-1111-4111-8111-111111111111",
      prediction_episode_id: "22222222-2222-4222-8222-222222222222",
      prediction: { status: "abstained", probability: null, interval: null },
      recommendation: {
        recommendation_instance_id: "33333333-3333-4333-8333-333333333333",
        status: "matched",
        rating: null,
      },
      outcome: { status: "pending", reported_at: null },
    },
  ],
};

function responder(cuerpo: unknown) {
  return { ok: true, status: 200, json: async () => cuerpo } as unknown as Response;
}

beforeEach(() => {
  olvidarRespuestas();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => responder(url.includes("/history") ? HISTORIAL : CHILDREN)),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HistorialView", () => {
  it("abre en la semana en curso, con el día de hoy elegido", async () => {
    const wrapper = mount(HistorialView);
    await flushPromises();

    expect(wrapper.findAll(".dia")).toHaveLength(7);
    expect(wrapper.get(".semana__etiqueta").text()).toContain(semanaDe(HOY, HOY).etiqueta);
    expect(wrapper.get(".dia--elegido").attributes("aria-label")).toContain("hoy");
    // En la semana en curso no hay a dónde volver, así que no hay atajo.
    expect(wrapper.find(".semana__hoy").exists()).toBe(false);
  });

  it("trae el historial del niño que devuelve la lista", async () => {
    const wrapper = mount(HistorialView);
    await flushPromises();

    expect(wrapper.text()).toContain("Ana");
    expect(wrapper.get(".detalle__estado").text()).toBe("Respondido");
    expect(wrapper.text()).toContain("Hay una recomendación guardada para este día.");
    // El track personal se abstiene: se dice, no se enseña un cero.
    expect(wrapper.text()).toContain("El modelo se abstuvo");
  });

  it("cambia de semana y ofrece volver a la actual", async () => {
    const wrapper = mount(HistorialView);
    await flushPromises();

    const anterior = semanaDe(HOY, HOY).dias[0]?.iso ?? HOY;
    await wrapper.get('[aria-label="Semana anterior"]').trigger("click");

    expect(wrapper.get(".semana__etiqueta").text()).not.toContain(semanaDe(anterior, HOY).etiqueta);
    expect(wrapper.find(".semana__hoy").exists()).toBe(true);

    await wrapper.get(".semana__hoy").trigger("click");
    expect(wrapper.get(".dia--elegido").attributes("aria-label")).toContain("hoy");
  });

  it("abre el cuestionario del día que se está mirando", async () => {
    const wrapper = mount(HistorialView);
    await flushPromises();

    await wrapper.get(".detalle__accion").trigger("click");
    expect(wrapper.emitted("abrirCuestionario")).toEqual([[HOY]]);
  });

  it("vuelve a Salud", async () => {
    const wrapper = mount(HistorialView);
    await flushPromises();

    await wrapper.get('[aria-label="Volver a Salud"]').trigger("click");
    expect(wrapper.emitted("volver")).toHaveLength(1);
  });
});
