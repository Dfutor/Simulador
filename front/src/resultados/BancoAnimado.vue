<script setup>
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Pane } from "tweakpane";
import { onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ajustes, versionTema } from "../estado.js";
import { horaReloj } from "../formato.js";

const props = defineProps({
  clientes: { type: Array, required: true },
  numeroServidores: { type: Number, required: true },
  inicio: { type: String, required: true },
});

const SEPARACION_CAJAS = 2.4;
const PERSONAS_POR_FILA = 14;
const FILAS_DE_ESPERA = 10;
const SEPARACION_PERSONAS = 0.85;
const MINUTOS_PARA_SALIR = 3;

const lienzo = ref(null);
const contenedorPanel = ref(null);
const tablero = reactive({ hora: props.inicio, enFila: 0, atendiendo: 0, atendidos: 0, afuera: 0 });

const anchoSala = Math.max(props.numeroServidores * SEPARACION_CAJAS + 4, PERSONAS_POR_FILA * SEPARACION_PERSONAS + 6);
const fondoSala = FILAS_DE_ESPERA * SEPARACION_PERSONAS + 9;
const zCajas = -fondoSala / 2 + 1.5;
const zAtencion = zCajas + 1.3;
const zInicioFila = zAtencion + 2;
const puntoEntrada = new THREE.Vector3(-anchoSala / 2 + 0.5, 0, fondoSala / 2 - 0.5);
const puntoSalida = new THREE.Vector3(anchoSala / 2 + 1.5, 0, fondoSala / 2 - 0.5);
const finDeLaAnimacion = Math.max(...props.clientes.map((cliente) => cliente.terminacionServicio)) + MINUTOS_PARA_SALIR;

const parametros = { minutosPorSegundo: 5, reproduciendo: ajustes.animaciones, minuto: 0, girarCamara: false };
const clientesPorInicio = [...props.clientes].sort((primero, segundo) => primero.inicioServicio - segundo.inicioServicio);

let renderizador, escena, camara, controles, panel, cuadroAnimacion, observadorTamano;
let materiales, cajas = [], personas = new Map();
let ultimoInstante = performance.now();
let ultimaActualizacionPanel = 0;
let actualizandoPanel = false;

function colorDe(variable) {
  return new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue(variable).trim());
}

function aplicarColores() {
  escena.background = colorDe("--superficie");
  materiales.piso.color = colorDe("--plano");
  materiales.pared.color = colorDe("--borde");
  materiales.mostrador.color = colorDe("--bordeFuerte");
  materiales.cajaOcupada.color = colorDe("--serie3");
  materiales.normal.color = colorDe("--serie1");
  materiales.prioritario.color = colorDe("--serie2");
}

function posicionDeCaja(numeroCaja) {
  const ancho = (props.numeroServidores - 1) * SEPARACION_CAJAS;
  return -ancho / 2 + (numeroCaja - 1) * SEPARACION_CAJAS;
}

/** Fila en zigzag: cada renglón cambia de sentido para que la fila se vea continua. */
function posicionEnFila(puesto) {
  const puestoVisible = Math.min(puesto, PERSONAS_POR_FILA * FILAS_DE_ESPERA - 1);
  const renglon = Math.floor(puestoVisible / PERSONAS_POR_FILA);
  let columna = puestoVisible % PERSONAS_POR_FILA;
  if (renglon % 2 === 1) columna = PERSONAS_POR_FILA - 1 - columna;
  const ancho = (PERSONAS_POR_FILA - 1) * SEPARACION_PERSONAS;
  return new THREE.Vector3(-ancho / 2 + columna * SEPARACION_PERSONAS, 0, zInicioFila + renglon * SEPARACION_PERSONAS);
}

function construirSala() {
  const piso = new THREE.Mesh(new THREE.BoxGeometry(anchoSala, 0.2, fondoSala), materiales.piso);
  piso.position.y = -0.1;
  piso.receiveShadow = true;
  escena.add(piso);

  const paredFondo = new THREE.Mesh(new THREE.BoxGeometry(anchoSala, 1.6, 0.2), materiales.pared);
  paredFondo.position.set(0, 0.8, -fondoSala / 2);
  const paredLateral = new THREE.Mesh(new THREE.BoxGeometry(0.2, 1.6, fondoSala), materiales.pared);
  paredLateral.position.set(-anchoSala / 2, 0.8, 0);
  escena.add(paredFondo, paredLateral);

  for (let numeroCaja = 1; numeroCaja <= props.numeroServidores; numeroCaja++) {
    const mostrador = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1, 0.8), materiales.mostrador);
    mostrador.position.set(posicionDeCaja(numeroCaja), 0.5, zCajas);
    mostrador.castShadow = true;
    escena.add(mostrador);
    cajas.push(mostrador);
  }
}

