import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
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

/**
 * Lo que tarda un diálogo en irse antes de avisar de que ya se puede desmontar.
 * `DialogoModal` lo hace con un temporizador, no con el final de la transición
 * CSS, justo para que aquí se pueda esperar una cifra y no un fotograma.
 */
const MS_CIERRE = 210;

async function esperarCierre(): Promise<void> {
  await new Promise((listo) => setTimeout(listo, MS_CIERRE + 20));
  await flushPromises();
}

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

/** Las preguntas visibles ahora mismo, en orden. */
function camposVisibles(wrapper: ReturnType<typeof abrir>): (string | undefined)[] {
  return wrapper.findAll("[data-campo]").map((campo) => campo.attributes("data-campo"));
}

/** Pasa al bloque siguiente del mismo formulario. */
async function siguiente(wrapper: ReturnType<typeof abrir>) {
  const pasos = wrapper.findAll(".paginador__paso");
  await pasos[pasos.length - 1]?.trigger("click");
  await flushPromises();
}

describe("DialogoCuestionario", () => {
  it("pide el plan del día y mantiene lo destacado por delante", async () => {
    const wrapper = abrir();
    await flushPromises();

    expect(llamadas[0]?.url).toContain(`/children/${NINO}/form-plan`);
    expect(llamadas[0]?.cuerpo).toEqual({ source: "caregiver_daily", answers: {} });

    // Un solo formulario, sin índice ni bloques temáticos que abrir.
    expect(wrapper.findAll("[data-categoria]")).toHaveLength(0);

    // Las tres preguntas del plan caben en un paso, y `sleep_quality` va
    // delante porque es la destacada: paginar no toca el orden del plan.
    expect(camposVisibles(wrapper)).toEqual([
      "sleep_quality",
      "sleep_hours",
      "activity_participation",
    ]);
    expect(wrapper.text()).toContain("Paso 1 de 1");
  });

  it("recorre el formulario de tres en tres, adelante y atrás", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("sin red");
      }),
    );

    const wrapper = abrir();
    await flushPromises();

    // Sin plan se preguntan los 18 campos de casa: 6 pasos de 3.
    expect(wrapper.text()).toContain("Paso 1 de 6");
    const primero = camposVisibles(wrapper);
    expect(primero).toHaveLength(3);

    // "Anterior" está apagado en el primero, no escondido.
    const [atras] = wrapper.findAll(".paginador__paso");
    expect(atras?.attributes("disabled")).toBeDefined();

    await siguiente(wrapper);
    expect(wrapper.text()).toContain("Paso 2 de 6");
    const segundo = camposVisibles(wrapper);
    expect(segundo).toHaveLength(3);
    expect(segundo).not.toEqual(primero);

    // Y volver devuelve exactamente las mismas tres preguntas.
    await wrapper.findAll(".paginador__paso")[0]?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Paso 1 de 6");
    expect(camposVisibles(wrapper)).toEqual(primero);
  });

  it("los campos numéricos salen en 1 y cuentan como respondidos", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("sin red");
      }),
    );

    const wrapper = abrir();
    await flushPromises();

    // `sleep_hours` es el primero del orden canónico y es continuo: su control
    // es una cifra, y nace en 1 —ni vacío ni 0.
    const horas = wrapper.get('[data-campo="sleep_hours"]');
    expect((horas.get("input").element as HTMLInputElement).value).toBe("1");

    // Los tres numéricos de casa cuentan desde el principio.
    expect(wrapper.get(".pie__cuenta").text()).toContain("3");
  });

  it("es un diálogo con nombre, y Escape lo cierra", async () => {
    const wrapper = abrir();
    await flushPromises();

    const dialogo = wrapper.get('[role="dialog"]');
    expect(dialogo.attributes("aria-modal")).toBe("true");
    expect(wrapper.text()).toContain("Martes, 25 de agosto");

    // La hoja está en su sitio mientras el diálogo está abierto.
    expect(wrapper.get(".velo").classes()).toContain("velo--dentro");

    /*
     * El diálogo se va antes de avisar. Y para poder irse tiene que seguir en el
     * DOM: lo que cambia al pulsar `Esc` es que pierde `velo--dentro` —o sea que
     * la hoja arranca a bajar—, no que desaparezca. Quitarla en ese momento
     * dejaría la salida sin nada que animar, que es justo lo que pasaba cuando
     * el movimiento dependía de las clases de `<Transition>`.
     */
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await nextTick();
    expect(wrapper.get(".velo").classes()).not.toContain("velo--dentro");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
    expect(wrapper.emitted("cerrar")).toBeUndefined();

    // Y solo cuando ha terminado de bajar avisa al padre, que es quien desmonta.
    await esperarCierre();
    expect(wrapper.emitted("cerrar")).toHaveLength(1);
  });

  it("es un diálogo y nada más: el cuestionario no abre otro encima", async () => {
    const wrapper = abrir();
    await flushPromises();

    expect(wrapper.findAll('[role="dialog"]')).toHaveLength(1);

    // Pasar de bloque no abre ni cierra nada: es el mismo formulario.
    await siguiente(wrapper);
    expect(wrapper.findAll('[role="dialog"]')).toHaveLength(1);
    expect(wrapper.emitted("cerrar")).toBeUndefined();
  });

  it("las sugerencias no se ven mientras se contesta", async () => {
    const wrapper = abrir();
    await flushPromises();

    // `activity_participation` tiene sugerencia en el plan y aun así no hay
    // ninguna caja de ayuda: el formulario no crece por ellas.
    expect(wrapper.find(".sugerencia").exists()).toBe(false);
    // Y el control sigue vacío: esconder la sugerencia no es precargarla.
    expect(wrapper.findAll(".escala__punto--activo")).toHaveLength(0);
  });

  it("al guardar enseña qué se va a enviar por ti y pregunta antes de hacerlo", async () => {
    const wrapper = abrir();
    await flushPromises();

    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    // No ha enviado nada todavía: solo estaba la llamada al plan.
    expect(llamadas).toHaveLength(1);

    // La lista es de solo lectura —pregunta, flecha, valor— y no trae ni un
    // control: editar se hace volviendo al formulario, no desde aquí.
    const resumen = wrapper.get(".sugeridas");
    expect(resumen.text()).toContain("Participación en actividades");
    expect(resumen.text()).toContain("4");
    expect(resumen.findAll("button, input, textarea, select")).toHaveLength(0);

    expect(wrapper.text()).toContain("¿Quieres cambiar alguna antes de guardar?");
  });

  it("rechazar la revisión envía las sugeridas tal cual, como accept_default", async () => {
    const wrapper = abrir();
    await flushPromises();

    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    // "No, guardar así" es el botón lleno del pie de la revisión.
    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    const envio = llamadas[1];
    expect(envio?.url).toContain(`/children/${NINO}/forms`);
    // La sugerencia viaja con el mismo `accept_default` que usaba el botón
    // "usar esta respuesta" de cada campo: el cuerpo no cambia de forma.
    expect(envio?.cuerpo.answers).toContainEqual({
      field_code: "activity_participation",
      interaction: "accept_default",
      value: 4,
    });
    expect(wrapper.text()).toContain("Cuestionario guardado");
  });

  it("aceptar la revisión devuelve al formulario con solo esas preguntas y su sugerencia", async () => {
    const wrapper = abrir();
    await flushPromises();

    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    await wrapper.get(".pie .boton--secundario").trigger("click");
    await flushPromises();

    // Solo la que quedó sugerida, y ahora sí con su caja de ayuda.
    expect(camposVisibles(wrapper)).toEqual(["activity_participation"]);
    expect(wrapper.get(".sugerencia").text()).toContain("Suele responder");
    // Sin paginador: son todas las que hay que revisar.
    expect(wrapper.findAll(".paginador__paso")).toHaveLength(0);

    // Cambiarla la manda como edición de la sugerencia, no como manual.
    await wrapper.get('[data-campo="activity_participation"] .escala__punto').trigger("click");
    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    expect(llamadas[1]?.cuerpo.answers).toContainEqual({
      field_code: "activity_participation",
      interaction: "edit_default",
      value: 1,
    });
  });

  it("no avisa de nada al marcar un valor bajo", async () => {
    const wrapper = abrir();
    await flushPromises();

    const horas = wrapper.get('[data-campo="sleep_hours"]');
    await horas.get("input").setValue("5");

    // 5 h dispara "Muy poco sueño" en `dominio/criticas`, que el historial
    // sigue usando. El cuestionario ya no: se contesta sin que la pantalla
    // opine de lo que se contesta.
    expect(horas.text()).not.toContain("Muy poco sueño");
    expect(wrapper.text()).not.toContain("Variables críticas");
  });

  it("envía el día con su fecha y guarda lo enviado", async () => {
    const wrapper = abrir();
    await flushPromises();

    await wrapper.get('[data-campo="sleep_quality"]').findAll("button")[0]?.trigger("click");

    // `sleep_hours` es el único numérico que pide el plan: cuenta con su 1 de
    // salida. Los otros dos del catálogo se sembraron al montar y se retiraron
    // en cuanto el plan dijo que hoy no se preguntan.
    expect(wrapper.get(".pie__cuenta").text()).toContain("2");

    // Guardar pasa por la revisión, porque `activity_participation` quedó con
    // su sugerencia sin tocar; "No, guardar así" es la salida corta.
    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();
    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    const envio = llamadas[1];
    expect(envio?.url).toContain(`/children/${NINO}/forms`);
    // El cuerpo tiene exactamente la forma de siempre. Lo único que se suma es
    // la sugerencia aceptada, que antes se aceptaba campo a campo.
    expect(envio?.cuerpo).toEqual({
      source: "caregiver_daily",
      local_date: FECHA,
      answers: [
        { field_code: "sleep_hours", interaction: "manual", value: 1 },
        { field_code: "sleep_quality", interaction: "manual", value: "restorative" },
        { field_code: "activity_participation", interaction: "accept_default", value: 4 },
      ],
    });

    expect(wrapper.emitted("enviado")).toHaveLength(1);
    expect(wrapper.text()).toContain("Cuestionario guardado");
    // La copia local se escribe solo después de que la API acepte el envío.
    expect(respuestasDe(NINO, FECHA)).toEqual({
      sleep_hours: 1,
      sleep_quality: "restorative",
      activity_participation: 4,
    });
  });

  it("sin sugerencias pendientes guarda directo, sin paso de revisión", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        llamadas.push({
          url,
          cuerpo: init?.body === undefined ? {} : JSON.parse(String(init.body)),
        });
        // El mismo plan, sin `defaults`.
        return url.endsWith("/form-plan") ? responder({ ...PLAN, defaults: [] }) : responder(ENVIO);
      }),
    );

    const wrapper = abrir();
    await flushPromises();

    await wrapper.get(".pie .boton--principal").trigger("click");
    await flushPromises();

    expect(wrapper.find(".sugeridas").exists()).toBe(false);
    expect(wrapper.text()).toContain("Cuestionario guardado");
  });

  it("el (?) de la cabecera explica el cuestionario sin bloquearlo", async () => {
    const wrapper = abrir();
    await flushPromises();

    const boton = wrapper.get(".ayuda__disparador");
    expect(boton.attributes("aria-label")).toBe("Cómo funciona el cuestionario diario");

    await boton.trigger("click");
    expect(wrapper.get(".ayuda__globo").text()).toContain("No hace falta responder todo");

    // No exige respuesta: el formulario sigue ahí y se sigue pudiendo contestar.
    expect(wrapper.findAll("[data-campo]").length).toBeGreaterThan(0);
    await wrapper.get(".ayuda__cerrar").trigger("click");
    expect(wrapper.find(".ayuda__globo").exists()).toBe(false);
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

    // Los 18 campos de casa —el catálogo entero menos `attendance_status`—
    // siguen preguntándose todos: repartidos en 6 pasos, ninguno de más y
    // ninguno de menos. Es lo que impide que paginar pierda una pregunta por el
    // camino cuando el contrato añada un campo nuevo.
    expect(wrapper.text()).toContain("Paso 1 de 6");

    const vistos: (string | undefined)[] = [...camposVisibles(wrapper)];
    for (let paso = 1; paso < 6; paso += 1) {
      await siguiente(wrapper);
      vistos.push(...camposVisibles(wrapper));
    }

    expect(vistos).toHaveLength(18);
    expect(new Set(vistos).size).toBe(18);

    // Y en el último no se puede seguir: no hay un paso 7 vacío.
    const pasos = wrapper.findAll(".paginador__paso");
    expect(pasos[pasos.length - 1]?.attributes("disabled")).toBeDefined();
  });
});
