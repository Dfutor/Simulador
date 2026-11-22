<script setup>
import { computed, defineAsyncComponent, ref, watch } from "vue";
import { pedirEntradaPorDefecto, pedirEstablecimiento, pedirSimulacion } from "./api.js";
import BarraPasos from "./componentes/BarraPasos.vue";
import PanelAjustes from "./componentes/PanelAjustes.vue";
import { cargarEntradaPorDefecto, cargarEstablecimiento, conteosValidos, entradaParaEnviar, establecimiento, simulacion } from "./estado.js";
import PasoLlegadas from "./pasos/PasoLlegadas.vue";
import PasoPruebaKS from "./pasos/PasoPruebaKS.vue";
import PasoServicio from "./pasos/PasoServicio.vue";

const PasoResultados = defineAsyncComponent(() => import("./pasos/PasoResultados.vue"));
const VistaEstablecimiento = defineAsyncComponent(() => import("./vistas/VistaEstablecimiento.vue"));
const PlanificaVisita = defineAsyncComponent(() => import("./vistas/PlanificaVisita.vue"));

const PASOS = ["Llegadas", "Servicio", "Prueba KS", "Resultados"];
const COMPONENTES_PASO = [PasoLlegadas, PasoServicio, PasoPruebaKS, PasoResultados];

const formulario = ref(null);
const pasoMaximoAlcanzado = ref(1);
const ajustesAbiertos = ref(false);
const pestana = ref("simulacion");

