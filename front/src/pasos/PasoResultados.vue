<script setup>
import { ref } from "vue";
import { ajustes, simulacion } from "../estado.js";
import SeccionJornada from "../resultados/SeccionJornada.vue";
import SeccionKS from "../resultados/SeccionKS.vue";
import SeccionVeredicto from "../resultados/SeccionVeredicto.vue";

const visible = ajustes.seccionesVisibles;
const jornadaElegida = ref(0);
</script>

<template>
  <div v-if="simulacion.resultado" class="resultados">
    <SeccionVeredicto v-if="visible.veredicto" />

    <section>
      <h3>Detalle por jornada</h3>
      <div class="pestanas" role="tablist">
        <button
          v-for="(jornada, posicion) in simulacion.resultado.jornadas"
          :key="jornada.numero"
          type="button"
          role="tab"
          :aria-selected="jornadaElegida === posicion"
          :class="{ activa: jornadaElegida === posicion }"
          @click="jornadaElegida = posicion"
        >
          Jornada {{ jornada.numero }} · {{ jornada.inicio }}–{{ jornada.fin }}
        </button>
      </div>
      <SeccionJornada :key="jornadaElegida" :jornada="simulacion.resultado.jornadas[jornadaElegida]" />
    </section>

    <SeccionKS v-if="visible.pruebaKS" />
  </div>
</template>

<style scoped>
.resultados { display: grid; grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
.resultados > section { border-top: 1px solid var(--borde); padding-top: 0.5rem; }
.resultados > section:first-child { border-top: none; padding-top: 0; }
</style>
