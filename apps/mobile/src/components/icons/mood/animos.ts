import type { Component } from "vue";

import IconMoodCalm from "./IconMoodCalm.vue";
import IconMoodContent from "./IconMoodContent.vue";
import IconMoodHappy from "./IconMoodHappy.vue";

/**
 * Las caras que puede sacar la portada del cuestionario.
 *
 * Solo las buenas. `IconMoodSad`, `IconMoodDizzy` y `IconMoodNeutral` existen en
 * esta carpeta y **no** entran aquí a propósito: la cara sale antes de que se
 * conteste nada, así que no puede opinar sobre el día —una cara triste encima de
 * un formulario en blanco se lee como un diagnóstico, y no hay ninguno todavía.
 * Lo que dice la portada es "esto es agradable de hacer", nada más.
 */
export const ANIMOS_BUENOS: readonly Component[] = [IconMoodContent, IconMoodHappy, IconMoodCalm];

/**
 * Una cara al azar, y si se dice cuál había antes, otra distinta: el sorteo se
 * repite en cada paso del formulario y sacar dos veces la misma se lee como que
 * la portada se quedó colgada, no como azar.
 */
export function animoAlAzar(salvo?: Component): Component {
  const posibles = ANIMOS_BUENOS.filter((cara) => cara !== salvo);
  const entre = posibles.length === 0 ? ANIMOS_BUENOS : posibles;
  const cual = Math.floor(Math.random() * entre.length);
  return entre[cual] ?? IconMoodContent;
}
