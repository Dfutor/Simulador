<script setup>
import { computed } from "vue";
import Grafica from "../componentes/Grafica.vue";
import { formatearNumero } from "../formato.js";
import { opcionPoisson, usarColores } from "../graficas.js";

const props = defineProps({
  prueba: { type: Object, required: true },
  conGrafica: { type: Boolean, default: true },
});

const colores = usarColores();
const opcion = computed(() => opcionPoisson(props.prueba.clases, colores.value));
</script>

<template>
  <div>
    <p class="veredicto">
      <span v-if="prueba.pasa === null" class="estado">⚠ Pocos datos para la prueba (se necesitan más clases con 5 o más esperados)</span>
      <span v-else-if="prueba.pasa" class="estado cumple">✓ Los conteos se ajustan a una Poisson</span>
      <span v-else class="estado noCumple">✗ Los conteos no se ajustan a una Poisson</span>
    </p>
    <p class="nota">
      Media {{ formatearNumero(prueba.media) }} y varianza {{ formatearNumero(prueba.varianza) }} (en una Poisson son parecidas).
      <template v-if="prueba.critico !== null">
        χ² = {{ formatearNumero(prueba.estadistico, 3) }} contra un valor crítico de {{ formatearNumero(prueba.critico, 3) }}
        con {{ prueba.gradosLibertad }} grado{{ prueba.gradosLibertad === 1 ? "" : "s" }} de libertad.
      </template>
    </p>
    <Grafica v-if="conGrafica" titulo="Intervalos observados contra los que espera una Poisson"
      explicacion="Las clases se juntan hasta esperar al menos 5 intervalos en cada una." :opcion="opcion" :alto="240" />
  </div>
</template>

<style scoped>
.veredicto { margin: 0.25rem 0 0; }
</style>
