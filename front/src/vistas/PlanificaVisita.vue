<script setup>
/**
 * Vista del cliente: elige una fecha y ve la espera estimada en la fila por franja horaria.
 * Todo sale de la API: el calendario (horario, excepciones, quincena) y las esperas (motor de simulación).
 */
import { computed, ref, watch } from "vue";
import { pedirVisita } from "../api.js";
import CalendarioMes from "../componentes/CalendarioMes.vue";
import { CATEGORIAS, formatearDuracion, formatearFecha } from "../formato.js";

const props = defineProps({ fechaInicial: { type: String, default: null } });   // desde #/visita/AAAA-MM-DD

const seleccion = ref(props.fechaInicial);
const visita = ref(null);
const cargando = ref(false);
const error = ref("");
let pedidoActual = 0;

function alSaberHoy(hoy) {
  if (!seleccion.value) seleccion.value = hoy;
}

watch(seleccion, async (fecha) => {
  if (!fecha) return;
  history.replaceState(null, "", `#/visita/${fecha}`);   // la fecha queda en la dirección para compartirla
  const pedido = ++pedidoActual;
  cargando.value = true;
  error.value = "";
  try {
    const respuesta = await pedirVisita(fecha);
    if (pedido === pedidoActual) visita.value = respuesta;
  } catch (problema) {
    if (pedido === pedidoActual) error.value = problema.message;
  } finally {
    if (pedido === pedidoActual) cargando.value = false;
  }
}, { immediate: true });

/** Las franjas en orden, con una fila de «cerrado» entre jornadas (p. ej. 12:00–14:00). */
const filas = computed(() => {
  const resultado = [];
  visita.value?.franjas.forEach((franja, posicion) => {
    const anterior = visita.value.franjas[posicion - 1];
    if (anterior && anterior.jornada !== franja.jornada) {
      resultado.push({ tipo: "cierre", desde: anterior.hasta, hasta: franja.desde });
    }
    resultado.push({ tipo: "franja", posicion, ...franja });
  });
  return resultado;
});

const mejor = computed(() => (visita.value?.recomendada == null ? null : visita.value.franjas[visita.value.recomendada]));
const similares = computed(() => (visita.value?.similares ?? []).map((posicion) => visita.value.franjas[posicion]));
const servicioMedio = computed(() => {
  const servicios = (visita.value?.franjas ?? []).filter((franja) => franja.servicio).map((franja) => franja.servicio.promedio);
  return servicios.length ? servicios.reduce((suma, valor) => suma + valor, 0) / servicios.length : null;
});
const rango = (franja) => `${franja.desde}–${franja.hasta}`;
</script>

