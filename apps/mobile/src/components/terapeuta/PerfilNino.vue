<script setup lang="ts">
import { computed } from "vue";

import GraficoRiesgo from "@/components/terapeuta/GraficoRiesgo.vue";
import { MINIMO_RESULTADOS } from "@/dominio/serieRiesgo";
import { CLASE_BANDA, bandaRiesgo } from "@/theme/riesgo";
import type { FichaNino } from "@/types/terapeuta";

const props = defineProps<{ ficha: FichaNino }>();

const banda = computed(() => bandaRiesgo(props.ficha.riesgo));

/**
 * La tasa observada, o por qué no la hay.
 *
 * Es la cifra que más se presta a leerse mal: no es "el riesgo de este niño",
 * es con qué frecuencia se ha confirmado un episodio entre los días que alguien
 * llegó a contestar. Por eso lleva su denominador escrito y no un porcentaje
 * solo, y por eso se abstiene por debajo del mínimo en vez de enseñar "1 de 2".
 */
const tasa = computed(() => {
  const observada = props.ficha.tasa;
  if (observada === null) {
    return {
      valor: "Sin base",
      nota: `Hacen falta ${MINIMO_RESULTADOS} resultados confirmados`,
    };
  }
  const porcentaje = Math.round((observada.episodios / observada.confirmados) * 100);
  return {
    valor: `${porcentaje}%`,
    nota: `${observada.episodios} de ${observada.confirmados} días confirmados`,
  };
});

const adherencia = computed(() => `${Math.round(props.ficha.adherencia * 100)}%`);

/** Riesgo del día, con la abstención dicha y no dibujada como un cero. */
const riesgo = computed(() =>
  props.ficha.riesgo === null ? "s/d" : `${Math.round(props.ficha.riesgo)}%`,
);

interface Etiquetas {
  readonly titulo: string;
  readonly valores: readonly string[];
  readonly alerta?: boolean;
}

/**
 * Perfil sensorial, apoyos y contraindicaciones.
 *
 * Las contraindicaciones van marcadas y las otras dos no: las primeras dicen
 * qué **no** hacer, y en una sesión eso pesa distinto que saber que el niño
 * busca presión táctil. Se enseñan aunque estén vacías, con su "sin registrar":
 * una lista ausente y una lista vacía se leen igual, y no lo son —una dice que
 * nadie lo ha registrado, la otra que se comprobó y no hay ninguna.
 */
const etiquetas = computed<Etiquetas[]>(() => [
  { titulo: "Perfil sensorial", valores: props.ficha.perfilSensorial },
  { titulo: "Apoyos de comunicación", valores: props.ficha.apoyosComunicacion },
  { titulo: "Contraindicaciones", valores: props.ficha.contraindicaciones, alerta: true },
]);
</script>

