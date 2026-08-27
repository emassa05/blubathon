/**
 * De dónde sale el nivel de confianza.
 *
 * El backend no publica ninguna confianza: lo único que dice sobre su propia
 * incertidumbre es el intervalo del modelo, el 5-95 del posterior Beta sobre los
 * resultados verificados de esa misma persona (C42, C43). La confianza se deriva
 * aquí de su anchura —cuantos más resultados confirmados hay, más estrecho es el
 * intervalo, y un intervalo estrecho es lo que "confianza alta" quiere decir.
 *
 * Lo que conviene tener presente al leer la cifra, y que está medido:
 *
 * - La ventana del baseline son 60 días (C18) y el mínimo son 5 resultados
 *   (C19), así que la anchura solo recorre ~0.58 → ~0.18. En la práctica el
 *   número vive entre el 42% y el 82%, y con un historial establecido se queda
 *   en 79-80.
 * - El 100% es inalcanzable por construcción: haría falta un intervalo de
 *   anchura cero, o sea infinitos resultados confirmados.
 *
 * Sin intervalo no hay confianza que dar, y devolver `null` es más honesto que
 * un número por defecto.
 */

function intervalo(valor: unknown): readonly [number, number] | null {
  if (!Array.isArray(valor) || valor.length !== 2) return null;
  const [inferior, superior] = valor;
  if (typeof inferior !== "number" || typeof superior !== "number") return null;
  if (!Number.isFinite(inferior) || !Number.isFinite(superior)) return null;
  // Del revés no se da la vuelta: se descarta. Un intervalo con los extremos
  // cambiados es un dato roto, no un dato que haya que reparar.
  if (superior < inferior) return null;
  return [inferior, superior];
}

export function confianzaDelIntervalo(valor: unknown): number | null {
  const rango = intervalo(valor);
  if (rango === null) return null;
  const ancho = Math.min(1, Math.max(0, rango[1] - rango[0]));
  return Math.round((1 - ancho) * 100);
}
