# Faro móvil — pantalla Salud

Interfaz visual de Faro en **Vue 3 + Vite + TypeScript**, conectada a la API de
`apps/api`. Es una página responsive de una sola vista, `Salud`, implementada
contra una especificación cerrada de diseño. No hay router, ni store, ni más
pantallas: no es un descuido, es el alcance.

Sin librerías de UI, sin librería de iconos y **sin un solo archivo de imagen**.
Todo el estilo son `<style scoped>` y variables CSS; los iconos y el horizonte del panel son SVG inline en componentes propios; la animación son `@keyframes`, no JavaScript.

---

## 1. Cómo correrlo

Hacen falta las dos mitades. Primero el backend, desde la raíz del repositorio:

```bash
uvicorn apps.api.main:_default_app --factory --port 8000
```

Y después la interfaz (pnpm workspace):

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

Sin backend la pantalla no queda rota: muestra el mensaje de error del sobre y
el panel en gris. Con backend pero sin datos —una base recién sembrada— muestra
el día sin estimación, que es un estado real, no un fallo.

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

## 2. Las cuatro bandas

El riesgo del día no solo cambia una cifra: cambia el color de la pantalla.

| Banda         | Riesgo    | Tono            |
| ------------- | --------- | --------------- |
| `desconocido` | sin cifra | gris            |
| `bajo`        | 0 – 19    | celeste pastel  |
| `medio`       | 20 – 49   | amarillo pastel |
| `alto`        | 50 – 100  | rojo pastel     |

Los cortes son los del backend (`p ≥ 0.5 → high`, `0.2 ≤ p < 0.5 → medium`).
Tienen que serlo: cuando la API declara la banda, la pantalla usa la suya, y dos
juegos de cortes harían que el color se contradijera con el dato.

**`desconocido` no es un cuarto nivel de riesgo: es la ausencia de estimación.**
El modelo se abstiene cuando no tiene resultados verificados suficientes
(SPEC 8.5), y entonces la pantalla escribe `—` en vez de una cifra, esconde la
pastilla de confianza y se pone gris. Pintar la abstención de celeste la leería
como riesgo bajo, que es justo lo que el backend no dijo.

`theme/riesgo.ts` es el único sitio donde viven los cortes. Traduce el riesgo en
una banda, y la banda en una clase (`faro-banda--desconocido`, `--bajo`,
`--medio`, `--alto`). Esa clase la pone `SaludView` en la columna y **lleva la
paleta entera** —panel, horizonte, textos y tarjeta de recomendación— desde
`styles/tokens.css`.

Ningún componente conoce las bandas. Todos consumen los mismos
`var(--faro-panel)`, `var(--faro-texto-fuerte)`, `var(--faro-rec-hoja)`… y el
color correcto les llega por herencia. Añadir otra banda es añadir su corte en
`riesgo.ts` y su paleta en `tokens.css`: cero cambios en componentes. La cuarta
—`desconocido`— entró así, sin tocar ni un componente salvo la cabecera, que
tuvo que aprender a no escribir cifra.

Todas siguen el mismo patrón, para que los estados se vean de una pieza:

- un pastel para el panel,
- tres tonos cada vez más profundos para las capas del horizonte,
- dos oscuros del mismo tono para el texto,
- y el tono dos pasos más claro para la tarjeta de recomendación, que acompaña
  al estado sin competir con él.

`desconocido` lo sigue con un gris de croma casi nulo, y reusa las siluetas de
`bajo`: son las más planas, y sin estimación no hay agitación que dibujar.

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
  api/config.ts                origen, niño y timeout, todo por variables de entorno
  api/http.ts                  el único `fetch` del frontend
  api/errores.ts               `ErrorFaro`: el sobre del backend, ya traducido
  api/faro.ts                  un envoltorio tipado por ruta de `apps/api`
  api/eventos.ts               el canal WebSocket de recomendaciones
  adaptadores/resumenSalud.ts  de las respuestas de la API al contrato de la pantalla
  components/salud/            NavegadorFecha, CabeceraRiesgo, FondoRiesgo,
                               TarjetaRecomendacion, FondoRecomendacion,
                               TarjetaFactores, TarjetaFormularios,
                               AvisoPendiente
  components/icons/            IconoLuna, IconoRombo, IconoPortapapeles,
                               IconoInfo, IconoEscudo, IconoDestello,
                               IconoChevron
  composables/                 useDiaSeleccionado, useResumenSalud
  types/salud.ts               el contrato de la pantalla
  theme/riesgo.ts              cortes de banda y clases
  theme/tokens.ts              tokens que necesita la lógica (animación, rango)
  styles/tokens.css            tokens CSS: paleta por banda, escala, medidas
  styles/reset.css             reset mínimo
tests/                         un test por componente + composable + adaptador +
                               transporte + axe, sobre `servidorFalso.ts`
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

## 5. La API

Cuatro capas, y cada una sabe una cosa sola:

