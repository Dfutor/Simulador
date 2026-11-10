<script setup>
import { ajustes, simulacion } from "../estado.js";

const entrada = simulacion.entrada;
const visible = ajustes.variablesVisibles;
</script>

<template>
  <div class="paso">
    <p class="nota">
      Cada corrida es un día simulado. Antes de usarla se revisa con la prueba de Kolmogorov-Smirnov que sus números
      aleatorios de llegada y de servicio sean uniformes; si no lo son, la corrida se descarta y se repite.
    </p>
    <div class="campos">
      <label v-if="visible.numeroCorridas" class="campo">Corridas (días simulados)
        <input v-model.number="entrada.numeroCorridas" type="number" min="2" max="500" step="1" required>
      </label>
      <label v-if="visible.alfa" class="campo">Nivel de significancia α
        <select v-model.number="entrada.alfa">
          <option :value="0.01">0,01 (más exigente con el rechazo)</option>
          <option :value="0.05">0,05 (el usual)</option>
          <option :value="0.1">0,10</option>
        </select>
      </label>
      <label v-if="visible.limiteIntentos" class="campo">Límite de intentos por corrida
        <input v-model.number="entrada.limiteIntentos" type="number" min="1" max="100" step="1" required>
      </label>
      <label v-if="visible.semilla" class="campo">Semilla <small>(vacía = resultados distintos cada vez)</small>
        <input v-model="entrada.semilla" type="number" step="1" placeholder="Ej. 12345">
      </label>
    </div>
    <label v-if="visible.compararConCiw" class="ciw">
      <input v-model="entrada.compararConCiw" type="checkbox">
      <span>
        <b>Validar con Ciw</b><br>
        <small>Simula el mismo banco con la librería independiente Ciw y compara los resultados.</small>
      </span>
    </label>
    <p v-if="Object.values(visible).some((estaVisible) => !estaVisible)" class="nota">
      Algunas variables están ocultas y usan su valor por defecto. Se cambian con el ícono de herramienta.
    </p>
  </div>
</template>

<style scoped>
.ciw { display: flex; gap: 0.75rem; align-items: flex-start; margin-top: 1.5rem; cursor: pointer; }
.ciw input { margin-top: 0.3rem; }
.ciw small { color: var(--textoSecundario); }
</style>
