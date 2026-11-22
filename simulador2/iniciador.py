"""Simulador de la fila del banco: una fila (con prioridad), varias cajas, varias jornadas."""

import math
import random
import time as reloj
from datetime import time

from medidas import calcularMedidas, resumirCorridas
from pruebaKS import pruebaKS
from pruebaPoisson import pruebaChiCuadradaPoisson
from validacionCiw import compararConCiw

# Corridas que pasaron la prueba KS. Se llena durante simularCorridas() y se vacía al final.
corridasAceptadas: list[dict] = []

MAXIMO_CAJAS_A_PROBAR = 30

# Cambia cuando cambia cómo se generan los números: misma semilla + misma versión → mismo resultado.
VERSION_MODELO = "2.1"


def resolverSemilla(semilla: int | None) -> int:
    """La semilla manual tiene prioridad; si no hay, se toma el reloj del computador en milisegundos.
    El milisegundo no garantiza que dos simulaciones tengan semillas distintas, solo que casi siempre lo serán."""
    return semilla if semilla is not None else reloj.time_ns() // 1_000_000


class UniformidadRechazada(Exception):
    pass


class JornadaSinClientes(Exception):
    pass


def convertirAMinutos(hora: time) -> int:
    return hora.hour * 60 + hora.minute


def duracionJornada(jornada: dict) -> int:
    return convertirAMinutos(jornada["fin"]) - convertirAMinutos(jornada["inicio"])


def generarExponencial(media: float) -> tuple[float, float]:
    """Transformada inversa: x = -media · ln(1 - R)."""
    aleatorio = random.random()
    return aleatorio, -media * math.log(1 - aleatorio)


def generarUniforme(minimo: float, maximo: float) -> tuple[float, float]:
    """Transformada inversa: x = mínimo + (máximo − mínimo) · R."""
    aleatorio = random.random()
    return aleatorio, minimo + (maximo - minimo) * aleatorio


def generadorDeServicio(jornada: dict):
    """Función que genera (aleatorio, tiempo de servicio) según la distribución de la jornada."""
    if jornada.get("distribucionServicio") == "uniforme":
        return lambda: generarUniforme(jornada["servicioMinimo"], jornada["servicioMaximo"])
    mediaServicio = jornada["tiempoEntreTomasDeDatos"] / jornada["tasaServicio"]
    return lambda: generarExponencial(mediaServicio)


def elegirCaja(cajaLibreEn: list[float]) -> int:
    cajaElegida = 0
    for caja in range(len(cajaLibreEn)):
        if cajaLibreEn[caja] < cajaLibreEn[cajaElegida]:
            cajaElegida = caja
    return cajaElegida


def generarLlegadas(numeroJornada: int, mediaEntreLlegadas: float, cierre: float,
                    proporcionPrioritarios: float) -> list[dict]:
    llegadas = []
    aleatorio, entreLlegadas = generarExponencial(mediaEntreLlegadas)
    momento = entreLlegadas
    while momento <= cierre:
        llegadas.append({
            "cliente": len(llegadas) + 1,
            "jornada": numeroJornada,
            "prioritario": random.random() < proporcionPrioritarios,
            "aleatorioLlegada": aleatorio,
            "tiempoEntreLlegadas": entreLlegadas,
            "momentoLlegada": momento,
        })
        aleatorio, entreLlegadas = generarExponencial(mediaEntreLlegadas)
        momento += entreLlegadas
    return llegadas


