<script setup>
import { formatearNumero, horaReloj } from "../formato.js";

defineProps({
  clientes: { type: Array, required: true },
  inicio: { type: String, required: true },
});
</script>

<template>
  <div class="tabla alta">
    <table>
      <thead>
        <tr>
          <th>Cliente</th><th>Prioritario</th><th>Caja</th><th>R llegada</th><th>Entre llegadas</th><th>Llega</th>
          <th>Pasa a caja</th><th>Espera</th><th>R servicio</th><th>Servicio</th><th>Sale</th><th>En el banco</th>
          <th>Personas al llegar</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="cliente in clientes" :key="cliente.cliente" :class="{ prioritario: cliente.prioritario }">
          <td>{{ cliente.cliente }}</td>
          <td>{{ cliente.prioritario ? "Sí" : "No" }}</td>
          <td>{{ cliente.servidor }}</td>
          <td>{{ formatearNumero(cliente.aleatorioLlegada, 4) }}</td>
          <td>{{ formatearNumero(cliente.tiempoEntreLlegadas) }}</td>
          <td>{{ horaReloj(inicio, cliente.momentoLlegada) }}</td>
          <td>{{ horaReloj(inicio, cliente.inicioServicio) }}</td>
          <td>{{ formatearNumero(cliente.tiempoEspera) }}</td>
          <td>{{ formatearNumero(cliente.aleatorioServicio, 4) }}</td>
          <td>{{ formatearNumero(cliente.tiempoServicio) }}</td>
          <td>{{ horaReloj(inicio, cliente.terminacionServicio) }}</td>
          <td>{{ formatearNumero(cliente.tiempoTotal) }}</td>
          <td>{{ cliente.personasAlLlegar }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.alta { max-height: 460px; }
tr.prioritario td { background: var(--resalte); }
</style>
