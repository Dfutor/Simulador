<script setup>
import { computed } from "vue";
import Grafica from "../componentes/Grafica.vue";
import { CATEGORIAS, formatearNumero } from "../formato.js";
import { opcionPromediosMoviles, usarColores } from "../graficas.js";

const props = defineProps({
  analisis: { type: Object, required: true },   // una jornada de /api/analisis-llegadas
  ventana: { type: Number, required: true },
});

const colores = usarColores();
const opcion = computed(() => opcionPromediosMoviles(props.analisis.intervalos, props.ventana, colores.value));
const prueba = computed(() => props.analisis.homogeneidad);
const primero = computed(() => props.analisis.intervalos[0]);
const ultimo = computed(() => props.analisis.intervalos.at(-1));
</script>

<template>
  <div class="analisis">
    <Grafica
      titulo="Llegadas por intervalo y promedios móviles"
      :explicacion="`Conteos de ${primero.desde} a ${ultimo.hasta}, en orden. El color de cada barra es la categoría de su franja.`"
      :opcion="opcion" :alto="260" />

    <p class="nota">
      <template v-if="prueba.estadistico === null">{{ prueba.advertencia }}</template>
      <template v-else>
        <span :class="['estado', prueba.rechaza ? 'noCumple' : 'cumple']">
          {{ prueba.rechaza ? "La tasa de llegadas cambia entre franjas" : "No hay diferencias significativas entre franjas" }}
        </span>
        (prueba χ² de homogeneidad: χ² = {{ formatearNumero(prueba.estadistico, 2) }}, {{ prueba.gradosLibertad }} g. l.,
        valor p = {{ formatearNumero(prueba.valorP, 3) }}).
        {{ prueba.rechaza
          ? `Cada franja se compara con la media; es pico o valle si |z| > ${formatearNumero(prueba.zCritico, 2)} (con corrección de Bonferroni).`
          : "Todas las franjas observadas quedan como normales." }}
        {{ prueba.advertencia }}
      </template>
    </p>

    <div class="tabla">
      <table>
        <thead><tr><th>Franja</th><th>Conteos</th><th>Media por intervalo</th><th>z</th><th>Categoría</th></tr></thead>
        <tbody>
          <tr v-for="franja in analisis.franjas" :key="franja.desde">
            <td>{{ franja.desde }}–{{ franja.hasta }}</td>
            <td>{{ franja.observaciones }}</td>
            <td>{{ franja.media === null ? "—" : formatearNumero(franja.media) }}</td>
            <td>{{ franja.z === null ? "—" : formatearNumero(franja.z, 2) }}</td>
            <td><span :class="['categoria', franja.categoria]">{{ CATEGORIAS[franja.categoria].nombre }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.analisis { display: grid; gap: 0.5rem; margin-top: 1rem; }
.analisis .nota { margin: 0; }
</style>
