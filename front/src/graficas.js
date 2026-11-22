import { computed } from "vue";
import { ajustes, versionTema } from "./estado.js";
import { formatearNumero, formatearPorcentaje, horaReloj } from "./formato.js";

// Paleta categórica validada (orden fijo, nunca se recicla). Una columna por modo.
const PALETA_CLARA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const PALETA_OSCURA = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];

function leerColores() {
  const estilo = getComputedStyle(document.documentElement);
  const variable = (nombre) => estilo.getPropertyValue(nombre).trim();
  const esOscuro = estilo.colorScheme === "dark";
  return {
    series: esOscuro ? PALETA_OSCURA : PALETA_CLARA,
    texto: variable("--texto"),
    textoSecundario: variable("--textoSecundario"),
    textoTenue: variable("--textoTenue"),
    borde: variable("--borde"),
    bordeFuerte: variable("--bordeFuerte"),
    superficie: variable("--superficie"),
    estadoCritico: variable("--estadoCritico"),
    estadoBueno: variable("--estadoBueno"),
    fuente: variable("--fuente"),
  };
}

/** Colores del tema activo; se recalculan cuando cambia el tema. */
export function usarColores() {
  return computed(() => {
    versionTema.value;
    return leerColores();
  });
}

function base(colores, conLeyenda = true) {
  return {
    animation: ajustes.animaciones,
    color: colores.series,
    textStyle: { fontFamily: colores.fuente, color: colores.textoSecundario },
    grid: { left: 64, right: 24, top: conLeyenda ? 44 : 20, bottom: 56 },
    legend: conLeyenda
      ? { top: 0, left: 0, icon: "roundRect", itemWidth: 14, itemHeight: 8, textStyle: { color: colores.textoSecundario } }
      : undefined,
    tooltip: {
      backgroundColor: colores.superficie,
      borderColor: colores.borde,
      textStyle: { color: colores.texto, fontFamily: colores.fuente },
    },
  };
}

function eje(colores, nombre, opciones = {}) {
  return {
    type: "value",
    name: nombre,
    nameLocation: "middle",
    nameGap: opciones.distanciaNombre ?? 40,
    nameTextStyle: { color: colores.textoSecundario },
    axisLine: { show: true, lineStyle: { color: colores.bordeFuerte } },
    axisTick: { show: false },
    axisLabel: { color: colores.textoTenue, hideOverlap: true },
    splitLine: { show: ajustes.mostrarCuadricula, lineStyle: { color: colores.borde } },
    ...opciones.extra,
  };
}

function estiloDeLinea() {
  if (ajustes.estiloLinea === "escalonada") return { step: "end" };
  if (ajustes.estiloLinea === "suave") return { smooth: 0.3 };
  return {};
}

const linea = (nombre, datos, color, extra = {}) => ({
  name: nombre,
  type: "line",
  data: datos,
  showSymbol: false,
  lineStyle: { width: 2, color },
  itemStyle: { color },
  emphasis: { focus: "series" },
  ...extra,
});

const barras = (nombre, datos, color) => ({
  name: nombre,
  type: "bar",
  data: datos,
  barMaxWidth: 28,
  itemStyle: { color, borderRadius: [4, 4, 0, 0] },
  label: { show: ajustes.mostrarEtiquetas, position: "top", color: "inherit" },
});

// ---------- Jornada ----------

export function opcionFilaEnElTiempo(serie, inicio, colores) {
  const aHora = (minuto) => horaReloj(inicio, minuto);
  return {
    ...base(colores),
    tooltip: {
      ...base(colores).tooltip,
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: colores.bordeFuerte } },
      formatter: (puntos) =>
        `<b>${aHora(puntos[0].value[0])}</b><br>` +
        puntos.map((punto) => `${punto.marker} ${punto.seriesName}: <b>${punto.value[1]}</b>`).join("<br>"),
    },
    xAxis: eje(colores, "Hora", { distanciaNombre: 32, extra: { axisLabel: { color: colores.textoTenue, formatter: aHora } } }),
    yAxis: eje(colores, "Personas"),
    series: [
      linea("En el banco", serie.map(([minuto, enSistema]) => [minuto, enSistema]), colores.series[0], estiloDeLinea()),
      linea("En la fila", serie.map(([minuto, , enCola]) => [minuto, enCola]), colores.series[1], estiloDeLinea()),
    ],
  };
}

