<script setup>
import { ref } from "vue";
import { ajustes, simulacion } from "../estado.js";
import SeccionJornada from "../resultados/SeccionJornada.vue";
import SeccionKS from "../resultados/SeccionKS.vue";
import SeccionVeredicto from "../resultados/SeccionVeredicto.vue";

const visible = ajustes.seccionesVisibles;
const jornadaElegida = ref(0);

/** Deja la semilla usada en el paso 3: la próxima simulación con los mismos datos da lo mismo. */
function fijarSemilla() {
  ajustes.variablesVisibles.semilla = true;
  simulacion.entrada.semilla = simulacion.resultado.semilla;
}
</script>

<template>
  <div v-if="simulacion.resultado" class="resultados">
    <p class="semilla nota">
      Semilla usada: <b>{{ simulacion.resultado.semilla }}</b>
      ({{ simulacion.resultado.semillaManual ? "escrita a mano" : "tomada del reloj del computador, en milisegundos" }})
      · versión del modelo {{ simulacion.resultado.versionModelo }}.
      <button v-if="String(simulacion.entrada.semilla) !== String(simulacion.resultado.semilla)" type="button" class="enlinea"
        @click="fijarSemilla">Fijar esta semilla para repetir</button>
      <span v-else>Con los mismos datos, la próxima simulación da lo mismo.</span>
    </p>
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
.resultados > section:first-of-type { border-top: none; padding-top: 0; }
.semilla { margin: 0; }
.enlinea { padding: 0.15rem 0.7rem; font-size: 0.85rem; margin-left: 0.25rem; }
</style>
