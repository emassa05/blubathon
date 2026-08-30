import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AvisoPendiente from "@/components/salud/AvisoPendiente.vue";

describe("AvisoPendiente", () => {
  it("la pastilla avisa de que hoy falta el cuestionario", () => {
    const wrapper = mount(AvisoPendiente, { props: { dia: "martes 25" } });

    expect(wrapper.get(".aviso__pastilla").text()).toBe("¡Hoy te falta el cuestionario!");
  });

  it("el disco lleva el icono y no lo anuncia dos veces", () => {
    const wrapper = mount(AvisoPendiente, { props: { dia: "martes 25" } });

    const insignia = wrapper.get(".aviso__insignia");
    expect(insignia.attributes("aria-hidden")).toBe("true");
    expect(insignia.find(".aviso__icono").exists()).toBe(true);
  });

  it("el CTA nombra el día pendiente y emite abrirFormulario", async () => {
    const wrapper = mount(AvisoPendiente, { props: { dia: "martes 25" } });

    const boton = wrapper.get("button");
    expect(boton.attributes("aria-label")).toBe("Abrir formulario pendiente del martes 25");

    await boton.trigger("click");
    expect(wrapper.emitted("abrirFormulario")).toHaveLength(1);
  });

  it("por defecto salta durante 5 segundos", () => {
    const wrapper = mount(AvisoPendiente, { props: { dia: "martes 25" } });

    expect(wrapper.classes()).toContain("aviso--animado");
    expect(wrapper.classes()).toContain("aviso--flotante");
    expect(wrapper.attributes("style")).toContain("--blubathon-dur: 5s");
  });

  it("acepta otra animación y recorta la duración al rango 3-9", () => {
    const wrapper = mount(AvisoPendiente, {
      props: { dia: "martes 25", animacion: "deslizamiento", duracion: 12 },
    });

    expect(wrapper.classes()).toContain("aviso--deslizamiento");
    expect(wrapper.attributes("style")).toContain("--blubathon-dur: 9s");
  });

  it("con animar en false no aplica ninguna clase de animación", () => {
    const wrapper = mount(AvisoPendiente, { props: { dia: "martes 25", animar: false } });

    expect(wrapper.classes()).not.toContain("aviso--animado");
    expect(wrapper.classes()).not.toContain("aviso--flotante");
  });
});
