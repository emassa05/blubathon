import { describe, expect, it } from "vitest";

import { useDiaSeleccionado } from "@/composables/useDiaSeleccionado";

describe("useDiaSeleccionado", () => {
  it("formatea el día con mayúscula inicial y ofrece la variante para aria-label", () => {
    const { etiqueta, etiquetaAccesible } = useDiaSeleccionado("2026-08-25");

    expect(etiqueta.value).toBe("Martes 25");
    expect(etiquetaAccesible.value).toBe("martes 25");
  });

  it("se mueve un día en cada dirección, cruzando el cambio de mes", () => {
    const { etiqueta, diaAnterior, diaSiguiente } = useDiaSeleccionado("2026-09-01");

    diaAnterior();
    expect(etiqueta.value).toBe("Lunes 31");

    diaSiguiente();
    diaSiguiente();
    expect(etiqueta.value).toBe("Miércoles 2");
  });
});
