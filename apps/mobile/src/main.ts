import "@fontsource/nunito/400.css";
import "@fontsource/nunito/500.css";
import "@fontsource/nunito/600.css";
import "@fontsource/nunito/700.css";

import "@/styles/reset.css";
import "@/styles/tokens.css";

import { createApp } from "vue";

import App from "@/App.vue";
import { ES_TERAPEUTA } from "@/api/config";
import { VARIABLE_REBOTE, aplicarFondo } from "@/theme/fondo";

// Antes de montar: la variante tiene que estar puesta cuando pinte el primer
// fotograma, o se vería el fondo plano y luego el degradado entrando.
aplicarFondo();

/*
 * El perfil se decide en el arranque y no cambia, y lo único que cuelga de él
 * aquí es el color de fuera del lienzo.
 *
 * El panel del terapeuta sí usa el fondo con burbujas —lo lleva dentro el
 * widget de la IA—, pero su página es el color plano. Un rebote azul debajo de
 * una página que no lo es sería el mismo corte, al revés.
 */
if (ES_TERAPEUTA) {
  document.documentElement.style.setProperty(VARIABLE_REBOTE, "var(--blubathon-fondo-final)");
}

createApp(App).mount("#app");
