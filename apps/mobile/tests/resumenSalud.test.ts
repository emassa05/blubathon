import { afterEach, describe, expect, it, vi } from "vitest";

import { cargarResumenSalud } from "@/adaptadores/resumenSalud";
import { fechaDeHoy } from "@/composables/useDiaSeleccionado";

import {
  ID_NINO_FALSO,
  diaFalso,
  historialFalso,
  instalarServidorFalso,
  planFalso,
} from "./servidorFalso";

const HOY = fechaDeHoy();
const CHILD = `/v1/children/${ID_NINO_FALSO}`;

function diaAntesDe(iso: string, dias = 1): string {
  const fecha = new Date(`${iso}T00:00:00`);
  fecha.setDate(fecha.getDate() - dias);
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${String(fecha.getDate()).padStart(2, "0")}`;
}

function cargarHoy() {
  return cargarResumenSalud({ idNino: ID_NINO_FALSO, fechaIso: HOY });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cargarResumenSalud", () => {
  it("pasa la probabilidad a porcentaje y el ancho del intervalo a confianza", async () => {
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([
        diaFalso({ fecha: HOY, probabilidad: 0.184, intervalo: [0.09, 0.24] }),
      ]),
      [`${CHILD}/form-plan`]: planFalso([]),
      [`${CHILD}/recommendations/today`]: { status: "pending", citations: [] },
    });

    const resumen = await cargarHoy();

    expect(resumen.riesgo).toBe(18);
    // Intervalo de 0.15 de ancho: 85% de confianza.
    expect(resumen.confianza).toBe(85);
  });

  it("la abstención del modelo no se convierte en un cero", async () => {
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([diaFalso({ fecha: HOY, probabilidad: null })]),
      [`${CHILD}/form-plan`]: planFalso([]),
      [`${CHILD}/recommendations/today`]: { status: "pending", citations: [] },
    });

    const resumen = await cargarHoy();

    expect(resumen.riesgo).toBeNull();
    expect(resumen.confianza).toBeNull();
  });

  it("cada estado de la recomendación dice lo que pasa, y la abstención dice por qué", async () => {
    const casos: readonly [unknown, string][] = [
      [{ status: "no_submission_today" }, "Todavía no hay formulario"],
      [{ status: "pending" }, "Estamos preparando"],
      [{ status: "matched", action_text_es: "Bajar el ruido de la tarde." }, "Bajar el ruido"],
      [{ status: "abstained", abstention_reason: "no_indexed_match" }, "No hay material indexado"],
      [
        { status: "abstained", abstention_reason: "draft_not_grounded" },
        "no quedó respaldada por sus fuentes",
      ],
    ];

    for (const [respuesta, esperado] of casos) {
      instalarServidorFalso({
        [`${CHILD}/history`]: historialFalso([diaFalso({ fecha: HOY, probabilidad: 0.2 })]),
        [`${CHILD}/form-plan`]: planFalso([]),
        [`${CHILD}/recommendations/today`]: respuesta,
      });

      const resumen = await cargarHoy();
      expect(resumen.recomendacion.texto).toContain(esperado);
    }
  });

  it("los factores son los destacados del plan, con la etiqueta del contrato", async () => {
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([diaFalso({ fecha: HOY, probabilidad: 0.2 })]),
      [`${CHILD}/form-plan`]: planFalso(["sleep_hours", "routine_changes"]),
      [`${CHILD}/recommendations/today`]: { status: "pending" },
    });

    const resumen = await cargarHoy();

    expect(resumen.factores).toEqual([
      {
        id: "sleep_hours",
        icono: "luna",
        titulo: "Horas de sueño",
        detalle: "Sin registrar hace 7 días o más",
        prioridad: "alta",
      },
      {
        id: "routine_changes",
        icono: "rombo",
        titulo: "Cambios en la rutina",
        detalle: "Sin registrar hace 7 días o más",
        prioridad: "alta",
      },
    ]);
  });

  it("el listado va por calendario, así que el día sin envío sale como hueco", async () => {
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([
        diaFalso({ fecha: HOY, probabilidad: 0.2 }),
        diaFalso({ fecha: diaAntesDe(HOY, 2), probabilidad: 0.2 }),
      ]),
      [`${CHILD}/form-plan`]: planFalso([]),
      [`${CHILD}/recommendations/today`]: { status: "pending" },
    });

    const resumen = await cargarHoy();
    const estados = resumen.formularios.map((registro) => registro.estado);

    expect(resumen.formularios.map((r) => r.id)).toEqual([
      diaAntesDe(HOY, 1),
      diaAntesDe(HOY, 2),
      diaAntesDe(HOY, 3),
      diaAntesDe(HOY, 4),
    ]);
    expect(estados).toEqual(["sin-responder", "respondido", "sin-responder", "sin-responder"]);
  });

  it("un día sin envío queda pendiente", async () => {
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([]),
      [`${CHILD}/form-plan`]: planFalso([]),
      [`${CHILD}/recommendations/today`]: { status: "no_submission_today" },
    });

    const resumen = await cargarHoy();

    expect(resumen.formularioPendiente).toBe(true);
  });

  it("un día pasado no pide el plan de hoy ni la recomendación de hoy", async () => {
    const ayer = diaAntesDe(HOY);
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([diaFalso({ fecha: ayer, probabilidad: 0.6 })]),
    });

    const resumen = await cargarResumenSalud({ idNino: ID_NINO_FALSO, fechaIso: ayer });

    expect(resumen.riesgo).toBe(60);
    expect(resumen.factores).toEqual([]);
    const rutas = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(rutas.some((ruta) => ruta.includes("form-plan"))).toBe(false);
    expect(rutas.some((ruta) => ruta.includes("recommendations/today"))).toBe(false);
  });

  it("un episodio sin recomendación es un día vacío, no un fallo", async () => {
    const ayer = diaAntesDe(HOY);
    instalarServidorFalso({
      [`${CHILD}/history`]: historialFalso([
        diaFalso({ fecha: ayer, probabilidad: 0.6, conRecomendacion: true }),
      ]),
      // `/prediction-episodes/.../recommendations` no está declarada: 404.
    });

    const resumen = await cargarResumenSalud({ idNino: ID_NINO_FALSO, fechaIso: ayer });

    expect(resumen.recomendacion.texto).toBe("Este día no tiene recomendación.");
  });
});