function crearPersona(cliente) {
  const persona = new THREE.Group();
  const material = cliente.prioritario ? materiales.prioritario : materiales.normal;
  const cuerpo = new THREE.Mesh(materiales.geometriaCuerpo, material);
  cuerpo.position.y = 0.45;
  const cabeza = new THREE.Mesh(materiales.geometriaCabeza, material);
  cabeza.position.y = 1.08;
  cuerpo.castShadow = cabeza.castShadow = true;
  persona.add(cuerpo, cabeza);
  if (cliente.prioritario) {
    const aro = new THREE.Mesh(materiales.geometriaAro, material);
    aro.rotation.x = Math.PI / 2;
    aro.position.y = 1.45;
    persona.add(aro);
  }
  persona.visible = false;
  escena.add(persona);
  return persona;
}

function actualizarPersonas(segundosReales) {
  const minuto = parametros.minuto;
  const suavizado = 1 - Math.exp(-segundosReales * (4 + parametros.minutosPorSegundo / 3));
  let puestoEnFila = 0;
  let atendiendo = 0;
  let atendidos = 0;
  const cajasOcupadas = new Set();

  for (const cliente of clientesPorInicio) {
    const persona = personas.get(cliente.cliente);
    let destino = null;
    if (minuto >= cliente.momentoLlegada && minuto < cliente.inicioServicio) {
      destino = posicionEnFila(puestoEnFila++);
    } else if (minuto >= cliente.inicioServicio && minuto < cliente.terminacionServicio) {
      destino = new THREE.Vector3(posicionDeCaja(cliente.servidor), 0, zAtencion);
      cajasOcupadas.add(cliente.servidor);
      atendiendo++;
    } else if (minuto >= cliente.terminacionServicio && minuto < cliente.terminacionServicio + MINUTOS_PARA_SALIR) {
      destino = puntoSalida;
    }
    if (minuto >= cliente.terminacionServicio) atendidos++;

    if (!destino) {
      persona.visible = false;
      continue;
    }
    if (!persona.visible) {
      persona.visible = true;
      persona.position.copy(destino === puntoSalida ? new THREE.Vector3(posicionDeCaja(cliente.servidor), 0, zAtencion) : puntoEntrada);
    }
    persona.position.lerp(destino, suavizado);
  }

  cajas.forEach((mostrador, posicion) => {
    mostrador.material = cajasOcupadas.has(posicion + 1) ? materiales.cajaOcupada : materiales.mostrador;
  });
  Object.assign(tablero, {
    hora: horaReloj(props.inicio, minuto),
    enFila: puestoEnFila,
    atendiendo,
    atendidos,
    afuera: Math.max(0, puestoEnFila - PERSONAS_POR_FILA * FILAS_DE_ESPERA),
  });
}

function animar(instante) {
  const segundosReales = Math.min((instante - ultimoInstante) / 1000, 0.1);
  ultimoInstante = instante;
  if (parametros.reproduciendo) {
    parametros.minuto = Math.min(parametros.minuto + segundosReales * parametros.minutosPorSegundo, finDeLaAnimacion);
    if (parametros.minuto >= finDeLaAnimacion) parametros.reproduciendo = false;
  }
  if (instante - ultimaActualizacionPanel > 150) {
    actualizandoPanel = true;
    panel.refresh();
    actualizandoPanel = false;
    ultimaActualizacionPanel = instante;
  }
  controles.autoRotate = parametros.girarCamara;
  controles.update();
  actualizarPersonas(segundosReales);
  renderizador.render(escena, camara);
  cuadroAnimacion = requestAnimationFrame(animar);
}

function ajustarTamano() {
  const ancho = lienzo.value.clientWidth;
  const alto = lienzo.value.clientHeight;
  renderizador.setSize(ancho, alto, false);
  const proporcion = ancho / alto;
  const mitadVista = Math.max(anchoSala, fondoSala) * 0.55;
  camara.left = -mitadVista * proporcion;
  camara.right = mitadVista * proporcion;
  camara.top = mitadVista;
  camara.bottom = -mitadVista;
  camara.updateProjectionMatrix();
}

function crearPanel() {
  panel = new Pane({ container: contenedorPanel.value, title: "Controles" });
  panel.addBinding(parametros, "reproduciendo", { label: "Reproducir" });
  panel.addBinding(parametros, "minutosPorSegundo", { label: "Velocidad (min/s)", min: 0.5, max: 60, step: 0.5 });
  panel.addBinding(parametros, "minuto", {
    label: "Hora", min: 0, max: finDeLaAnimacion, step: 0.5, format: (minuto) => horaReloj(props.inicio, minuto),
  }).on("change", () => {
    if (!actualizandoPanel) parametros.reproduciendo = false;
  });
  panel.addBinding(parametros, "girarCamara", { label: "Girar cámara" });
  panel.addButton({ title: "Volver a empezar" }).on("click", () => {
    parametros.minuto = 0;
    parametros.reproduciendo = true;
  });
}

