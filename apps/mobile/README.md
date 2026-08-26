# Faro móvil — pantalla Salud

Interfaz visual de Faro en **Vue 3 + Vite + TypeScript**. Contiene una sola
pantalla, `Salud`, implementada contra una especificación cerrada de diseño.
No hay router, ni store, ni más pantallas: no es un descuido, es el alcance.

Sin librerías de UI y sin librería de iconos. Todo el estilo son
`<style scoped>` y variables CSS; los iconos son SVG inline en componentes
propios; la animación son `@keyframes`, no JavaScript.

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

La pantalla se ve de dos formas y las dos salen del mismo componente:

| Ancho de viewport    | Qué se ve                                                                             |
| -------------------- | ------------------------------------------------------------------------------------- |
| < 480px (móvil real) | la pantalla ocupa el viewport entero (`100dvh`), sin esquinas redondeadas ni etiqueta |
| ≥ 480px (preview)    | marco de 390 × 844 con `border-radius: 44`, sombra, y la etiqueta `Salud` debajo      |

El punto de corte está duplicado en `App.vue` y `SaludView.vue` porque `@media`
no acepta `var()`; `styles/tokens.css` lo documenta.

---

## 2. El mapa

```text
src/
  main.ts                      monta la app y carga fuentes, reset y tokens
  App.vue                      lienzo de la vista de catálogo (marco + etiqueta)
  views/SaludView.vue          la pantalla: única dueña de los datos
  components/salud/            BarraEstado, NavegadorFecha, CabeceraBienestar,
                               TarjetaRecomendacion, TarjetaFactores,
                               TarjetaFormularios, AvisoPendiente
  components/icons/            IconoLuna, IconoRombo, IconoPortapapeles
  composables/                 useDiaSeleccionado, useEstadoDispositivo
  data/saludMock.ts            los datos ficticios
  types/salud.ts               el contrato de la pantalla
  theme/tokens.ts              tokens que necesita la lógica (animación, rango)
  styles/tokens.css            tokens CSS: paleta, escala, medidas, sombras
  styles/reset.css             reset mínimo
tests/                         un test por componente + composable + axe
```

Los componentes de `components/` son presentacionales puros: reciben `props`
tipadas, emiten eventos (`diaAnterior`, `diaSiguiente`, `verMas`,
`abrirFormulario`) y no tocan red ni estado global.

---

## 3. Qué es mock y dónde entra la API real

Todo lo que se ve son datos ficticios de `src/data/saludMock.ts`, detrás del
tipo `ResumenSalud` (`src/types/salud.ts`).

**`SaludView.vue` es el único punto de entrada de datos:**

```ts
// src/views/SaludView.vue
const resumen = RESUMEN_SALUD_MOCK;
```

Sustituir esa línea por la respuesta del endpoint —o por un store— es todo lo
que hay que tocar para conectar la API: si respeta `ResumenSalud`, ningún
componente cambia.

Tres puntos más de conexión, marcados en el código con `TODO(spec)`:

| Qué                                 | Dónde                         | Estado                                                                         |
| ----------------------------------- | ----------------------------- | ------------------------------------------------------------------------------ |
| Foto de la tarjeta de recomendación | `recomendacion.imagen`        | `null` → se pinta un placeholder a rayas, deliberadamente distinto de una foto |
| Abrir el formulario del día         | `SaludView.abrirFormulario()` | vacío: no hay navegación en el alcance                                         |
| Ver todos los formularios           | `SaludView.verMas()`          | vacío: ídem                                                                    |

La barra de estado no es mock del todo: `useEstadoDispositivo` pone la hora del
reloj del sistema y pide la batería a `navigator.getBattery()` cuando el
navegador la expone. Si no existe o falla, se queda con `18:09` y `58` del mock,
en silencio.

---

## 4. La animación del aviso "Pendiente"

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

## 5. Accesibilidad

Lo que la pantalla garantiza:

- `<button>` para todo lo pulsable, `<h1>`/`<h2>` para la jerarquía real,
  `<ul>/<li>` en las dos listas, `<header>` para la cabecera de bienestar.
- Área táctil de 44 × 44 en chevrons, `ver más` y el botón naranja: el padding
  crece y un margen negativo devuelve el espacio, así que el diseño no se mueve.
- `aria-label` en los tres chevrons/acciones y en el CTA, que nombra el día.
- `86%` se anuncia una sola vez: `role="group"` con
  `aria-label="Bienestar de hoy: 86 por ciento"` y las partes visuales en
  `aria-hidden`.
