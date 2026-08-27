import { afterEach, describe, expect, it, vi } from "vitest";

const OTRO_NINO = "5c19a89f-f567-4531-8cde-aa8d19df0509";

/** `ID_NINO` se resuelve al importar el módulo, así que cada caso lo reimporta. */
async function idNinoCon(busqueda: string, env?: string): Promise<string> {
  vi.stubGlobal("location", { search: busqueda });
  vi.stubEnv("VITE_FARO_CHILD_ID", env ?? "");
  vi.resetModules();
  return (await import("@/api/config")).ID_NINO;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("ID_NINO", () => {
  it("toma `?child_id=` de la URL", async () => {
    expect(await idNinoCon(`?child_id=${OTRO_NINO}`)).toBe(OTRO_NINO);
  });

  it("la URL gana sobre la variable de entorno", async () => {
    expect(await idNinoCon(`?child_id=${OTRO_NINO}`, "de-la-env")).toBe(OTRO_NINO);
  });

  it("sin `?child_id=` cae a la variable de entorno", async () => {
    expect(await idNinoCon("", "de-la-env")).toBe("de-la-env");
  });

  it("sin ninguno de los dos queda vacío y decide el backend", async () => {
    expect(await idNinoCon("")).toBe("");
  });
});
