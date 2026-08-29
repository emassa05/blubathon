<script setup lang="ts">
import { BLUBATHON_TEXTS_ES } from "@blubathon/contract/texts";
import { computed, onMounted } from "vue";

import AvisoPendiente from "@/components/salud/AvisoPendiente.vue";
import CabeceraRiesgo from "@/components/salud/CabeceraRiesgo.vue";
import DialogoDesregulacion from "@/components/salud/DialogoDesregulacion.vue";
import FondoRiesgo from "@/components/salud/FondoRiesgo.vue";
import NavegadorFecha from "@/components/salud/NavegadorFecha.vue";
import RachaSinDesregulacion from "@/components/salud/RachaSinDesregulacion.vue";
import TarjetaFactores from "@/components/salud/TarjetaFactores.vue";
import TarjetaFormularios from "@/components/salud/TarjetaFormularios.vue";
import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";
import TarjetaResultado from "@/components/salud/TarjetaResultado.vue";
import { useDesregulacion } from "@/composables/useDesregulacion";
import { useDiaSeleccionado } from "@/composables/useDiaSeleccionado";
import { useResumenSalud } from "@/composables/useResumenSalud";
import { CLASE_BANDA, bandaRiesgo } from "@/theme/riesgo";

const emitir = defineEmits<{
  verHistorial: [];
  abrirCuestionario: [fecha: string];
}>();

// Único punto de la pantalla donde entran los datos. Los componentes reciben
// `props` ya traducidas y no saben que existe una API.
const { fechaIso, etiqueta, etiquetaAccesible, diaAnterior, diaSiguiente } = useDiaSeleccionado();
const { resumen, cargando, error, recargar } = useResumenSalud(fechaIso);

/*
 * La pregunta de cierre —¿hubo un evento de desregulación?— no depende del día
 * que se esté mirando: es la que el sistema dejó abierta y hay que contestar
 * antes de que venza.
 *
 * Llega de dos maneras, y cuál toca lo decide `useDesregulacion`, no esta
 * pantalla:
 *
 * - **Obligatoria**, en un diálogo delante de todo, cuando ya se puede
 *   contestar que sí y que no. Hasta que no se responde no hay pantalla.
 * - **Informativa**, en la tarjeta de siempre, mientras la ventana de 24 h
 *   sigue abierta y un "no ocurrió" todavía no resolvería nada. Exigirla ahí
 *   dejaría "sí, ocurrió" como única salida y ese falso positivo se escribiría
 *   en los datos de los que sale la estimación siguiente.
 */
const {
  obligatoria,
  informativa,
  error: errorResultado,
  enviando,
  responder,
  cargar: cargarResultados,
} = useDesregulacion();

onMounted(cargarResultados);

/** Reportar cambia la estimación del día: el resumen se vuelve a pedir. */
async function alReportar(valor: "yes" | "no"): Promise<void> {
  if (await responder(valor)) await recargar();
}

// Mientras se carga o cuando falla no hay estimación, y eso es exactamente la
// banda `desconocido`: gris, no celeste. Pintar de "riesgo bajo" un día del que
// todavía no se sabe nada sería afirmar algo que la API no dijo.
const banda = computed(() => bandaRiesgo(resumen.value?.riesgo ?? null));

// El envío del cuestionario deja viejo el resumen del día: App lo avisa por aquí.
defineExpose({ recargar });
</script>

