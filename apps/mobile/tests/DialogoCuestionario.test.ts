import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DialogoCuestionario from "@/components/cuestionario/DialogoCuestionario.vue";
import { olvidarRespuestas, respuestasDe } from "@/estado/respuestas";

const NINO = "00000000-0000-4000-8000-000000000101";
const FECHA = "2026-08-25";

const PLAN = {
  questions: [
    { field_code: "sleep_quality", highlighted: true, reason: "staleness", voi_nats: null },
    { field_code: "sleep_hours", highlighted: false, reason: "canonical_order", voi_nats: null },
    {
      field_code: "activity_participation",
      highlighted: false,
      reason: "canonical_order",
      voi_nats: null,
    },
  ],
  defaults: [{ field_code: "activity_participation", value: 4, window_days: 60, sample_size: 31 }],
  voi_status: "unavailable_model",
  coverage: 0,
};

const ENVIO = {
  submission_id: "11111111-1111-4111-8111-111111111111",
  status: "episode_created",
  prediction_episode_id: "22222222-2222-4222-8222-222222222222",
  recommendation_instance_id: "33333333-3333-4333-8333-333333333333",
  outcome_request_id: null,
};

interface Llamada {
  url: string;
  cuerpo: Record<string, unknown>;
}

const llamadas: Llamada[] = [];

function responder(cuerpo: unknown) {
  return { ok: true, status: 200, json: async () => cuerpo } as unknown as Response;
}

beforeEach(() => {
  llamadas.length = 0;
  olvidarRespuestas();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      llamadas.push({
        url,
        cuerpo: init?.body === undefined ? {} : JSON.parse(String(init.body)),
      });
      return url.endsWith("/form-plan") ? responder(PLAN) : responder(ENVIO);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function abrir() {
  return mount(DialogoCuestionario, { props: { ninoId: NINO, fecha: FECHA } });
}

describe("DialogoCuestionario", () => {
  it("pide el plan del día y separa lo destacado del resto", async () => {
    const wrapper = abrir();
    await flushPromises();

    expect(llamadas[0]?.url).toContain(`/children/${NINO}/form-plan`);
    expect(llamadas[0]?.cuerpo).toEqual({ source: "caregiver_daily", answers: {} });

    const grupos = wrapper.findAll(".grupo__titulo").map((titulo) => titulo.text());
    expect(grupos).toEqual(["Lo primero de hoy", "El resto del día"]);

    const campos = wrapper.findAll("[data-campo]").map((campo) => campo.attributes("data-campo"));
    expect(campos).toEqual(["sleep_quality", "sleep_hours", "activity_participation"]);
  });

  it("es un diálogo con nombre, y Escape lo cierra", async () => {
    const wrapper = abrir();
    await flushPromises();

    const dialogo = wrapper.get('[role="dialog"]');
    expect(dialogo.attributes("aria-modal")).toBe("true");
    expect(wrapper.text()).toContain("Martes, 25 de agosto");

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(wrapper.emitted("cerrar")).toHaveLength(1);
  });

  it("enseña la sugerencia como ayuda y solo la usa si se acepta", async () => {
    const wrapper = abrir();
    await flushPromises();

    const sugerencia = wrapper.get(".sugerencia");
    expect(sugerencia.text()).toContain("Suele responder");
    // La escala sigue vacía: una sugerencia no precarga el control.
    expect(wrapper.findAll(".escala__punto--activo")).toHaveLength(0);

    await sugerencia.get("button").trigger("click");
    expect(wrapper.findAll(".escala__punto--activo")).toHaveLength(1);
  });

  it("avisa cuando la respuesta es una variable crítica", async () => {
    const wrapper = abrir();
    await flushPromises();

    const horas = wrapper.get('[data-campo="sleep_hours"]');
    await horas.get("input").setValue("5");

    expect(horas.text()).toContain("Muy poco sueño");
    expect(wrapper.text()).toContain("Variables críticas");
  });

  it("envía el día con su fecha y guarda lo enviado", async () => {
    const wrapper = abrir();
    await flushPromises();

    await wrapper.get('[data-campo="sleep_quality"]').findAll("button")[0]?.trigger("click");
    await wrapper.get(".pie__enviar").trigger("click");
    await flushPromises();

    const envio = llamadas[1];
    expect(envio?.url).toContain(`/children/${NINO}/forms`);
    expect(envio?.cuerpo).toEqual({
      source: "caregiver_daily",
      local_date: FECHA,
      answers: [{ field_code: "sleep_quality", interaction: "manual", value: "restorative" }],
    });

    expect(wrapper.emitted("enviado")).toHaveLength(1);
    expect(wrapper.text()).toContain("Cuestionario guardado");
    // La copia local se escribe solo después de que la API acepte el envío.
    expect(respuestasDe(NINO, FECHA)).toEqual({ sleep_quality: "restorative" });
  });

  it("sin plan sigue preguntando el catálogo de casa entero", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("sin red");
      }),
    );

    const wrapper = abrir();
    await flushPromises();

    expect(wrapper.text()).toContain("Se preguntan todos los campos");
    // Los 18 campos de casa: el catálogo entero menos `attendance_status`.
    expect(wrapper.findAll("[data-campo]")).toHaveLength(18);
  });
});
