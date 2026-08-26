# Faro móvil — pantalla Salud

Interfaz visual de Faro en **Vue 3 + Vite + TypeScript**. Es una página
responsive de una sola vista, `Salud`, implementada contra una especificación
cerrada de diseño. No hay router, ni store, ni más pantallas: no es un
descuido, es el alcance.

Sin librerías de UI, sin librería de iconos y **sin un solo archivo de imagen**.
Todo el estilo son `<style scoped>` y variables CSS; los iconos y el horizonte del panel son SVG inline en componentes propios; la animación son `@keyframes`, no JavaScript.

---

## 1. Cómo correrlo

Desde la raíz del repositorio (pnpm workspace):

```bash
pnpm install
pnpm --dir apps/mobile dev        # http://localhost:5173
```

O desde este directorio:

```bash
pnpm dev          # servidor de desarrollo
pnpm build        # vue-tsc --noEmit && vite build
pnpm preview      # sirve dist/
pnpm test         # Vitest (incluye un pase de axe sobre la pantalla)
pnpm typecheck    # vue-tsc --noEmit
pnpm lint         # ESLint (vue + vuejs-accessibility), 0 warnings
pnpm format       # Prettier
```

No hay marco de prototipo ni barra de estado simulada: es una página. El
contenido va en una columna que se adapta:

| Ancho de viewport | Qué hace la columna                                |
| ----------------- | -------------------------------------------------- |
| hasta 480px       | ocupa todo el ancho; los paddings (24) son fijos   |
| a partir de 480px | se queda en 480 y se centra, con el fondo a sangre |

En vertical, la columna toma como referencia el alto del diseño (844px): en una
ventana más alta no se estira sin fin, mantiene esa proporción; en una más baja,
la página se desplaza como cualquier otra. A 390 × 844 —el tamaño del diseño— la
pantalla entra entera, sin desplazamiento. No hay ni un solo punto de corte por
ancho: el ajuste sale de `max-width`, `min(100dvh, ...)` y `flex`. El único
`@media` del código es el de `prefers-reduced-motion`.

---

## 2. Las tres bandas

El riesgo del día no solo cambia una cifra: cambia el color de la pantalla.

| Banda   | Riesgo   | Tono            |
| ------- | -------- | --------------- |
| `bajo`  | 0 – 24   | celeste pastel  |
| `medio` | 25 – 50  | amarillo pastel |
| `alto`  | 51 – 100 | rojo pastel     |

`theme/riesgo.ts` es el único sitio donde viven los cortes. Traduce el riesgo en
una banda, y la banda en una clase (`faro-banda--bajo`, `--medio`, `--alto`).
Esa clase la pone `SaludView` en la columna y **lleva la paleta entera** —panel,
horizonte, textos y tarjeta de recomendación— desde `styles/tokens.css`.

Ningún componente conoce las bandas. Todos consumen los mismos
`var(--faro-panel)`, `var(--faro-texto-fuerte)`, `var(--faro-rec-hoja)`… y el
color correcto les llega por herencia. Añadir una cuarta banda es añadir su
corte en `riesgo.ts` y su paleta en `tokens.css`: cero cambios en componentes.

Las tres siguen el mismo patrón, para que los tres estados se vean de una pieza:

- un pastel para el panel,
- tres tonos cada vez más profundos para las capas del horizonte,
- dos oscuros del mismo tono para el texto,
- y el tono dos pasos más claro para la tarjeta de recomendación, que acompaña
  al estado sin competir con él.

### El botón de prueba

Abajo a la izquierda del panel hay una pastilla blanca `PRUEBA · BAJO` que
recorre las tres bandas al pulsarla. Es **temporal**, y está marcada con
`TODO(spec)` en `SaludView.vue` y en `riesgo.ts`.

Vive en el hueco que el panel deja por debajo del texto, así que no le cuesta ni
un píxel de alto a la composición: al quitarlo, la pantalla queda exactamente
igual. Cambia el riesgo mostrado a uno representativo de cada banda
(`RIESGO_DE_PRUEBA`), sin tocar el mock.

---

## 3. El panel

El fondo de la cabecera es un gradiente de la banda —casi blanco arriba, con el
color abajo— y un **horizonte de tres capas** encima. El texto cae siempre en la
parte clara, que es donde más contraste hay, y el color se concentra abajo, que
es donde se ve la cúpula.