<template>
  <main class="pantalla">
    <!-- La banda es lo único que decide el color: la clase lleva la paleta
         entera y de aquí la heredan el panel y la tarjeta de recomendación. -->
    <div class="pantalla__columna" :class="CLASE_BANDA[banda]">
      <div class="pantalla__panel">
        <FondoRiesgo :banda="banda" />

        <div class="pantalla__panel-contenido">
          <NavegadorFecha
            :etiqueta="etiqueta"
            @dia-anterior="diaAnterior"
            @dia-siguiente="diaSiguiente"
          />

          <CabeceraRiesgo
            class="pantalla__riesgo"
            :riesgo="resumen?.riesgo ?? null"
            :confianza="resumen?.confianza ?? null"
          />

          <!-- La racha acompaña a la cifra dentro del panel: las dos hablan de
               episodios de desregulación, una hacia delante y otra hacia atrás,
               y separarlas obligaría a desplazarse para compararlas. -->
          <RachaSinDesregulacion
            v-if="resumen?.rachaSinDesregulacion"
            class="pantalla__racha"
            :racha="resumen.rachaSinDesregulacion"
          />
        </div>
      </div>

      <div class="pantalla__contenido">
        <!-- Carga y error ocupan el sitio de las tarjetas, no se superponen a
             ellas: el contenido de un día nunca se lee bajo el de otro. -->
        <p v-if="cargando" class="pantalla__aviso" role="status">
          {{ BLUBATHON_TEXTS_ES.loadingEs }}
        </p>

        <p v-else-if="error" class="pantalla__aviso" role="alert">
          {{ error.mensajeEs }}
        </p>

        <!--
          Las clases `pantalla__zona--*` no pintan nada en móvil: son solo el
          nombre de la casilla que ocupa cada pieza en la retícula de
          escritorio. En un teléfono el contenido sigue siendo una columna y
          estas piezas siguen apiladas en este mismo orden.
        -->
        <template v-else-if="resumen">
          <!--
            La pregunta de cierre va la primera, por encima de la recomendación.
            Es la única pieza de la pantalla con un plazo —fuera de él el reporte
            se guarda y no resuelve nada— y la única de la que depende que el
            modelo vuelva a tener cifra. Estaba la cuarta de la columna, debajo
            de dos tarjetas que solo informan, y en un teléfono había que
            desplazarse para encontrarla.
          -->
          <TarjetaResultado
            v-if="informativa"
            class="pantalla__zona--resultado"
            :solicitud="informativa"
            :enviando="enviando"
            :error="errorResultado"
            @reportar="alReportar"
          />

          <TarjetaRecomendacion
            class="pantalla__zona--recomendacion"
            :recomendacion="resumen.recomendacion"
          />
          <TarjetaFactores class="pantalla__zona--factores" :factores="resumen.factores" />
          <!-- "ver más" abre el calendario semanal; cada fila abre el
               cuestionario de su día. El id de la fila es su fecha ISO. -->
          <TarjetaFormularios
            class="pantalla__zona--formularios"
            :registros="resumen.formularios"
            @ver-mas="emitir('verHistorial')"
            @abrir-registro="(id) => emitir('abrirCuestionario', id)"
          />

          <AvisoPendiente
            v-if="resumen.formularioPendiente"
            class="pantalla__zona--pendiente"
            :dia="etiquetaAccesible"
            @abrir-formulario="emitir('abrirCuestionario', fechaIso)"
          />
        </template>
      </div>
    </div>

    <!--
      El diálogo obligatorio va el último y fuera de la columna: es `fixed`, así
      que su sitio en el DOM no decide dónde se ve, y el último es el único que
      no obliga a leer la pantalla entera para encontrarlo.
    -->
    <DialogoDesregulacion
      v-if="obligatoria"
      :solicitud="obligatoria"
      :enviando="enviando"
      :error="errorResultado"
      @responder="alReportar"
    />
  </main>
</template>

<style scoped>
.pantalla {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  min-height: 100dvh;
  /* Plano a propósito. Las burbujas son de la columna, que es el lienzo de la
     aplicación; extenderlas a todo el ancho las estiraría hasta desaparecer en
     una ventana de escritorio. */
  background: var(--blubathon-fondo-final);
}

/*
 * La columna de contenido. Ocupa el ancho que haya, siempre: en un teléfono es
 * la pantalla, y en cualquier ventana más ancha que la columna de 480 sigue
 * siendo la ventana entera, no una tira de 480 con dos franjas de fondo muerto
 * a los lados.
 *
 * Lo que se topa es el texto, y se topa con el acolchado del panel y del bloque
 * de tarjetas, no aquí: un `max-width` en la columna se llevaría con él el
 * degradado de la cabecera, las burbujas y la cúpula, que son justo lo que
 * tiene que llegar a los bordes.
 */
.pantalla__columna {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  /*
   * La ventana entera, siempre. Estuvo topada al alto de referencia de un
   * teléfono —844— para que en una ventana muy alta los bloques no se
   * repartieran por toda la pantalla, y el tope se veía: el fondo con burbujas
   * lo pinta el contenido de esta columna, así que en cualquier pantalla más
   * alta que eso —casi todos los teléfonos de hoy— el azul se cortaba en una
   * línea recta y debajo quedaba una franja de color plano.
   *
   * Que los bloques no se repartan ya no depende de esto: lo dice
   * `pantalla__contenido`, que los apila desde arriba y deja abajo el sitio que
   * sobre, pintado.
   */
  min-height: 100dvh;
  /*
   * Sin acolchado abajo: la columna no tiene fondo propio —lo lleva el
   * contenido—, así que cualquier acolchado suyo cae por fuera del lienzo y se
   * ve como una franja de color plano pegada al borde inferior, con un corte
   * recto justo donde acaban las burbujas. El aire de abajo lo pone el
   * contenido, que es quien pinta.
   */
}