def generarLlegadasPorTramos(numeroJornada: int, tramos: list[tuple[float, float, float]],
                             proporcionPrioritarios: float) -> list[dict]:
    """Llegadas con una tasa distinta en cada tramo (desde, hasta, media entre llegadas), en minutos de la jornada.
    Por la falta de memoria de la exponencial, la llegada que cae en el tramo siguiente se descarta y se
    vuelve a generar desde el borde con la media nueva: es exacto para un proceso de Poisson por tramos.
    La fila no se reinicia en los bordes: los tramos solo cambian el ritmo de llegada."""
    llegadas = []
    anterior = 0.0
    for posicion, (desde, hasta, media) in enumerate(tramos):
        ultimo = posicion == len(tramos) - 1
        aleatorio, entreLlegadas = generarExponencial(media)
        momento = desde + entreLlegadas
        while momento < hasta or (ultimo and momento == hasta):
            llegadas.append({
                "cliente": len(llegadas) + 1,
                "jornada": numeroJornada,
                "prioritario": random.random() < proporcionPrioritarios,
                "aleatorioLlegada": aleatorio,
                "tiempoEntreLlegadas": momento - anterior,
                "momentoLlegada": momento,
            })
            anterior = momento
            aleatorio, entreLlegadas = generarExponencial(media)
            momento += entreLlegadas
    return llegadas


def siguienteEnFila(pendientes: list[dict], cajaLibre: float) -> dict:
    """Un prioritario que ya esté esperando cuando la caja se libera; si no, el primero en llegar."""
    for cliente in pendientes:
        if cliente["momentoLlegada"] > cajaLibre:
            break
        if cliente["prioritario"]:
            return cliente
    return pendientes[0]


def atender(llegadas: list[dict], numeroServidores: int, generarServicio) -> None:
    cajaLibreEn = [0.0] * numeroServidores
    pendientes = list(llegadas)
    while pendientes:
        caja = elegirCaja(cajaLibreEn)
        libre = cajaLibreEn[caja]
        cliente = siguienteEnFila(pendientes, libre)
        pendientes.remove(cliente)

        llegada = cliente["momentoLlegada"]
        inicio = max(llegada, libre)
        aleatorio, servicio = generarServicio()
        cliente.update({
            "servidor": caja + 1,
            "inicioServicio": inicio,
            "tiempoEspera": inicio - llegada,
            "aleatorioServicio": aleatorio,
            "tiempoServicio": servicio,
            "terminacionServicio": inicio + servicio,
            "tiempoTotal": inicio - llegada + servicio,
            "tiempoOcio": max(0.0, llegada - libre),
        })
        cajaLibreEn[caja] = inicio + servicio

    for posicion, cliente in enumerate(llegadas):
        cliente["personasAlLlegar"] = sum(
            1 for anterior in llegadas[:posicion] if anterior["terminacionServicio"] > cliente["momentoLlegada"])


def modelo(jornadas: dict, numeroServidores: int = 1, proporcionPrioritarios: float = 0.0) -> list[dict]:
    """Simula un día. Cada jornada empieza con el banco vacío.
    Si la jornada trae "tramos" [(desde, hasta, tasaLlegada)], la tasa cambia dentro de la jornada."""
    clientes = []
    for numeroJornada, jornada in jornadas.items():
        if len(jornada.get("tramos") or []) > 1:
            tramos = [(desde, hasta, jornada["tiempoEntreTomasDeDatos"] / tasa) for desde, hasta, tasa in jornada["tramos"]]
            llegadas = generarLlegadasPorTramos(numeroJornada, tramos, proporcionPrioritarios)
        else:
            mediaEntreLlegadas = jornada["tiempoEntreTomasDeDatos"] / jornada["tasaLlegada"]
            llegadas = generarLlegadas(numeroJornada, mediaEntreLlegadas, duracionJornada(jornada),
                                       proporcionPrioritarios)
        if not llegadas:
            raise JornadaSinClientes(
                f"La jornada {numeroJornada} no recibió ningún cliente en una corrida. "
                "Aumenta los conteos o la duración de la jornada.")
        atender(llegadas, numeroServidores, generadorDeServicio(jornada))
        clientes += llegadas
    return clientes


def separarAleatorios(clientes: list[dict]) -> tuple[list[float], list[float]]:
    llegadas = [cliente["aleatorioLlegada"] for cliente in clientes]
    servicios = [cliente["aleatorioServicio"] for cliente in clientes]
    return llegadas, servicios


