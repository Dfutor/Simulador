"""API JSON del simulador (FastAPI). Documentación interactiva en /docs.

Uso:  .venv/bin/python simulador2/api.py   →   http://localhost:8000
"""

import threading
from datetime import date, time
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

import planificacion
from analisisLlegadas import analizarLlegadas
from calendario import diasDelMes, hoy, revisarJornadas
from iniciador import JornadaSinClientes, UniformidadRechazada, buscarCajasNecesarias, simular
from pruebaPoisson import pruebaChiCuadradaPoisson

CARPETA_FRONT_COMPILADO = Path(__file__).resolve().parent.parent / "front" / "dist"

# Conteos observados desde afuera del banco (documento, sección 1.3)
CONTEOS_MANANA = [7, 9, 8, 6, 4, 7, 5, 11, 8, 2, 4, 6, 3, 1, 3, 9, 6, 4, 8, 7, 2, 3, 4, 3]
CONTEOS_TARDE = [3, 3, 2, 3, 3, 7, 9, 4, 7, 6, 4, 4, 6, 3, 7, 4, 8, 5, 3, 5, 9, 3, 7, 6, 4, 2, 3, 3, 2, 0]


class Jornada(BaseModel):
    inicio: time
    fin: time
    conteos: list[int] = Field(min_length=2, description="Personas que entraron en cada intervalo")
    inicioConteos: time | None = Field(None, description="Hora del primer conteo (vacío = cuando abre la jornada). "
                                                         "Ubica cada conteo en el reloj para los promedios móviles y las franjas")
    minutosPorCliente: float = Field(13.5, gt=0, description="Media del servicio si es exponencial")
    servicioMinimo: float = Field(1, ge=0, description="Mínimo del servicio si es uniforme")
    servicioMaximo: float = Field(25, gt=0, description="Máximo del servicio si es uniforme")

    @model_validator(mode="after")
    def revisarJornada(self):
        if self.fin <= self.inicio:
            raise ValueError("La jornada debe terminar después de empezar")
        if any(conteo < 0 for conteo in self.conteos) or sum(self.conteos) == 0:
            raise ValueError("Los conteos no pueden ser negativos y debe haber al menos una llegada")
        if self.servicioMaximo <= self.servicioMinimo:
            raise ValueError("El servicio máximo debe ser mayor que el mínimo")
        if self.inicioConteos is not None and not self.inicio <= self.inicioConteos < self.fin:
            raise ValueError("El primer conteo debe caer dentro de la jornada")
        return self


class Entrada(BaseModel):
    numeroServidores: int = Field(5, ge=1, le=100)
    distribucionServicio: Literal["uniforme", "exponencial"] = "uniforme"
    tiempoEntreTomasDeDatos: float = Field(5, gt=0)
    proporcionVanACaja: float = Field(1, gt=0, le=1)
    proporcionPrioritarios: float = Field(0.05, ge=0, le=1)
    factorLlegadas: float = Field(1, gt=0, description="1 = día normal, 1.3 = quincena")
    numeroCorridas: int = Field(30, ge=2, le=500)
    alfa: float = Field(0.05, gt=0, lt=1, description="Nivel de significancia de las pruebas")
    limiteIntentos: int = Field(10, ge=1, le=100)
    semilla: int | None = None
    compararConCiw: bool = False
    jornadas: list[Jornada] = Field(min_length=1, default_factory=lambda: [
        # La mañana se contó de 9:40 a 11:40 (documento, sección 1.3)
        Jornada(inicio=time(8, 0), fin=time(12, 0), conteos=CONTEOS_MANANA, minutosPorCliente=13.5,
                inicioConteos=time(9, 40)),
        Jornada(inicio=time(14, 0), fin=time(16, 30), conteos=CONTEOS_TARDE, minutosPorCliente=14,
                inicioConteos=time(14, 0)),
    ])


# ---------- Establecimiento: días y horarios de atención ----------

class Tramo(BaseModel):
    inicio: time
    fin: time


def revisarHorario(abierto: bool, jornadas: list[Tramo]) -> None:
    revisarJornadas([jornada.model_dump() for jornada in jornadas])
    if abierto and not jornadas:
        raise ValueError("Un día abierto necesita al menos una jornada")


class DiaSemana(BaseModel):
    abierto: bool = False
    jornadas: list[Tramo] = Field(default_factory=list, description="Se conservan aunque el día esté cerrado")

    @model_validator(mode="after")
    def revisarDia(self):
        revisarHorario(self.abierto, self.jornadas)
        return self