export function opcionLongitudes(probabilidadSistema, probabilidadCola, colores) {
  const mayor = Math.max(...Object.keys(probabilidadSistema).map(Number));
  const personas = Array.from({ length: mayor + 1 }, (_, posicion) => posicion);
  return {
    ...base(colores),
    tooltip: {
      ...base(colores).tooltip,
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: colores.bordeFuerte } },
      valueFormatter: (valor) => formatearPorcentaje(valor, 2),
    },
    xAxis: { ...eje(colores, "Personas (n)", { distanciaNombre: 32 }), type: "category", boundaryGap: false, data: personas },
    yAxis: eje(colores, "Fracción del tiempo", { distanciaNombre: 48, extra: { axisLabel: { color: colores.textoTenue, formatter: (valor) => formatearPorcentaje(valor, 0) } } }),
    series: [
      linea("En el banco", personas.map((cantidad) => probabilidadSistema[cantidad] ?? 0), colores.series[0],
        { step: "middle", areaStyle: { opacity: 0.15 } }),
      linea("En la fila", personas.map((cantidad) => probabilidadCola[cantidad] ?? 0), colores.series[1],
        { step: "middle", areaStyle: { opacity: 0.15 } }),
    ],
  };
}

export function opcionEsperaPorCorrida(medidasPorCorrida, resumenWq, colores) {
  const meta = ajustes.metaEsperaMinutos;
  const opciones = base(colores, false);
  return {
    ...opciones,
    // Las etiquetas de las líneas van a la derecha, fuera de las barras, para que no se tapen
    grid: { ...opciones.grid, right: 84 },
    tooltip: { ...opciones.tooltip, trigger: "item", formatter: (punto) => `Corrida ${punto.name}: <b>${formatearNumero(punto.value)} min</b>` },
    xAxis: { ...eje(colores, "Corrida", { distanciaNombre: 32 }), type: "category", data: medidasPorCorrida.map((_, posicion) => posicion + 1) },
    yAxis: eje(colores, "Espera en la fila (min)"),
    series: [{
      ...barras("Espera promedio", medidasPorCorrida.map((medidas) => medidas.Wq), colores.series[0]),
      markArea: {
        silent: true,
        itemStyle: { color: colores.series[0], opacity: 0.12 },
        label: { show: false },   // el subtítulo de la gráfica explica la franja
        data: [[{ yAxis: resumenWq.limiteInferior }, { yAxis: resumenWq.limiteSuperior }]],
      },
      markLine: {
        silent: true,
        symbol: "none",
        data: [
          { yAxis: resumenWq.promedio, name: "Promedio", lineStyle: { color: colores.texto, width: 1.5 } },
          { yAxis: meta, name: "Meta", lineStyle: { color: colores.textoSecundario, type: "dashed" } },
        ],
        label: {
          position: "end", distance: 6, color: colores.textoSecundario, lineHeight: 15,
          formatter: (punto) => `${punto.name}\n${formatearNumero(punto.value, 1)}`,
        },
      },
    }],
  };
}

export function opcionOcupacionPorCaja(utilizacionPorServidor, colores) {
  return {
    ...base(colores, false),
    tooltip: { ...base(colores).tooltip, trigger: "item", formatter: (punto) => `Caja ${punto.name}: <b>${formatearPorcentaje(punto.value)}</b>` },
    xAxis: { ...eje(colores, "Caja", { distanciaNombre: 32 }), type: "category", data: utilizacionPorServidor.map((_, posicion) => posicion + 1) },
    yAxis: eje(colores, "Tiempo ocupada", { distanciaNombre: 48, extra: { max: 1, axisLabel: { color: colores.textoTenue, formatter: (valor) => formatearPorcentaje(valor, 0) } } }),
    series: [{
      ...barras("Ocupación", utilizacionPorServidor.map((intervalo) => intervalo.promedio), colores.series[0]),
      markArea: {
        silent: true,
        itemStyle: { color: colores.estadoBueno, opacity: 0.1 },
        label: { show: false },   // las barras la tapaban; el subtítulo dice que la franja verde es el rango meta
        data: [[{ yAxis: ajustes.utilizacionMinima / 100 }, { yAxis: ajustes.utilizacionMaxima / 100 }]],
      },
    }],
  };
}

// ---------- Pruebas estadísticas ----------

function acumuladaObservada(numeros) {
  const ordenados = [...numeros].sort((primero, segundo) => primero - segundo);
  return [[0, 0], ...ordenados.map((numero, posicion) => [numero, (posicion + 1) / ordenados.length]), [1, 1]];
}

