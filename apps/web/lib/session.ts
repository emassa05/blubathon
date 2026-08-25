/**
 * Sesión local de la demo.
 *
 * `SPEC 12.3`: la demo usa una sesión ficticia preseeded. El token identifica a
 * un usuario sembrado por `tools/seed`; no es un secreto de producción y el modo
 * piloto no acepta este mecanismo.
 */

"use client";

const STORAGE_KEY = "faro.demo.token";

export interface DemoAccount {
  readonly token: string;
  readonly label: string;
  readonly role: "caregiver" | "professional" | "model_evaluator";
}

export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  { token: "demo-cuidadora-ana", label: "Ana Ríos (cuidadora ficticia)", role: "caregiver" },
  {
    token: "demo-profesional-a",
    label: "Pilar Soto (profesional ficticia)",
    role: "professional",
  },
  { token: "demo-evaluador-a", label: "Evaluador Demo A", role: "model_evaluator" },
];

export function readToken(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // Un navegador sin almacenamiento sigue funcionando durante la sesión.
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Sin almacenamiento no hay nada que limpiar.
  }
}