El horizonte no es adorno neutro: **la forma dice el estado**. Con riesgo bajo
está abajo y casi plano; según sube el riesgo sube también y se agita, más alto
y más frecuente. Cada curva es una suma de dos senos —uno lento y otro rápido y
más pequeño— muestreada y suavizada con puntos medios, para que ondule sin
repetirse de forma evidente. Están en `FondoRiesgo.vue`, tres siluetas por
banda; el color lo pone la banda, no el componente.
`preserveAspectRatio="none"` solo estira en horizontal, que en una onda no se
nota, y nunca en vertical, que sí.

El alto (`--faro-panel-alto`, 296px) es un mínimo, no un alto fijo: si el texto
crece con el zoom, el panel crece con él. Y tiene que contar con la cúpula, que
le tapa 44px del centro: con menos, la pastilla de confianza queda pegada a la
curva y parece que se sale. La barra de estado del dispositivo
(`env(safe-area-inset-top)`) se suma al acolchado de arriba en vez de comerse el
panel.

### Cómo termina el panel

Abajo no lleva radio. El contenido **sube sobre él** y lo recorta con una
cúpula: el panel llega más abajo por los lados que por el centro. No es un
`border-radius` en las esquinas —eso deja dos curvas y un tramo recto en medio—
sino los dos radios de arriba del contenido con el eje horizontal al 50%:

```css
border-radius: 50% 50% 0 0 / var(--faro-cupula) var(--faro-cupula) 0 0;
```

Las dos elipses se encuentran justo en el centro y forman un arco continuo de
lado a lado. El contenido lleva el color de la página, así que lo único que se
ve es el corte, y el acolchado de arriba devuelve exactamente lo que se comió el
margen negativo: la cúpula no cuesta ni un píxel de alto.

### Elevación

Dos niveles, y no más:

| Nivel | Qué                        | Sombra                    |
| ----- | -------------------------- | ------------------------- |
| 0     | el panel                   | ninguna: es la superficie |
| 1     | todas las tarjetas         | `--faro-elev-1`           |
| 2     | el botón naranja del aviso | `--faro-elev-2`           |

Cada nivel son **dos capas**: un contacto corto y pegado, que asienta la pieza,
y una difusa y muy abierta, que da la altura. Una sola capa grande siempre acaba
pareciendo una mancha.

Las tarjetas están todas al mismo nivel, la de recomendación incluida: lo que la
distingue es el color, no la altura. Variar la elevación por decoración rompe la
única cosa que la elevación comunica.

El tono de la sombra es frío y neutro, no verde: una sombra teñida delata el
color del fondo que había cuando se eligió, y aquí el fondo cambia con la
banda.

---

## 4. El mapa

```text
src/
  main.ts                      monta la app y carga fuentes, reset y tokens
  App.vue                      raíz: solo monta la vista
  views/SaludView.vue          la página: dueña de los datos, del layout y de la banda
  components/salud/            NavegadorFecha, CabeceraRiesgo, FondoRiesgo,
                               TarjetaRecomendacion, FondoRecomendacion,
                               TarjetaFactores, TarjetaFormularios,
                               AvisoPendiente
  components/icons/            IconoLuna, IconoRombo, IconoPortapapeles,
                               IconoInfo, IconoEscudo, IconoDestello,
                               IconoChevron
  composables/                 useDiaSeleccionado
  data/saludMock.ts            los datos ficticios
  types/salud.ts               el contrato de la pantalla
  theme/riesgo.ts              cortes de banda, clases y riesgos de prueba
  theme/tokens.ts              tokens que necesita la lógica (animación, rango)
  styles/tokens.css            tokens CSS: paleta por banda, escala, medidas
  styles/reset.css             reset mínimo
tests/                         un test por componente + composable + axe
```

Los componentes de `components/` son presentacionales puros: reciben `props`
tipadas, emiten eventos (`diaAnterior`, `diaSiguiente`, `masInfo`, `verMas`,
`abrirFormulario`) y no tocan red ni estado global.

`FondoRecomendacion` habla el mismo idioma que el panel —líneas de nivel— pero
dibuja otra figura: un solo relieve, anclado a la esquina de abajo a la derecha.
Las elipses van descentradas unas de otras a propósito; concéntricas perfectas
parecen una diana, no un mapa.

La tarjeta va **alineada a la izquierda**, con una insignia redonda delante del
rótulo. Una frase de dos líneas centrada obliga a buscar el principio de cada
una, y aquí lo que se lee es la frase, no el rótulo. El relieve vive solo en la
esquina, fuera de la caja del texto, en vez de pasar por detrás de las palabras.

---

## 5. Qué es mock y dónde entra la API real

