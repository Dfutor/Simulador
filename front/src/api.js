function explicarError(detalle) {
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle)) {
    return detalle
      .map((problema) => {
        const ubicacion = problema.loc
          .slice(1)
          .map((parte) => (typeof parte === "number" ? `n.º ${parte + 1}` : parte))
          .join(" › ");
        const mensaje = problema.msg.replace(/^Value error, /, "");
        return ubicacion ? `${ubicacion}: ${mensaje}` : mensaje;
      })
      .join(" · ");
  }
  return "Error desconocido";
}

async function pedir(ruta, cuerpo, metodo = "POST") {
  let respuesta;
  try {
    respuesta = await fetch(ruta, cuerpo === undefined ? {} : {
      method: metodo,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
  } catch {
    throw new Error("No hay conexión con la API. Inicia el proyecto con: docker compose up -d");
  }
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(explicarError(datos.detail));
  return datos;
}

export const pedirEntradaPorDefecto = () => pedir("/api/entrada-por-defecto");
export const pedirSimulacion = (entrada) => pedir("/api/simular", entrada);
export const pedirCajasNecesarias = (entrada, metaEsperaMinutos) =>
  pedir("/api/cajas-necesarias", { entrada, metaEsperaMinutos });
export const pedirAjustePoisson = (conteos, alfa) => pedir("/api/poisson", { conteos, alfa });
export const pedirAnalisisLlegadas = (entrada, minutosPorFranja, ventana) =>
  pedir("/api/analisis-llegadas", { entrada, minutosPorFranja, ventana });

// Establecimiento, calendario y «Planifica tu visita»
export const pedirEstablecimiento = () => pedir("/api/establecimiento");
export const guardarEstablecimiento = (configuracion) => pedir("/api/establecimiento", configuracion, "PUT");
export const pedirCalendario = (anio, mes) => pedir(`/api/calendario/${anio}/${mes}`);
export const pedirVisita = (fecha) => pedir(`/api/visita/${fecha}`);
export const pedirComparacionDias = (fechaA, fechaB, categoria) =>
  pedir(`/api/comparar-dias?${new URLSearchParams({ fechaA, fechaB, categoria })}`);
