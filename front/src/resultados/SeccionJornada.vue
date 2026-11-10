<script setup>
import { computed } from "vue";
import Grafica from "../componentes/Grafica.vue";
import { ajustes } from "../estado.js";
import { MEDIDAS, formatearMedida, formatearNumero, formatearPorcentaje } from "../formato.js";
import { opcionEsperaPorCorrida, opcionFilaEnElTiempo, opcionLongitudes, opcionOcupacionPorCaja, usarColores } from "../graficas.js";
import BancoAnimado from "./BancoAnimado.vue";
import ResultadoPoisson from "./ResultadoPoisson.vue";
import TablaClientes from "./TablaClientes.vue";

const props = defineProps({ jornada: { type: Object, required: true } });

const visible = ajustes.seccionesVisibles;
const colores = usarColores();
const resumen = computed(() => props.jornada.resumen);
const numeroServidores = computed(() => resumen.value.utilizacionPorServidor.length);

const opcionFila = computed(() => opcionFilaEnElTiempo(props.jornada.corrida1.medidas.serie, props.jornada.inicio, colores.value));
const opcionTablaLongitudes = computed(() => opcionLongitudes(resumen.value.probabilidadSistema, resumen.value.probabilidadCola, colores.value));
const opcionCorridas = computed(() => opcionEsperaPorCorrida(props.jornada.medidasPorCorrida, resumen.value.Wq, colores.value));
const opcionCajas = computed(() => opcionOcupacionPorCaja(resumen.value.utilizacionPorServidor, colores.value));

const filasResumen = computed(() => Object.entries(MEDIDAS)
  .filter(([clave]) => resumen.value[clave])
  .map(([clave, medida]) => ({ clave, medida, valores: resumen.value[clave] })));

const filasLongitudes = computed(() => {
  const mayor = Math.max(...Object.keys(resumen.value.probabilidadSistema).map(Number));
  let acumuladaSistema = 0;
  let acumuladaCola = 0;
  return Array.from({ length: mayor + 1 }, (_, personas) => {
    const enSistema = resumen.value.probabilidadSistema[personas] ?? 0;
    const enCola = resumen.value.probabilidadCola[personas] ?? 0;
    acumuladaSistema += enSistema;
    acumuladaCola += enCola;
    return { personas, enSistema, acumuladaSistema, enCola, acumuladaCola };
  });
});

const filasCiw = computed(() => props.jornada.ciw && Object.entries(props.jornada.ciw)
  .map(([clave, comparacion]) => ({ medida: MEDIDAS[clave], propio: resumen.value[clave], ...comparacion })));
const medidasDistintas = computed(() => filasCiw.value?.filter((fila) => !fila.coinciden).length ?? 0);

const intervalo = (valores, medida) => `${formatearMedida(valores.limiteInferior, medida)} – ${formatearMedida(valores.limiteSuperior, medida)}`;
</script>

