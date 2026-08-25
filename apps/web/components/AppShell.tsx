"use client";

/**
 * Shell de la aplicación: identidad de la demo, navegación y selector de cuenta.
 *
 * El límite de emergencia acompaña a la navegación en todas las pantallas
 * (SPEC 13.2). La cuenta es una sesión ficticia local (SPEC 12.3).
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { EmergencyNotice } from "@/components/EmergencyNotice";
import { DEMO_ACCOUNTS, readToken, writeToken } from "@/lib/session";
import { TEXTS } from "@/lib/texts";

const NAV = [
  { href: "/cuidador", label: "Cuidador" },
  { href: "/profesional", label: "Profesional" },
  { href: "/evaluacion", label: "Evaluación" },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [token, setToken] = useState<string>(DEMO_ACCOUNTS[0]!.token);

  useEffect(() => {
    const stored = readToken();
    if (stored !== null) setToken(stored);
  }, []);

  function chooseAccount(next: string) {
    setToken(next);
    writeToken(next);
    // Un cambio de cuenta reinicia las vistas para no mezclar autorizaciones.
    window.location.reload();
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-4 p-4">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:faro-button focus:absolute"
      >
        Saltar al contenido
      </a>

      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <p className="text-xl font-semibold text-ink">{TEXTS.appName}</p>
            <p className="faro-hint">{TEXTS.tagline}</p>
          </div>
          <p className="rounded bg-canvas px-2 py-1 text-xs font-semibold text-muted">
            demo local · datos ficticios
          </p>
        </div>

        <nav aria-label="Secciones" className="flex flex-wrap gap-2">
          {NAV.map((item) => {
            const active = pathname?.startsWith(item.href) ?? false;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "faro-button-primary"
                    : "faro-button"
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <label className="faro-label">
          Cuenta de demostración
          <select
            className="faro-input mt-1"
            value={token}
            onChange={(event) => chooseAccount(event.target.value)}
          >
            {DEMO_ACCOUNTS.map((account) => (
              <option key={account.token} value={account.token}>
                {account.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      <EmergencyNotice />

      <main id="contenido" className="flex-1 space-y-4">
        {children}
      </main>

      <footer className="faro-hint border-t border-line pt-3">
        Faro no diagnostica, no prescribe y no reemplaza el criterio profesional. Esta
        demostración usa datos completamente ficticios.
      </footer>
    </div>
  );
}