def validarUniformidadPruebaKS(clientes: list[dict], alfa: float) -> dict:
    llegadas, servicios = separarAleatorios(clientes)
    ksLlegada = pruebaKS(llegadas, alfa)
    ksServicio = pruebaKS(servicios, alfa)
    return {"llegada": ksLlegada, "servicio": ksServicio, "pasa": ksLlegada["pasa"] and ksServicio["pasa"]}


def simularCorridas(jornadas: dict, numeroServidores: int, numeroCorridas: int, alfa: float = 0.05,
                    limiteIntentos: int = 10, proporcionPrioritarios: float = 0.0) -> dict:
    """Simula `numeroCorridas` días. Una corrida que no pasa la prueba KS se descarta y se repite."""
    rechazos = []
    try:
        for corrida in range(1, numeroCorridas + 1):
            for intento in range(1, limiteIntentos + 1):
                clientes = modelo(jornadas, numeroServidores, proporcionPrioritarios)
                ks = validarUniformidadPruebaKS(clientes, alfa)
                if ks["pasa"]:
                    break
                fallaron = [nombre for nombre in ("llegada", "servicio") if not ks[nombre]["pasa"]]
                print(f"Corrida {corrida}, intento {intento}: no pasó la prueba KS "
                      f"({', '.join(fallaron)}). Se rechaza la uniformidad; se vuelve a simular.")
                rechazos.append({"corrida": corrida, "intento": intento, **ks})
            else:
                raise UniformidadRechazada(
                    f"La corrida {corrida} no pasó la prueba KS en {limiteIntentos} intentos "
                    f"(α = {alfa}). Se rechaza la uniformidad y se detiene la simulación.")
            corridasAceptadas.append({"corrida": corrida, "intentos": intento, "ks": ks, "clientes": clientes})

        medidasPorJornada = {}
        for numeroJornada, jornada in jornadas.items():
            medidasPorJornada[numeroJornada] = [
                calcularMedidas([cliente for cliente in aceptada["clientes"] if cliente["jornada"] == numeroJornada],
                                numeroServidores, duracionJornada(jornada))
                for aceptada in corridasAceptadas
            ]
        return {
            "medidas": medidasPorJornada,
            "clientesCorrida1": corridasAceptadas[0]["clientes"],
            "clientesPorCorrida": [aceptada["clientes"] for aceptada in corridasAceptadas],
            "ks": [{"corrida": aceptada["corrida"], "intentos": aceptada["intentos"], **aceptada["ks"]}
                   for aceptada in corridasAceptadas],
            "rechazos": rechazos,
        }
    finally:
        corridasAceptadas.clear()


def armarJornadas(entrada: dict) -> dict:
    """λ = promedio de los conteos · proporción que va a caja · factor de llegadas  (llegadas por intervalo).
    μ = minutos entre tomas de datos ÷ tiempo medio de servicio  (servicios por caja por intervalo)."""
    minutosPorIntervalo = entrada["tiempoEntreTomasDeDatos"]
    distribucion = entrada.get("distribucionServicio", "exponencial")
    jornadas = {}
    for numeroJornada, datosJornada in enumerate(entrada["jornadas"], start=1):
        conteos = datosJornada["conteos"]
        if distribucion == "uniforme":
            mediaServicio = (datosJornada["servicioMinimo"] + datosJornada["servicioMaximo"]) / 2
        else:
            mediaServicio = datosJornada["minutosPorCliente"]
        jornadas[numeroJornada] = {
            "inicio": time.fromisoformat(datosJornada["inicio"]),
            "fin": time.fromisoformat(datosJornada["fin"]),
            "conteos": conteos,
            "tiempoEntreTomasDeDatos": minutosPorIntervalo,
            "tasaLlegada": sum(conteos) / len(conteos) * entrada["proporcionVanACaja"] * entrada["factorLlegadas"],
            "tasaServicio": minutosPorIntervalo / mediaServicio,
            "distribucionServicio": distribucion,
            "servicioMinimo": datosJornada.get("servicioMinimo"),
            "servicioMaximo": datosJornada.get("servicioMaximo"),
        }
    return jornadas


