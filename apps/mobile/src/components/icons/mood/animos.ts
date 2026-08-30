import type { Component } from "vue";

import IconMoodBlush from "./IconMoodBlush.vue";
import IconMoodContent from "./IconMoodContent.vue";
import IconMoodHappy from "./IconMoodHappy.vue";
import IconMoodLaugh from "./IconMoodLaugh.vue";
import IconMoodSparkle from "./IconMoodSparkle.vue";
import IconMoodWink from "./IconMoodWink.vue";

/**
 * Las caras que puede sacar la portada del cuestionario.
 *
 * Solo las buenas. `IconMoodSad`, `IconMoodDizzy` y `IconMoodNeutral` existen en
 * esta carpeta y **no** entran aquí a propósito: la cara sale antes de que se
 * conteste nada, así que no puede opinar sobre el día —una cara triste encima de
 * un formulario en blanco se lee como un diagnóstico, y no hay ninguno todavía.
 * Lo que dice la portada es "esto es agradable de hacer", nada más.
 *
 * Y entre las buenas, cada una tiene que distinguirse de un vistazo: la mitad
 * del efecto está en que cambiar de paso se note. Por eso cada una lleva su
 * propio tono y su propia combinación de ojos y boca, y por eso no hay ninguna
 * azul —la portada ya es celeste y una cara azul se disuelve en ella—. La calma
 * celeste que hubo aquí se borró por eso mismo: puntos por ojos y un arco por
 * boca, lo mismo que la amarilla, y entre las dos solo cambiaba el color.
 */
export const ANIMOS_BUENOS: readonly Component[] = [
  IconMoodContent,
  IconMoodHappy,
  IconMoodWink,
  IconMoodLaugh,
  IconMoodBlush,
  IconMoodSparkle,
];

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
