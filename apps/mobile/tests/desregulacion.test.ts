import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { nextTick } from "vue";
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

function servidor(solicitudes: unknown[]): void {
  pendientes = solicitudes;
  instalarServidorFalso({
    "/v1/children": { children: [{ child_id: ID_NINO_FALSO, display_label: "Niña demo 1" }] },
    [`${CHILD}/history`]: historialFalso([diaFalso({ fecha: HOY, probabilidad: 0.18 })]),
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
    it("tapa la pantalla hasta que se responde", async () => {
      servidor([solicitudFalsa(CONTESTABLE)]);
      const wrapper = await montar();

      const dialogo = wrapper.get('[role="dialog"]');
      expect(dialogo.attributes("aria-modal")).toBe("true");
      // Una sola pregunta, corta, y las dos respuestas. Ni las anclas ni el
      // plazo: el enunciado del contrato es de tres renglones y hay que leerlo
      // entero antes de poder contestar sí o no.
      expect(dialogo.text()).toContain("¿Ocurrió una desregulación en las últimas 24 horas?");
      expect(dialogo.text()).not.toContain("Necesitó apoyo de una persona");
      expect(dialogo.text()).not.toContain("para responder");
    });

    it("no se puede cerrar sin contestar: ni aspa, ni velo, ni Escape", async () => {
      servidor([solicitudFalsa(CONTESTABLE)]);
      const wrapper = await montar();

      // Ni aspa ni velo pulsable: no es que estén desactivados, es que no
      // existen. Un control que no lleva a ningún sitio no debería anunciarse.
      expect(wrapper.find(".dialogo__cerrar").exists()).toBe(false);
      expect(wrapper.find("button.velo__fondo").exists()).toBe(false);

      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      await nextTick();
      expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
    });

    it("al responder se va y vuelve a pedir el resumen del día", async () => {
      servidor([solicitudFalsa(CONTESTABLE)]);
      const wrapper = await montar();

      const peticiones = () =>
        vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/history")).length;
      const antes = peticiones();

      // Al reportar, la lista se vuelve a pedir; ya sin la solicitud abierta.
      pendientes = [];
      await wrapper.get(".desregulacion__boton--no").trigger("click");
      await flushPromises();

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
      expect(peticiones()).toBe(antes + 1);
    });

    it("con la ventana abierta informa en la tarjeta y deja pasar", async () => {
      servidor([solicitudFalsa(EN_CURSO)]);
      const wrapper = await montar();

      // Sigue sin bloquear la pantalla: eso no cambia, y es lo que impide que
      // "sí, ocurrió" sea la única salida de un diálogo obligatorio.
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

      // "Sí, ocurrió" cuenta desde el primer momento: la ventana empieza en el
      // propio envío, así que ese sí se puede pulsar.
      expect(wrapper.find(".resultado__boton--si").exists()).toBe(true);
    });

    it("con la ventana abierta no ofrece el 'no', que no resolvería nada", async () => {
      servidor([solicitudFalsa(EN_CURSO)]);
      const wrapper = await montar();

      // El backend acepta ese reporte —201, `early`— y lo deja pendiente: la
      // solicitud sigue abierta, la tarjeta no se va y la racha no se mueve.
      // Ofrecerlo era ofrecer un botón que no hacía nada.
      expect(wrapper.find(".resultado__boton--no").exists()).toBe(false);

      // Y se dice por qué, en vez de dejar el hueco: un botón que falta sin
      // explicación se lee igual de roto que uno que no responde.
      expect(wrapper.get(".resultado__espera").text()).toContain("ventana de 24 h");
    });

    it("el 'no' que no resolvería no llega a salir a la red", async () => {
      servidor([solicitudFalsa(EN_CURSO)]);
      const wrapper = await montar();

      const reportes = () =>
        vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/outcome-reports"))
          .length;

      // La tarjeta ya no lo ofrece; esto comprueba la otra mitad, que el
      // composable tampoco lo mandaría si alguien llegara por otro camino.
      expect(reportes()).toBe(0);
      expect(wrapper.find(".resultado__boton--no").exists()).toBe(false);
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
