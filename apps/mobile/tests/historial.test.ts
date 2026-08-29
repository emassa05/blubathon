import { describe, expect, it } from "vitest";

import type { ChildHistoryDay } from "@/api/contrato";
import { unificarPorDia } from "@/dominio/historial";

/**
 * La fila que deja un segundo envío del mismo día: trae su `submission_id` y
 * nada más, porque el episodio, la estimación, la recomendación y el resultado
 * cuelgan del primer envío, al que este se enlaza.
 */
const REENVIO: ChildHistoryDay = {
  local_date: "2026-08-28",
  submission_id: "envio-nuevo",
  prediction_episode_id: null,
  prediction: null,
  recommendation: null,
  outcome: null,
};

const ORIGINAL: ChildHistoryDay = {
  local_date: "2026-08-28",
  submission_id: "envio-viejo",
  prediction_episode_id: "episodio-1",
  prediction: { status: "ok", probability: 0.16, interval: null },
  recommendation: {
    recommendation_instance_id: "reco-1",
    status: "abstained",
    rating: null,
  },
  outcome: { status: "no", reported_at: "2026-08-28T14:00:00Z" },
};

const AYER: ChildHistoryDay = {
  local_date: "2026-08-27",
  submission_id: "envio-ayer",
  prediction_episode_id: "episodio-0",
  prediction: { status: "ok", probability: 0.36, interval: null },
  recommendation: null,
  outcome: { status: "no", reported_at: "2026-08-27T14:00:00Z" },
};

describe("unificarPorDia", () => {
  it("deja una sola fila por fecha", () => {
    const dias = unificarPorDia([REENVIO, ORIGINAL, AYER]);

    expect(dias.map((dia) => dia.local_date)).toEqual(["2026-08-28", "2026-08-27"]);
  });

  it("se queda el envío más reciente y el episodio que sí existe", () => {
    const [hoy] = unificarPorDia([REENVIO, ORIGINAL, AYER]);

    // El envío es el último que se hizo…
    expect(hoy?.submission_id).toBe("envio-nuevo");
    // …y lo demás es lo del día, que solo trae la fila vieja. Quedarse con la
    // primera fila entera dejaba el día sin estimación y sin resultado: el
    // riesgo salía como "—" y la racha dejaba de contar el día.
    expect(hoy?.prediction_episode_id).toBe("episodio-1");
    expect(hoy?.prediction?.probability).toBe(0.16);
    expect(hoy?.recommendation?.recommendation_instance_id).toBe("reco-1");
    expect(hoy?.outcome?.status).toBe("no");
  });

  it("no cuenta dos veces el mismo día", () => {
    const dias = unificarPorDia([REENVIO, ORIGINAL, AYER]);

    expect(dias).toHaveLength(2);
  });

  it("con un solo envío por día no cambia nada", () => {
    const dias = unificarPorDia([ORIGINAL, AYER]);

    expect(dias).toEqual([ORIGINAL, AYER]);
  });

  it("una lista vacía sigue vacía", () => {
    expect(unificarPorDia([])).toEqual([]);
  });
});
