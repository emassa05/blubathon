import type { ResumenSalud } from "@/types/salud";

/**
 * Datos ficticios de la pantalla Salud.
 *
 * `SaludView` es el único que los lee. Para conectar la API real basta con
 * sustituir esta constante por la respuesta del endpoint (o por un store)
 * respetando `ResumenSalud`: ningún componente cambia.
 */
export const RESUMEN_SALUD_MOCK: ResumenSalud = {
  fecha: "2026-08-25",
  // Cae en la banda "bajo" (< 25). Subir este número por encima de 25 o de 50
  // es lo único que hace falta para ver las otras dos paletas; el botón de
  // prueba de `SaludView` hace lo mismo sin tocar el mock.
  riesgo: 18,
  confianza: 85,
  recomendacion: {
    texto: "Mantener la rutina de sueño y un momento tranquilo antes de dormir.",
  },
  factores: [
    {
      id: "horas-de-sueno",
      icono: "luna",
      titulo: "Horas de sueño",
      detalle: "6.2 h · Bajo lo habitual",
      prioridad: "alta",
    },
    {
      id: "estres-percibido",
      icono: "rombo",
      titulo: "Estrés percibido",
      detalle: "4/5 · Elevado",
      prioridad: "alta",
    },
  ],
  formularios: [
    { id: "2026-08-24", dia: "Lunes 24", estado: "respondido" },
    { id: "2026-08-23", dia: "Domingo 23", estado: "sin-responder" },
  ],
  formularioPendiente: true,
};
