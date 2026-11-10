"""API JSON del simulador (FastAPI). Documentación interactiva en /docs.

Uso:  .venv/bin/python simulador2/api.py   →   http://localhost:8000
"""

import threading
from datetime import time
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

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
        Jornada(inicio=time(8, 0), fin=time(12, 0), conteos=CONTEOS_MANANA, minutosPorCliente=13.5),
        Jornada(inicio=time(14, 0), fin=time(16, 30), conteos=CONTEOS_TARDE, minutosPorCliente=14),
    ])


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
    if sum(pedido.conteos) == 0:
        raise HTTPException(status_code=422, detail="Debe haber al menos una llegada")
    return pruebaChiCuadradaPoisson(pedido.conteos, pedido.alfa)


if CARPETA_FRONT_COMPILADO.exists():
    app.mount("/", StaticFiles(directory=CARPETA_FRONT_COMPILADO, html=True), name="front")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