<template>
  <section class="visita" aria-labelledby="tituloVisita">
    <header class="encabezado">
      <h1 id="tituloVisita">Planifica tu visita</h1>
      <p class="nota">Elige una fecha y mira cuánto se espera en la fila según la hora a la que llegues.</p>
    </header>

    <div class="columnas">
      <div class="tarjeta">
        <CalendarioMes v-model:seleccion="seleccion" @hoy="alSaberHoy" />
      </div>

      <section class="tarjeta resultados" aria-live="polite" :aria-busy="cargando">
        <p v-if="error" class="aviso" role="alert">{{ error }}</p>
        <p v-else-if="!visita" class="nota">{{ cargando ? "Consultando…" : "Elige una fecha en el calendario." }}</p>

        <template v-else>
          <h2>{{ formatearFecha(visita.fecha) }}</h2>
          <p class="tipo">
            {{ visita.tipoDia === "quincena" ? "Período de quincena: suele llegar más gente" : "Día regular" }}
            <template v-if="visita.origen === 'excepcion' && visita.abierto"> · Horario especial{{ visita.motivo ? `: ${visita.motivo}` : "" }}</template>
          </p>

          <!-- Cerrado -->
          <template v-if="!visita.abierto">
            <p class="cerrado">
              El establecimiento no presta atención en esta fecha{{ visita.motivo ? ` (${visita.motivo})` : "" }}.
              <template v-if="visita.siguienteAbierta">
                La próxima fecha disponible es el {{ formatearFecha(visita.siguienteAbierta.fecha, "diaMes").toLowerCase() }}.
              </template>
              <template v-else>No hay fechas con atención en el próximo año.</template>
            </p>
            <button v-if="visita.siguienteAbierta" type="button" class="principal"
              @click="seleccion = visita.siguienteAbierta.fecha">
              Ver el {{ formatearFecha(visita.siguienteAbierta.fecha, "diaMes").toLowerCase() }}
            </button>
          </template>

          <p v-else-if="visita.sinEstimacion" class="aviso">
            Abrimos de {{ visita.jornadas.map((jornada) => `${jornada.inicio} a ${jornada.fin}`).join(" y de ") }}, pero todavía
            no hay estimaciones de espera para este horario. Vuelve a consultar más tarde.
          </p>

          <!-- Abierto: espera por franja -->
          <template v-else>
            <ul class="franjas" aria-label="Espera estimada en la fila según la hora de llegada">
              <template v-for="fila in filas" :key="`${fila.tipo}-${fila.desde}`">
                <li v-if="fila.tipo === 'cierre'" class="pausa">
                  <span>{{ rango(fila) }}</span><span>Cerrado</span>
                </li>
                <li v-else :class="{ mejor: fila.posicion === visita.recomendada }">
                  <span>
                    <strong class="hora">{{ rango(fila) }}</strong>
                    <span class="afluencia">{{ CATEGORIAS[fila.categoria].cliente }}</span>
                  </span>
                  <span class="espera">
                    <strong>{{ fila.Wq ? formatearDuracion(fila.Wq.promedio) : "—" }}</strong>
                    <span v-if="fila.posicion === visita.recomendada" class="sello">Recomendado</span>
                  </span>
                </li>
              </template>
            </ul>

            <p v-if="mejor" class="recomendacion">
              Te recomendamos llegar entre las <b>{{ mejor.desde }}</b> y las <b>{{ mejor.hasta }}</b>: es la franja con
              menor espera estimada en la fila (unos {{ formatearDuracion(mejor.Wq.promedio) }}).
              <template v-if="similares.length">
                Entre las {{ similares.map(rango).join(", las ") }} la espera es parecida.
              </template>
            </p>

            <p class="explicacion">
              <b>Espera en la fila</b>: tiempo desde que llegas hasta que una caja te llama.
              <template v-if="servicioMedio">Después, la atención en caja toma unos {{ formatearDuracion(servicioMedio) }}.</template>
              Es el promedio de {{ visita.corridas }} días simulados; un día real puede variar.
            </p>
          </template>
        </template>
      </section>
    </div>

    <p class="pie"><a class="enlace" href="#/">Ir al simulador (administración)</a></p>
  </section>
</template>

<style scoped>
.encabezado { margin-bottom: 1.25rem; }
.encabezado h1 { font-size: 1.6rem; }
.columnas { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr); gap: 1rem; align-items: start; }
.resultados h2 { font-size: 1.2rem; }
.tipo { color: var(--textoSecundario); margin: 0.2rem 0 0; }
.cerrado { margin: 1rem 0; }
.franjas { list-style: none; padding: 0; margin: 1rem 0; }
.franjas li {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.2rem 0.75rem;
  padding: 0.65rem 0.6rem; border-bottom: 1px solid var(--borde);
}
.franjas li.mejor { background: var(--resalte); border-radius: 10px; border-bottom-color: transparent; }
.franjas li.pausa { color: var(--textoTenue); font-size: 0.85rem; padding: 0.35rem 0.6rem; border-bottom-style: dashed; }
.hora { display: block; font-variant-numeric: tabular-nums; }
.afluencia { display: block; color: var(--textoSecundario); font-size: 0.82rem; }
.espera { display: flex; align-items: center; gap: 0.5rem; }
.espera strong { font-size: 1.15rem; font-variant-numeric: tabular-nums; }
.sello { font-size: 0.75rem; font-weight: 600; color: var(--acento); border: 1.5px solid currentColor; border-radius: 999px; padding: 0 0.5rem; }
.recomendacion { margin: 0.5rem 0; }
.explicacion { color: var(--textoSecundario); font-size: 0.85rem; margin: 0.75rem 0 0; }
.pie { text-align: center; margin-top: 1.5rem; font-size: 0.85rem; }
@media (max-width: 760px) {
  .columnas { grid-template-columns: minmax(0, 1fr); }
}
</style>
