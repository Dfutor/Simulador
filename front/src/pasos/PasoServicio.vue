<script setup>
import { simulacion } from "../estado.js";
import { formatearNumero } from "../formato.js";

const entrada = simulacion.entrada;
const mediaUniforme = (jornada) => (Number(jornada.servicioMinimo) + Number(jornada.servicioMaximo)) / 2;
</script>

<template>
  <div class="paso">
    <p class="nota">Cuánto tarda una caja con cada cliente y cuántas cajas atienden.</p>
    <div class="campos">
      <label class="campo">Número de cajas abiertas
        <input v-model.number="entrada.numeroServidores" type="number" min="1" max="100" step="1" required>
      </label>
      <label class="campo">Distribución del tiempo de servicio
        <select v-model="entrada.distribucionServicio">
          <option value="uniforme">Uniforme (mínimo y máximo)</option>
          <option value="exponencial">Exponencial (media)</option>
        </select>
      </label>
    </div>

    <article v-for="(jornada, posicion) in entrada.jornadas" :key="posicion" class="jornada">
      <h3>Jornada {{ posicion + 1 }} · {{ jornada.inicio }}–{{ jornada.fin }}</h3>
      <div v-if="entrada.distribucionServicio === 'uniforme'" class="campos">
        <label class="campo">Servicio mínimo (min)
          <input v-model.number="jornada.servicioMinimo" type="number" min="0" step="any" required>
        </label>
        <label class="campo">Servicio máximo (min)
          <input v-model.number="jornada.servicioMaximo" type="number" :min="Number(jornada.servicioMinimo) + 0.1" step="any" required>
          <small>Media: {{ formatearNumero(mediaUniforme(jornada), 1) }} min</small>
        </label>
      </div>
      <div v-else class="campos">
        <label class="campo">Tiempo medio de servicio (min)
          <input v-model.number="jornada.minutosPorCliente" type="number" min="0.1" step="any" required>
        </label>
      </div>
    </article>
  </div>
</template>

<style scoped>
.jornada { border-top: 1px solid var(--borde); margin-top: 1.25rem; }
.jornada h3 { margin: 1rem 0 0.75rem; }
</style>
