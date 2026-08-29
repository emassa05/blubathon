import { flushPromises, mount } from "@vue/test-utils";
import axe from "axe-core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { olvidarTerapeuta } from "@/estado/terapeuta";
import TerapeutaView from "@/views/TerapeutaView.vue";

import { diaFalso, historialFalso, instalarServidorFalso } from "./servidorFalso";

const ANA = "00000000-0000-4000-8000-000000000101";
const BETO = "00000000-0000-4000-8000-000000000102";
const RECOMENDACION = "33333333-3333-4333-8333-333333333333";

function perfilFalso(etiqueta: string, extra: Record<string, unknown> = {}): unknown {
  return {
    child_id: ANA,
    display_label: etiqueta,
    sensory_profile_tags: ["auditory_hypersensitive"],
    communication_support_tags: [],
    contraindication_tags: [],
    care_mode: "home_only",
    profile_version: "1.0.0",
    prediction_episode_id: null,
    ...extra,
  };
}

function recomendacionFalsa(extra: Record<string, unknown> = {}): unknown {
  return {
    recommendation_instance_id: RECOMENDACION,
    child_id: ANA,
    child_label: "Niña demo 1",
    prediction_episode_id: "22222222-2222-4222-8222-222222222222",
    local_date: "2026-08-25",
    created_at: "2026-08-25T12:00:00Z",
    risk_band: "medium",
    query_es: "sueño interrumpido",
    status: "matched",
    action_text_es: "Adelantar la rutina de sueño treinta minutos.",
    purpose_es: "Reducir la deuda de sueño acumulada.",
    citations: [
      {
        document_title_es: "Guía de apoyos (ficticia)",
        locator: "p. 12",
        quote_es: "Un horario estable de acostarse reduce los despertares nocturnos.",
      },
    ],
    abstention_reason: null,
    attempt: 1,
    rating: null,
    in_review_sample: true,
    review_decision: null,
    reviewed_at: null,
    ...extra,
  };
}

/** La cola es mutable: decidir la vuelve a pedir, y lo que prueba que la
 *  decisión llegó es que la segunda respuesta ya trae el veredicto. */
let colaActual: unknown[] = [];

function servidor(extra: Record<string, unknown> = {}): void {
  colaActual = [recomendacionFalsa()];
  instalarServidorFalso({
    "/v1/children": {
      children: [
        { child_id: ANA, display_label: "Niña demo 1" },
        { child_id: BETO, display_label: "Niño demo 2" },
      ],
    },
    [`/v1/children/${ANA}`]: perfilFalso("Niña demo 1"),
    [`/v1/children/${BETO}`]: perfilFalso("Niño demo 2", { child_id: BETO }),
    [`/v1/children/${ANA}/history`]: historialFalso([
      diaFalso({ fecha: "2026-08-25", probabilidad: 0.62, intervalo: [0.4, 0.8] }),
      diaFalso({ fecha: "2026-08-24", probabilidad: 0.18, intervalo: [0.1, 0.3] }),
    ]),
    [`/v1/children/${BETO}/history`]: historialFalso([
      diaFalso({ fecha: "2026-08-25", probabilidad: 0.05, intervalo: [0.01, 0.12] }),
    ]),
    // El POST de la decisión. Sin declararlo, el doble responde 404 y la vista
    // pintaría el error en vez del veredicto.
    [`/v1/recommendations/${RECOMENDACION}/review`]: {
      estado: 201,
      cuerpo: {
        decision_id: "55555555-5555-4555-8555-555555555555",
        recommendation_instance_id: RECOMENDACION,
        decision: "approved",
        reviewed_at: "2026-08-25T13:00:00Z",
      },
    },
    get "/v1/recommendations/review-queue"() {
      return {
        cuerpo: {
          items: colaActual,
          sample_denominator: 5,
          sample_policy_version: "review-sample-0.4.0",
          candidates: 9,
        },
      };
    },
    ...extra,
  });
}

async function montar() {
  const wrapper = mount(TerapeutaView, { attachTo: document.body });
  await flushPromises();
  return wrapper;
}

