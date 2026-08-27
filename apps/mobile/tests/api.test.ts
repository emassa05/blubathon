import { afterEach, describe, expect, it, vi } from "vitest";

import { ErrorBlubathon } from "@/api/errores";
import { pedir } from "@/api/http";
import { historialNino, listarRecomendaciones, valorarRecomendacion } from "@/api/blubathon";

import { instalarServidorFalso } from "./servidorFalso";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("pedir", () => {
  it("devuelve el cuerpo ya parseado", async () => {
    instalarServidorFalso({ "/v1/children": { children: [] } });

    await expect(pedir("/children")).resolves.toEqual({ children: [] });
  });

  it("traduce el sobre de error del backend, con su código y su request id", async () => {
    instalarServidorFalso({
      "/v1/children": {
        estado: 422,
        cuerpo: {
          error: {
            code: "validation_error",
            message_es: "Los datos enviados no cumplen el contrato.",
            request_id: "abc",
          },
        },
      },
    });

    const fallo = await pedir("/children").catch((error: unknown) => error);

    expect(fallo).toBeInstanceOf(ErrorBlubathon);
    expect(fallo).toMatchObject({
      codigo: "validation_error",
      mensajeEs: "Los datos enviados no cumplen el contrato.",
      estado: 422,
      requestId: "abc",
    });
  });

  it("una respuesta que no es el sobre no se hace pasar por un error de dominio", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("<html>502</html>", { status: 502 }))),
    );

    const fallo = (await pedir("/children").catch((error: unknown) => error)) as ErrorBlubathon;

    expect(fallo.codigo).toBe("internal_error");
    expect(fallo.estado).toBe(502);
  });

  it("una red caída no llega a la pantalla como excepción cruda", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );

    const fallo = (await pedir("/children").catch((error: unknown) => error)) as ErrorBlubathon;

    expect(fallo.codigo).toBe("network_error");
    expect(fallo.mensajeEs).toBe("No pudimos conectar con el servidor.");
  });

  it("propaga la cancelación del llamador tal cual, sin convertirla en error", async () => {
    const controlador = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        controlador.abort();
        return Promise.reject(new DOMException("Aborted", "AbortError"));
      }),
    );

    const fallo = await pedir("/children", { signal: controlador.signal }).catch(
      (error: unknown) => error,
    );

    expect(fallo).not.toBeInstanceOf(ErrorBlubathon);
  });
});

describe("rutas", () => {
  it("cada envoltorio pega en la ruta y el método de `apps/api/routes/v1.py`", async () => {
    instalarServidorFalso({
      "/v1/children/nina/history": { child_id: "nina", days: [] },
      "/v1/recommendations": { items: [] },
      "/v1/recommendations/rec-1/feedback": { feedback_id: "f1", rating: "good", attempt: 1 },
    });

    await historialNino("nina", { limite: 7 });
    await listarRecomendaciones({ estado: "matched", idNino: "nina" });
    await valorarRecomendacion("rec-1", { rating: "good" });

    const llamadas = vi.mocked(fetch).mock.calls;
    expect(String(llamadas[0]?.[0])).toBe("/v1/children/nina/history?limit=7");
    expect(String(llamadas[1]?.[0])).toBe("/v1/recommendations?status=matched&child_id=nina");
    expect(llamadas[2]?.[1]?.method).toBe("POST");
    expect(llamadas[2]?.[1]?.body).toBe('{"rating":"good"}');
  });
});
