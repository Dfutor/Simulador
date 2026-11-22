<script setup>
/**
 * Administración del establecimiento: cuándo se atiende y cómo se publican las estimaciones del cliente.
 * Al guardar, el servidor valida, simula cada escenario con los parámetros de los pasos 1 a 3 y lo publica.
 */
import { ref } from "vue";
import { guardarEstablecimiento } from "../api.js";
import CalendarioMes from "../componentes/CalendarioMes.vue";
import EditorJornadas from "../componentes/EditorJornadas.vue";
import { cargarEstablecimiento, conteosValidos, entradaParaEnviar, establecimiento, simulacion } from "../estado.js";
import { formatearFecha } from "../formato.js";
import ComparacionDias from "../resultados/ComparacionDias.vue";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const ZONAS = ["America/Bogota", "America/Mexico_City", "America/Lima", "America/Santiago", "America/Argentina/Buenos_Aires", "Europe/Madrid", "UTC"];

const configuracion = establecimiento.configuracion;
const guardando = ref(false);
const error = ref("");
const aviso = ref("");
const version = ref(0);
const fechaVistaPrevia = ref(establecimiento.hoy);

function alternarDia(dia) {
  if (dia.abierto && !dia.jornadas.length) dia.jornadas.push({ inicio: "08:00", fin: "12:00" });
}

function agregarExcepcion() {
  configuracion.excepciones.push({ fecha: establecimiento.hoy, motivo: "Festivo", abierto: false, jornadas: [] });
}

function cambiarTipoExcepcion(excepcion) {
  if (excepcion.abierto && !excepcion.jornadas.length) excepcion.jornadas.push({ inicio: "08:00", fin: "12:00" });
}

async function guardar() {
  error.value = "";
  aviso.value = "";
  if (!simulacion.entrada.jornadas.every((jornada) => conteosValidos(jornada.conteosTexto))) {
    error.value = "Los conteos del paso 1 no son válidos: corrígelos antes de publicar.";
    return;
  }
  guardando.value = true;
  try {
    // Una sola fuente: el horario de esta pestaña + los parámetros actuales de los pasos 1 a 3
    cargarEstablecimiento(await guardarEstablecimiento({ ...configuracion, entrada: entradaParaEnviar() }));
    version.value++;
    aviso.value = "Configuración guardada y estimaciones publicadas.";
  } catch (problema) {
    error.value = problema.message;
  } finally {
    guardando.value = false;
  }
}

const fechaHora = (iso) => new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
</script>

