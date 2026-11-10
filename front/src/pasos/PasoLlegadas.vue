<script setup>
import { reactive, watch } from "vue";
import { pedirAjustePoisson } from "../api.js";
import { ajustes, conteosValidos, entradaParaEnviar, leerConteos, simulacion } from "../estado.js";
import { formatearNumero } from "../formato.js";
import ResultadoPoisson from "../resultados/ResultadoPoisson.vue";

const entrada = simulacion.entrada;
const visible = ajustes.variablesVisibles;
const pruebasPoisson = reactive({});
const temporizadores = {};

function revisarPoisson(posicion) {
  clearTimeout(temporizadores[posicion]);
  temporizadores[posicion] = setTimeout(async () => {
    const texto = entrada.jornadas[posicion]?.conteosTexto ?? "";
    if (!conteosValidos(texto)) {
      pruebasPoisson[posicion] = null;
      return;
    }
    try {
      pruebasPoisson[posicion] = await pedirAjustePoisson(leerConteos(texto), entradaParaEnviar().alfa);
    } catch {
      pruebasPoisson[posicion] = null;
    }
  }, 400);
}

watch(() => entrada.jornadas.map((jornada) => jornada.conteosTexto),
  () => entrada.jornadas.forEach((_, posicion) => revisarPoisson(posicion)), { immediate: true });

function llegadasPorIntervalo(jornada) {
  const conteos = leerConteos(jornada.conteosTexto);
  if (!conteosValidos(jornada.conteosTexto)) return "—";
  const enviada = entradaParaEnviar();
  const promedio = conteos.reduce((suma, conteo) => suma + conteo, 0) / conteos.length;
  return formatearNumero(promedio * enviada.proporcionVanACaja * enviada.factorLlegadas);
}

function agregarJornada() {
  entrada.jornadas.push({ inicio: "08:00", fin: "12:00", conteosTexto: "", minutosPorCliente: 5, servicioMinimo: 1, servicioMaximo: 10 });
}

function quitarJornada(posicion) {
  entrada.jornadas.splice(posicion, 1);
}
</script>

<template>
  <div class="paso">
    <p class="nota">Cuántas personas entran al banco. Escribe lo que se contó en cada intervalo, separado por comas o espacios.</p>

    <div class="campos">
      <label v-if="visible.tiempoEntreTomasDeDatos" class="campo">Minutos de cada intervalo de conteo
        <input v-model.number="entrada.tiempoEntreTomasDeDatos" type="number" min="0.1" step="any" required>
      </label>
      <label v-if="visible.proporcionVanACaja" class="campo">Proporción que va a caja
        <input v-model.number="entrada.proporcionVanACaja" type="number" min="0.01" max="1" step="any" required>
        <small>1 = todos los que entran hacen fila para caja</small>
      </label>
      <label v-if="visible.proporcionPrioritarios" class="campo">Proporción de clientes prioritarios
        <input v-model.number="entrada.proporcionPrioritarios" type="number" min="0" max="1" step="any" required>
        <small>Embarazadas y adultos mayores, pasan primero</small>
      </label>
      <label v-if="visible.escenario" class="campo">Escenario
        <select v-model="simulacion.escenario">
          <option value="normal">Día normal</option>
          <option value="quincena">Día de quincena</option>
        </select>
      </label>
      <label v-if="visible.escenario && simulacion.escenario === 'quincena'" class="campo">Aumento de llegadas en quincena
        <input v-model.number="simulacion.factorQuincena" type="number" min="1" step="0.05" required>
        <small>1,3 = llega 30 % más gente</small>
      </label>
    </div>

    <article v-for="(jornada, posicion) in entrada.jornadas" :key="posicion" class="jornada">
      <header>
        <h3>Jornada {{ posicion + 1 }}</h3>
        <button v-if="entrada.jornadas.length > 1" type="button" class="quitar" @click="quitarJornada(posicion)">Quitar</button>
      </header>
      <div class="campos">
        <label class="campo">Abre a las <input v-model="jornada.inicio" type="time" required></label>
        <label class="campo">Cierra la puerta a las <input v-model="jornada.fin" type="time" required></label>
      </div>
      <label class="campo conteos">Personas por intervalo ({{ leerConteos(jornada.conteosTexto).length }} intervalos)
        <textarea v-model="jornada.conteosTexto" rows="2" required></textarea>
        <small>Llegadas que se simulan: <b>{{ llegadasPorIntervalo(jornada) }}</b> personas por intervalo</small>
      </label>
      <ResultadoPoisson v-if="pruebasPoisson[posicion]" :prueba="pruebasPoisson[posicion]" />
    </article>

    <button type="button" class="agregar" @click="agregarJornada">+ Agregar jornada</button>
  </div>
</template>

<style scoped>
.jornada { border-top: 1px solid var(--borde); margin-top: 1.5rem; padding-top: 0.5rem; }
.jornada header { display: flex; justify-content: space-between; align-items: center; }
.jornada .campos { margin: 0.75rem 0 1rem; }
.conteos { margin-bottom: 0.75rem; }
.quitar { padding: 0.3rem 0.8rem; font-size: 0.9rem; }
.agregar { margin-top: 1.5rem; width: 100%; border-style: dashed; color: var(--acento); }
</style>
