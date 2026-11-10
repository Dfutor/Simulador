<script setup>
import { computed } from "vue";
import { pedirCajasNecesarias } from "../api.js";
import Grafica from "../componentes/Grafica.vue";
import { ajustes, entradaParaEnviar, simulacion } from "../estado.js";
import { formatearNumero, formatearPorcentaje, horaReloj } from "../formato.js";
import { opcionCurvaCajas, usarColores } from "../graficas.js";

const colores = usarColores();
const jornadas = computed(() => simulacion.resultado.jornadas);
const cajasActuales = computed(() => entradaParaEnviar().numeroServidores);

function evaluarJornada(jornada) {
  const espera = jornada.resumen.Wq;
  const ocupacion = jornada.resumen.utilizacion.promedio;
  return {
    espera,
    ocupacion,
    ultimaSalida: horaReloj(jornada.inicio, jornada.resumen.ultimaSalida.promedio),
    esperaCumple: espera.promedio <= ajustes.metaEsperaMinutos,
    ocupacionCumple: ocupacion >= ajustes.utilizacionMinima / 100 && ocupacion <= ajustes.utilizacionMaxima / 100,
    ocupacionTexto: ocupacion > ajustes.utilizacionMaxima / 100 ? "demasiado alta" : ocupacion < ajustes.utilizacionMinima / 100 ? "demasiado baja" : "en el rango",
  };
}

const evaluaciones = computed(() => jornadas.value.map(evaluarJornada));

async function buscarCajas() {
  simulacion.cargando = true;
  simulacion.error = "";
  try {
    simulacion.cajasNecesarias = await pedirCajasNecesarias(entradaParaEnviar(), ajustes.metaEsperaMinutos);
  } catch (error) {
    simulacion.error = error.message;
  } finally {
    simulacion.cargando = false;
  }
}

const opcionEspera = computed(() => simulacion.cajasNecesarias
  && opcionCurvaCajas(simulacion.cajasNecesarias.curva, jornadas.value, "Wq", colores.value));
const opcionOcupacion = computed(() => simulacion.cajasNecesarias
  && opcionCurvaCajas(simulacion.cajasNecesarias.curva, jornadas.value, "utilizacion", colores.value));
</script>

<template>
  <section class="seccion">
    <h3>Veredicto con {{ cajasActuales }} caja{{ cajasActuales === 1 ? "" : "s" }}</h3>
    <div class="jornadas">
      <article v-for="(jornada, posicion) in jornadas" :key="jornada.numero" class="tarjetaJornada">
        <h4>Jornada {{ jornada.numero }} · {{ jornada.inicio }}–{{ jornada.fin }}</h4>
        <div class="cifras">
          <div>
            <span class="etiqueta">Espera promedio en la fila</span>
            <span class="cifra">{{ formatearNumero(evaluaciones[posicion].espera.promedio, 1) }} <small>min</small></span>
            <span :class="['estado', evaluaciones[posicion].esperaCumple ? 'cumple' : 'noCumple']">
              {{ evaluaciones[posicion].esperaCumple ? "✓ Cumple" : "✗ No cumple" }} la meta de {{ formatearNumero(ajustes.metaEsperaMinutos, 1) }} min
            </span>
          </div>
          <div>
            <span class="etiqueta">Ocupación de las cajas</span>
            <span class="cifra">{{ formatearPorcentaje(evaluaciones[posicion].ocupacion, 0) }}</span>
            <span :class="['estado', evaluaciones[posicion].ocupacionCumple ? 'cumple' : 'noCumple']">
              {{ evaluaciones[posicion].ocupacionCumple ? "✓" : "✗" }} {{ evaluaciones[posicion].ocupacionTexto }}
              ({{ ajustes.utilizacionMinima }}–{{ ajustes.utilizacionMaxima }} %)
            </span>
          </div>
          <div>
            <span class="etiqueta">El último cliente sale a las</span>
            <span class="cifra">{{ evaluaciones[posicion].ultimaSalida }}</span>
            <span class="nota">La puerta cierra a las {{ jornada.fin }}</span>
          </div>
        </div>
        <p class="nota">
          Con 95 % de confianza, la espera promedio está entre {{ formatearNumero(evaluaciones[posicion].espera.limiteInferior, 1) }}
          y {{ formatearNumero(evaluaciones[posicion].espera.limiteSuperior, 1) }} minutos.
        </p>
      </article>
    </div>

    <div class="cajas">
      <button type="button" class="principal" :disabled="simulacion.cargando" @click="buscarCajas">
        {{ simulacion.cargando ? "Buscando…" : `¿Cuántas cajas se necesitan para esperar menos de ${formatearNumero(ajustes.metaEsperaMinutos, 1)} min?` }}
      </button>
      <template v-if="simulacion.cajasNecesarias">
        <p v-if="simulacion.cajasNecesarias.cajasRecomendadas" class="recomendacion">
          Se necesitan <b>{{ simulacion.cajasNecesarias.cajasRecomendadas }} cajas</b> para que la espera promedio
          sea de {{ formatearNumero(simulacion.cajasNecesarias.metaEsperaMinutos, 1) }} minutos o menos en todas las jornadas.
        </p>
        <p v-else class="recomendacion">Ni con {{ simulacion.cajasNecesarias.curva.length }} cajas se cumple la meta.</p>
        <div class="rejillaGraficas">
          <Grafica titulo="Espera promedio según el número de cajas" explicacion="Cada punto es el promedio de todas las corridas."
            :opcion="opcionEspera" />
          <Grafica titulo="Ocupación de las cajas según su número" explicacion="Más cajas: menos espera, pero más tiempo sin atender."
            :opcion="opcionOcupacion" />
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.seccion h3 { margin-top: 0; }
.jornadas { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr)); }
.tarjetaJornada { border: 1px solid var(--borde); border-radius: 12px; padding: 1rem 1.25rem; }
.tarjetaJornada h4 { margin: 0 0 0.75rem; font-size: 1rem; }
.cifras { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr)); }
.cifras > div { display: grid; gap: 0.15rem; align-content: start; }
.etiqueta { color: var(--textoSecundario); font-size: 0.85rem; }
.cifra { font-size: 1.9rem; font-weight: 600; line-height: 1.1; }
.cifra small { font-size: 1rem; font-weight: 400; color: var(--textoSecundario); }
.cifras .estado { font-size: 0.85rem; }
.cifras .nota { margin: 0; font-size: 0.85rem; }
.cajas { margin-top: 1.25rem; display: grid; gap: 0.75rem; justify-items: start; }
.cajas .rejillaGraficas { width: 100%; }
.recomendacion { font-size: 1.1rem; margin: 0.25rem 0; }
</style>