<template>
  <form class="establecimiento" @submit.prevent="guardar">
    <section>
      <h3>Días y horarios de atención</h3>
      <p class="nota">Las jornadas de un mismo día no se pueden superponer. Entre dos jornadas el banco cierra y termina de atender a los de adentro.</p>
      <div class="tabla">
        <table class="semana">
          <thead><tr><th>Día</th><th>Atiende</th><th>Jornadas</th></tr></thead>
          <tbody>
            <tr v-for="(dia, posicion) in configuracion.horarioSemanal" :key="posicion">
              <td>{{ DIAS[posicion] }}</td>
              <td><input v-model="dia.abierto" type="checkbox" :aria-label="`${DIAS[posicion]} abierto`" @change="alternarDia(dia)"></td>
              <td><EditorJornadas :jornadas="dia.jornadas" :deshabilitado="!dia.abierto" :nombre="DIAS[posicion]" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <h3>Excepciones</h3>
      <p class="nota">Festivos, cierres administrativos, horarios especiales o aperturas extraordinarias. Mandan sobre el horario semanal.</p>
      <div v-for="(excepcion, posicion) in configuracion.excepciones" :key="posicion" class="excepcion">
        <label class="campo">Fecha <input v-model="excepcion.fecha" type="date" required></label>
        <label class="campo">Ese día
          <select v-model="excepcion.abierto" @change="cambiarTipoExcepcion(excepcion)">
            <option :value="false">No se atiende</option>
            <option :value="true">Se atiende con este horario</option>
          </select>
        </label>
        <label class="campo">Motivo <input v-model="excepcion.motivo" type="text" maxlength="80" placeholder="Ej. Festivo"></label>
        <EditorJornadas v-if="excepcion.abierto" :jornadas="excepcion.jornadas" :nombre="excepcion.fecha" class="jornadasExcepcion" />
        <button type="button" class="quitar" :aria-label="`Quitar la excepción del ${excepcion.fecha}`"
          @click="configuracion.excepciones.splice(posicion, 1)">Quitar</button>
      </div>
      <button type="button" class="agregar" @click="agregarExcepcion">+ Agregar excepción</button>
    </section>

    <section>
      <h3>Estimaciones para el cliente</h3>
      <div class="campos">
        <label class="campo">Zona horaria del establecimiento
          <input v-model="configuracion.zonaHoraria" list="zonasHorarias" required>
          <datalist id="zonasHorarias"><option v-for="zona in ZONAS" :key="zona" :value="zona" /></datalist>
          <small>Define qué día es «hoy» para el calendario</small>
        </label>
        <label class="campo">Largo de las franjas (min)
          <select v-model.number="configuracion.minutosPorFranja">
            <option v-for="minutos in [15, 30, 60, 120]" :key="minutos" :value="minutos">{{ minutos }}</option>
          </select>
          <small>Cada cuánto se parte la jornada para mostrar la espera</small>
        </label>
        <label class="campo">Aumento de llegadas en quincena
          <input v-model.number="configuracion.factorQuincena" type="number" min="1" max="3" step="0.05" required>
          <small>Supuesto del estudio, no observado: no se contó ningún día de quincena</small>
        </label>
        <label class="campo">Tasa de llegadas dentro de la jornada
          <select v-model="configuracion.modeloLlegadas">
            <option value="jornada">Una por jornada (modelo original)</option>
            <option value="franja">Una por franja, si la prueba la distingue</option>
          </select>
          <small>Con «por franja», las franjas pico y valle del paso 1 usan su propia tasa</small>
        </label>
      </div>
      <p class="nota">
        Al publicar se simula cada horario distinto en día regular y en quincena con los parámetros actuales de los pasos 1 a 3
        (cajas, conteos, servicio, corridas y semilla). Cada jornada se simula completa y las esperas se agrupan por hora de llegada.
      </p>

      <p v-if="error" class="aviso error" role="alert">{{ error }}</p>
      <p v-if="aviso" role="status"><span class="estado cumple">✓ {{ aviso }}</span></p>
      <button type="submit" class="principal" :disabled="guardando">{{ guardando ? "Simulando y publicando…" : "Guardar y publicar estimaciones" }}</button>

      <p v-if="establecimiento.publicacion" class="nota publicacion">
        <span :class="['estado', establecimiento.publicacion.vigente ? 'cumple' : 'noCumple']">
          {{ establecimiento.publicacion.vigente ? "✓ Publicadas" : "✗ Desactualizadas" }}
        </span>
        el {{ fechaHora(establecimiento.publicacion.publicadoEn) }} · {{ establecimiento.publicacion.escenarios.length }} escenarios ·
        {{ establecimiento.publicacion.corridas }} corridas cada uno · semilla {{ establecimiento.publicacion.semilla }}
        ({{ establecimiento.publicacion.semillaManual ? "manual" : "del reloj" }}) · modelo {{ establecimiento.publicacion.versionModelo }}
      </p>
      <p v-else class="nota">Todavía no hay estimaciones publicadas: se publican solas la primera vez que un cliente consulta.</p>
    </section>

    <section>
      <h3>Vista previa del calendario</h3>
      <p class="nota">
        Es el mismo calendario que ve el cliente, con lo último que se guardó.
        <a class="enlace" href="#/visita" target="_blank" rel="noopener">Abrir la vista del cliente ↗</a>
      </p>
      <div class="vistaPrevia">
        <CalendarioMes v-model:seleccion="fechaVistaPrevia" :version="version" />
        <p v-if="fechaVistaPrevia" class="nota seleccionada">
          <span>{{ formatearFecha(fechaVistaPrevia) }}</span>
          <a class="enlace" :href="`#/visita/${fechaVistaPrevia}`" target="_blank" rel="noopener">Ver como cliente ↗</a>
        </p>
      </div>
    </section>
  </form>

  <ComparacionDias :key="version" />
</template>

<style scoped>
.establecimiento { display: grid; gap: 0.5rem; }
.establecimiento > section { border-bottom: 1px solid var(--borde); padding-bottom: 1.25rem; }
.establecimiento h3:first-child { margin-top: 0.5rem; }
.semana td, .semana th { text-align: left; white-space: normal; vertical-align: middle; }
.semana td:first-child { font-weight: 600; width: 7rem; }
.semana td:nth-child(2) { width: 5rem; }
.excepcion {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(min(190px, 100%), 1fr)); gap: 0.5rem 1rem; align-items: end;
  padding: 0.75rem 0; border-bottom: 1px dashed var(--borde);
}
.jornadasExcepcion { grid-column: 1 / -1; }
.quitar { justify-self: start; padding: 0.4rem 0.9rem; font-size: 0.9rem; }
.agregar { margin-top: 0.75rem; width: 100%; border-style: dashed; color: var(--acento); }
.error { border-color: var(--estadoCritico); color: var(--estadoCritico); }
.publicacion { margin-top: 0.75rem; }
.vistaPrevia { max-width: 420px; }
.seleccionada { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.25rem 1rem; }</style>
