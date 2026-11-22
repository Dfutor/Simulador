<script setup>
/**
 * Calendario de un mes. No calcula reglas: pide a la API qué días se atiende y cuáles son de quincena,
 * así la vista del cliente y la de administración muestran siempre lo mismo.
 */
import { onMounted, ref, watch } from "vue";
import { pedirCalendario } from "../api.js";
import { formatearFecha } from "../formato.js";

const props = defineProps({
  seleccion: { type: String, default: null },   // "AAAA-MM-DD"
  version: { type: Number, default: 0 },        // cambia cuando cambia la configuración → se vuelve a pedir
});
const emit = defineEmits(["update:seleccion", "hoy"]);

const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const anio = ref(0);
const mes = ref(0);
const dias = ref([]);
const hoy = ref(null);
const error = ref("");

const espaciosAntes = () => (new Date(Date.UTC(anio.value, mes.value - 1, 1)).getUTCDay() + 6) % 7;

async function cargar() {
  try {
    const respuesta = await pedirCalendario(anio.value, mes.value);
    if (respuesta.anio !== anio.value || respuesta.mes !== mes.value) return;   // llegó tarde: ya se cambió de mes
    dias.value = respuesta.dias;
    error.value = "";
    if (hoy.value !== respuesta.hoy) {
      hoy.value = respuesta.hoy;
      emit("hoy", respuesta.hoy);
    }
  } catch (problema) {
    error.value = problema.message;
  }
}

function irAlMesDe(fecha) {
  const [nuevoAnio, nuevoMes] = fecha.split("-").map(Number);
  if (nuevoAnio === anio.value && nuevoMes === mes.value) return;
  anio.value = nuevoAnio;
  mes.value = nuevoMes;
  cargar();
}

function moverMes(cambio) {
  const fecha = new Date(Date.UTC(anio.value, mes.value - 1 + cambio, 1));
  irAlMesDe(fecha.toISOString().slice(0, 10));
}

function etiqueta(dia) {
  return [
    formatearFecha(dia.fecha),
    dia.fecha === hoy.value && "hoy",
    dia.tipoDia === "quincena" && "período de quincena",
    dia.abierto ? (dia.origen === "excepcion" ? `horario especial${dia.motivo ? `: ${dia.motivo}` : ""}` : "con atención")
      : `sin atención${dia.motivo ? `: ${dia.motivo}` : ""}`,
  ].filter(Boolean).join(", ");
}

onMounted(() => {
  const local = new Date();
  irAlMesDe(props.seleccion ?? `${local.getFullYear()}-${String(local.getMonth() + 1).padStart(2, "0")}-01`);
});
watch(() => props.seleccion, (fecha) => fecha && irAlMesDe(fecha));
watch(() => props.version, cargar);
</script>

<template>
  <section class="calendario" aria-label="Calendario">
    <div class="mes">
      <h3 aria-live="polite">{{ anio ? formatearFecha(`${anio}-${String(mes).padStart(2, "0")}-01`, "mes") : "" }}</h3>
      <div class="navegacion">
        <button type="button" aria-label="Mes anterior" @click="moverMes(-1)">‹</button>
        <button type="button" aria-label="Mes siguiente" @click="moverMes(1)">›</button>
      </div>
    </div>
    <p v-if="error" class="aviso" role="alert">{{ error }}</p>
    <div class="semana" aria-hidden="true"><span v-for="dia in DIAS" :key="dia">{{ dia }}</span></div>
    <div class="dias" role="group">
      <span v-for="espacio in espaciosAntes()" :key="`espacio-${espacio}`" aria-hidden="true"></span>
      <button
        v-for="dia in dias" :key="dia.fecha" type="button" class="dia"
        :class="{ cerrado: !dia.abierto, excepcion: dia.origen === 'excepcion', hoy: dia.fecha === hoy }"
        :aria-pressed="dia.fecha === seleccion" :aria-label="etiqueta(dia)" :title="etiqueta(dia)"
        @click="emit('update:seleccion', dia.fecha)"
      >
        {{ Number(dia.fecha.slice(8)) }}
        <span v-if="dia.tipoDia === 'quincena'" class="punto" aria-hidden="true"></span>
      </button>
    </div>
    <p class="leyenda">
      <span><span class="punto" aria-hidden="true"></span> Quincena</span>
      <span><span class="muestra cerrado" aria-hidden="true">7</span> Sin atención</span>
      <span><span class="muestra excepcion" aria-hidden="true">7</span> Horario especial</span>
    </p>
  </section>
</template>

<style scoped>
.calendario { min-width: 0; }
.mes { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.5rem; }
.mes h3 { margin: 0; }
.navegacion { display: flex; gap: 0.25rem; }
.navegacion button { width: 44px; height: 44px; padding: 0; font-size: 1.35rem; border-radius: 8px; }
.semana, .dias { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 3px; text-align: center; }
.semana { color: var(--textoSecundario); font-size: 0.78rem; margin-bottom: 0.3rem; }
.dia {
  position: relative; min-height: 44px; padding: 0 0 6px; border: 1.5px solid transparent; border-radius: 8px;
  font-variant-numeric: tabular-nums;
}
.dia:hover { background: var(--resalte); }
.dia.hoy { border-color: var(--bordeFuerte); }
.dia.cerrado { color: var(--textoTenue); text-decoration: line-through; }
.dia.excepcion { text-decoration: underline dotted; text-underline-offset: 3px; }
.dia.cerrado.excepcion { text-decoration: line-through; }
.dia[aria-pressed="true"] { background: var(--acento); border-color: var(--acento); color: var(--acentoTexto); font-weight: 600; }
.punto { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--serie2); }
.dia .punto { position: absolute; bottom: 6px; left: calc(50% - 3px); }
.dia[aria-pressed="true"] .punto { background: currentColor; }
.leyenda { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; margin: 0.75rem 0 0; font-size: 0.8rem; color: var(--textoSecundario); }
.leyenda > span { display: inline-flex; align-items: center; gap: 0.35rem; }
.muestra { font-variant-numeric: tabular-nums; }
.muestra.cerrado { color: var(--textoTenue); text-decoration: line-through; }
.muestra.excepcion { text-decoration: underline dotted; text-underline-offset: 3px; }
</style>
