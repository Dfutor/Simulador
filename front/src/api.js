function explicarError(detalle) {
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle)) {
    return detalle
      .map((problema) => {
        const ubicacion = problema.loc
          .slice(1)
          .map((parte) => (typeof parte === "number" ? `jornada ${parte + 1}` : parte))
          .join(" › ");
        return ubicacion ? `${ubicacion}: ${problema.msg}` : problema.msg;
      })
      .join(" · ");
  }
  return "Error desconocido";
}

async function pedir(ruta, cuerpo) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, cuerpo === undefined ? {} : {
      method: "POST",
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
