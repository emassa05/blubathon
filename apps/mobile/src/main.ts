import "@fontsource/nunito/400.css";
import "@fontsource/nunito/500.css";
import "@fontsource/nunito/600.css";
import "@fontsource/nunito/700.css";

import "@/styles/reset.css";
import "@/styles/tokens.css";

import { createApp } from "vue";

import App from "@/App.vue";
import { aplicarFondo } from "@/theme/fondo";

// Antes de montar: la variante tiene que estar puesta cuando pinte el primer
// fotograma, o se vería el fondo plano y luego el degradado entrando.
aplicarFondo();

createApp(App).mount("#app");
