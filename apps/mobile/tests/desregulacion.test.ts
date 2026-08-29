import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { exigeRespuesta } from "@/composables/useDesregulacion";
import { fechaDeHoy } from "@/composables/useDiaSeleccionado";
import { olvidarResultados } from "@/estado/resultados";
import SaludView from "@/views/SaludView.vue";

import {
  ID_NINO_FALSO,
  diaFalso,
  historialFalso,
  instalarServidorFalso,
  planFalso,
  solicitudFalsa,
} from "./servidorFalso";

const HOY = fechaDeHoy();
const CHILD = `/v1/children/${ID_NINO_FALSO}`;

type Solicitud = Parameters<typeof exigeRespuesta>[0];

const EPISODIO = "22222222-2222-4222-8222-222222222222";

/**
 * La lista de solicitudes es mutable a propósito: reportar la vuelve a pedir, y
 * lo que hace que el diálogo se vaya es que la segunda respuesta ya no la
 * traiga. Volver a instalar el doble en medio del test perdería la cuenta de
 * llamadas.
 */
let pendientes: unknown[] = [];

/**
 * @param dias El historial. Por defecto, hoy ya registrado: es la condición de
 *   la pregunta de cierre, que no se ofrece sobre un día en blanco.
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
    [`/v1/prediction-episodes/${EPISODIO}/outcome-reports`]: {
      outcome_request_id: "44444444-4444-4444-8444-444444444444",
      resolution_status: "resolved",
    },
  });
}

/** Contestable: la ventana de 24 h ya cerró y todavía queda plazo. */
const CONTESTABLE = { finVentanaEnHoras: -2, vencimientoEnHoras: 22 };
/** Todavía no: la ventana sigue abierta, así que un "no" no resolvería nada. */
const EN_CURSO = { finVentanaEnHoras: 6, vencimientoEnHoras: 30 };

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
  describe("cuándo se exige", () => {
    it("con la ventana cerrada y en plazo", () => {
      expect(exigeRespuesta(solicitudFalsa(CONTESTABLE) as Solicitud)).toBe(true);
    });

    it("no mientras la ventana del objetivo sigue abierta", () => {
      expect(exigeRespuesta(solicitudFalsa(EN_CURSO) as Solicitud)).toBe(false);
    });

    it("no cuando ya venció el plazo de captura", () => {
      const vencida = solicitudFalsa({ finVentanaEnHoras: -30, vencimientoEnHoras: -6 });
      expect(exigeRespuesta(vencida as Solicitud)).toBe(false);
    });

    it("no cuando no hay ninguna pregunta abierta", () => {
      expect(exigeRespuesta(null)).toBe(false);
    });
  });

  describe("en la pantalla de Salud", () => {
    it("la pregunta que ya toca se ofrece en la tarjeta, sin tapar la pantalla", async () => {
      servidor([solicitudFalsa(CONTESTABLE)]);
      const wrapper = await montar();

      // Un solo sitio: la tarjeta del menú. El diálogo que bloqueaba se fue,
      // porque con el día ya registrado solo se ponía delante justo al volver
      // del formulario.
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

      const tarjeta = wrapper.get(".resultado");
      // Una sola pregunta, corta, y las dos respuestas. Ni las anclas ni el
      // plazo: el enunciado del contrato es de tres renglones y hay que leerlo
      // entero antes de poder contestar sí o no.
      expect(tarjeta.text()).toContain("¿Ocurrió una desregulación en las últimas 24 horas?");
      expect(tarjeta.text()).not.toContain("Necesitó apoyo de una persona");
      expect(tarjeta.text()).not.toContain("para responder");
      expect(wrapper.find(".resultado__boton--si").exists()).toBe(true);
      expect(wrapper.find(".resultado__boton--no").exists()).toBe(true);
    });

    it("al responder se va y vuelve a pedir el resumen del día", async () => {
      servidor([solicitudFalsa(CONTESTABLE)]);
      const wrapper = await montar();

      const peticiones = () =>
        vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/history")).length;
      const antes = peticiones();

      // Al reportar, la lista se vuelve a pedir; ya sin la solicitud abierta.
      pendientes = [];
      await wrapper.get(".resultado__boton--no").trigger("click");
      await flushPromises();

      expect(wrapper.find(".resultado").exists()).toBe(false);
      expect(peticiones()).toBe(antes + 1);
    });

    it("la pregunta de un episodio recién abierto todavía no se hace", async () => {
      // Es la que abre el propio envío de hoy: su ventana acaba de empezar, así
      // que "¿ocurrió en las últimas 24 horas?" no significa nada todavía.
      //
      // Preguntarla al momento era la mitad de un problema real: se contestaba
      // la de ayer y acto seguido salía esta, palabra por palabra igual, y se
      // leía como la misma pregunta dos veces. Le toca mañana.
      servidor([solicitudFalsa(EN_CURSO)]);
      const wrapper = await montar();

      expect(wrapper.find(".resultado").exists()).toBe(false);
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    });

    it("con el día sin registrar no se ofrece el cierre, aunque esté abierto", async () => {
      // La solicitud es de ayer y sigue abierta, pero hoy está en blanco:
      // primero se registra el día y después se cierra el anterior.
      servidor([solicitudFalsa(CONTESTABLE)], []);

      const wrapper = await montar();

      // Ni la tarjeta ni el diálogo, que es el que además taparía el camino
      // hacia el propio formulario que hay que rellenar.
      expect(wrapper.find(".resultado").exists()).toBe(false);
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

      // Y el aviso del formulario sí: es lo único que toca hacer ahora.
      expect(wrapper.find(".aviso").exists()).toBe(true);
    });

    it("sin pregunta abierta no aparece nada", async () => {
      servidor([]);
      const wrapper = await montar();

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
      expect(wrapper.find(".resultado").exists()).toBe(false);
    });

    it("no deja violaciones de axe", async () => {
      servidor([solicitudFalsa(CONTESTABLE)]);

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
