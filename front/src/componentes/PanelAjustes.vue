<script setup>
import { FUENTES, SECCIONES_RESULTADOS, VARIABLES_OPCIONALES, ajustes, restaurarAjustes, simulacion } from "../estado.js";

const emit = defineEmits(["cerrar"]);

function valorPorDefecto(nombre) {
  const porDefecto = simulacion.entradaPorDefecto;
  if (!porDefecto) return "";
  if (nombre === "escenario") return "día normal";
  if (nombre === "semilla") return "reloj del computador (ms)";
  if (nombre === "compararConCiw") return "no";
  return porDefecto[nombre];
}
</script>

<template>
  <div class="fondo" @click.self="emit('cerrar')">
    <aside class="panel" role="dialog" aria-label="Ajustes">
      <header>
        <h2>Ajustes</h2>
        <button class="icono" title="Cerrar" @click="emit('cerrar')">✕</button>
      </header>

      <section>
        <h3>Apariencia</h3>
        <label class="campo">Tema
          <select v-model="ajustes.tema">
            <option value="automatico">Automático (como el sistema)</option>
            <option value="claro">Claro</option>
            <option value="oscuro">Oscuro</option>
          </select>
        </label>
        <label class="campo">Tipo de letra
          <select v-model="ajustes.fuente">
            <option v-for="(fuente, clave) in FUENTES" :key="clave" :value="clave">{{ fuente.nombre }}</option>
          </select>
        </label>
        <label class="campo">Tamaño de letra: {{ ajustes.tamanoLetra }} px
          <input v-model.number="ajustes.tamanoLetra" type="range" min="13" max="21" step="1">
        </label>
      </section>

      <section>
        <h3>Gráficas</h3>
        <label class="campo">Estilo de las líneas
          <select v-model="ajustes.estiloLinea">
            <option value="escalonada">Escalonada (muestra cada cambio)</option>
            <option value="recta">Recta</option>
            <option value="suave">Suavizada</option>
          </select>
        </label>
        <label class="opcion"><input v-model="ajustes.mostrarCuadricula" type="checkbox"> Mostrar cuadrícula</label>
        <label class="opcion"><input v-model="ajustes.mostrarEtiquetas" type="checkbox"> Mostrar valores sobre las barras</label>
        <label class="opcion"><input v-model="ajustes.animaciones" type="checkbox"> Animaciones</label>
      </section>

      <section>
        <h3>Resultados óptimos (metas)</h3>
        <p class="nota">Los resultados se marcan como “cumple” o “no cumple” con estas metas, y con ellas se buscan las cajas necesarias.</p>
        <label class="campo">Espera máxima aceptable en la fila (min)
          <input v-model.number="ajustes.metaEsperaMinutos" type="number" min="0.5" step="0.5">
        </label>
        <div class="dosColumnas">
          <label class="campo">Ocupación mínima (%)
            <input v-model.number="ajustes.utilizacionMinima" type="number" min="0" max="100">
          </label>
          <label class="campo">Ocupación máxima (%)
            <input v-model.number="ajustes.utilizacionMaxima" type="number" min="0" max="100">
          </label>
        </div>
      </section>

      <section>
        <h3>Variables que se piden</h3>
        <p class="nota">Las que no se piden usan el valor por defecto que se muestra. Las jornadas, los conteos, el tiempo de servicio y las cajas siempre se piden.</p>
        <label v-for="(nombre, clave) in VARIABLES_OPCIONALES" :key="clave" class="opcion">
          <input v-model="ajustes.variablesVisibles[clave]" type="checkbox">
          <span>{{ nombre }} <small>· por defecto: {{ valorPorDefecto(clave) }}</small></span>
        </label>
      </section>

      <section>
        <h3>Resultados que se muestran</h3>
        <label v-for="(nombre, clave) in SECCIONES_RESULTADOS" :key="clave" class="opcion">
          <input v-model="ajustes.seccionesVisibles[clave]" type="checkbox"> {{ nombre }}
        </label>
      </section>

      <button class="restaurar" @click="restaurarAjustes">Restaurar ajustes</button>
    </aside>
  </div>
</template>

<style scoped>
.fondo { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.35); z-index: 20; display: flex; justify-content: flex-end; }
.panel {
  width: min(420px, 100%); height: 100%; overflow-y: auto;
  background: var(--superficie); border-left: 1px solid var(--borde);
  padding: 1.25rem 1.5rem 2rem; display: grid; align-content: start; gap: 0.5rem;
}
header { display: flex; justify-content: space-between; align-items: center; }
section { display: grid; gap: 0.75rem; padding-bottom: 1rem; border-bottom: 1px solid var(--borde); }
section h3 { margin-top: 1rem; }
.opcion { display: flex; gap: 0.6rem; align-items: baseline; font-size: 0.95rem; cursor: pointer; }
.opcion small { color: var(--textoTenue); }
.dosColumnas { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.restaurar { margin-top: 1rem; }
</style>
