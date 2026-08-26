import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DialogoCuestionario from "@/components/cuestionario/DialogoCuestionario.vue";
import HistorialView from "@/views/HistorialView.vue";
import SaludView from "@/views/SaludView.vue";

/**
 * Pase de axe sobre cada pantalla montada.
 *
 * En jsdom no hay layout, así que axe desactiva por su cuenta las reglas que
 * necesitan píxeles (`color-contrast` entre ellas). Los contrastes se verifican
 * a mano: ver el README.
 */
const REGLAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"];

function responder(cuerpo: unknown) {
  return { ok: true, status: 200, json: async () => cuerpo } as unknown as Response;
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/children") && url.endsWith("/children")) {
        return responder({ children: [{ child_id: "nino-1", display_label: "Ana" }] });
      }
      if (url.includes("/history")) return responder({ child_id: "nino-1", days: [] });
      if (url.endsWith("/form-plan")) {
        return responder({
          questions: [
            { field_code: "sleep_hours", highlighted: true, reason: "staleness", voi_nats: null },
            {
              field_code: "sleep_quality",
              highlighted: false,
              reason: "canonical_order",
              voi_nats: null,
            },
            {
              field_code: "relevant_event_flag",
              highlighted: false,
              reason: "canonical_order",
              voi_nats: null,
            },
            { field_code: "notes", highlighted: false, reason: "canonical_order", voi_nats: null },
          ],
          defaults: [{ field_code: "sleep_hours", value: 9, window_days: 60, sample_size: 20 }],
          voi_status: "unavailable_model",
          coverage: 0,
        });
      }
      return responder({ status: "no_submission_today" });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function violaciones(componente: unknown, props: Record<string, unknown> = {}) {
  const contenedor = document.createElement("div");
  document.body.appendChild(contenedor);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const wrapper = mount(componente as any, { attachTo: contenedor, props });
  await flushPromises();
  const resultado = await axe.run(contenedor, { runOnly: REGLAS });

  wrapper.unmount();
  contenedor.remove();
  return resultado.violations.map((fallo) => `${fallo.id}: ${fallo.nodes.length} nodo(s)`);
}

describe("accesibilidad", () => {
  it("la pantalla de Salud no deja violaciones de axe", async () => {
    expect(await violaciones(SaludView)).toEqual([]);
  });

  it("el historial de cuestionarios no deja violaciones de axe", async () => {
    expect(await violaciones(HistorialView)).toEqual([]);
  });

  it("el diálogo del cuestionario no deja violaciones de axe", async () => {
    expect(
      await violaciones(DialogoCuestionario, { ninoId: "nino-1", fecha: "2026-08-25" }),
    ).toEqual([]);
  });
});