class Excepcion(BaseModel):
    fecha: date
    motivo: str = Field("", max_length=80, description="Festivo, cierre administrativo, apertura extraordinaria…")
    abierto: bool = Field(False, description="False = cerrado ese día; True = abre con las jornadas indicadas")
    jornadas: list[Tramo] = Field(default_factory=list)

    @model_validator(mode="after")
    def revisarExcepcion(self):
        revisarHorario(self.abierto, self.jornadas)
        return self


def horarioSemanalPorDefecto() -> list[DiaSemana]:
    habitual = [Tramo(inicio=time(8, 0), fin=time(12, 0)), Tramo(inicio=time(14, 0), fin=time(16, 30))]
    semana = [DiaSemana(abierto=True, jornadas=habitual) for _ in range(5)]
    return semana + [DiaSemana(abierto=False, jornadas=[Tramo(inicio=time(8, 0), fin=time(12, 0))]), DiaSemana()]


class Establecimiento(BaseModel):
    zonaHoraria: str = "America/Bogota"
    horarioSemanal: list[DiaSemana] = Field(min_length=7, max_length=7, default_factory=horarioSemanalPorDefecto,
                                            description="De lunes a domingo")
    excepciones: list[Excepcion] = Field(default_factory=list, description="Tienen prioridad sobre el horario semanal")
    factorQuincena: float = Field(1.3, ge=1, le=3, description="SUPUESTO: no se observó ningún día de quincena")
    minutosPorFranja: int = Field(60, ge=5, le=240, description="Largo de las franjas horarias de análisis")
    modeloLlegadas: Literal["jornada", "franja"] = Field(
        "jornada", description="jornada = una tasa por jornada (modelo original); "
                               "franja = la tasa de cada franja si la prueba de homogeneidad la distingue")
    entrada: Entrada = Field(default_factory=Entrada, description="Parámetros de la simulación")

    @model_validator(mode="after")
    def revisarEstablecimiento(self):
        try:
            ZoneInfo(self.zonaHoraria)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"Zona horaria desconocida: {self.zonaHoraria}. Usa un nombre como America/Bogota")
        fechas = [excepcion.fecha for excepcion in self.excepciones]
        if len(fechas) != len(set(fechas)):
            raise ValueError("Hay dos excepciones para la misma fecha")
        if not any(dia.abierto for dia in self.horarioSemanal):
            raise ValueError("El establecimiento debe atender al menos un día de la semana")
        intervalo = self.entrada.tiempoEntreTomasDeDatos
        if abs(self.minutosPorFranja / intervalo - round(self.minutosPorFranja / intervalo)) > 1e-9:
            raise ValueError(f"Las franjas ({self.minutosPorFranja} min) deben ser un múltiplo del intervalo "
                             f"de conteo ({intervalo:g} min) para no partir un conteo en dos")
        return self


class PedidoAnalisis(BaseModel):
    entrada: Entrada
    minutosPorFranja: int = Field(60, ge=5, le=240)
    ventana: int = Field(3, ge=2, le=24, description="Observaciones de cada promedio móvil")


class PedidoCajas(BaseModel):
    entrada: Entrada
    metaEsperaMinutos: float = Field(gt=0)


class PedidoPoisson(BaseModel):
    conteos: list[int] = Field(min_length=2)
    alfa: float = Field(0.05, gt=0, lt=1)


app = FastAPI(title="Simulador de la fila del banco")

# El simulador usa el generador `random` y la lista global `corridasAceptadas`:
# se simula una petición a la vez para que dos usuarios no mezclen sus resultados.
candadoSimulacion = threading.Lock()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/entrada-por-defecto")
def entradaPorDefecto() -> dict:
    return Entrada().model_dump(mode="json")


@app.post("/api/simular")
def simularBanco(entrada: Entrada) -> dict:
    try:
        with candadoSimulacion:
            return simular(entrada.model_dump(mode="json"))
    except UniformidadRechazada as error:
        raise HTTPException(status_code=409, detail=str(error))
    except JornadaSinClientes as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/cajas-necesarias")
def cajasNecesarias(pedido: PedidoCajas) -> dict:
    try:
        with candadoSimulacion:
            return buscarCajasNecesarias(pedido.entrada.model_dump(mode="json"), pedido.metaEsperaMinutos)
    except UniformidadRechazada as error:
        raise HTTPException(status_code=409, detail=str(error))
    except JornadaSinClientes as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/poisson")
