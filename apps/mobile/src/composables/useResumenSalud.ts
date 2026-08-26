/**
 * Los datos de la pantalla de Salud, con la API delante y el mock detrás.
 *
 * La pantalla se diseñó contra `ResumenSalud` y sigue hablando ese idioma: aquí
 * no cambia ni un componente. Lo que cambia es de dónde sale cada pieza.
 *
 * | Pieza                  | De dónde sale                                            |
 * | ---------------------- | -------------------------------------------------------- |
 * | Riesgo y confianza     | del mock, **siempre**                                    |
 * | Recomendación de hoy   | `GET /children/{id}/recommendations/today`, si hay texto  |
 * | Últimos formularios    | `GET /children/{id}/history`                             |
 * | Formulario pendiente   | el día elegido no tiene envío                            |
 * | Lo más importante hoy  | variables críticas del día elegido                       |
 *
 * **Por qué el riesgo sigue siendo del mock.** La API no publica ninguna banda
 * operativa: `PredictionEpisodeResponse.risk_band` está tipado a `None` en el
 * contrato, y el único track con probabilidad —`real_personal_baseline_v1`— se
 * abstiene mientras no haya resultados verificados suficientes, así que hoy
 * devuelve `null`. Poner un número inventado en la tarjeta del riesgo sería
 * justo lo que el SPEC prohíbe, y quitarlo sería romper un diseño aprobado. Se
 * queda el dato de ejemplo, y queda anotado en `NOTAS-API.md`.
 *
 * Si la API no responde, todo lo demás también cae al mock: la pantalla se ve
 * exactamente como el día que se aprobó.
 */

import { computed, ref, type Ref } from "vue";

import { RESUMEN_SALUD_MOCK } from "@/data/saludMock";
import { resumenDeDia } from "@/dominio/dia";
import { etiquetaDiaCorto, hoyIso } from "@/dominio/semana";
import { useHistorial } from "@/estado/historial";
import { useRecomendacionHoy } from "@/estado/recomendacion";
import { diasConRespuestas, respuestasDe } from "@/estado/respuestas";
import type { FactorRiesgo, RegistroFormulario, ResumenSalud } from "@/types/salud";

/** Cuántos días anteriores enseña la tarjeta de últimos formularios. */
const DIAS_EN_LA_TARJETA = 2;

/** Cuántas variables críticas caben en la tarjeta sin desbordar su diseño. */
const CRITICAS_EN_LA_TARJETA = 3;

function diaAnterior(iso: string, cuantos: number): string {
  const fecha = new Date(`${iso}T00:00:00`);
  fecha.setDate(fecha.getDate() - cuantos);
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${String(fecha.getDate()).padStart(2, "0")}`;
}

export function useResumenSalud(ninoId: Ref<string | null>, fecha: Ref<string>) {
  const { porFecha, cargado, cargar: cargarHistorial, error: errorHistorial } = useHistorial();
  const { recomendacion, cargar: cargarRecomendacion } = useRecomendacionHoy();
  const hoy = ref(hoyIso());

  async function cargar(forzar = false): Promise<void> {
    if (ninoId.value === null) return;
    await Promise.all([
      cargarHistorial(ninoId.value, forzar),
      cargarRecomendacion(ninoId.value, forzar),
    ]);
  }

  const resumenDelDia = computed(() =>
    resumenDeDia(
      fecha.value,
      hoy.value,
      porFecha.value.get(fecha.value),
      ninoId.value === null ? undefined : respuestasDe(ninoId.value, fecha.value),
      ninoId.value === null
        ? []
        : diasConRespuestas(ninoId.value).filter((dia) => dia.fecha !== fecha.value),
    ),
  );

  /** Las críticas del día, en el formato que la tarjeta ya sabía pintar. */
  const factores = computed<readonly FactorRiesgo[]>(() => {
    const criticas = resumenDelDia.value.criticas;
    if (criticas.length === 0) return RESUMEN_SALUD_MOCK.factores;
    return criticas.slice(0, CRITICAS_EN_LA_TARJETA).map((critica) => ({
      id: critica.campo,
      icono: critica.icono,
      titulo: critica.titulo,
      detalle: `${critica.valor} · ${critica.motivo}`,
      prioridad: critica.severidad,
    }));
  });

  const formularios = computed<readonly RegistroFormulario[]>(() => {
    if (!cargado.value && porFecha.value.size === 0) return RESUMEN_SALUD_MOCK.formularios;
    const registros: RegistroFormulario[] = [];
    for (let atras = 1; atras <= DIAS_EN_LA_TARJETA; atras += 1) {
      const iso = diaAnterior(fecha.value, atras);
      const respondido =
        porFecha.value.has(iso) ||
        (ninoId.value !== null && respuestasDe(ninoId.value, iso) !== undefined);
      registros.push({
        id: iso,
        dia: etiquetaDiaCorto(iso),
        estado: respondido ? "respondido" : "sin-responder",
      });
    }
    return registros;
  });

  const textoRecomendacion = computed(() => {
    const respuesta = recomendacion.value;
    if (fecha.value !== hoy.value) return RESUMEN_SALUD_MOCK.recomendacion.texto;
    if (respuesta?.status === "matched" && respuesta.action_text_es) {
      return respuesta.action_text_es;
    }
    return RESUMEN_SALUD_MOCK.recomendacion.texto;
  });

  const resumen = computed<ResumenSalud>(() => ({
    fecha: fecha.value,
    riesgo: RESUMEN_SALUD_MOCK.riesgo,
    confianza: RESUMEN_SALUD_MOCK.confianza,
    recomendacion: { texto: textoRecomendacion.value },
    factores: factores.value,
    formularios: formularios.value,
    formularioPendiente: resumenDelDia.value.estado === "sin-responder",
  }));

  return { resumen, resumenDelDia, error: errorHistorial, cargar };
}
