import type { EstadoDispositivo, ResumenSalud } from "@/types/salud";

/**
 * Datos ficticios de la pantalla Salud.
 *
 * `SaludView` es el único que los lee. Para conectar la API real basta con
 * sustituir esta constante por la respuesta del endpoint (o por un store)
 * respetando `ResumenSalud`: ningún componente cambia.
 */
export const RESUMEN_SALUD_MOCK: ResumenSalud = {
  fecha: "2026-08-25",
  bienestar: 86,
  recomendacion: {
    texto: "Mantener la rutina de sueño y un momento tranquilo antes de dormir.",
    // TODO(spec): la foto familiar la aporta el equipo. Hasta entonces se pinta
    // el placeholder marcado de `TarjetaRecomendacion`.
    imagen: null,
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

/**
 * Fallback de la barra de estado: son los valores del diseño. La hora real la
 * pone el reloj del sistema y la batería `navigator.getBattery()` cuando existe
 * (ver `useEstadoDispositivo`).
 */
export const ESTADO_DISPOSITIVO_MOCK: EstadoDispositivo = {
  hora: "18:09",
  bateria: 58,
};