<template>
  <div class="seccionJornada">
    <p class="nota">
      Llegan {{ formatearNumero(jornada.tasaLlegada) }} personas por intervalo y cada caja atiende
      {{ formatearNumero(jornada.tasaServicio, 3) }} clientes por intervalo.
    </p>

    <template v-if="visible.banco">
      <h3>El banco durante la corrida 1</h3>
      <BancoAnimado :key="jornada.numero" :clientes="jornada.corrida1.clientes" :numero-servidores="numeroServidores" :inicio="jornada.inicio" />
    </template>

    <template v-if="visible.graficas">
      <h3>Gráficas</h3>
      <div class="rejillaGraficas">
        <Grafica titulo="Personas en el banco y en la fila (corrida 1)" explicacion="Pasa el cursor para ver la hora exacta." :opcion="opcionFila" />
        <Grafica titulo="Espera promedio en cada corrida" explicacion="La franja es el intervalo de confianza del 95 %." :opcion="opcionCorridas" />
        <Grafica titulo="Fracción del tiempo con n personas" explicacion="Promedio de todas las corridas." :opcion="opcionTablaLongitudes" />
        <Grafica titulo="Ocupación de cada caja" explicacion="La franja verde es el rango meta." :opcion="opcionCajas" />
      </div>
    </template>

    <template v-if="visible.resumen">
      <h3>Medidas de efectividad · promedio de {{ jornada.medidasPorCorrida.length }} corridas</h3>
      <div class="tabla">
        <table>
          <thead><tr><th>Medida</th><th>Promedio</th><th>Intervalo de confianza 95 %</th><th>Mínimo</th><th>Máximo</th></tr></thead>
          <tbody>
            <tr v-for="fila in filasResumen" :key="fila.clave">
              <td>{{ fila.medida.nombre }}<br><small class="descripcion">{{ fila.medida.descripcion }}</small></td>
              <td><b>{{ formatearMedida(fila.valores.promedio, fila.medida) }}</b> <small>{{ fila.medida.unidad === "%" ? "" : fila.medida.unidad }}</small></td>
              <td>{{ intervalo(fila.valores, fila.medida) }}</td>
              <td>{{ formatearMedida(fila.valores.minimo, fila.medida) }}</td>
              <td>{{ formatearMedida(fila.valores.maximo, fila.medida) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template v-if="visible.ciw && filasCiw">
      <h3>Validación con Ciw</h3>
      <p class="nota">
        El mismo banco simulado con la librería independiente Ciw. Cada medida se compara con la prueba t de Welch:
        si el valor p es mayor que α, no hay diferencia significativa.
        <template v-if="medidasDistintas">
          Con varias comparaciones al mismo α, alguna puede salir distinta solo por azar; si se repite con otra semilla
          o con más corridas, sí indica un problema.
        </template>
      </p>
      <div class="tabla">
        <table>
          <thead><tr><th>Medida</th><th>Este simulador</th><th>Ciw</th><th>Valor p</th><th>¿Coinciden?</th></tr></thead>
          <tbody>
            <tr v-for="fila in filasCiw" :key="fila.medida.nombre">
              <td>{{ fila.medida.nombre }}</td>
              <td>{{ formatearMedida(fila.propio.promedio, fila.medida) }} <small>({{ intervalo(fila.propio, fila.medida) }})</small></td>
              <td>{{ formatearMedida(fila.ciw.promedio, fila.medida) }} <small>({{ intervalo(fila.ciw, fila.medida) }})</small></td>
              <td>{{ formatearNumero(fila.valorP, 3) }}</td>
              <td><span :class="['estado', fila.coinciden ? 'cumple' : 'noCumple']">{{ fila.coinciden ? "✓ Sí" : "✗ Diferencia significativa" }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template v-if="visible.poisson">
      <h3>¿Las llegadas son Poisson?</h3>
      <ResultadoPoisson :prueba="jornada.poisson" />
    </template>

    <details v-if="visible.longitudes">
      <summary>Tabla de longitudes</summary>
      <div class="tabla alta">
        <table>
          <thead><tr><th>n personas</th><th>P(banco = n)</th><th>Acumulada</th><th>P(fila = n)</th><th>Acumulada</th></tr></thead>
          <tbody>
            <tr v-for="fila in filasLongitudes" :key="fila.personas">
              <td>{{ fila.personas }}</td>
              <td>{{ formatearPorcentaje(fila.enSistema, 2) }}</td>
              <td>{{ formatearPorcentaje(fila.acumuladaSistema, 2) }}</td>
              <td>{{ formatearPorcentaje(fila.enCola, 2) }}</td>
              <td>{{ formatearPorcentaje(fila.acumuladaCola, 2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <details v-if="visible.clientes">
      <summary>Corrida 1: tabla cliente por cliente ({{ jornada.corrida1.clientes.length }} clientes)</summary>
      <TablaClientes :clientes="jornada.corrida1.clientes" :inicio="jornada.inicio" />
    </details>
  </div>
</template>

<style scoped>
.seccionJornada { display: grid; grid-template-columns: minmax(0, 1fr); }
.descripcion { color: var(--textoTenue); }
.tabla.alta { max-height: 420px; }
td small { color: var(--textoSecundario); }
</style>