Todo lo que se ve son datos ficticios de `src/data/saludMock.ts`, detrás del
tipo `ResumenSalud` (`src/types/salud.ts`).

**`SaludView.vue` es el único punto de entrada de datos:**

```ts
// src/views/SaludView.vue
const resumen = RESUMEN_SALUD_MOCK;
```

Sustituir esa línea por la respuesta del endpoint —o por un store— es todo lo
que hay que tocar para conectar la API: si respeta `ResumenSalud`, ningún
componente cambia, y el color de la pantalla sale solo del `riesgo`.

Tres puntos de conexión, marcados en el código con `TODO(spec)`:

| Qué                          | Dónde                         | Estado                                 |
| ---------------------------- | ----------------------------- | -------------------------------------- |
| Popup del riesgo (icono `!`) | `SaludView.masInfo()`         | vacío: solo existe el disparador       |
| Abrir el formulario del día  | `SaludView.abrirFormulario()` | vacío: no hay navegación en el alcance |
| Ver todos los formularios    | `SaludView.verMas()`          | vacío: ídem                            |

---

## 6. La animación del aviso "Pendiente"

`AvisoPendiente` acepta tres props con valores por defecto:

```vue
<AvisoPendiente :animar="true" animacion="pulso" :duracion="5" />
```

- `animar: boolean = true`
- `animacion: 'pulso' | 'aparicion' | 'deslizamiento' = 'pulso'`
- `duracion: number = 5` segundos, recortada al rango 3–9 con paso 0.5
  (`normalizarDuracion` en `theme/tokens.ts`)

La duración viaja por la variable CSS `--faro-dur`; los `@keyframes` están
escritos en el CSS del componente, nunca generados desde JavaScript.

`@media (prefers-reduced-motion: reduce)` anula la animación aunque `animar`
sea `true`, y lo hace por especificidad (dos clases), sin `!important`.

---

## 7. Accesibilidad

Lo que la pantalla garantiza:

- `<button>` para todo lo pulsable, `<h1>`/`<h2>` para la jerarquía real,
  `<ul>/<li>` en las dos listas, `<header>` para la cabecera del riesgo.
- Área táctil de 44 × 44 en chevrons, el icono `!`, `ver más`, el botón naranja
  y la pastilla de prueba: el padding crece y un margen negativo devuelve el
  espacio, así que el diseño no se mueve. En el icono `!` el margen es
  asimétrico, para que en la línea ocupe lo mismo que su glifo más el hueco de 6
  y no descoloque el sobretítulo.
- `aria-label` en los chevrons, el icono `!`, `ver más`, el CTA —que nombra el
  día— y la pastilla de prueba, que dice a qué banda va a cambiar.
- El riesgo se anuncia una sola vez: `role="group"` con
  `aria-label="Riesgo de desregulación: 18 por ciento"` y las partes visuales
  en `aria-hidden`. El icono `!` queda **fuera** de ese `aria-hidden`: es un
  control con su propio nombre.
- El color no informa solo: la banda cambia el tono, pero el dato sigue siendo
  la cifra y el sobretítulo, que se leen igual en las tres.
- SVG decorativos con `aria-hidden="true"` y `focusable="false"`; en la tarjeta
  de recomendación el `aria-hidden` está en el envoltorio del fondo, y el test
  comprueba que ningún dibujo quede expuesto, esté donde esté el atributo.
- `:focus-visible` con anillo de 2px y `outline-offset`; ningún `outline: none`
  sin sustituto. Sobre el panel el anillo toma el color fuerte de la banda, así
  que nunca se pierde contra el fondo. El orden de tabulación es el del DOM.
- El día seleccionado vive en una región `aria-live="polite"`.
- Junto al punto verde/gris de cada formulario va siempre `Respondido` /
  `Sin responder`.
- Tipografía en `rem`, para que el zoom de texto funcione. Al 200% —de página o
  solo de texto— no hay recortes ni solapes, y no aparece desplazamiento
  horizontal a ningún ancho entre 320px y pantalla completa: el layout está en
  flujo normal, sin posiciones absolutas salvo las capas decorativas.
- `pnpm lint` incluye `eslint-plugin-vuejs-accessibility` con 0 warnings, y
  `tests/accesibilidad.test.ts` corre axe-core sobre la pantalla montada
  (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `best-practice`): 0 violaciones.

Hay **una** excepción de lint, en `CabeceraRiesgo.vue`:
`vuejs-accessibility/heading-has-content` solo mira el texto del encabezado y no
su `aria-label`, así que marca como vacío un `<h1>` que sí tiene nombre
accesible. Está silenciada en esa línea y explicada allí.