// Dos experiencias en la misma aplicación: #/visita (cliente) y el resto (administración)
const ruta = ref(location.hash);
window.addEventListener("hashchange", () => { ruta.value = location.hash; });
const esCliente = computed(() => ruta.value.startsWith("#/visita"));
const fechaDeLaRuta = computed(() => ruta.value.match(/^#\/visita\/(\d{4}-\d{2}-\d{2})$/)?.[1] ?? null);

// El cliente solo necesita el calendario; la administración se carga al entrar a ella
watch(esCliente, async (cliente) => {
  if (cliente || simulacion.entrada) return;
  try {
    const [porDefecto, estado] = await Promise.all([pedirEntradaPorDefecto(), pedirEstablecimiento()]);
    cargarEstablecimiento(estado);
    // Si el establecimiento ya guardó sus parámetros, el simulador arranca con esos
    cargarEntradaPorDefecto(porDefecto, estado.guardada ? estado.configuracion.entrada : null);
  } catch (error) {
    simulacion.error = error.message;
  }
}, { immediate: true });

function irAlPaso(numero) {
  simulacion.pasoActual = numero;
  pasoMaximoAlcanzado.value = Math.max(pasoMaximoAlcanzado.value, numero);
  simulacion.error = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function pasoEsValido() {
  if (!formulario.value.reportValidity()) return false;
  if (simulacion.pasoActual === 1 && !simulacion.entrada.jornadas.every((jornada) => conteosValidos(jornada.conteosTexto))) {
    simulacion.error = "Cada jornada necesita al menos dos conteos enteros (0 o más), separados por comas o espacios.";
    return false;
  }
  return true;
}

async function simular() {
  simulacion.cargando = true;
  simulacion.error = "";
  simulacion.cajasNecesarias = null;
  try {
    simulacion.resultado = await pedirSimulacion(entradaParaEnviar());
    irAlPaso(4);
  } catch (error) {
    simulacion.error = error.message;
  } finally {
    simulacion.cargando = false;
  }
}

function siguiente() {
  if (!pasoEsValido()) return;
  if (simulacion.pasoActual === 3) simular();
  else irAlPaso(simulacion.pasoActual + 1);
}
</script>

<template>
  <main v-if="esCliente" class="pagina">
    <PlanificaVisita :key="fechaDeLaRuta ?? 'hoy'" :fecha-inicial="fechaDeLaRuta" />
  </main>

  <main v-else class="pagina" :class="{ ancha: pestana === 'simulacion' && simulacion.pasoActual === 4 }">
    <header class="encabezado">
      <h1>Simulador de la fila del banco</h1>
      <p class="nota">Una fila con prioridad, varias cajas y varias jornadas · metodología de Coss Bu</p>
    </header>

    <nav class="pestanas secciones" aria-label="Secciones">
      <button type="button" :class="{ activa: pestana === 'simulacion' }" :aria-current="pestana === 'simulacion' ? 'page' : undefined"
        @click="pestana = 'simulacion'">Simulación</button>
      <button type="button" :class="{ activa: pestana === 'establecimiento' }" :aria-current="pestana === 'establecimiento' ? 'page' : undefined"
        :disabled="!establecimiento.configuracion || !simulacion.entrada" @click="pestana = 'establecimiento'">Establecimiento</button>
      <a class="botonManual" href="/manual/">Manual de usuario</a>
      <a class="enlace vistaCliente" href="#/visita">Planifica tu visita (cliente) →</a>
    </nav>

    <div v-if="pestana === 'establecimiento'" class="tarjeta">
      <VistaEstablecimiento />
    </div>

    <template v-else>
    <BarraPasos :pasos="PASOS" :paso-actual="simulacion.pasoActual" :paso-maximo-alcanzado="pasoMaximoAlcanzado" @ir="irAlPaso" />

    <form ref="formulario" class="tarjeta" novalidate @submit.prevent="siguiente">
      <div class="tituloPaso">
        <h2>Paso {{ simulacion.pasoActual }}: {{ PASOS[simulacion.pasoActual - 1] }}</h2>
        <button type="button" class="icono" title="Ajustes" aria-label="Abrir ajustes" @click="ajustesAbiertos = true">
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path d="M14.7 6.3a4 4 0 0 0-5.4 5.2L3.6 17.2a1.4 1.4 0 0 0 0 2l1.2 1.2a1.4 1.4 0 0 0 2 0l5.7-5.7a4 4 0 0 0 5.2-5.4l-2.6 2.6-2.2-.6-.6-2.2z"
              fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
          </svg>
        </button>
      </div>

      <p v-if="simulacion.error" class="error" role="alert">{{ simulacion.error }}</p>

      <component :is="COMPONENTES_PASO[simulacion.pasoActual - 1]" v-if="simulacion.entrada" />
      <p v-else-if="!simulacion.error" class="nota">Cargando los valores por defecto…</p>

      <div class="navegacion">
        <button v-if="simulacion.pasoActual > 1" type="button" @click="irAlPaso(simulacion.pasoActual - 1)">Anterior</button>
        <span v-else></span>
        <button v-if="simulacion.pasoActual < 4" type="submit" class="principal" :disabled="simulacion.cargando || !simulacion.entrada">
          {{ simulacion.pasoActual === 3 ? (simulacion.cargando ? "Simulando…" : "Simular") : "Siguiente" }}
        </button>
        <button v-else type="button" class="principal" @click="irAlPaso(1)">Nueva simulación</button>
      </div>
    </form>
    </template>

    <PanelAjustes v-if="ajustesAbiertos" @cerrar="ajustesAbiertos = false" />
  </main>
</template>

<style scoped>
.pagina { max-width: 980px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
.pagina.ancha { max-width: 1280px; }
.encabezado { margin-bottom: 1.75rem; }
.encabezado h1 { font-size: 1.6rem; }
.secciones { align-items: center; }
.secciones button:disabled { cursor: default; }
.botonManual {
  padding: 0.4rem 1rem;
  border: 1px solid var(--bordeFuerte);
  border-radius: 999px;
  background: var(--superficie);
  color: var(--acento);
  text-decoration: none;
}
.botonManual:hover { text-decoration: underline; }
.vistaCliente { margin-left: auto; font-size: 0.92rem; }
.tituloPaso { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; }
.navegacion { display: flex; justify-content: space-between; margin-top: 2rem; }
.error {
  border: 1.5px solid var(--estadoCritico); color: var(--estadoCritico);
  border-radius: 10px; padding: 0.75rem 1rem; margin: 0 0 1rem;
}
@media (max-width: 640px) {
  .pagina { padding: 1rem 1rem 3rem; }
}
</style>
