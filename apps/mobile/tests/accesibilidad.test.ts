import { mount } from "@vue/test-utils";
import axe from "axe-core";
import { describe, expect, it } from "vitest";

import SaludView from "@/views/SaludView.vue";

/**
 * Pase de axe sobre la pantalla montada.
 *
 * En jsdom no hay layout, así que axe desactiva por su cuenta las reglas que
 * necesitan píxeles (`color-contrast` entre ellas). Los contrastes se verifican
 * a mano: ver el README.
 */
describe("accesibilidad de la pantalla Salud", () => {
  it("no deja violaciones de axe", async () => {
    const contenedor = document.createElement("div");
    document.body.appendChild(contenedor);

    const wrapper = mount(SaludView, { attachTo: contenedor });
    const resultado = await axe.run(contenedor, {
      runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
    });

    expect(resultado.violations.map((v) => `${v.id}: ${v.nodes.length} nodo(s)`)).toEqual([]);

    wrapper.unmount();
    contenedor.remove();
  });
});
