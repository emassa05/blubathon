/**
 * El cliente HTTP cumple el protocolo de la API (SPEC 11.2, 11.7).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/lib/api";

const originalFetch = globalThis.fetch;

function respond(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Vitest tipa `mock.calls` de forma laxa; esto lo estrecha sin usar `any`. */
function lastInit(mock: { mock: { calls: unknown[][] } }): RequestInit {
  const call = mock.mock.calls[0];
  if (call === undefined || call[1] === undefined) {
    throw new Error("fetch no fue llamado con opciones");
  }
  return call[1] as RequestInit;
}

function lastHeaders(mock: { mock: { calls: unknown[][] } }): Record<string, string> {
  return lastInit(mock).headers as Record<string, string>;
}

describe("cliente de la API", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("todo POST manda Idempotency-Key", async () => {
    const fetchMock = vi.fn(async () => respond({ form_session_id: "s1" }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    await api.openFormSession("token", { subjectId: "sub-1", source: "home" });
    const init = lastInit(fetchMock);
    const headers = lastHeaders(fetchMock);
    expect(init.method).toBe("POST");
    expect(headers["Idempotency-Key"]).toBeTruthy();
    expect(headers.Authorization).toBe("Bearer token");
  });

  it("un GET no manda Idempotency-Key", async () => {
    const fetchMock = vi.fn(async () => respond({ items: [] }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    await api.outcomeRequests("token");
    const init = lastInit(fetchMock);
    const headers = lastHeaders(fetchMock);
    expect(init.method).toBe("GET");
    expect(headers["Idempotency-Key"]).toBeUndefined();
  });

  it("los recursos con revisión mandan If-Match", async () => {
    const fetchMock = vi.fn(async () => respond({ review_id: "r1", revision: "rev-2" }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    await api.review(
      "token",
      "instance-1",
      { strategyVersionId: "strategy-1", decision: "approved" },
      "rev-1",
    );
    expect(lastHeaders(fetchMock)["If-Match"]).toBe("rev-1");
  });

  it("un error del servidor conserva código, mensaje y request_id", async () => {
    globalThis.fetch = (async () =>
      respond(
        {
          error: {
            code: "subject_access_denied",
            message_es: "No tienes una autorización vigente sobre esta persona.",
            request_id: "req-9",
          },
        },
        403,
      )) as unknown as typeof fetch;
    await expect(api.session("token")).rejects.toMatchObject({
      code: "subject_access_denied",
      status: 403,
      requestId: "req-9",
    });
  });

  it("una caída de red se reporta sin inventar un estado", async () => {
    globalThis.fetch = (async () => {
      throw new TypeError("failed to fetch");
    }) as unknown as typeof fetch;
    const caught = await api.session("token").catch((error: unknown) => error);
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).code).toBe("network_error");
  });

  it("no envía el valor de un campo que el usuario no tocó", async () => {
    const fetchMock = vi.fn(async () => respond({ field_code: "food_changes" }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    await api.answer("token", "session-1", {
      fieldCode: "food_changes",
      interaction: "accept_default",
      defaultPresentationId: "presentation-1",
    });
    expect(JSON.parse(lastInit(fetchMock).body as string)).toEqual({
      field_code: "food_changes",
      interaction: "accept_default",
      value: null,
      default_presentation_id: "presentation-1",
    });
  });
});
