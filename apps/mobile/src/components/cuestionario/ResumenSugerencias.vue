<script setup lang="ts">
/**
 * Qué se va a enviar por ti.
 *
 * Es una lista de texto y nada más: pregunta, flecha, valor. Sin tarjetas, sin
 * iconos, sin controles. Es deliberado —y es lo que la hace útil— porque llega
 * justo cuando quien responde creía haber terminado: cualquier cosa que se
 * parezca a un campo se lee como una pregunta más, y el formulario acabaría
 * siendo más largo por intentar ser más corto.
 *
 * De solo lectura, sin excepción. Para cambiar algo se pasa por "Revisarlas",
 * que devuelve al formulario con esos campos abiertos; editar aquí duplicaría
 * los controles de `CampoCuestionario` con la mitad de sus reglas.
 */
import type { DefaultSuggestion } from "@/api/contrato";
import { etiquetaCampo, formatearValor } from "@/dominio/campos";
import type { ValorCampo } from "@/api/contrato";

defineProps<{ sugerencias: readonly DefaultSuggestion[] }>();
</script>

<template>
  <dl class="sugeridas">
    <div v-for="sugerencia in sugerencias" :key="sugerencia.field_code" class="sugeridas__fila">
      <dt class="sugeridas__pregunta">{{ etiquetaCampo(sugerencia.field_code) }}</dt>
      <dd class="sugeridas__valor">
        <!-- La flecha es decorativa: la relación pregunta-respuesta ya la lleva
             el `dl`, y un lector que la leyera diría "flecha" en medio de cada
             par. -->
        <span class="sugeridas__flecha" aria-hidden="true">→</span>
        {{ formatearValor(sugerencia.field_code, sugerencia.value as ValorCampo) }}
      </dd>
    </div>
  </dl>
</template>

<style scoped>
.sugeridas {
  margin-top: var(--blubathon-esp-10);
}

/*
 * Una línea por par mientras quepa, y la respuesta debajo cuando no. `baseline`
 * y no `center`: la pregunta puede ocupar dos renglones y la respuesta tiene que
 * alinearse con el primero, que es donde se lee.
 */
.sugeridas__fila {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--blubathon-esp-4) var(--blubathon-esp-8);
  padding-block: var(--blubathon-esp-6);
}

.sugeridas__fila + .sugeridas__fila {
  border-top: 1px solid var(--blubathon-linea);
}

.sugeridas__pregunta {
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.sugeridas__valor {
  font-size: var(--blubathon-fs-125);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.sugeridas__flecha {
  margin-right: 2px;
  font-weight: 400;
  color: var(--blubathon-punto-inactivo);
}
</style>
