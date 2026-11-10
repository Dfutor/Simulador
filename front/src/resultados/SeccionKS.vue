<script setup>
import { computed } from "vue";
import Grafica from "../componentes/Grafica.vue";
import { simulacion } from "../estado.js";
import { formatearNumero } from "../formato.js";
import { opcionAcumuladaKS, opcionDPorCorrida, usarColores } from "../graficas.js";

const colores = usarColores();
const aceptadas = computed(() => simulacion.resultado.ks);
const rechazos = computed(() => simulacion.resultado.rechazos);
const clientesCorrida1 = computed(() => simulacion.resultado.jornadas.flatMap((jornada) => jornada.corrida1.clientes));
const primeraCorrida = computed(() => aceptadas.value[0]);

const opcionAcumulada = computed(() => opcionAcumuladaKS(
  clientesCorrida1.value.map((cliente) => cliente.aleatorioLlegada),
  clientesCorrida1.value.map((cliente) => cliente.aleatorioServicio),
  primeraCorrida.value.llegada.critico,
  colores.value,
));
const opcionD = computed(() => opcionDPorCorrida(aceptadas.value, rechazos.value, colores.value));

const veredicto = (prueba) => `${formatearNumero(prueba.D, 4)} / ${formatearNumero(prueba.critico, 4)}`;
</script>

<template>
  <section>
    <h3>Prueba de Kolmogorov-Smirnov</h3>
    <p class="nota">
      {{ aceptadas.length }} corridas aceptadas y {{ rechazos.length }} descartadas por rechazar la uniformidad.
      Con dos pruebas por corrida es normal descartar cerca de 2α de las corridas solo por azar.
    </p>
    <div class="rejillaGraficas">
      <Grafica titulo="Acumulada de los números aleatorios (corrida 1)"
        :explicacion="`Si la escalera no sale de la franja punteada (± ${formatearNumero(primeraCorrida.llegada.critico, 4)}), los números son uniformes.`"
        :opcion="opcionAcumulada" />
      <Grafica titulo="D de cada corrida comparada con su valor crítico"
        explicacion="Por debajo de 1 se acepta la uniformidad; los triángulos son intentos descartados." :opcion="opcionD" />
    </div>

    <details>
      <summary>Detalle por corrida (D / valor crítico)</summary>
      <div class="tabla alta">
        <table>
          <thead><tr><th>Corrida</th><th>Intentos</th><th>Números (n)</th><th>R de llegadas</th><th>R de servicios</th></tr></thead>
          <tbody>
            <tr v-for="corrida in aceptadas" :key="corrida.corrida">
              <td>{{ corrida.corrida }}</td>
              <td>{{ corrida.intentos }}</td>
              <td>{{ corrida.llegada.n }}</td>
              <td class="estado cumple">✓ {{ veredicto(corrida.llegada) }}</td>
              <td class="estado cumple">✓ {{ veredicto(corrida.servicio) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <details v-if="rechazos.length" open>
      <summary>Intentos descartados</summary>
      <div class="tabla">
        <table>
          <thead><tr><th>Corrida</th><th>Intento</th><th>R de llegadas</th><th>R de servicios</th></tr></thead>
          <tbody>
            <tr v-for="rechazo in rechazos" :key="`${rechazo.corrida}-${rechazo.intento}`">
              <td>{{ rechazo.corrida }}</td>
              <td>{{ rechazo.intento }}</td>
              <td :class="['estado', rechazo.llegada.pasa ? 'cumple' : 'noCumple']">{{ rechazo.llegada.pasa ? "✓" : "✗" }} {{ veredicto(rechazo.llegada) }}</td>
              <td :class="['estado', rechazo.servicio.pasa ? 'cumple' : 'noCumple']">{{ rechazo.servicio.pasa ? "✓" : "✗" }} {{ veredicto(rechazo.servicio) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </section>
</template>

<style scoped>
.alta { max-height: 380px; }
td.estado { display: table-cell; }
</style>
