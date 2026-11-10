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
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

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
