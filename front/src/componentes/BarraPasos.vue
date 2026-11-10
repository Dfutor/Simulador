<script setup>
const props = defineProps({
  pasos: { type: Array, required: true },
  pasoActual: { type: Number, required: true },
  pasoMaximoAlcanzado: { type: Number, required: true },
});
const emit = defineEmits(["ir"]);

function estadoDelPaso(numero) {
  if (numero === props.pasoActual) return "actual";
  if (numero < props.pasoActual || numero <= props.pasoMaximoAlcanzado) return "completo";
  return "pendiente";
}
</script>

<template>
  <nav class="barraPasos" aria-label="Pasos de la simulación">
    <template v-for="(nombre, posicion) in pasos" :key="nombre">
      <div v-if="posicion > 0" class="conector" :class="{ hecho: posicion + 1 <= pasoActual }"></div>
      <button
        class="paso"
        :class="estadoDelPaso(posicion + 1)"
        :disabled="estadoDelPaso(posicion + 1) === 'pendiente'"
        :aria-current="posicion + 1 === pasoActual ? 'step' : undefined"
        @click="emit('ir', posicion + 1)"
      >
        <span class="circulo">
          <svg v-if="estadoDelPaso(posicion + 1) === 'completo'" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <template v-else>{{ posicion + 1 }}</template>
        </span>
        <span class="nombre">{{ nombre }}</span>
      </button>
    </template>
  </nav>
</template>

<style scoped>
.barraPasos { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }
.paso {
  display: flex; align-items: center; gap: 0.6rem;
  border: none; padding: 0; background: none; color: var(--textoSecundario);
  font-size: 1.05rem; white-space: nowrap;
}
.paso:disabled { cursor: default; opacity: 1; }
.circulo {
  width: 2.6rem; height: 2.6rem; border-radius: 50%;
  display: grid; place-items: center;
  border: 2px solid var(--bordeFuerte); color: var(--texto);
  font-weight: 600; background: var(--superficie);
  transition: background 0.2s, border-color 0.2s;
}
.paso.actual .circulo { background: var(--acento); border-color: var(--acento); color: var(--acentoTexto); }
.paso.actual .nombre { color: var(--texto); font-weight: 600; }
.paso.completo .circulo { background: var(--estadoBueno); border-color: var(--estadoBueno); color: #ffffff; }
.conector { flex: 1; height: 2px; min-width: 1rem; background: var(--borde); }
.conector.hecho { background: var(--texto); }

@media (max-width: 720px) {
  .barraPasos { gap: 0.4rem; }
  .paso .nombre { display: none; }
}
</style>
