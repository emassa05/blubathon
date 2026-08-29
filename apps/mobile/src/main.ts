import "@fontsource/nunito/400.css";
import "@fontsource/nunito/500.css";
import "@fontsource/nunito/600.css";
import "@fontsource/nunito/700.css";

import "@/styles/reset.css";
import "@/styles/tokens.css";

import { createApp } from "vue";

import App from "@/App.vue";
import { ES_TERAPEUTA } from "@/api/config";
import { aplicarFondo } from "@/theme/fondo";

// Antes de montar: la variante tiene que estar puesta cuando pinte el primer
// fotograma, o se vería el fondo plano y luego el degradado entrando.
aplicarFondo();

// El perfil se decide en el arranque y no cambia. Lo único que cuelga de él
// aquí es el color de fuera del lienzo: el panel del terapeuta no lleva
// burbujas y su rebote es el plano de su propia página (`tokens.css`).
if (ES_TERAPEUTA) document.documentElement.dataset.rol = "terapeuta";

createApp(App).mount("#app");
