import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sePuedeContestar } from "@/composables/useDesregulacion";
import { fechaDeHoy } from "@/composables/useDiaSeleccionado";
import { olvidarResultados } from "@/estado/resultados";
import SaludView from "@/views/SaludView.vue";

import {
  ID_NINO_FALSO,
  diaFalso,
  historialFalso,
  idEpisodioFalso,
  instalarServidorFalso,
  planFalso,
  solicitudFalsa,
} from "./servidorFalso";

const HOY = fechaDeHoy();
const CHILD = `/v1/children/${ID_NINO_FALSO}`;

type Solicitud = Parameters<typeof sePuedeContestar>[0];

/**
 * La lista de solicitudes es mutable a propósito: reportar la vuelve a pedir, y
 * lo que hace que una tarjeta se vaya es que la segunda respuesta ya no la
 * traiga. Volver a instalar el doble en medio del test perdería la cuenta de
 * llamadas.
 */
let pendientes: unknown[] = [];

/** La ruta de reporte de cada episodio que un test pueda llegar a contestar. */
const REPORTES = Object.fromEntries(
  ["a", "b"].map((sufijo) => [
    `/v1/prediction-episodes/${idEpisodioFalso(sufijo)}/outcome-reports`,
    {
      outcome_request_id: `4444444${sufijo}-4444-4444-8444-444444444444`,
      resolution_status: "resolved",
    },
  ]),
);

/**
 * @param dias El historial. Por defecto, hoy ya registrado.
 */
function servidor(
  solicitudes: unknown[],
  dias: unknown[] = [diaFalso({ fecha: HOY, probabilidad: 0.18 })],
): void {
  pendientes = solicitudes;
  instalarServidorFalso({
    "/v1/children": { children: [{ child_id: ID_NINO_FALSO, display_label: "Niña demo 1" }] },
    [`${CHILD}/history`]: historialFalso(dias),
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
    "/v1/outcome-requests": {
      get cuerpo() {
        return { items: pendientes };
      },
    },
    ...REPORTES,
  });
}

/** La del envío de ayer: su ventana de 24 h ya cerró y todavía queda plazo. */
const DE_AYER = { finVentanaEnHoras: -2, vencimientoEnHoras: 22, sufijo: "a" };
/** La que abre el envío de hoy: la ventana acaba de empezar. */
const DE_HOY = { finVentanaEnHoras: 22, vencimientoEnHoras: 46, sufijo: "b" };

async function montar() {
  const wrapper = mount(SaludView);
  await flushPromises();
  return wrapper;
}

