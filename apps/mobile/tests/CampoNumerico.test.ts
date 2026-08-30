import { type DOMWrapper, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { FieldCode, Interaccion, ValorCampo } from "@/api/contrato";
import CampoCuestionario from "@/components/cuestionario/CampoCuestionario.vue";

/** Lo que separa dos pulsaciones distintas de un rebote de la misma. */
const GESTO_MS = 150;
const REBOTE_MS = 12;

/**
 * El campo numérico con un padre de verdad detrás: lo que se emite vuelve como
 * prop, que es como lo monta el cuestionario.
 *
 * Las pulsaciones se despachan a mano y con su sello de reloj porque el control
 * distingue una pulsación de un rebote por ahí, y `trigger` no deja elegirlo:
 * todos sus eventos caerían dentro del mismo milisegundo.
 */
function montar(campo: FieldCode, inicial: number) {
  let valor: ValorCampo = inicial;
  let reloj = 1000;

  const wrapper = mount(CampoCuestionario, {
    props: {
      pregunta: { field_code: campo, highlighted: false, reason: "canonical_order", voi_nats: null },
      borrador: { valor, interaccion: "manual" as Interaccion },
      onResponder: (nuevo: ValorCampo) => {
        valor = nuevo;
      },
    },
  });

  const boton = (direccion: "mas" | "menos"): DOMWrapper<Element> =>
    wrapper.findAll("button.numero__paso")[direccion === "mas" ? 1 : 0]!;

  /** Un clic con su marca de reloj. `timeStamp` es de solo lectura: se fuerza. */
  const despachar = (destino: DOMWrapper<Element>, sello: number): void => {
    const evento = new MouseEvent("click", { bubbles: true });
    Object.defineProperty(evento, "timeStamp", { value: sello });
    destino.element.dispatchEvent(evento);
  };

  return {
    leer: () => valor as number,
    /** Una pulsación separada de la anterior lo bastante para ser otro gesto. */
    pulsar: async (direccion: "mas" | "menos") => {
      reloj += GESTO_MS;
      despachar(boton(direccion), reloj);
      await nextTick();
    },
    /** El mismo gesto, rebotado: otro despacho, pegado en el reloj. */
    rebotar: async (direccion: "mas" | "menos") => {
      reloj += REBOTE_MS;
      despachar(boton(direccion), reloj);
      await nextTick();
    },
    /** Dos llegadas del mismo despacho, como un oyente duplicado. */
    duplicar: async (direccion: "mas" | "menos") => {
      reloj += GESTO_MS;
      const destino = boton(direccion);
      despachar(destino, reloj);
      despachar(destino, reloj);
      await nextTick();
    },
    /** El padre escribe el campo por su cuenta, sin pasar por los pasos. */
    imponer: async (nuevo: number) => {
      valor = nuevo;
      await wrapper.setProps({ borrador: { valor, interaccion: "manual" as Interaccion } });
      await nextTick();
    },
  };
}

describe("los pasos del campo numérico", () => {
  it("cada pulsación cuenta, aunque el padre no haya repintado entre medias", async () => {
    // `sleep_hours` es `continuous`: su paso es medio, no uno.
    const campo = montar("sleep_hours", 1);

    await campo.pulsar("mas");
    await campo.pulsar("mas");
    expect(campo.leer()).toBe(2);

    await campo.pulsar("mas");
    await campo.pulsar("mas");
    expect(campo.leer()).toBe(3);
  });

  it("bajar tampoco pierde pulsaciones", async () => {
    const campo = montar("sleep_hours", 8);

    await campo.pulsar("menos");
    await campo.pulsar("menos");
    expect(campo.leer()).toBe(7);
  });

  it("un campo de cuenta avanza de uno en uno", async () => {
    const campo = montar("night_awakenings", 1);

    await campo.pulsar("mas");
    await campo.pulsar("mas");
    await campo.pulsar("mas");
    expect(campo.leer()).toBe(4);
  });

  it("el rebote de un gesto rápido no cuenta dos veces", async () => {
    // Despachos separados —el microtask ya se vació— pero pegados en el reloj.
    // Es lo que hace que despacio vaya bien y deprisa suba de dos en dos.
    const campo = montar("night_awakenings", 1);

    await campo.pulsar("mas");
    await campo.rebotar("mas");
    expect(campo.leer()).toBe(2);
  });

  it("y con medio paso el rebote se ve como que avanza uno entero", async () => {
    const campo = montar("sleep_hours", 1);

    await campo.pulsar("mas");
    await campo.rebotar("mas");
    expect(campo.leer()).toBe(1.5);
  });

  it("rebotar al bajar tampoco cuenta dos veces", async () => {
    const campo = montar("night_awakenings", 8);

    await campo.pulsar("menos");
    await campo.rebotar("menos");
    expect(campo.leer()).toBe(7);
  });

  it("dos llegadas del mismo despacho cuentan una", async () => {
    const campo = montar("night_awakenings", 1);

    await campo.duplicar("mas");
    expect(campo.leer()).toBe(2);
  });

  it("no se pasa del rango del catálogo", async () => {
    // `night_awakenings` va de 0 a 15.
    const techo = montar("night_awakenings", 15);
    await techo.pulsar("mas");
    expect(techo.leer()).toBe(15);

    const suelo = montar("night_awakenings", 0);
    await suelo.pulsar("menos");
    expect(suelo.leer()).toBe(0);
  });

  it("lo que llega de fuera sigue mandando sobre la cuenta local", async () => {
    const campo = montar("sleep_hours", 1);

    await campo.pulsar("mas");
    expect(campo.leer()).toBe(1.5);

    // El padre impone otro valor —se acepta una sugerencia, se reabre un día ya
    // enviado— y el paso siguiente tiene que partir de ahí, no de lo contado.
    await campo.imponer(10);
    await campo.pulsar("mas");
    expect(campo.leer()).toBe(10.5);
  });
});
