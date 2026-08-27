import { beforeEach, describe, expect, it } from "vitest";

import {
  guardarRespuestas,
  olvidarRespuestas,
  reconciliar,
  respuestasDe,
} from "@/estado/respuestas";

const NINO = "00000000-0000-4000-8000-000000000101";
const OTRO = "00000000-0000-4000-8000-000000000102";

beforeEach(() => {
  olvidarRespuestas();
});

describe("reconciliar", () => {
  it("descarta el día que el servidor no devuelve", () => {
    guardarRespuestas(NINO, "2026-08-25", { sleep_quality: "restorative" });
    guardarRespuestas(NINO, "2026-08-26", { sleep_quality: "interrupted" });

    reconciliar(NINO, { conEnvio: new Set(["2026-08-25"]), completo: true });

    expect(respuestasDe(NINO, "2026-08-25")).toEqual({ sleep_quality: "restorative" });
    // La copia local solo se escribe cuando la API aceptó el envío. Si el
    // servidor ya no lo tiene, lo que queda aquí es un fantasma.
    expect(respuestasDe(NINO, "2026-08-26")).toBeUndefined();
  });

  it("con el historial completo y vacío, no sobrevive ningún día", () => {
    guardarRespuestas(NINO, "2026-08-25", { sleep_quality: "restorative" });
    guardarRespuestas(NINO, "2026-08-26", { sleep_quality: "interrupted" });

    reconciliar(NINO, { conEnvio: new Set(), completo: true });

    expect(respuestasDe(NINO, "2026-08-25")).toBeUndefined();
    expect(respuestasDe(NINO, "2026-08-26")).toBeUndefined();
  });

  it("con el historial recortado no toca lo anterior al día más viejo recibido", () => {
    guardarRespuestas(NINO, "2026-06-01", { sleep_quality: "restorative" });
    guardarRespuestas(NINO, "2026-08-20", { sleep_quality: "interrupted" });
    guardarRespuestas(NINO, "2026-08-26", { sleep_quality: "interrupted" });

    // `GET /history` llegó lleno: de un día ausente no se puede decir si no
    // existe o si no cupo, así que solo se limpia desde el más viejo recibido.
    reconciliar(NINO, { conEnvio: new Set(["2026-08-20"]), completo: false });

    expect(respuestasDe(NINO, "2026-06-01")).toEqual({ sleep_quality: "restorative" });
    expect(respuestasDe(NINO, "2026-08-20")).toEqual({ sleep_quality: "interrupted" });
    expect(respuestasDe(NINO, "2026-08-26")).toBeUndefined();
  });

  it("no toca los días de otra persona", () => {
    guardarRespuestas(NINO, "2026-08-26", { sleep_quality: "interrupted" });
    guardarRespuestas(OTRO, "2026-08-26", { sleep_quality: "restorative" });

    reconciliar(NINO, { conEnvio: new Set(), completo: true });

    expect(respuestasDe(NINO, "2026-08-26")).toBeUndefined();
    expect(respuestasDe(OTRO, "2026-08-26")).toEqual({ sleep_quality: "restorative" });
  });

  it("sin nada guardado de esa persona no hace nada", () => {
    expect(() => reconciliar(NINO, { conEnvio: new Set(), completo: true })).not.toThrow();
    expect(respuestasDe(NINO, "2026-08-26")).toBeUndefined();
  });
});