```text
componentes      props tipadas. No saben que existe una red.
  ↑
SaludView        pide un día, pinta carga / error / datos
  ↑
useResumenSalud  el día visible como estado reactivo: cancela, reintenta, falla
  ↑
adaptadores/     traduce la API al contrato de la pantalla
  ↑
api/faro.ts      un envoltorio tipado por ruta
  ↑
api/http.ts      el único `fetch`: URL, cabeceras, sobre de error
```

### Los tipos salen del backend

`@faro/contract` es el contrato ejecutable que genera
`python -m tools.contracts.generate` desde el mismo esquema que valida
`apps/api`. El frontend lo importa como dependencia del workspace, así que
**cambiar el contrato rompe la compilación de la interfaz**, no el navegador de
alguien. Los rótulos de campo y los textos genéricos vienen del mismo sitio
(`FARO_TEXTS_ES`): ningún componente inventa copy que el backend ya publica.

Solo se importan los tipos y las tablas (`@faro/contract/contract`,
`/texts`, `/constants`), no los esquemas Zod. No hay validación en tiempo de
ejecución a propósito: los esquemas generados son `.strict()` y las vistas HTTP
añaden campos sobre el modelo base, así que validar rechazaría respuestas
correctas. El contrato es la puerta.

### CORS y el proxy

En desarrollo el navegador ve **un solo origen**: `/v1` y `/health` salen de
`localhost:5173` y el proxy de `vite.config.ts` los lleva al backend. Ni
preflight ni allowlist que mantener en dos sitios. Para producción,
`VITE_FARO_API_URL` apunta al backend directamente y ese origen tiene que estar
en `BLUBATHON_CORS_ORIGINS`.

Ver `.env.example` para las cuatro variables. Ninguna es obligatoria.

### Qué mapea a qué

| Lo que muestra la pantalla | De dónde sale                                                                  |
| -------------------------- | ------------------------------------------------------------------------------ |
| Cifra de riesgo            | `history[dia].prediction.probability × 100`, track `real_personal_baseline_v1` |
| Nivel de confianza         | ancho del intervalo 5-95 del posterior Beta: `(1 − (sup − inf)) × 100`         |
| Recomendación de hoy       | `GET /recommendations/today`; otros días, la del episodio                      |
| Lo más importante hoy      | preguntas `highlighted` de `POST /form-plan`                                   |
| Últimos formularios        | calendario de 4 días, cruzado con los envíos de `GET /history`                 |
| Aviso "Pendiente"          | el día visible no tiene `submission_id`                                        |

Dos decisiones que conviene conocer antes de tocar el adaptador:

- **La confianza es derivada, no un campo.** El backend no publica un "nivel de
  confianza"; publica un intervalo. Un intervalo estrecho es exactamente lo que
  esa frase quiere decir, y sin intervalo la pastilla desaparece en vez de
  mostrar un número por defecto.
- **"Lo más importante hoy" no son causas del riesgo.** El track visible es una
  tasa observada y no pondera predictores, así que no hay importancias que
  mostrar. Lo que se lista es lo que el formulario prioriza preguntar
  (SPEC 6.9), y el subtítulo de la tarjeta lo dice con esas palabras. Solo
  aplica al día de hoy: para un día pasado la tarjeta queda vacía, porque el
  plan de hoy no describe aquel día.

### Estados que el diseño no cubría

| Estado                 | Qué se ve                                               |
| ---------------------- | ------------------------------------------------------- |
| Cargando               | tarjeta con "Cargando…", panel gris, `role="status"`    |
| Error                  | tarjeta con el `message_es` del backend, `role="alert"` |
| El modelo se abstiene  | `—` en vez de cifra, sin pastilla de confianza, gris    |
| Sin formulario ese día | la recomendación lo dice, y el aviso naranja aparece    |
| El RAG se abstiene     | la tarjeta dice **por qué** (los tres motivos del SPEC) |

Cambiar de día cancela la petición anterior: al pulsar el chevron varias veces
seguidas, una respuesta que llegue tarde no puede pisar al día que se está
mirando. Y al fallar, el resumen se vacía en vez de quedarse con el del día
anterior — una cifra de riesgo bajo la fecha equivocada es peor que no mostrar
cifra.

### Llamadas listas sin pantalla que las use

La pantalla Salud solo lee. `api/faro.ts` cubre **todas** las rutas de
`apps/api/routes/v1.py`, tenga o no la interfaz un destino todavía:

| Llamada                                                   | Estado                                   |
| --------------------------------------------------------- | ---------------------------------------- |
| `planFormulario`, `enviarFormulario`                      | listas; falta la pantalla del formulario |
| `valorarRecomendacion`                                    | lista; falta el control de pulgar        |
| `listarSolicitudesDeResultado`, `reportarResultado`       | listas; falta la pantalla de resultado   |
| `obtenerNino`, `obtenerEpisodio`, `listarRecomendaciones` | listas; sin vista que las pida           |
| `conectarEventos` (WebSocket)                             | lista; el RAG avisa cuando termina       |