def simular(entrada: dict) -> dict:
    """Recibe las variables de entrada (JSON) y devuelve los resultados (JSON)."""
    jornadas = armarJornadas(entrada)
    semilla = resolverSemilla(entrada.get("semilla"))
    random.seed(semilla)
    resultado = simularCorridas(jornadas, entrada["numeroServidores"], entrada["numeroCorridas"],
                                entrada["alfa"], entrada["limiteIntentos"], entrada["proporcionPrioritarios"])
    ciw = None
    if entrada.get("compararConCiw"):
        ciw = compararConCiw(jornadas, entrada["numeroServidores"], entrada["proporcionPrioritarios"],
                             entrada["alfa"], duracionJornada, resultado["medidas"])

    return {
        "semilla": semilla,
        "semillaManual": entrada.get("semilla") is not None,
        "versionModelo": VERSION_MODELO,
        "ks": resultado["ks"],
        "rechazos": resultado["rechazos"],
        "jornadas": [{
            "numero": numeroJornada,
            "inicio": jornada["inicio"].strftime("%H:%M"),
            "fin": jornada["fin"].strftime("%H:%M"),
            "tasaLlegada": jornada["tasaLlegada"],
            "tasaServicio": jornada["tasaServicio"],
            "poisson": pruebaChiCuadradaPoisson(jornada["conteos"], entrada["alfa"]),
            "resumen": resumirCorridas(resultado["medidas"][numeroJornada]),
            "medidasPorCorrida": [
                {"Wq": medidas["Wq"], "L": medidas["L"], "utilizacion": medidas["utilizacion"]}
                for medidas in resultado["medidas"][numeroJornada]
            ],
            "ciw": ciw[numeroJornada] if ciw else None,
            "corrida1": {
                "clientes": [cliente for cliente in resultado["clientesCorrida1"] if cliente["jornada"] == numeroJornada],
                "medidas": resultado["medidas"][numeroJornada][0],
            },
        } for numeroJornada, jornada in jornadas.items()],
    }


def buscarCajasNecesarias(entrada: dict, metaEsperaMinutos: float) -> dict:
    """Simula con 1, 2, 3… cajas hasta que la espera promedio (Wq) de todas las jornadas cumpla la meta."""
    jornadas = armarJornadas(entrada)
    semilla = resolverSemilla(entrada.get("semilla"))
    curva = []
    cajasRecomendadas = None
    for numeroServidores in range(1, MAXIMO_CAJAS_A_PROBAR + 1):
        random.seed(semilla)   # la misma semilla para cada número de cajas: solo cambian las cajas
        resultado = simularCorridas(jornadas, numeroServidores, entrada["numeroCorridas"], entrada["alfa"],
                                    entrada["limiteIntentos"], entrada["proporcionPrioritarios"])
        porJornada = []
        for numeroJornada in jornadas:
            resumen = resumirCorridas(resultado["medidas"][numeroJornada])
            porJornada.append({"Wq": resumen["Wq"]["promedio"], "utilizacion": resumen["utilizacion"]["promedio"]})
        curva.append({"cajas": numeroServidores, "jornadas": porJornada})

        if cajasRecomendadas is None and all(jornada["Wq"] <= metaEsperaMinutos for jornada in porJornada):
            cajasRecomendadas = numeroServidores
        elif cajasRecomendadas is not None:
            break   # una caja más que la recomendada, para ver cuánto mejora
    return {"metaEsperaMinutos": metaEsperaMinutos, "cajasRecomendadas": cajasRecomendadas, "curva": curva,
            "semilla": semilla}
