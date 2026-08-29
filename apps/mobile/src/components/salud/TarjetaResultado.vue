<script setup lang="ts">
import type { OutcomeRequestView } from "@/api/contrato";
import BotonAccion from "@/components/base/BotonAccion.vue";
import IconoCheck from "@/components/icons/IconoCheck.vue";
import IconoAlerta from "@/components/icons/IconoAlerta.vue";
import IconoRombo from "@/components/icons/IconoRombo.vue";

defineProps<{
  solicitud: OutcomeRequestView;
  enviando: boolean;
  error: string | null;
}>();

defineEmits<{
  reportar: [valor: "yes" | "no"];
}>();

/**
 * La pregunta, en una línea.
 *
 * No se usa `solicitud.question_es`: el backend la redacta para el registro
 * —"…mayor…, según las anclas acordadas para esta demostración"— y eso son tres
 * renglones de condiciones que hay que leer enteros antes de poder contestar sí
 * o no. Lo que se pregunta es lo mismo; lo que cambia es que se lee de un
 * vistazo. La definición formal sigue siendo la del contrato y viaja intacta en
 * el reporte: aquí solo se decide cómo se enuncia en pantalla.
 */
const PREGUNTA = "¿Ocurrió una desregulación en las últimas 24 horas?";
</script>

<template>
  <section class="resultado" aria-labelledby="resultado-titulo">
    <!--
      La etiqueta lleva insignia y la insignia late. Es lo que la separa de las
      tarjetas que solo informan: hasta que esta pregunta no se contesta, el
      baseline se queda sin resultados verificados y el modelo no da cifra. Sin
      esto era un rótulo naranja de 11px encima de un titular, indistinguible
      de cualquier otro sobretítulo de la pantalla.
    -->
    <p class="resultado__etiqueta">
      <span class="resultado__insignia" aria-hidden="true">
        <IconoRombo class="resultado__rombo" />
      </span>
      Resultado pendiente
    </p>
    <h2 id="resultado-titulo" class="resultado__titulo">{{ PREGUNTA }}</h2>

    <div class="resultado__acciones">
      <BotonAccion
        variante="negativo"
        class="resultado__boton resultado__boton--si"
        :disabled="enviando"
        @click="$emit('reportar', 'yes')"
      >
        <IconoAlerta class="resultado__icono" aria-hidden="true" />
        Sí, ocurrió
      </BotonAccion>

      <!-- Las dos respuestas, siempre. Un "no" resuelve en cuanto se da: ver
           `report_is_eligible` en el dominio del backend. -->
      <button
        type="button"
        class="resultado__boton resultado__boton--no"
        :disabled="enviando"
        @click="$emit('reportar', 'no')"
      >
        <IconoCheck class="resultado__icono" aria-hidden="true" />
        No ocurrió
      </BotonAccion>
    </div>

    <p v-if="error" class="resultado__error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
/*
 * Fuera de las bandas, igual que el aviso pendiente y por la misma razón: no
 * habla del riesgo del día sino de algo que falta por hacer. Va en elevación 2
 * porque pide una acción, no informa.
 *
 * Y por encima de eso, tres cosas que ninguna otra tarjeta tiene, porque
 * ninguna otra vence: el filete de acento en el borde de arriba, el lavado
 * naranja que entra por esa misma esquina, y el titular un cuerpo más grande.
 * Es el mismo naranja del aviso pendiente —no entra ningún color nuevo—, usado
 * aquí con más superficie porque esto sí tiene plazo.
 */
.resultado {
  padding: var(--blubathon-esp-18) var(--blubathon-esp-16) var(--blubathon-esp-16);
  background:
    radial-gradient(120% 140% at 0% 0%, var(--blubathon-aviso-fondo), transparent 58%),
    var(--blubathon-superficie);
  border-top: 3px solid var(--blubathon-aviso-insignia);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-2);
}

.resultado__etiqueta {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-8);
  font-size: var(--blubathon-fs-12);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-aviso-etiqueta);
}

/*
 * La insignia late despacio: dos segundos por ciclo y solo la opacidad, que no
 * repinta ni mueve nada de alrededor. Es lo que distingue "pendiente" de
 * "informativo" sin recurrir a un color más fuerte ni a más superficie.
 */
.resultado__insignia {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-caja-icono);
  height: var(--blubathon-caja-icono);
  color: var(--blubathon-aviso-insignia);
  background: var(--blubathon-aviso-fondo);
  border-radius: 50%;
  animation: resultado-latido 2s ease-in-out infinite;
}

.resultado__rombo {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

@keyframes resultado-latido {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.55;
  }
}

/* El latido es un realce, no información: sin él la tarjeta sigue diciendo todo
   lo que dice. Quien pide menos movimiento se queda con la insignia quieta. */
@media (prefers-reduced-motion: reduce) {
  .resultado__insignia {
    animation: none;
  }
}

.resultado__titulo {
  margin-top: var(--blubathon-esp-8);
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  line-height: 1.3;
  color: var(--blubathon-marca-profundo);
}

/* Envuelven en pantallas estrechas: dos áreas táctiles de 44 no caben en 320
   sin encogerse por debajo del mínimo. */
.resultado__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-12);
  margin-top: var(--blubathon-esp-16);
}

/* La forma y los tonos los pone `BotonAccion`; aquí solo se dice que los dos se
   reparten la fila y envuelven en pantallas estrechas. */
.resultado__boton {
  flex: 1 1 10rem;
}

.resultado__icono {
  flex: none;
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.resultado__error {
  margin-top: var(--blubathon-esp-12);
  padding: var(--blubathon-esp-9) var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
  border-radius: var(--blubathon-radio-14);
}
</style>