onMounted(() => {
  renderizador = new THREE.WebGLRenderer({ canvas: lienzo.value, antialias: true });
  renderizador.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderizador.shadowMap.enabled = true;
  escena = new THREE.Scene();
  camara = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
  camara.position.set(22, 20, 22);
  camara.lookAt(0, 0, 0);
  controles = new OrbitControls(camara, lienzo.value);
  controles.enableDamping = true;
  controles.maxPolarAngle = Math.PI / 2.2;

  escena.add(new THREE.HemisphereLight(0xffffff, 0x808080, 1.8));
  const sol = new THREE.DirectionalLight(0xffffff, 1.5);
  sol.position.set(10, 18, 8);
  sol.castShadow = true;
  sol.shadow.mapSize.set(1024, 1024);
  Object.assign(sol.shadow.camera, { left: -anchoSala, right: anchoSala, top: fondoSala, bottom: -fondoSala });
  escena.add(sol);

  materiales = {
    piso: new THREE.MeshStandardMaterial({ roughness: 0.95 }),
    pared: new THREE.MeshStandardMaterial({ roughness: 0.9 }),
    mostrador: new THREE.MeshStandardMaterial({ roughness: 0.6 }),
    cajaOcupada: new THREE.MeshStandardMaterial({ roughness: 0.6 }),
    normal: new THREE.MeshStandardMaterial({ roughness: 0.5 }),
    prioritario: new THREE.MeshStandardMaterial({ roughness: 0.5 }),
    geometriaCuerpo: new THREE.CylinderGeometry(0.22, 0.28, 0.9, 16),
    geometriaCabeza: new THREE.SphereGeometry(0.2, 16, 12),
    geometriaAro: new THREE.TorusGeometry(0.16, 0.04, 8, 20),
  };
  aplicarColores();
  construirSala();
  for (const cliente of props.clientes) personas.set(cliente.cliente, crearPersona(cliente));

  crearPanel();
  ajustarTamano();
  observadorTamano = new ResizeObserver(ajustarTamano);
  observadorTamano.observe(lienzo.value);
  cuadroAnimacion = requestAnimationFrame(animar);
});

watch(versionTema, () => escena && aplicarColores());

onBeforeUnmount(() => {
  cancelAnimationFrame(cuadroAnimacion);
  observadorTamano?.disconnect();
  panel?.dispose();
  controles?.dispose();
  renderizador?.dispose();
});
</script>

<template>
  <div class="banco">
    <canvas ref="lienzo" aria-label="Animación del banco durante la corrida 1"></canvas>
    <div class="tablero">
      <span class="hora">{{ tablero.hora }}</span>
      <span>{{ tablero.enFila }} en la fila</span>
      <span>{{ tablero.atendiendo }} en caja</span>
      <span>{{ tablero.atendidos }} atendidos</span>
      <span v-if="tablero.afuera">(+{{ tablero.afuera }} fuera de cuadro)</span>
    </div>
    <div class="leyenda">
      <span><i class="punto normal"></i> Cliente</span>
      <span><i class="punto prioritario"></i> Prioritario (con aro)</span>
      <span><i class="punto ocupada"></i> Caja atendiendo</span>
    </div>
    <div ref="contenedorPanel" class="panel"></div>
  </div>
</template>

<style scoped>
.banco { position: relative; border: 1px solid var(--borde); border-radius: 12px; overflow: hidden; }
canvas { display: block; width: 100%; height: 460px; touch-action: none; }
.tablero, .leyenda {
  position: absolute; left: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; align-items: baseline;
  background: color-mix(in srgb, var(--superficie) 85%, transparent);
  border-radius: 8px; padding: 0.4rem 0.75rem; font-size: 0.85rem; color: var(--textoSecundario);
}
.tablero { top: 0.75rem; }
.tablero .hora { font-size: 1.5rem; font-weight: 600; color: var(--texto); font-variant-numeric: tabular-nums; }
.leyenda { bottom: 0.75rem; }
.punto { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; vertical-align: -1px; }
.punto.normal { background: var(--serie1); }
.punto.prioritario { background: var(--serie2); }
.punto.ocupada { background: var(--serie3); border-radius: 2px; }
.panel { position: absolute; top: 0.75rem; right: 0.75rem; width: 250px; }
@media (max-width: 640px) {
  canvas { height: 380px; }
  .panel { position: static; width: auto; }
}
</style>
