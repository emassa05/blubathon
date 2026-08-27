import { flushPromises, mount } from "@vue/test-utils";
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

// En local, no en UTC: `toISOString` movería el día según el huso de la máquina.
function diaAntesDe(iso: string): string {
  const fecha = new Date(`${iso}T00:00:00`);
  fecha.setDate(fecha.getDate() - 1);
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${String(fecha.getDate()).padStart(2, "0")}`;
}

const AYER_ISO = diaAntesDe(HOY);

const CHILD = `/v1/children/${ID_NINO_FALSO}`;

function servidor(extra: Record<string, unknown> = {}): void {
  instalarServidorFalso({
    "/v1/children": { children: [{ child_id: ID_NINO_FALSO, display_label: "Niña demo 1" }] },
    [`${CHILD}/history`]: historialFalso([
      diaFalso({ fecha: HOY, probabilidad: 0.18, intervalo: [0.1, 0.25], conRecomendacion: true }),
      diaFalso({ fecha: AYER_ISO, probabilidad: 0.62 }),
    ]),
    [`${CHILD}/form-plan`]: planFalso(["sleep_quality", "routine_changes"]),
    [`${CHILD}/recommendations/today`]: {
      status: "matched",
      risk_band: "low",
      recommendation_instance_id: "33333333-3333-4333-8333-333333333333",
      action_text_es: "Mantener la rutina de sueño.",
      purpose_es: null,
      citations: [],
      abstention_reason: null,
      rating: null,
    },
    ...extra,
  });
}

async function montar() {
  const wrapper = mount(SaludView);
  await flushPromises();
  return wrapper;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SaludView", () => {
  it("arma la pantalla con lo que devuelve la API", async () => {
    servidor();
    const wrapper = await montar();
    const texto = wrapper.text();

    expect(texto).toContain("Riesgo de desregulación");
    expect(texto).toContain("18%");
    expect(texto).toContain("Mantener la rutina de sueño.");
    expect(texto).toContain("Lo más importante hoy");
    // Los destacados del plan del formulario, con su etiqueta del contrato.
    expect(texto).toContain("Calidad del sueño");
    expect(texto).toContain("Cambios en la rutina");
    expect(texto).toContain("Últimos formularios");
  });

  it("la columna lleva la clase de la banda que le toca al riesgo", async () => {
    servidor();
    const wrapper = await montar();

    expect(wrapper.get(".pantalla__columna").classes()).toContain("blubathon-banda--bajo");
  });

  it("anuncia la carga antes de tener datos", () => {
    servidor();
    const wrapper = mount(SaludView);

    expect(wrapper.get('[role="status"]').text()).toBe("Cargando…");
    expect(wrapper.get(".pantalla__columna").classes()).toContain("blubathon-banda--desconocido");
  });

  it("cuando el modelo se abstiene no muestra cifra ni la pinta de riesgo bajo", async () => {
    servidor({
      [`${CHILD}/history`]: historialFalso([diaFalso({ fecha: HOY, probabilidad: null })]),
    });
    const wrapper = await montar();

    expect(wrapper.get(".riesgo__cifra").text()).toBe("—");
    expect(wrapper.find(".riesgo__confianza").exists()).toBe(false);
    expect(wrapper.get(".pantalla__columna").classes()).toContain("blubathon-banda--desconocido");
  });

  it("muestra el mensaje del backend cuando la petición falla", async () => {
    servidor({
      [`${CHILD}/history`]: {
        estado: 500,
        cuerpo: {
          error: { code: "internal_error", message_es: "Ocurrió un error.", request_id: "r1" },
        },
      },
    });
    const wrapper = await montar();

    expect(wrapper.get('[role="alert"]').text()).toBe("Ocurrió un error.");
    expect(wrapper.find(".recomendacion").exists()).toBe(false);
  });

  it("navega de día y vuelve a pedir el resumen", async () => {
    servidor();
    const wrapper = await montar();
    const peticiones = () =>
      vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/history")).length;

    const antes = peticiones();
    await wrapper.get('[aria-label="Día anterior"]').trigger("click");
    await flushPromises();

    expect(peticiones()).toBe(antes + 1);
  });

  it("tiene un único h1 y un h2 por sección", async () => {
    servidor();
    const wrapper = await montar();

    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.findAll("h2").map((h) => h.text())).toEqual([
      "Recomendación de hoy",
      "Lo más importante hoy",
      "Últimos formularios",
    ]);
  });

  it("el 'ver más' de los formularios lleva al historial", async () => {
    servidor();
    const wrapper = await montar();

    await wrapper.get('[aria-label="Ver todos los formularios"]').trigger("click");
    expect(wrapper.emitted("verHistorial")).toHaveLength(1);
  });

  it("el aviso pendiente abre el cuestionario del día que se está mirando", async () => {
    // Sin envío en el día visible, el aviso aparece: es su única condición.
    servidor({ [`${CHILD}/history`]: historialFalso([]) });
    const wrapper = await montar();

    await wrapper.get(".aviso").trigger("click");
    expect(wrapper.emitted("abrirCuestionario")).toEqual([[HOY]]);
  });

  it("cada fila de formulario abre el cuestionario de su día", async () => {
    servidor();
    const wrapper = await montar();

    // La lista empieza en el día visible, así que la primera fila es hoy y la
    // segunda ayer. Hoy tiene que estar: el aviso de pendiente desaparece al
    // enviarlo y antes el día se quedaba sin aparecer en ningún sitio.
    await wrapper.findAll(".formulario__fila")[0]?.trigger("click");
    await wrapper.findAll(".formulario__fila")[1]?.trigger("click");
    expect(wrapper.emitted("abrirCuestionario")).toEqual([[HOY], [AYER_ISO]]);
  });
});