/*
 * El panel del riesgo: un gradiente de la banda, casi blanco arriba y con
 * color abajo, más un brillo difuso muy abierto en la parte de arriba. El texto
 * cae siempre en la zona clara, que es donde más contraste hay, y el color se
 * concentra donde se ve la cúpula.
 *
 * Abajo no lleva radio: la curva la recorta el contenido, que sube sobre él.
 *
 * `min-height` es un mínimo, no un alto: si el texto crece con el zoom, el
 * panel crece con él. La barra de estado del dispositivo se suma al acolchado
 * de arriba.
 */
.pantalla__panel {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: var(--blubathon-panel-alto);
  /*
   * El acolchado lateral es el de siempre mientras la ventana no pase del ancho
   * de lectura, y a partir de ahí es lo que sobra repartido a los dos lados.
   * En un teléfono `(100% - 480px)` es negativo y gana el 24 de siempre: el
   * `max()` no cambia ni un píxel de lo que ya había.
   */
  padding: calc(var(--blubathon-esp-14) + env(safe-area-inset-top, 0px))
    max(var(--blubathon-esp-24), (100% - var(--blubathon-ancho-lectura)) / 2)
    var(--blubathon-esp-26);
  overflow: hidden;
  background:
    radial-gradient(130% 62% at 50% 0%, var(--blubathon-brillo), transparent 62%),
    linear-gradient(180deg, var(--blubathon-panel-cima) 0%, var(--blubathon-panel) 100%);
}

.pantalla__panel-contenido {
  position: relative;
}

.pantalla__riesgo {
  margin-top: var(--blubathon-esp-4);
}

/*
 * La racha cuelga de la cabecera, así que se centra con ella y no con el panel:
 * el panel es de borde a borde y la cabecera está topada a 480.
 *
 * Y reserva el hueco de la cúpula. El contenido sube sobre el panel y lo recorta
 * con un arco que es **más alto en el centro** —los dos radios se encuentran al
 * 50%—, justo por donde pasa esta línea, que va centrada. El acolchado de abajo
 * del panel ya cubre parte de esa profundidad; lo que falta es la diferencia, y
 * se pide aquí para que el panel crezca solo cuando hay racha: sin ella no
 * cambia ni un píxel de lo que ya estaba validado.
 *
 * `max()` con cero porque en ventana baja la cúpula es más corta que el
 * acolchado y la resta se va a negativo.
 */
.pantalla__racha {
  margin-inline: auto;
  margin-bottom: max(0px, calc(var(--blubathon-cupula) - var(--blubathon-esp-26)));
}

/*
 * El contenido no empieza donde acaba el panel: sube sobre él y lo recorta con
 * una cúpula, de modo que el panel llega más abajo por los lados que por el
 * centro. Es el mismo color de la página, así que lo único que se ve es el
 * corte.
 *
 * La curva son los dos radios de arriba con el eje horizontal al 50%: las dos
 * elipses se encuentran justo en el centro y forman un arco continuo, sin la
 * esquina que deja un `border-radius` normal.
 *
 * El acolchado de arriba devuelve exactamente lo que se comió el margen
 * negativo, así que la cúpula no le cuesta ni un píxel de alto a la página.
 */
.pantalla__contenido {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  /* Desde arriba: el espacio que sobre se queda entero al final, que es donde
     no separa nada. Repartido entre los bloques —lo que hacía
     `space-between`—, un día con una sola tarjeta la dejaba flotando en mitad
     de la pantalla. */
  justify-content: flex-start;
  gap: var(--blubathon-esp-14);
  /* El mismo margen que crece del panel, por la misma razón y con la misma
     cuenta: las tarjetas y la cabecera tienen que caer sobre la misma línea. */
  padding: calc(var(--blubathon-esp-14) + var(--blubathon-cupula))
    max(var(--blubathon-esp-24), (100% - var(--blubathon-ancho-lectura)) / 2)
    calc(var(--blubathon-esp-26) + env(safe-area-inset-bottom, 0px));
  margin-top: calc(var(--blubathon-cupula) * -1);
  /* Las burbujas se dimensionan contra esta caja, así que llenan la columna
     igual en un teléfono que en una ventana ancha. */
  background: var(--blubathon-fondo-pagina);
  border-radius: 50% 50% 0 0 / var(--blubathon-cupula) var(--blubathon-cupula) 0 0;
}

/*
 * Carga y error. Una tarjeta más del mismo sistema —misma superficie, mismo
 * radio, misma elevación— y no un bloque aparte: el sitio donde iban a estar
 * las tarjetas no cambia de aspecto según qué haya pasado con la red.
 *
 * Queda arriba del todo, justo donde el ojo ya estaba buscando la
 * recomendación: se lo da la columna, que apila desde arriba.
 */
.pantalla__aviso {
  padding: var(--blubathon-esp-18) var(--blubathon-esp-16);
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-gris-texto);
  text-align: center;
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-sombra-tarjeta);
}