export function opcionAcumuladaKS(aleatoriosLlegada, aleatoriosServicio, critico, colores) {
  // Guías de la prueba: F₀(x) ± crítico, recortadas a [0, 1]. Son paralelas a la diagonal (pendiente 1).
  const c = Math.min(critico, 1);
  const bandaSuperior = [[0, c], [1 - c, 1], [1, 1]];
  const bandaInferior = [[0, 0], [c, 0], [1, 1 - c]];
  const lineaBanda = (nombre, puntos) => linea(nombre, puntos, colores.textoTenue, {
    lineStyle: { width: 1, type: "dashed", color: colores.textoTenue }, tooltip: { show: false }, emphasis: { disabled: true },
  });
  return {
    ...base(colores),
    tooltip: { ...base(colores).tooltip, trigger: "axis", valueFormatter: (valor) => formatearNumero(valor, 3) },
    xAxis: eje(colores, "Número aleatorio R", { distanciaNombre: 32, extra: { min: 0, max: 1 } }),
    yAxis: eje(colores, "Acumulada", { extra: { min: 0, max: 1 } }),
    series: [
      linea("R de llegadas", acumuladaObservada(aleatoriosLlegada), colores.series[0], { step: "end" }),
      linea("R de servicios", acumuladaObservada(aleatoriosServicio), colores.series[1], { step: "end" }),
      linea("Uniforme U(0, 1)", [[0, 0], [1, 1]], colores.texto, { lineStyle: { width: 1.5, color: colores.texto } }),
      lineaBanda("Límite superior (± valor crítico)", bandaSuperior),
      lineaBanda("Límite inferior", bandaInferior),
    ],
    legend: { ...base(colores).legend, data: ["R de llegadas", "R de servicios", "Uniforme U(0, 1)", "Límite superior (± valor crítico)"] },
  };
}

export function opcionDPorCorrida(aceptadas, rechazos, colores) {
  const razon = (prueba) => prueba.D / prueba.critico;
  const puntos = (lista, nombre) => lista.map((corrida) => [corrida.corrida, razon(corrida[nombre])]);
  const dispersion = (nombre, datos, color, simbolo = "circle") => ({
    name: nombre, type: "scatter", data: datos, symbol: simbolo, symbolSize: 9,
    itemStyle: { color, borderColor: colores.superficie, borderWidth: 2 },
  });
  return {
    ...base(colores),
    tooltip: {
      ...base(colores).tooltip,
      trigger: "item",
      formatter: (punto) => `Corrida ${punto.value[0]} · ${punto.seriesName}<br>D ÷ crítico = <b>${formatearNumero(punto.value[1], 3)}</b>`,
    },
    xAxis: eje(colores, "Corrida", { distanciaNombre: 32, extra: { minInterval: 1 } }),
    yAxis: eje(colores, "D ÷ valor crítico", { extra: { min: 0 } }),
    series: [
      {
        ...dispersion("R de llegadas", puntos(aceptadas, "llegada"), colores.series[0]),
        markLine: {
          silent: true, symbol: "none",
          lineStyle: { color: colores.texto, type: "dashed" },
          label: {
            formatter: "Límite: por encima se rechaza", color: colores.textoSecundario, position: "insideEndTop",
            backgroundColor: colores.superficie, padding: [2, 6], borderRadius: 4,
          },
          data: [{ yAxis: 1 }],
        },
      },
      dispersion("R de servicios", puntos(aceptadas, "servicio"), colores.series[1]),
      dispersion("Intentos descartados", rechazos.map((rechazo) => [rechazo.corrida, Math.max(razon(rechazo.llegada), razon(rechazo.servicio))]),
        colores.estadoCritico, "triangle"),
    ],
  };
}

export function nombreClase(clase) {
  if (clase.hasta === null) return `${clase.desde} o más`;
  return clase.desde === clase.hasta ? `${clase.desde}` : `${clase.desde} a ${clase.hasta}`;
}

export function opcionPoisson(clases, colores) {
  return {
    ...base(colores),
    tooltip: { ...base(colores).tooltip, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (valor) => formatearNumero(valor, 2) },
    xAxis: { ...eje(colores, "Personas por intervalo", { distanciaNombre: 32 }), type: "category", data: clases.map(nombreClase) },
    yAxis: eje(colores, "Intervalos", { extra: { minInterval: 1 } }),
    series: [
      barras("Observados", clases.map((clase) => clase.observadas), colores.series[0]),
      barras("Esperados si fuera Poisson", clases.map((clase) => clase.esperadas), colores.series[1]),
    ],
  };
}

// ---------- Llegadas: promedios móviles y comparación de días ----------

/** Color fijo de cada categoría: valle, normal y pico nunca cambian de color entre gráficas. */
export function colorCategoria(categoria, colores) {
  return { valle: colores.series[2], normal: colores.series[0], pico: colores.series[7], sinDatos: colores.textoTenue }[categoria];
}

