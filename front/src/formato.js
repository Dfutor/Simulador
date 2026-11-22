export function formatearNumero(valor, decimales = 2) {
  if (valor == null || Number.isNaN(valor)) return "—";
  return valor.toLocaleString("es-CO", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

export function formatearPorcentaje(valor, decimales = 1) {
  if (valor == null) return "—";
  return `${formatearNumero(valor * 100, decimales)} %`;
}

export function formatearMedida(valor, medida) {
  return medida.unidad === "%" ? formatearPorcentaje(valor) : formatearNumero(valor, medida.decimales);
}

/** "08:00" + 95.4 minutos → "09:35" */
export function horaReloj(inicio, minutosDesdeApertura) {
  const [horas, minutos] = inicio.split(":").map(Number);
  const total = horas * 60 + minutos + Math.round(minutosDesdeApertura);
  // Con mucha sobrecarga la atención pasa de la medianoche: 25:10 se muestra como 01:10 (+1 d)
  const dias = Math.floor(total / 1440);
  const enElDia = total - dias * 1440;
  const hora = `${String(Math.floor(enElDia / 60)).padStart(2, "0")}:${String(enElDia % 60).padStart(2, "0")}`;
  return dias > 0 ? `${hora} (+${dias} d)` : hora;
}

/** 59.4 → "59 min";  125 → "2 h 5 min" (para el cliente) */
export function formatearDuracion(minutos) {
  if (minutos == null) return "—";
  const total = Math.round(minutos);
  if (total < 60) return `${total} min`;
  const horas = Math.floor(total / 60);
  const resto = total % 60;
  return resto ? `${horas} h ${resto} min` : `${horas} h`;
}

const FORMATOS_FECHA = {
  larga: new Intl.DateTimeFormat("es-CO", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }),
  diaMes: new Intl.DateTimeFormat("es-CO", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }),
  corta: new Intl.DateTimeFormat("es-CO", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }),
  mes: new Intl.DateTimeFormat("es-CO", { month: "long", year: "numeric", timeZone: "UTC" }),
};

/** "2026-12-07" → "Lunes, 7 de diciembre de 2026". La fecha es de calendario: se formatea sin zona horaria. */
export function formatearFecha(iso, formato = "larga") {
  const texto = FORMATOS_FECHA[formato].format(new Date(`${iso}T12:00:00Z`));
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Categoría de una franja según las llegadas observadas */
export const CATEGORIAS = {
  valle: { nombre: "Valle", cliente: "Afluencia baja" },
  normal: { nombre: "Normal", cliente: "Afluencia habitual" },
  pico: { nombre: "Pico", cliente: "Afluencia alta" },
  sinDatos: { nombre: "Sin datos", cliente: "Afluencia sin medir" },
};

export const MEDIDAS = {
  Wq: { nombre: "Espera promedio en la fila (Wq)", descripcion: "Minutos que un cliente pasa haciendo fila", decimales: 2, unidad: "min" },
  W: { nombre: "Tiempo promedio en el banco (W)", descripcion: "Fila más atención en caja", decimales: 2, unidad: "min" },
  Lq: { nombre: "Personas promedio en la fila (Lq)", descripcion: "Cuántos hacen fila en un momento cualquiera", decimales: 2, unidad: "personas" },
  L: { nombre: "Personas promedio en el banco (L)", descripcion: "Fila más los que están en caja", decimales: 2, unidad: "personas" },
  utilizacion: { nombre: "Ocupación de las cajas", descripcion: "Parte del tiempo en que las cajas atienden", decimales: 1, unidad: "%" },
  WqPrioritarios: { nombre: "Espera de los prioritarios", descripcion: "Embarazadas y adultos mayores", decimales: 2, unidad: "min" },
  WqNormales: { nombre: "Espera de los demás clientes", descripcion: "Clientes sin prioridad", decimales: 2, unidad: "min" },
  esperaMaxima: { nombre: "Espera más larga", descripcion: "El cliente que más esperó ese día", decimales: 2, unidad: "min" },
  personasAlLlegar: { nombre: "Personas en el banco al llegar", descripcion: "Lo que ve un cliente cuando entra", decimales: 2, unidad: "personas" },
  clientesAtendidos: { nombre: "Clientes atendidos", descripcion: "Por jornada", decimales: 1, unidad: "clientes" },
  clientesPrioritarios: { nombre: "Clientes prioritarios", descripcion: "Por jornada", decimales: 1, unidad: "clientes" },
  longitudMaximaSistema: { nombre: "Máximo de personas en el banco", descripcion: "El momento más lleno", decimales: 1, unidad: "personas" },
  longitudMaximaCola: { nombre: "Fila más larga", descripcion: "El momento con más gente esperando", decimales: 1, unidad: "personas" },
  tiempoTotalCola: { nombre: "Minutos de fila sumados", descripcion: "La espera de todos los clientes junta", decimales: 1, unidad: "min" },
  ocioTotal: { nombre: "Minutos sin atender, todas las cajas", descripcion: "Incluye el rato vacío al final", decimales: 1, unidad: "min" },
};
