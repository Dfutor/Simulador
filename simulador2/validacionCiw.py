"""Validación con una implementación independiente: el mismo banco simulado con la librería Ciw.

Cada medida se compara con la prueba t de Welch: si el valor p es mayor que α,
no hay diferencia significativa entre los dos simuladores.
"""

import math
import random
import statistics
import warnings

import ciw
from scipy.stats import ttest_ind

from medidas import calcularMedidas, resumirCorridas

MEDIDAS_COMPARADAS = ["L", "Lq", "W", "Wq", "WqPrioritarios", "WqNormales", "utilizacion"]


class LlegadasHastaElCierre(ciw.dists.Distribution):
    """Exponencial, pero después del cierre de la puerta no entra nadie más."""

    def __init__(self, tasaPorMinuto: float, cierre: float):
        self.tasaPorMinuto = tasaPorMinuto
        self.cierre = cierre

    def sample(self, t=None, ind=None):
        siguienteLlegada = random.expovariate(self.tasaPorMinuto)
        if t + siguienteLlegada > self.cierre:
            return float("inf")
        return siguienteLlegada


def simularJornadaConCiw(jornada: dict, duracion: float, numeroServidores: int,
                         proporcionPrioritarios: float) -> list[dict]:
    llegadasPorMinuto = jornada["tasaLlegada"] / jornada["tiempoEntreTomasDeDatos"]
    serviciosPorMinuto = jornada["tasaServicio"] / jornada["tiempoEntreTomasDeDatos"]
    def distribucionDeServicio():
        if jornada.get("distribucionServicio") == "uniforme":
            return ciw.dists.Uniform(jornada["servicioMinimo"], jornada["servicioMaximo"])
        return ciw.dists.Exponential(serviciosPorMinuto)

    # Una clase solo existe si llega alguien de ella (con tasa cero, la exponencial no está definida)
    llegadas, servicios, prioridades = {}, {}, {}
    if proporcionPrioritarios < 1:
        llegadas["normal"] = [LlegadasHastaElCierre(llegadasPorMinuto * (1 - proporcionPrioritarios), duracion)]
        servicios["normal"] = [distribucionDeServicio()]
        prioridades["normal"] = 1
    if proporcionPrioritarios > 0:
        llegadas["prioritario"] = [LlegadasHastaElCierre(llegadasPorMinuto * proporcionPrioritarios, duracion)]
        servicios["prioritario"] = [distribucionDeServicio()]
        prioridades["prioritario"] = 0

    red = ciw.create_network(
        arrival_distributions=llegadas,
        service_distributions=servicios,
        number_of_servers=[numeroServidores],
        priority_classes=prioridades,
    )
    simulacion = ciw.Simulation(red)
    simulacion.simulate_until_max_time(float(10**7))

    clientes = []
    for registro in simulacion.get_all_records():
        clientes.append({
            "prioritario": registro.customer_class == "prioritario",
            "servidor": registro.server_id,
            "momentoLlegada": registro.arrival_date,
            "inicioServicio": registro.service_start_date,
            "tiempoEspera": registro.waiting_time,
            "tiempoServicio": registro.service_time,
            "terminacionServicio": registro.service_end_date,
            "tiempoTotal": registro.waiting_time + registro.service_time,
            "personasAlLlegar": registro.queue_size_at_arrival,
        })
    return clientes


def compararMedida(valoresPropios: list[float], valoresCiw: list[float], alfa: float) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        resultadoWelch = ttest_ind(valoresPropios, valoresCiw, equal_var=False)
    valorP = float(resultadoWelch.pvalue)
    if not math.isfinite(valorP):
        # Las dos muestras no varían (por ejemplo, 100 % de ocupación en todas las corridas): no hay t de Welch.
        # Se comparan directamente y el valor p queda vacío (NaN no se puede enviar en JSON).
        return {"valorP": None, "coinciden": statistics.fmean(valoresPropios) == statistics.fmean(valoresCiw)}
    return {"valorP": valorP, "coinciden": valorP > alfa}


def compararConCiw(jornadas: dict, numeroServidores: int, proporcionPrioritarios: float, alfa: float,
                   duracionJornada, medidasPropiasPorJornada: dict) -> dict:
    """Simula con Ciw tantas corridas como el simulador propio y compara cada medida, por jornada."""
    comparacionPorJornada = {}
    for numeroJornada, jornada in jornadas.items():
        duracion = duracionJornada(jornada)
        medidasPropias = medidasPropiasPorJornada[numeroJornada]
        medidasCiw = []
        intentos = 0
        # Las jornadas en que Ciw no recibe a nadie se repiten, con un tope para no quedar en un ciclo sin fin
        while len(medidasCiw) < len(medidasPropias) and intentos < 20 * len(medidasPropias):
            intentos += 1
            clientes = simularJornadaConCiw(jornada, duracion, numeroServidores, proporcionPrioritarios)
            if clientes:
                medidasCiw.append(calcularMedidas(clientes, numeroServidores, duracion))
        if len(medidasCiw) < 2:
            comparacionPorJornada[numeroJornada] = {}
            continue
        resumenCiw = resumirCorridas(medidasCiw)

        comparacion = {}
        for medida in MEDIDAS_COMPARADAS:
            valoresPropios = [medidas[medida] for medidas in medidasPropias if medidas[medida] is not None]
            valoresCiw = [medidas[medida] for medidas in medidasCiw if medidas[medida] is not None]
            if len(valoresPropios) < 2 or len(valoresCiw) < 2:
                continue
            comparacion[medida] = {"ciw": resumenCiw[medida], **compararMedida(valoresPropios, valoresCiw, alfa)}
        comparacionPorJornada[numeroJornada] = comparacion
    return comparacionPorJornada