/*
 * Tableta, o una ventana a media pantalla: de 600 a 900.
 *
 * La columna crece sola —`--blubathon-ancho-max` ya vale más a partir de 600—, así
 * que aquí solo va lo que no puede crecer con ella: la cabecera del riesgo. La
 * cifra de 104 px, su pastilla de confianza y el navegador de fecha están
 * dibujados para 480, y repartidos por 660 dejan de ser una cabecera para ser
 * una fila de cosas sueltas. El panel sigue yendo a sangre; lo que se queda
 * quieto es su contenido.
 */
@media (min-width: 600px) and (min-height: 500px), (min-width: 1100px) {
  /*
   * El ancho de lectura ya subió a 660 en los tokens, y el panel y las tarjetas
   * lo siguen solos. Aquí solo va lo que no puede seguirlo.
   *
   * La cabecera del riesgo es lo único: la cifra de 104 px, su pastilla de
   * confianza y el navegador de fecha están dibujados para 480, y repartidos
   * por 660 dejan de ser una cabecera para ser una fila de cosas sueltas.
   */
  .pantalla__panel-contenido {
    width: 100%;
    max-width: var(--blubathon-ancho-cabecera);
    margin-inline: auto;
  }
}

/*
 * Escritorio, a partir de 900. Todo lo de arriba es el móvil y sigue intacto:
 * de aquí abajo no se corrige ni un valor de la columna de 480, solo se declara
 * lo que pasa cuando hay sitio de sobra.
 *
 * Y lo que pasa es que la columna deja de ser una columna. Dos brazos, la misma
 * retícula que ya usaba el historial —contenido y un rail de 372— para que las
 * dos pantallas de escritorio no tengan dos anchos parecidos pero distintos. A
 * la izquierda lo que dice el día: la recomendación y lo que el formulario
 * pregunta primero. A la derecha lo que hay que hacer con él: el aviso, la
 * pregunta de cierre y los últimos formularios.
 *
 * La cúpula y el alto del panel crecen con el ancho. Son proporciones, no
 * medidas: un arco de 44 sobre 1040 px se lee como una línea recta.
 */
@media (min-width: 900px) {
  .pantalla__columna {
    --blubathon-cupula: var(--blubathon-cupula-amplia);
    --blubathon-panel-alto: var(--blubathon-panel-alto-amplio);
  }

  .pantalla__contenido {
    display: grid;
    /*
     * Las casillas se declaran enteras porque las piezas de la derecha
     * aparecen y desaparecen —no siempre hay aviso pendiente, no siempre hay
     * pregunta de cierre— y con colocación automática cada combinación habría
     * dado una retícula distinta.
     */
    /*
     * Cuatro columnas y dos son márgenes. Los `1fr` de los extremos se comen
     * todo el ancho que sobre, así que el contenido se queda en su medida y
     * centrado sin que haga falta toparlo con un `max-width` —que aquí se
     * llevaría por delante el fondo y la cúpula, que sí van de borde a borde.
     */
    grid-template-columns:
      minmax(var(--blubathon-esp-40), 1fr)
      minmax(0, var(--blubathon-ancho-principal))
      var(--blubathon-rail-ancho)
      minmax(var(--blubathon-esp-40), 1fr);
    /* La pregunta de cierre encabeza el rail por lo mismo que encabeza la
       columna en móvil: es la única con plazo. El aviso del formulario baja un
       puesto —no vence— y los últimos formularios cierran. */
    grid-template-areas:
      ". recomendacion resultado   ."
      ". factores      pendiente   ."
      ". factores      formularios .";
    align-content: start;
    /* Cada tarjeta con su alto: la de factores ocupa dos filas y sin esto se
       estiraría hasta el fondo de la segunda, dejándose media tarjeta en
       blanco. */
    align-items: start;
    gap: var(--blubathon-esp-20);
    padding: calc(var(--blubathon-esp-20) + var(--blubathon-cupula)) 0
      calc(var(--blubathon-esp-20) + env(safe-area-inset-bottom, 0px));
  }

  .pantalla__zona--recomendacion {
    grid-area: recomendacion;
  }

  .pantalla__zona--factores {
    grid-area: factores;
  }

  .pantalla__zona--formularios {
    grid-area: formularios;
  }

  .pantalla__zona--resultado {
    grid-area: resultado;
  }

  .pantalla__zona--pendiente {
    grid-area: pendiente;
  }

  /* Carga y error ocupan el sitio de todo lo demás, que es exactamente lo que
     hacían en la columna: no hay tarjetas con las que compartir la retícula. */
  .pantalla__aviso {
    grid-row: 1;
    /* De margen a margen, no de borde a borde: un aviso centrado en la ventana
       entera se leería lejos de donde iban a estar las tarjetas. */
    grid-column: 2 / 4;
    align-self: start;
  }
}
</style>
