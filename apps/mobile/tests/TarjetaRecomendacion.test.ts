import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";
import { MS_MAXIMO } from "@/composables/useMaquinaDeEscribir";

const TEXTO = "Mantener la rutina de sueño y un momento tranquilo antes de dormir.";
const OTRO = "Bajar las luces una hora antes de acostarse.";
const EN_CURSO = "Estamos preparando la recomendación de este día.";

/**
 * El tecleo va con `requestAnimationFrame` y mide con `performance.now`, así
 * que se falsean los dos: sin `performance` el reloj no avanzaría y el texto se
 * quedaría siempre en el primer carácter.
 */
beforeEach(() => {
  vi.useFakeTimers({
    toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"],
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("TarjetaRecomendacion", () => {
  it("muestra el sobretítulo y la recomendación", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, estado: "lista" as const } },
    });

    expect(wrapper.get("h2").text()).toBe("Recomendación de hoy");
    expect(wrapper.get(".recomendacion__frase").text()).toBe(TEXTO);
    // Montar un día ya redactado no teclea nada: no ha llegado, ya estaba, así
    // que está entero desde el primer fotograma y no queda nada por escribir.
    expect(wrapper.get(".recomendacion__escrito").text()).toBe(TEXTO);
    expect(wrapper.get(".recomendacion__resto").text()).toBe("");
  });

  it("ni el fondo ilustrado ni el destello llegan al lector de pantalla", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, estado: "lista" as const } },
    });

    // Da igual si el `aria-hidden` está en el propio SVG o en el envoltorio:
    // lo que se comprueba es que ningún dibujo quede expuesto.
    const svgs = [...wrapper.element.querySelectorAll("svg")];
    expect(svgs.length).toBeGreaterThan(0);
    for (const svg of svgs) {
      expect(svg.closest('[aria-hidden="true"]')).not.toBeNull();
      expect(svg.getAttribute("focusable")).toBe("false");
    }
  });

  it("mientras el RAG redacta no escribe la espera: gira el destello y deja los renglones", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: EN_CURSO, estado: "pendiente" as const } },
    });

    // La frase de espera no se ve en ninguna parte de la tarjeta salvo en la
    // región de estado, que es la que la lee quien no ve girar nada.
    expect(wrapper.find(".recomendacion__frase").exists()).toBe(false);
    expect(wrapper.get(".recomendacion__estado").text()).toBe(EN_CURSO);
    expect(wrapper.get(".recomendacion__estado").attributes("role")).toBe("status");

    // El giro es de la clase, que es lo que la hoja de estilo anima; y los tres
    // renglones con la forma del párrafo que viene siguen ahí, decorativos.
    expect(wrapper.classes()).toContain("recomendacion--redactando");
    expect(wrapper.findAll(".cargando__renglon")).toHaveLength(3);
    expect(wrapper.get(".cargando").attributes("aria-hidden")).toBe("true");
  });

  it("cuando la recomendación llega la escribe, en vez de ponerla de golpe", async () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: EN_CURSO, estado: "pendiente" as const } },
    });

    await wrapper.setProps({ recomendacion: { texto: TEXTO, estado: "lista" as const } });

    // Recién llegada: los renglones se van y el texto todavía no está entero.
    expect(wrapper.find(".cargando").exists()).toBe(false);
    expect(wrapper.get(".recomendacion__escrito").text().length).toBeLessThan(TEXTO.length);

    vi.advanceTimersByTime(MS_MAXIMO);
    await nextTick();

    expect(wrapper.get(".recomendacion__escrito").text()).toBe(TEXTO);
    expect(wrapper.get(".recomendacion__resto").text()).toBe("");
  });

  it("el hueco del texto está reservado desde el primer carácter", async () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: EN_CURSO, estado: "pendiente" as const } },
    });

    await wrapper.setProps({ recomendacion: { texto: TEXTO, estado: "lista" as const } });

    // Lo que falta por escribir está en el DOM en transparente: el párrafo mide
    // ya lo que va a medir acabado y nada de lo que hay debajo se mueve.
    expect(wrapper.get(".recomendacion__frase").text()).toBe(TEXTO);
    expect(wrapper.get(".recomendacion__resto").text()).not.toBe("");
  });

  it("hojear de un día redactado a otro no reteclea nada", async () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: TEXTO, estado: "lista" as const } },
    });

    await wrapper.setProps({ recomendacion: { texto: OTRO, estado: "lista" as const } });

    // No llegó nada: ya estaba escrita, así que se pone entera de una vez.
    expect(wrapper.get(".recomendacion__escrito").text()).toBe(OTRO);
    expect(wrapper.get(".recomendacion__resto").text()).toBe("");
  });

  it("una abstención se pinta quieta: no hay nada en camino", () => {
    const wrapper = mount(TarjetaRecomendacion, {
      props: { recomendacion: { texto: "No se muestra.", estado: "abstenida" as const } },
    });

    expect(wrapper.find(".cargando").exists()).toBe(false);
    expect(wrapper.classes()).not.toContain("recomendacion--redactando");
  });
});