- SVG decorativos con `aria-hidden="true"` y `focusable="false"`.
- `:focus-visible` con anillo de 2px y `outline-offset`; ningún `outline: none`
  sin sustituto. El orden de tabulación es el del DOM.
- El día seleccionado vive en una región `aria-live="polite"`.
- El color nunca informa solo: junto al punto verde/gris va siempre
  `Respondido` / `Sin responder`.
- Tipografía en `rem`, para que el zoom de texto funcione. El contenedor de
  contenido desplaza (`overflow-y: auto`) antes que recortar; en horizontal
  recorta (`overflow-x: clip`), porque no hay nada que desplazar y así no
  aparece la barra que provocarían los pocos píxeles que el `scale()` del aviso
  añade al área desbordada.

  Con **zoom de página** al 200% (el habitual) todo escala junto y la pantalla
  se ve igual. Con **zoom solo de texto** al 200%, el contenido sigue completo y
  desplazable, pero la banda superior se solapa: el navegador de fecha, el
  sobretítulo y la cifra están anclados a `top: 66 / 104 / 236`, que es lo que
  fija el diseño. Despegarlos de esas coordenadas cambiaría la pantalla al 100%,
  así que queda anotado en vez de corregido.

- `pnpm lint` incluye `eslint-plugin-vuejs-accessibility` con 0 warnings, y
  `tests/accesibilidad.test.ts` corre axe-core sobre la pantalla montada
  (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `best-practice`): 0 violaciones.

Hay **una** excepción de lint, en `CabeceraBienestar.vue`:
`vuejs-accessibility/heading-has-content` solo mira el texto del encabezado y no
su `aria-label`, así que marca como vacío un `<h1>` que sí tiene nombre
accesible. Está silenciada en esa línea y explicada allí.

### Contrastes verificados

Calculados sobre los `oklch()` del diseño convertidos a sRGB. Los que **no**
llegan a AA:

| Par                                     | Ratio      | Mínimo | Dónde                                                                                   |
| --------------------------------------- | ---------- | ------ | --------------------------------------------------------------------------------------- |
| `grisTexto` sobre blanco                | **4.25:1** | 4.5:1  | subtítulo de "Lo más importante hoy", detalle de cada factor, estado de cada formulario |
| blanco al 85% sobre el gradiente (~13%) | **4.27:1** | 4.5:1  | sobretítulo `BIENESTAR DE HOY`                                                          |

Los dos se arreglan con un retoque mínimo de paleta —`grisTexto` a
`oklch(0.55 0.015 168)` da 4.9:1, y subir la opacidad del sobretítulo de 0.85 a
1 da 5.0:1— pero la especificación es cerrada, así que quedan como están y
constan aquí.

El resto pasa: `verdeProfundo` 12.5:1, `verdeTitulo` 11.6:1, `verdeTexto`
9.1:1, `verdeAccion` 5.3:1, `alertaTexto` sobre `alertaFondo` 4.7:1,
`naranjaEtiqueta` 5.1:1, `naranjaTitulo` 9.1:1, la hora 8.8:1, la fecha 6.1:1 y
la cifra `86%` 4.1:1 (texto grande, mínimo 3:1).

Los puntos de estado quedan en 2.75:1 (`puntoActivo`) y 1.52:1
(`puntoInactivo`) sobre blanco. No incumplen 1.4.11 porque no portan
información por sí solos —el texto de estado va al lado—, pero como señal
visual son débiles.

axe no puede comprobar contraste en jsdom (no hay layout); estos números salen
del cálculo directo, no del test.

---

## 6. Lo que falta para producción

- **Datos reales.** Conectar `ResumenSalud` a la API y decidir estados de carga
  y de error, que el diseño no cubre.
- **La foto familiar.** Mientras `recomendacion.imagen` sea `null` se ve el
  placeholder a rayas.
- **Navegación.** `abrirFormulario` y `verMas` están vacíos: hoy no hay router
  ni destino.
- **El día no cambia los datos.** Los chevrons mueven la fecha, pero el resumen
  sigue siendo el mismo: falta el fetch por día.
- **Los dos contrastes** de la tabla de arriba, si el equipo de diseño acepta el
  retoque.
- **CI.** El gate del repositorio (`.github/workflows/p2.yml`) todavía solo
  corre `apps/web`. Faltan los cuatro pasos equivalentes para `apps/mobile`.
- **Verificación con lectores de pantalla reales** (VoiceOver / TalkBack) y en
  dispositivo, no solo axe en jsdom.
- **Iconos.** Los tres SVG están dibujados a mano contra la descripción del
  diseño; conviene contrastarlos con los originales.