beforeEach(() => {
  olvidarResultados();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("evento de desregulación", () => {
  describe("cuándo se puede contestar", () => {
    it("con la ventana ya cerrada y todavía en plazo", () => {
      expect(sePuedeContestar(solicitudFalsa(DE_AYER) as Solicitud)).toBe(true);
    });

    it("también con la ventana del objetivo abierta: un `no` resuelve igual", () => {
      expect(sePuedeContestar(solicitudFalsa(DE_HOY) as Solicitud)).toBe(true);
    });

    it("no cuando ya venció el plazo de captura", () => {
      const vencida = solicitudFalsa({ finVentanaEnHoras: -30, vencimientoEnHoras: -6 });
      expect(sePuedeContestar(vencida as Solicitud)).toBe(false);
    });

    it("no cuando no hay ninguna pregunta abierta", () => {
      expect(sePuedeContestar(null)).toBe(false);
    });
  });

  describe("en la pantalla de Salud", () => {
    it("la pregunta se ofrece en la tarjeta, sin tapar la pantalla", async () => {
      servidor([solicitudFalsa(DE_AYER)]);
      const wrapper = await montar();

      // Un solo sitio: la tarjeta del menú. El diálogo que bloqueaba se fue.
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

      const tarjeta = wrapper.get(".resultado");
      // Una sola pregunta, corta, y las dos respuestas. Ni las anclas ni el
      // plazo: el enunciado del contrato es de tres renglones y hay que leerlo
      // entero antes de poder contestar sí o no.
      expect(tarjeta.text()).toContain("¿Ocurrió una desregulación?");
      expect(tarjeta.text()).not.toContain("Necesitó apoyo de una persona");
      expect(tarjeta.text()).not.toContain("para responder");
      // La cara hace el trabajo que hacía el sobretítulo: separar esta tarjeta
      // de las que solo informan. Con las dos, el rótulo sobraba.
      expect(tarjeta.find(".resultado__cara").exists()).toBe(true);
      expect(tarjeta.text()).not.toContain("Resultado pendiente");
      expect(wrapper.find(".resultado__boton--si").exists()).toBe(true);
      expect(wrapper.find(".resultado__boton--no").exists()).toBe(true);
    });

    it("la pregunta que abre el envío de hoy se ofrece ya, sin esperar a mañana", async () => {
      // Es la mitad del arreglo: quien acaba de rellenar el cuestionario ve la
      // pregunta de ese envío. Antes se guardaba hasta que su ventana cerrara y
      // al volver del formulario no aparecía nada.
      servidor([solicitudFalsa(DE_HOY)]);
      const wrapper = await montar();

      expect(wrapper.find(".resultado").exists()).toBe(true);
    });

    it("con el día sin registrar se sigue ofreciendo la de ayer", async () => {
      // La otra mitad: la solicitud es de la persona, no de la fecha, y su plazo
      // corre aunque hoy esté en blanco. Escondiéndola se vencía sin que nadie
      // la hubiera visto.
      servidor([solicitudFalsa(DE_AYER)], []);
      const wrapper = await montar();

      expect(wrapper.find(".resultado").exists()).toBe(true);
      // Y el aviso del formulario sigue estando: las dos cosas quedan por hacer.
      expect(wrapper.find(".aviso").exists()).toBe(true);
    });

    it("dos preguntas abiertas son dos tarjetas, cada una con su ventana", async () => {
      servidor([solicitudFalsa(DE_AYER), solicitudFalsa(DE_HOY)]);
      const wrapper = await montar();

      const tarjetas = wrapper.findAll(".resultado");
      expect(tarjetas).toHaveLength(2);

      // Sin el periodo serían dos tarjetas idénticas palabra por palabra, que se
      // leen como la misma preguntada dos veces.
      const ventanas = wrapper.findAll(".resultado__ventana").map((nodo) => nodo.text());
      expect(ventanas[0]).not.toEqual(ventanas[1]);
      expect(ventanas[0]).toContain("hasta hoy");
      expect(ventanas[1]).toContain("hasta mañana");
    });

    it("al responder una se va ella sola y vuelve a pedir el resumen del día", async () => {
      servidor([solicitudFalsa(DE_AYER), solicitudFalsa(DE_HOY)]);
      const wrapper = await montar();

      const peticiones = () =>
        vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/history")).length;
      const antes = peticiones();

      // Al reportar, la lista se vuelve a pedir; ya sin la que se contestó.
      pendientes = [solicitudFalsa(DE_HOY)];
      await wrapper.get(".resultado__boton--no").trigger("click");
      await flushPromises();

      expect(wrapper.findAll(".resultado")).toHaveLength(1);
      expect(wrapper.get(".resultado__ventana").text()).toContain("hasta mañana");
      expect(peticiones()).toBe(antes + 1);
    });

    it("la última respondida deja la pantalla sin tarjetas", async () => {
      servidor([solicitudFalsa(DE_AYER)]);
      const wrapper = await montar();

      pendientes = [];
      await wrapper.get(".resultado__boton--no").trigger("click");
      await flushPromises();

      expect(wrapper.find(".resultado").exists()).toBe(false);
    });

    it("hojear a otro día no repite la pregunta", async () => {
      // Las solicitudes son de la persona y no de la fecha: sin esto salía la
      // misma tarjeta en todos los días y el navegador parecía no hacer nada.
      servidor([solicitudFalsa(DE_AYER)]);
      const wrapper = await montar();
      expect(wrapper.find(".resultado").exists()).toBe(true);

      await wrapper.get('[aria-label="Día anterior"]').trigger("click");
      await flushPromises();
      expect(wrapper.find(".resultado").exists()).toBe(false);

      // Y al volver a hoy sigue estando: no se ha contestado.
      await wrapper.get('[aria-label="Día siguiente"]').trigger("click");
      await flushPromises();
      expect(wrapper.find(".resultado").exists()).toBe(true);
    });

    it("sin pregunta abierta no aparece nada", async () => {
      servidor([]);
      const wrapper = await montar();

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
      expect(wrapper.find(".resultado").exists()).toBe(false);
    });

    it("no deja violaciones de axe, ni siquiera con dos tarjetas", async () => {
      servidor([solicitudFalsa(DE_AYER), solicitudFalsa(DE_HOY)]);

      const contenedor = document.createElement("div");
      document.body.appendChild(contenedor);
      const wrapper = mount(SaludView, { attachTo: contenedor });
      await flushPromises();

      const resultado = await axe.run(contenedor, {
        runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
      });

      wrapper.unmount();
      contenedor.remove();
      expect(resultado.violations.map((fallo) => fallo.id)).toEqual([]);
    });
  });
});