beforeEach(() => {
  olvidarTerapeuta();
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("panel del terapeuta", () => {
  it("lista a los niños de la organización con su riesgo", async () => {
    servidor();
    const wrapper = await montar();

    const filas = wrapper.findAll(".fila");
    expect(filas).toHaveLength(2);
    expect(filas[0]?.text()).toContain("Niña demo 1");
    // 0.62 del último día, en la escala 0-100 de la interfaz.
    expect(filas[0]?.text()).toContain("62%");
    expect(filas[1]?.text()).toContain("5%");
  });

  it("marca la fila elegida y solo esa", async () => {
    servidor();
    const wrapper = await montar();

    const filas = () => wrapper.findAll(".fila");
    // La cartera abre con el primero elegido: sin nadie marcado, la columna no
    // diría desde dónde se está mirando la pantalla.
    expect(filas()[0]?.attributes("aria-current")).toBe("true");

    await filas()[1]?.trigger("click");
    expect(filas()[0]?.attributes("aria-current")).toBeUndefined();
    expect(filas()[1]?.attributes("aria-current")).toBe("true");
  });

  it("cuenta el conjunto por bandas en vez de promediarlo", async () => {
    servidor();
    const wrapper = await montar();

    const conjunto = wrapper.find(".conjunto");
    expect(conjunto.text()).toContain("Riesgo alto");
    expect(conjunto.text()).toContain("Riesgo bajo");
    // Nunca aparece una cifra de "riesgo medio de la cartera".
    expect(conjunto.text()).not.toContain("Riesgo promedio");
  });

  it("no tiene faltas de accesibilidad detectables", async () => {
    servidor();
    const wrapper = await montar();
    const resultado = await axe.run(wrapper.element as HTMLElement);
    expect(resultado.violations).toEqual([]);
  });
});

describe("cola de revisión", () => {
  it("declara que es una muestra, con el denominador que da el servidor", async () => {
    servidor();
    const wrapper = await montar();
    // Escrito a mano diría siempre "1 de cada 5"; esto lo lee de la respuesta,
    // así que cambiar la política cambia la frase.
    expect(wrapper.find(".revision__muestra").text()).toContain("1 de cada 5");
    expect(wrapper.find(".revision__muestra").text()).toContain("9 redactadas");
  });

  it("enseña las citas junto a la recomendación que hay que aprobar", async () => {
    servidor();
    const wrapper = await montar();
    // Aprobar sin ver la fuente sería firmar a ciegas: la recomendación solo
    // existe porque cada afirmación salió de un fragmento del corpus.
    expect(wrapper.find(".citas").text()).toContain("Guía de apoyos (ficticia)");
    expect(wrapper.find(".citas").text()).toContain("p. 12");
  });

  it("manda la decisión y refleja el veredicto que devuelve el servidor", async () => {
    servidor();
    const wrapper = await montar();

    // La segunda lectura de la cola ya trae la revisión guardada: se prepara
    // antes del clic porque la recarga sale dentro de la misma cadena.
    colaActual = [
      recomendacionFalsa({ review_decision: "approved", reviewed_at: "2026-08-25T13:00:00Z" }),
    ];
    await wrapper.find(".tarjeta__boton--bien").trigger("click");
    await flushPromises();

    const llamadas = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    const envio = llamadas.find(([url]) => String(url).includes(`/${RECOMENDACION}/review`));
    expect(envio).toBeDefined();
    expect(JSON.parse(String((envio?.[1] as RequestInit).body))).toEqual({ decision: "approved" });
    expect(wrapper.find(".veredicto").text()).toBe("Aprobada");
  });

  it("no aprobar usa la ruta de revisión y no la de valoración", async () => {
    // Un `bad` del cuidador redacta de nuevo; un rechazo profesional no. Si
    // este botón pegara en `/feedback`, rechazar dispararía una redacción.
    servidor();
    const wrapper = await montar();

    await wrapper.find(".tarjeta__boton--mal").trigger("click");
    await flushPromises();

    const rutas = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.map(([url]) =>
      String(url),
    );
    expect(rutas.some((ruta) => ruta.includes(`/${RECOMENDACION}/review`))).toBe(true);
    expect(rutas.some((ruta) => ruta.includes("/feedback"))).toBe(false);
  });

  it("dice que la muestra vino vacía en vez de parecer un fallo de red", async () => {
    servidor();
    colaActual = [];
    const wrapper = await montar();
    expect(wrapper.text()).toContain("Ninguna recomendación de hoy entró en la muestra");
  });
});
