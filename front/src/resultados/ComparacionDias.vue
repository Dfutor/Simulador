<script setup>
/**
 * Histograma comparativo de dos fechas: personas que llegan por intervalo, con las mismas clases
 * y en frecuencia relativa (los dos días pueden tener distinta cantidad de intervalos).
 * Las barras son escenarios simulados con el modelo; el día de conteo del estudio se muestra como referencia.
 */
import { computed, ref } from "vue";
import { pedirComparacionDias } from "../api.js";
import Grafica from "../componentes/Grafica.vue";
import { establecimiento } from "../estado.js";
import { CATEGORIAS, formatearFecha, formatearNumero } from "../formato.js";
import { opcionComparacionDias, usarColores } from "../graficas.js";

const colores = usarColores();

function proximoDia(desde, condicion) {
  const fecha = new Date(`${desde}T12:00:00Z`);
  for (let dias = 0; dias < 40; dias++, fecha.setUTCDate(fecha.getUTCDate() + 1)) {
    if (condicion(fecha)) return fecha.toISOString().slice(0, 10);
  }
  return desde;
}
const hoy = establecimiento.hoy ?? new Date().toISOString().slice(0, 10);
// Por defecto: el próximo día 5 y el próximo día 15, como en el ejemplo del enunciado
const fechaA = ref(proximoDia(hoy, (fecha) => fecha.getUTCDate() === 5));
const fechaB = ref(proximoDia(hoy, (fecha) => fecha.getUTCDate() === 15));
const categoria = ref("todas");
const comparacion = ref(null);
const cargando = ref(false);
const error = ref("");

async function comparar() {
  cargando.value = true;
  error.value = "";
  try {
    comparacion.value = await pedirComparacionDias(fechaA.value, fechaB.value, categoria.value);
  } catch (problema) {
    error.value = problema.message;
    comparacion.value = null;
  } finally {
    cargando.value = false;
  }
}

const series = computed(() => comparacion.value?.series.map((serie) => ({
  ...serie,
  etiqueta: `${formatearFecha(serie.fecha, "corta")} (${serie.tipoDia})`,
})) ?? []);
const conDatos = computed(() => series.value.filter((serie) => serie.n > 0));
const opcion = computed(() => comparacion.value && opcionComparacionDias({ ...comparacion.value, series: series.value }, colores.value));
const nombreCategoria = computed(() => (categoria.value === "todas" ? "todas las franjas" : `franjas ${CATEGORIAS[categoria.value].nombre.toLowerCase()}`));
</script>

<template>
  <section>
    <h3>Comparar dos días</h3>
    <p class="nota">Distribución de las llegadas por intervalo en dos fechas, con las mismas clases y en frecuencia relativa.</p>
    <form class="campos" @submit.prevent="comparar">
      <label class="campo">Día A <input v-model="fechaA" type="date" required></label>
      <label class="campo">Día B <input v-model="fechaB" type="date" required></label>
      <label class="campo">Categoría de franja
        <select v-model="categoria">
          <option value="todas">Todas</option>
          <option v-for="(datos, clave) in CATEGORIAS" :key="clave" :value="clave">{{ datos.nombre }}</option>
        </select>
      </label>
      <button type="submit" class="principal comparar" :disabled="cargando">{{ cargando ? "Comparando…" : "Comparar" }}</button>
    </form>

    <p v-if="error" class="aviso" role="alert">{{ error }}</p>
    <template v-if="comparacion">
      <p class="aviso simulacion">
        <b>Escenarios simulados con el modelo.</b> Cada barra resume {{ comparacion.corridas }} días simulados;
        el rombo es el día de conteo del estudio, como referencia.
      </p>
      <ul class="resumen">
        <li v-for="serie in series" :key="serie.fecha">
          <b>{{ serie.etiqueta }}</b>:
          <template v-if="!serie.abierto">sin atención ese día: no hay nada que comparar.</template>
          <template v-else-if="!serie.n">no tiene {{ nombreCategoria }}.</template>
          <template v-else>{{ serie.n }} intervalos simulados, media {{ formatearNumero(serie.media) }} personas por intervalo.</template>
        </li>
        <li v-if="comparacion.observado">
          <b>Día de conteo</b>: {{ comparacion.observado.n }} intervalos observados, media {{ formatearNumero(comparacion.observado.media) }}.
        </li>
      </ul>
      <Grafica v-if="conDatos.length" :titulo="`Llegadas por intervalo · ${nombreCategoria}`"
        explicacion="Frecuencia relativa: la parte de los intervalos en que llegó esa cantidad de personas." :opcion="opcion" />
    </template>
  </section>
</template>

<style scoped>
form.campos { align-items: start; }
.comparar { align-self: end; }
.resumen { margin: 0.5rem 0; padding-left: 1.2rem; font-size: 0.92rem; }
</style>