El WebSocket importa más de lo que parece: el RAG corre **después** de guardar
el formulario, así que la recomendación no viaja en la respuesta del `POST`.
Llega por `recommendation.ready`.

Tres puntos de navegación siguen vacíos, marcados con `TODO(spec)`:

| Qué                          | Dónde                         | Estado                             |
| ---------------------------- | ----------------------------- | ---------------------------------- |
| Popup del riesgo (icono `!`) | `SaludView.masInfo()`         | vacío: solo existe el disparador   |
| Abrir el formulario del día  | `SaludView.abrirFormulario()` | falta el destino, no el transporte |
| Ver todos los formularios    | `SaludView.verMas()`          | ídem                               |

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
- Área táctil de 44 × 44 en chevrons, el icono `!`, `ver más` y el botón
  naranja: el padding crece y un margen negativo devuelve el espacio, así que el
  diseño no se mueve. En el icono `!` el margen es asimétrico, para que en la
  línea ocupe lo mismo que su glifo más el hueco de 6 y no descoloque el
  sobretítulo.
- `aria-label` en los chevrons, el icono `!`, `ver más` y el CTA, que nombra el
  día.
- El riesgo se anuncia una sola vez: `role="group"` con
  `aria-label="Riesgo de desregulación: 18 por ciento"` y las partes visuales
  en `aria-hidden`. Sin estimación la etiqueta lo dice —"sin estimación
  todavía"— en vez de leer el guion. El icono `!` queda **fuera** de ese
  `aria-hidden`: es un control con su propio nombre.
- El color no informa solo: la banda cambia el tono, pero el dato sigue siendo
  la cifra y el sobretítulo, que se leen igual en las cuatro.
- Carga y error se anuncian: `role="status"` y `role="alert"`.
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

| Par                                    | bajo   | medio  | alto   | descon. | Mínimo AA |
| -------------------------------------- | ------ | ------ | ------ | ------- | --------- |
| La cifra sobre la onda más profunda    | 6.02:1 | 6.30:1 | 5.96:1 | 6.11:1  | 3:1       |
| Fecha y sobretítulo sobre el gradiente | 7.70:1 | 7.32:1 | 8.43:1 | 7.22:1  | 4.5:1     |
| Sobretítulo sobre el panel             | 6.17:1 | 6.20:1 | 6.34:1 | 5.85:1  | 4.5:1     |
| La confianza sobre su pastilla         | 6.81:1 | 6.60:1 | 7.38:1 | —       | 4.5:1     |
| `RECOMENDACIÓN DE HOY` sobre blanco    | 8.38:1 | 7.85:1 | 9.28:1 | 7.76:1  | 4.5:1     |
| El destello sobre su insignia          | 5.92:1 | 5.83:1 | 6.50:1 | 5.58:1  | 3:1       |

La columna `desconocido` sale del mismo cálculo sobre los `oklch()` de la banda.
La pastilla de confianza no tiene número porque en esa banda no se dibuja: sin
estimación no hay confianza que dar.

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

- **La pantalla del formulario.** Es lo que falta para cerrar el círculo: hoy la
  pantalla lee, pero nadie puede escribir. `planFormulario` y `enviarFormulario`
  ya están, tipadas y probadas; falta la vista.
- **Reaccionar al WebSocket.** `conectarEventos` existe pero nadie se suscribe:
  cuando el RAG termina, la pantalla no se entera hasta que se recarga.
- **Reintentar desde la tarjeta de error.** `useResumenSalud` expone `recargar`,
  pero la tarjeta no ofrece el botón; hoy hay que recargar la página.
- **Borrar `public/`.** `HeroNoRisk.png` y `RecomendacionHoy.png` son de la
  versión anterior y ya no los usa nadie; siguen entrando en el build.
- **El popup del riesgo.** El icono `!` ya está, con su área táctil y su nombre
  accesible, pero `masInfo()` está vacío: falta el contenido y el patrón de
  diálogo (foco atrapado, `Esc`, retorno del foco). Es el sitio donde va el
  `intendedUseEs` del contrato, que hoy no se muestra en ninguna parte.
- **Navegación.** `abrirFormulario` y `verMas` están vacíos: hoy no hay router
  ni destino.
- **Navegación de los formularios.** Cada fila ya es un botón y emite
  `abrirRegistro(id)` con la fecha ISO del día, pero `SaludView` no tiene adónde
  llevarla.
- **Selector de niño.** Sin `?child_id=` ni `VITE_FARO_CHILD_ID` se toma el
  primero de `GET /v1/children`. Con más de uno, hace falta elegir.
- **Verificación con lectores de pantalla reales** (VoiceOver / TalkBack) y en
  dispositivo, no solo axe en jsdom.
- **CI.** El gate del repositorio (`.github/workflows/p2.yml`) todavía solo
  corre `apps/web`. Faltan los cuatro pasos equivalentes para `apps/mobile`.
- **Iconos.** Los seis SVG están dibujados a mano contra la descripción del
  diseño; conviene contrastarlos con los originales.
