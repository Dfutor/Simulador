<script setup>
/** Jornadas de un día (inicio y fin). Se usa en el horario semanal y en las excepciones. */
const props = defineProps({
  jornadas: { type: Array, required: true },
  deshabilitado: { type: Boolean, default: false },
  nombre: { type: String, default: "" },
});

function agregar() {
  const ultima = props.jornadas.at(-1);
  props.jornadas.push(ultima ? { inicio: "14:00", fin: "16:30" } : { inicio: "08:00", fin: "12:00" });
}
</script>

<template>
  <div class="jornadas" :class="{ deshabilitado }">
    <div v-for="(jornada, posicion) in jornadas" :key="posicion" class="jornada">
      <input v-model="jornada.inicio" type="time" required :disabled="deshabilitado" :aria-label="`${nombre} jornada ${posicion + 1}: abre`">
      <span aria-hidden="true">–</span>
      <input v-model="jornada.fin" type="time" required :disabled="deshabilitado" :aria-label="`${nombre} jornada ${posicion + 1}: cierra`">
      <button type="button" class="mini" :disabled="deshabilitado" :aria-label="`Quitar la jornada ${posicion + 1} de ${nombre}`"
        @click="jornadas.splice(posicion, 1)">✕</button>
    </div>
    <button type="button" class="mini agregar" :disabled="deshabilitado" @click="agregar">+ Jornada</button>
  </div>
</template>

<style scoped>
.jornadas { display: flex; flex-wrap: wrap; gap: 0.4rem 0.75rem; align-items: center; }
.jornadas.deshabilitado { opacity: 0.55; }
.jornada { display: inline-flex; align-items: center; gap: 0.3rem; }
.jornada input { width: 7.5rem; padding: 0.35rem 0.5rem; }
.mini { padding: 0.25rem 0.6rem; font-size: 0.85rem; }
.mini:disabled { cursor: not-allowed; }
.agregar { border-style: dashed; color: var(--acento); }
</style>
