/** Formato de fechas y valores visibles. La zona de referencia es America/Santiago. */

const REFERENCE_TIMEZONE = "America/Santiago";

const dateTime = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: REFERENCE_TIMEZONE,
});

export function formatMoment(iso: string | null): string {
  if (iso === null) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return dateTime.format(parsed);
}

export function hoursUntil(iso: string, now: Date = new Date()): number {
  const target = new Date(iso).getTime();
  return Math.round((target - now.getTime()) / 3_600_000);
}

/** Un valor booleano observado no es lo mismo que su ausencia (SPEC 8.2). */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "sin valor";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (Array.isArray(value)) return value.length === 0 ? "ninguna" : value.join(", ");
  return String(value);
}
