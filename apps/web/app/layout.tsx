import type { Metadata } from "next";

import { AppShell } from "@/components/AppShell";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Faro - demo local v0.3.0",
  description:
    "Registro diario, estadística personal y apoyo revisado. Demo local con datos ficticios.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-CL">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