export function opcionPromediosMoviles(intervalos, ventana, colores) {
  const horas = intervalos.map((intervalo) => intervalo.desde);
  // Una serie de barras por categoría, apiladas: cada conteo queda en su hora con el color de su franja
  const barrasDe = (categoria, nombre) => ({
    ...barras(nombre, intervalos.map((intervalo) => (intervalo.categoria === categoria ? intervalo.conteo : null)),
      colorCategoria(categoria, colores)),
    stack: "conteo",
    barMaxWidth: 16,
    itemStyle: { color: colorCategoria(categoria, colores), opacity: 0.55, borderRadius: [3, 3, 0, 0] },
  });
  const presentes = ["valle", "normal", "pico"].filter((categoria) => intervalos.some((intervalo) => intervalo.categoria === categoria));
  return {
    ...base(colores),
    tooltip: { ...base(colores).tooltip, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (valor) => formatearNumero(valor, 2) },
    xAxis: { ...eje(colores, "Inicio del intervalo", { distanciaNombre: 32 }), type: "category", data: horas },
    yAxis: eje(colores, "Personas por intervalo", { extra: { minInterval: 1 } }),
    series: [
      ...presentes.map((categoria) => barrasDe(categoria, `Observado · ${{ valle: "valle", normal: "normal", pico: "pico" }[categoria]}`)),
      linea(`Promedio móvil simple (${ventana})`, intervalos.map((intervalo) => intervalo.promedioSimple), colores.texto,
        { connectNulls: false, lineStyle: { width: 2, color: colores.texto } }),
      linea(`Promedio móvil ponderado (${ventana})`, intervalos.map((intervalo) => intervalo.promedioPonderado), colores.series[1],
        { connectNulls: false, lineStyle: { width: 2, type: "dashed", color: colores.series[1] } }),
    ],
  };
}

export function opcionComparacionDias(comparacion, colores) {
  const nombre = (serie) => `Simulado · ${serie.etiqueta}`;
  const series = comparacion.series.filter((serie) => serie.n > 0)
    .map((serie, posicion) => barras(nombre(serie), serie.relativas, colores.series[posicion === 0 ? 0 : 1]));
  if (comparacion.observado) {
    series.push(linea("Observado · día de conteo", comparacion.observado.relativas, colores.texto, {
      showSymbol: true, symbol: "diamond", symbolSize: 9, lineStyle: { width: 1, type: "dotted", color: colores.texto },
    }));
  }
  return {
    ...base(colores),
    tooltip: { ...base(colores).tooltip, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (valor) => formatearPorcentaje(valor, 1) },
    xAxis: { ...eje(colores, `Personas que llegan en ${formatearNumero(comparacion.minutosIntervalo, 0)} min`, { distanciaNombre: 32 }),
      type: "category", data: comparacion.clases },
    yAxis: eje(colores, "Frecuencia relativa", { distanciaNombre: 48, extra: { axisLabel: { color: colores.textoTenue, formatter: (valor) => formatearPorcentaje(valor, 0) } } }),
    series,
  };
}

// ---------- Cajas necesarias ----------

export function opcionCurvaCajas(curva, jornadas, campo, colores) {
  const esOcupacion = campo === "utilizacion";
  const formatear = (valor) => (esOcupacion ? formatearPorcentaje(valor) : `${formatearNumero(valor)} min`);
  const lineaDeJornada = (jornada, posicion) => linea(
    `Jornada ${jornada.numero}`,
    curva.map((punto) => [punto.cajas, punto.jornadas[posicion][campo]]),
    colores.series[posicion % colores.series.length],
    { showSymbol: true, symbolSize: 8, itemStyle: { color: colores.series[posicion], borderColor: colores.superficie, borderWidth: 2 } },
  );
  const series = jornadas.map(lineaDeJornada);
  series[0].markLine = {
    silent: true, symbol: "none",
    lineStyle: { color: colores.textoSecundario, type: "dashed" },
    label: { formatter: (punto) => `Meta ${formatear(punto.value)}`, color: colores.textoSecundario, position: "insideEndTop" },
    data: esOcupacion
      ? [{ yAxis: ajustes.utilizacionMinima / 100 }, { yAxis: ajustes.utilizacionMaxima / 100 }]
      : [{ yAxis: ajustes.metaEsperaMinutos }],
  };
  return {
    ...base(colores),
    tooltip: { ...base(colores).tooltip, trigger: "axis", valueFormatter: formatear },
    xAxis: eje(colores, "Número de cajas", { distanciaNombre: 32, extra: { minInterval: 1 } }),
    yAxis: eje(colores, esOcupacion ? "Ocupación de las cajas" : "Espera en la fila (min)", {
      distanciaNombre: 52,
      extra: esOcupacion ? { max: 1, axisLabel: { color: colores.textoTenue, formatter: (valor) => formatearPorcentaje(valor, 0) } } : {},
    }),
    series,
  };
}
