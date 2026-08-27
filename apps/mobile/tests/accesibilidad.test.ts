import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DialogoCuestionario from "@/components/cuestionario/DialogoCuestionario.vue";
import { fechaDeHoy } from "@/composables/useDiaSeleccionado";
import HistorialView from "@/views/HistorialView.vue";
import SaludView from "@/views/SaludView.vue";

import {
  ID_NINO_FALSO,
  diaFalso,
  historialFalso,
  instalarServidorFalso,
  planFalso,
} from "./servidorFalso";

const HOY = fechaDeHoy();
const CHILD = `/v1/children/${ID_NINO_FALSO}`;

/**
 * Pase de axe sobre cada pantalla montada, ya con los datos de la API.
 *
 * En jsdom no hay layout, así que axe desactiva por su cuenta las reglas que
 * necesitan píxeles (`color-contrast` entre ellas). Los contrastes se verifican
 * a mano: ver el README.
 */
const REGLAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"];

beforeEach(() => {
  instalarServidorFalso({
    "/v1/children": { children: [{ child_id: ID_NINO_FALSO, display_label: "Niña demo 1" }] },
    [`${CHILD}/history`]: historialFalso([
      diaFalso({ fecha: HOY, probabilidad: 0.18, intervalo: [0.1, 0.25] }),
    ]),
    [`${CHILD}/form-plan`]: planFalso(["sleep_quality"]),
    [`${CHILD}/recommendations/today`]: {
      status: "matched",
      risk_band: "low",
      recommendation_instance_id: "33333333-3333-4333-8333-333333333333",
      action_text_es: "Mantener la rutina de sueño.",
      citations: [],
      abstention_reason: null,
      rating: null,
    },
  });
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
    expect(await violaciones(DialogoCuestionario, { ninoId: ID_NINO_FALSO, fecha: HOY })).toEqual(
      [],
    );
  });
});