def ajustePoisson(pedido: PedidoPoisson) -> dict:
    # La misma regla que en Jornada: un conteo negativo no es una cantidad de personas
    if any(conteo < 0 for conteo in pedido.conteos) or sum(pedido.conteos) == 0:
        raise HTTPException(status_code=422, detail="Los conteos no pueden ser negativos y debe haber al menos una llegada")
    return pruebaChiCuadradaPoisson(pedido.conteos, pedido.alfa)


@app.post("/api/analisis-llegadas")
def analisisLlegadas(pedido: PedidoAnalisis) -> dict:
    """Promedios móviles (simple y ponderado) y categoría de cada franja, por jornada observada."""
    try:
        return analizarLlegadas(pedido.entrada.model_dump(mode="json"), pedido.minutosPorFranja, pedido.ventana)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# ---------- Establecimiento, calendario y «Planifica tu visita» ----------

def configuracionActual() -> dict:
    """La configuración guardada (revalidada, por si el formato cambió) o la de por defecto."""
    guardada = planificacion.cargarConfiguracion()
    modelo = Establecimiento.model_validate(guardada) if guardada is not None else Establecimiento()
    return modelo.model_dump(mode="json")


def publicarYGuardar(configuracion: dict) -> dict:
    try:
        with candadoSimulacion:
            estimaciones = planificacion.publicar(configuracion)
            planificacion.guardar(configuracion, estimaciones)
            return estimaciones
    except UniformidadRechazada as error:
        raise HTTPException(status_code=409, detail=str(error))
    except (JornadaSinClientes, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error))


def estimacionesVigentes(configuracion: dict) -> dict:
    """Las estimaciones publicadas para esta configuración; si no existen o quedaron viejas, se publican ahora."""
    estimaciones = planificacion.cargarEstimaciones()
    if estimaciones is None or estimaciones["huella"] != planificacion.huellaDe(configuracion):
        estimaciones = publicarYGuardar(configuracion)
    return estimaciones


def estadoEstablecimiento(configuracion: dict, guardada: bool) -> dict:
    return {
        "configuracion": configuracion,
        "guardada": guardada,
        "hoy": hoy(configuracion).isoformat(),
        "publicacion": planificacion.resumenPublicacion(planificacion.cargarEstimaciones(), configuracion),
    }


@app.get("/api/establecimiento")
def leerEstablecimiento() -> dict:
    return estadoEstablecimiento(configuracionActual(), planificacion.cargarConfiguracion() is not None)


@app.put("/api/establecimiento")
def guardarEstablecimiento(establecimiento: Establecimiento) -> dict:
    """Guarda la configuración y publica las estimaciones de todos sus escenarios."""
    configuracion = establecimiento.model_dump(mode="json")
    publicarYGuardar(configuracion)
    return estadoEstablecimiento(configuracion, True)


@app.get("/api/calendario/{anio}/{mes}")
def calendarioDelMes(anio: int, mes: int) -> dict:
    if not 1 <= mes <= 12 or not 1900 <= anio <= 2999:
        raise HTTPException(status_code=422, detail="Mes o año fuera de rango")
    configuracion = configuracionActual()
    return {"anio": anio, "mes": mes, "hoy": hoy(configuracion).isoformat(), "dias": diasDelMes(configuracion, anio, mes)}


@app.get("/api/visita/{fecha}")
def visitaEnFecha(fecha: date) -> dict:
    """Horario, tipo de día y espera estimada en la fila por franja (o la próxima fecha abierta)."""
    configuracion = configuracionActual()
    return planificacion.consultarFecha(configuracion, estimacionesVigentes(configuracion), fecha)


@app.get("/api/comparar-dias")
def compararDias(fechaA: date, fechaB: date,
                 categoria: Literal["todas", "valle", "normal", "pico", "sinDatos"] = "todas") -> dict:
    if fechaA == fechaB:
        raise HTTPException(status_code=422, detail="Elige dos fechas distintas")
    configuracion = configuracionActual()
    return planificacion.compararDias(configuracion, estimacionesVigentes(configuracion), [fechaA, fechaB], categoria)


if CARPETA_FRONT_COMPILADO.exists():
    app.mount("/", StaticFiles(directory=CARPETA_FRONT_COMPILADO, html=True), name="front")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