<template>
  <section class="perfil" :class="CLASE_BANDA[banda]" aria-labelledby="perfil-titulo">
    <header class="perfil__cabecera">
      <div>
        <p class="perfil__sobretitulo">Perfil del niño</p>
        <h2 id="perfil-titulo" class="perfil__nombre">{{ ficha.etiqueta }}</h2>
      </div>

      <p class="perfil__riesgo">
        <span class="perfil__riesgo-cifra">{{ riesgo }}</span>
        <span class="perfil__riesgo-nota">riesgo del último día estimado</span>
      </p>
    </header>

    <GraficoRiesgo class="perfil__grafico" :serie="ficha.serie" :etiqueta="ficha.etiqueta" />

    <!--
      Tres cifras y no más. Cada una responde a una pregunta que el terapeuta se
      hace antes de una sesión: ¿con qué frecuencia le pasa?, ¿me puedo fiar de
      estos datos?, ¿hay algo sin cerrar? Añadir una cuarta que no responda a
      ninguna solo repartiría la atención.
    -->
    <dl class="perfil__cifras">
      <div class="cifra">
        <dt class="cifra__titulo">Tasa observada</dt>
        <dd class="cifra__valor">{{ tasa.valor }}</dd>
        <dd class="cifra__nota">{{ tasa.nota }}</dd>
      </div>

      <div class="cifra">
        <dt class="cifra__titulo">Adherencia</dt>
        <dd class="cifra__valor">{{ adherencia }}</dd>
        <dd class="cifra__nota">{{ ficha.serie.length }} días con registro</dd>
      </div>

      <div class="cifra">
        <dt class="cifra__titulo">Cierres pendientes</dt>
        <dd class="cifra__valor" :class="{ 'cifra__valor--alerta': ficha.pendientes > 0 }">
          {{ ficha.pendientes }}
        </dd>
        <dd class="cifra__nota">preguntas sin contestar</dd>
      </div>
    </dl>

    <dl class="perfil__etiquetas">
      <div v-for="grupo in etiquetas" :key="grupo.titulo" class="grupo">
        <dt class="grupo__titulo">{{ grupo.titulo }}</dt>
        <dd class="grupo__valores">
          <template v-if="grupo.valores.length > 0">
            <span
              v-for="valor in grupo.valores"
              :key="valor"
              class="grupo__etiqueta"
              :class="{ 'grupo__etiqueta--alerta': grupo.alerta }"
            >
              {{ valor }}
            </span>
          </template>
          <span v-else class="grupo__vacio">Sin registrar</span>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.perfil {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-16);
  padding: var(--blubathon-esp-18);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

.perfil__cabecera {
  display: flex;
  gap: var(--blubathon-esp-12);
  align-items: flex-start;
  justify-content: space-between;
}

.perfil__sobretitulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.perfil__nombre {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-20);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

/*
 * La cifra del día lleva el color de la banda —es lo único del perfil que lo
 * lleva— y va acompañada siempre de la palabra. El color aquí es un refuerzo,
 * no el dato: quien no lo distingue lee el número igual.
 */
.perfil__riesgo {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
}

.perfil__riesgo-cifra {
  font-size: var(--blubathon-fs-26);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-cifra);
  color: var(--blubathon-texto-fuerte, var(--blubathon-marca-profundo));
  font-variant-numeric: tabular-nums;
}

.perfil__riesgo-nota {
  max-width: 14ch;
  font-size: var(--blubathon-fs-11);
  line-height: 1.3;
  color: var(--blubathon-gris-texto);
}

.perfil__cifras {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--blubathon-esp-12);
  padding-top: var(--blubathon-esp-14);
  border-top: 1px solid var(--blubathon-linea);
}

.cifra__titulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.cifra__valor {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-20);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
  font-variant-numeric: tabular-nums;
}

.cifra__valor--alerta {
  color: var(--blubathon-aviso-etiqueta);
}

.cifra__nota {
  font-size: var(--blubathon-fs-11);
  line-height: 1.35;
  color: var(--blubathon-gris-texto);
}

.perfil__etiquetas {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-10);
  padding-top: var(--blubathon-esp-14);
  border-top: 1px solid var(--blubathon-linea);
}

.grupo {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-8);
  align-items: baseline;
}

.grupo__titulo {
  min-width: 15ch;
  font-size: var(--blubathon-fs-12);
  color: var(--blubathon-gris-texto);
}

.grupo__valores {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-6);
}

.grupo__etiqueta {
  padding: 2px var(--blubathon-esp-8);
  font-size: var(--blubathon-fs-12);
  font-weight: 600;
  color: var(--blubathon-marca-texto);
  background: var(--blubathon-marca-icono-fondo);
  border-radius: var(--blubathon-radio-pastilla);
}

.grupo__etiqueta--alerta {
  color: var(--blubathon-alerta-texto);
  background: var(--blubathon-alerta-fondo);
}

.grupo__vacio {
  font-size: var(--blubathon-fs-12);
  color: var(--blubathon-gris-texto);
}

@media (max-width: 600px) {
  .perfil__cifras {
    grid-template-columns: minmax(0, 1fr);
  }

  .cifra + .cifra {
    padding-top: var(--blubathon-esp-10);
    border-top: 1px solid var(--blubathon-linea);
  }
}
</style>