### Contrastes verificados

El fondo es un gradiente, así que los ratios se calculan, no se miden. Se
reportan **contra la onda más profunda**, que es lo más oscuro que puede quedar
debajo de una letra, y contra la parte más oscura del gradiente.

| Par                                    | bajo   | medio  | alto   | Mínimo AA |
| -------------------------------------- | ------ | ------ | ------ | --------- |
| La cifra sobre la onda más profunda    | 6.02:1 | 6.30:1 | 5.96:1 | 3:1       |
| Fecha y sobretítulo sobre el gradiente | 7.70:1 | 7.32:1 | 8.43:1 | 4.5:1     |
| Sobretítulo sobre el panel             | 6.17:1 | 6.20:1 | 6.34:1 | 4.5:1     |
| La confianza sobre su pastilla         | 6.81:1 | 6.60:1 | 7.38:1 | 4.5:1     |
| `RECOMENDACIÓN DE HOY` sobre blanco    | 8.38:1 | 7.85:1 | 9.28:1 | 4.5:1     |
| El destello sobre su insignia          | 5.92:1 | 5.83:1 | 6.50:1 | 3:1       |

Dos piezas quedan **fuera de las bandas**, con el mismo valor siempre, porque no
hablan del riesgo del día: la pastilla de prioridad (6.02:1 sobre su fondo) y el
aviso pendiente —`PENDIENTE` 5.23:1 sobre la crema, su título 9.32:1 y el icono
blanco sobre el naranja 3.86:1—.

Las ondas del panel y el lavado de la recomendación no portan información: son
textura, y el texto que va encima se mide contra ellas.

**Tarjetas blancas.** No dependen de la banda. Pasan `verdeProfundo` 12.5:1,
`verdeTitulo` 11.6:1, `verdeTexto` 9.1:1, `verdeAccion` 5.3:1, `alertaTexto`
sobre `alertaFondo` 4.7:1, `naranjaEtiqueta` 5.1:1 y `naranjaTitulo` 9.1:1.

Ya no queda ningún par por debajo de AA. El único que fallaba era `grisTexto`
—el subtítulo de "Lo más importante hoy", el detalle de cada factor y el estado
de cada formulario— con 4.26:1; bajarlo a `oklch(0.55 0.015 168)` lo deja en
4.8:1.

Los puntos de estado quedan en 2.75:1 (`puntoActivo`) y 1.52:1
(`puntoInactivo`) sobre blanco. No incumplen 1.4.11 porque no portan
información por sí solos —el texto de estado va al lado—, pero como señal
visual son débiles.

axe no puede comprobar contraste en jsdom (no hay layout); estos números salen
del cálculo directo sobre los `oklch()` de `tokens.css`, no del test: la puerta
automática no ve un fallo de contraste, hay que mirarlo a mano.

---

## 8. Lo que falta para producción

- **Datos reales.** Conectar `ResumenSalud` a la API y decidir estados de carga
  y de error, que el diseño no cubre.
- **Quitar el botón de prueba** y `RIESGO_DE_PRUEBA` cuando el riesgo venga de
  la API. Los dos están marcados con `TODO(spec)`.
- **Borrar `public/`.** `HeroNoRisk.png` y `RecomendacionHoy.png` son de la
  versión anterior y ya no los usa nadie; siguen entrando en el build.
- **El popup del riesgo.** El icono `!` ya está, con su área táctil y su nombre
  accesible, pero `masInfo()` está vacío: falta el contenido y el patrón de
  diálogo (foco atrapado, `Esc`, retorno del foco).
- **Navegación.** `abrirFormulario` y `verMas` están vacíos: hoy no hay router
  ni destino.
- **El día no cambia los datos.** Los chevrons mueven la fecha, pero el resumen
  sigue siendo el mismo: falta el fetch por día.
- **Navegación de los formularios.** Cada fila ya es un botón y emite
  `abrirRegistro(id)`, pero `SaludView` no tiene adónde llevarla.
- **Verificación con lectores de pantalla reales** (VoiceOver / TalkBack) y en
  dispositivo, no solo axe en jsdom.
- **CI.** El gate del repositorio (`.github/workflows/p2.yml`) todavía solo
  corre `apps/web`. Faltan los cuatro pasos equivalentes para `apps/mobile`.
- **Iconos.** Los seis SVG están dibujados a mano contra la descripción del
  diseño; conviene contrastarlos con los originales.
