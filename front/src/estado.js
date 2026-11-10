import { reactive, ref, watch } from "vue";

export const VARIABLES_OPCIONALES = {
  tiempoEntreTomasDeDatos: "Minutos entre tomas de datos",
  proporcionVanACaja: "Proporción que va a caja",
  proporcionPrioritarios: "Proporción de clientes prioritarios",
  escenario: "Escenario (día normal o quincena)",
  numeroCorridas: "Número de corridas",
  alfa: "Nivel de significancia α",
  limiteIntentos: "Límite de intentos por corrida",
  semilla: "Semilla",
  compararConCiw: "Comparar con la librería Ciw",
};

export const SECCIONES_RESULTADOS = {
  veredicto: "Veredicto y metas",
  banco: "Banco animado en 3D",
  graficas: "Gráficas de la jornada",
  resumen: "Tabla de medidas",
  longitudes: "Tabla de longitudes",
  pruebaKS: "Prueba de Kolmogorov-Smirnov",
  poisson: "Ajuste de Poisson de los conteos",
  ciw: "Validación con Ciw",
  clientes: "Tabla cliente por cliente",
};

export const FUENTES = {
  sistema: { nombre: "Del sistema", familia: 'system-ui, -apple-system, "Segoe UI", sans-serif' },
  legible: { nombre: "Atkinson Hyperlegible", familia: '"Atkinson Hyperlegible", system-ui, sans-serif' },
  inter: { nombre: "Inter", familia: '"Inter", system-ui, sans-serif' },
  serif: { nombre: "Serif", familia: 'Georgia, "Times New Roman", serif' },
  monoespaciada: { nombre: "Monoespaciada", familia: 'ui-monospace, "SF Mono", Menlo, monospace' },
};

const todasVisibles = (catalogo) => Object.fromEntries(Object.keys(catalogo).map((clave) => [clave, true]));

const AJUSTES_INICIALES = {
  tema: "automatico",
  fuente: "sistema",
  tamanoLetra: 16,
  estiloLinea: "escalonada",
  mostrarCuadricula: true,
  animaciones: true,
  mostrarEtiquetas: false,
  metaEsperaMinutos: 10,
  utilizacionMinima: 60,
  utilizacionMaxima: 90,
  variablesVisibles: todasVisibles(VARIABLES_OPCIONALES),
  seccionesVisibles: todasVisibles(SECCIONES_RESULTADOS),
};

const CLAVE_GUARDADO = "ajustesSimuladorBanco";

function leerAjustesGuardados() {
  try {
    const guardados = JSON.parse(localStorage.getItem(CLAVE_GUARDADO) ?? "{}");
    return {
      ...structuredClone(AJUSTES_INICIALES),
      ...guardados,
      variablesVisibles: { ...AJUSTES_INICIALES.variablesVisibles, ...guardados.variablesVisibles },
      seccionesVisibles: { ...AJUSTES_INICIALES.seccionesVisibles, ...guardados.seccionesVisibles },
    };
  } catch {
    return structuredClone(AJUSTES_INICIALES);
  }
}

export const ajustes = reactive(leerAjustesGuardados());

export function restaurarAjustes() {
  Object.assign(ajustes, structuredClone(AJUSTES_INICIALES));
}

// Cambia cada vez que cambian los colores (tema o modo del sistema); las gráficas lo escuchan.
export const versionTema = ref(0);

function aplicarAjustes() {
  const raiz = document.documentElement;
  if (ajustes.tema === "claro") raiz.dataset.theme = "light";
  else if (ajustes.tema === "oscuro") raiz.dataset.theme = "dark";
  else delete raiz.dataset.theme;
  raiz.style.setProperty("--fuente", FUENTES[ajustes.fuente].familia);
  raiz.style.fontSize = `${ajustes.tamanoLetra}px`;
  versionTema.value++;
  try {
    localStorage.setItem(CLAVE_GUARDADO, JSON.stringify(ajustes));
  } catch {
    // Sin almacenamiento disponible: los ajustes duran solo esta sesión
  }
}

watch(ajustes, aplicarAjustes, { deep: true, immediate: true });
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => versionTema.value++);

// ---------- Variables de entrada ----------

export const simulacion = reactive({
  pasoActual: 1,
  entradaPorDefecto: null,
  entrada: null,
  escenario: "normal",
  factorQuincena: 1.3,
  resultado: null,
  cajasNecesarias: null,
  cargando: false,
  error: "",
});

export function jornadaParaFormulario(jornada) {
  return {
    inicio: jornada.inicio.slice(0, 5),
    fin: jornada.fin.slice(0, 5),
    conteosTexto: jornada.conteos.join(", "),
    minutosPorCliente: jornada.minutosPorCliente,
    servicioMinimo: jornada.servicioMinimo,
    servicioMaximo: jornada.servicioMaximo,
  };
}

export function cargarEntradaPorDefecto(entradaPorDefecto) {
  simulacion.entradaPorDefecto = entradaPorDefecto;
  simulacion.entrada = {
    ...structuredClone(entradaPorDefecto),
    jornadas: entradaPorDefecto.jornadas.map(jornadaParaFormulario),
  };
}

export function leerConteos(texto) {
  return texto.split(/[\s,;]+/).filter(Boolean).map(Number);
}

export function conteosValidos(texto) {
  const conteos = leerConteos(texto);
  return conteos.length >= 2 && conteos.every((conteo) => Number.isInteger(conteo) && conteo >= 0)
    && conteos.some((conteo) => conteo > 0);
}

/** Arma el JSON para la API. Las variables que no se piden toman su valor por defecto. */
export function entradaParaEnviar() {
  const { entrada, entradaPorDefecto } = simulacion;
  const valor = (nombre) => (ajustes.variablesVisibles[nombre] ? entrada[nombre] : entradaPorDefecto[nombre]);
  const esQuincena = ajustes.variablesVisibles.escenario && simulacion.escenario === "quincena";
  return {
    numeroServidores: entrada.numeroServidores,
    distribucionServicio: entrada.distribucionServicio,
    tiempoEntreTomasDeDatos: valor("tiempoEntreTomasDeDatos"),
    proporcionVanACaja: valor("proporcionVanACaja"),
    proporcionPrioritarios: valor("proporcionPrioritarios"),
    factorLlegadas: esQuincena ? simulacion.factorQuincena : 1,
    numeroCorridas: valor("numeroCorridas"),
    alfa: valor("alfa"),
    limiteIntentos: valor("limiteIntentos"),
    semilla: ajustes.variablesVisibles.semilla && entrada.semilla !== "" ? entrada.semilla : null,
    compararConCiw: valor("compararConCiw"),
    jornadas: entrada.jornadas.map((jornada) => ({
      inicio: jornada.inicio,
      fin: jornada.fin,
      conteos: leerConteos(jornada.conteosTexto),
      minutosPorCliente: jornada.minutosPorCliente,
      servicioMinimo: jornada.servicioMinimo,
      servicioMaximo: jornada.servicioMaximo,
    })),
  };
}
