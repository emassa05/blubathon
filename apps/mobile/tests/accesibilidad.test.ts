import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fechaDeHoy } from "@/composables/useDiaSeleccionado";
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
 * Pase de axe sobre la pantalla montada, ya con los datos de la API.
 *
 * En jsdom no hay layout, así que axe desactiva por su cuenta las reglas que
 * necesitan píxeles (`color-contrast` entre ellas). Los contrastes se verifican
 * a mano: ver el README.
 */
describe("accesibilidad de la pantalla Salud", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("no deja violaciones de axe", async () => {
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

    const contenedor = document.createElement("div");
    document.body.appendChild(contenedor);

    const wrapper = mount(SaludView, { attachTo: contenedor });
    await flushPromises();

    const resultado = await axe.run(contenedor, {
      runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
    });

    expect(resultado.violations.map((v) => `${v.id}: ${v.nodes.length} nodo(s)`)).toEqual([]);

    wrapper.unmount();
    contenedor.remove();
  });
});
