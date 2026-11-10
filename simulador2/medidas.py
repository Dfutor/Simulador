"""Medidas de efectividad de una jornada y su resumen entre corridas."""

import math

from scipy.stats import t as distribucionT


# ---------------------------------------------------------------------------
# 1. Medidas de UNA jornada de UNA corrida
# ---------------------------------------------------------------------------
def recorrerLineaDeTiempo(clientes: list[dict], tiempoObservado: float) -> tuple[dict, dict, list]:
    """Recorre la jornada evento por evento:
        llegada            → sistema +1 y, si le toca esperar, cola +1
        inicio de servicio → cola −1   (solo si esperó)
        fin de servicio    → sistema −1

    Devuelve los minutos que hubo n personas en el sistema, los minutos con n en la cola
    y la serie [minuto, personas en el sistema, personas en la cola] para graficar.
    """
    eventos = []   # (minuto, cambioSistema, cambioCola)
    for cliente in clientes:
        esperoEnFila = cliente["tiempoEspera"] > 0
        eventos.append((cliente["momentoLlegada"], +1, +1 if esperoEnFila else 0))
        if esperoEnFila:
            eventos.append((cliente["inicioServicio"], 0, -1))
        eventos.append((cliente["terminacionServicio"], -1, 0))
    eventos.sort(key=lambda evento: evento[0])

    minutosSistema: dict[int, float] = {}
    minutosCola: dict[int, float] = {}
    serie = [[0.0, 0, 0]]
    enSistema = enCola = 0
    reloj = 0.0

    for minuto, cambioSistema, cambioCola in eventos:
        duracion = minuto - reloj
        if duracion > 0:
            minutosSistema[enSistema] = minutosSistema.get(enSistema, 0.0) + duracion
            minutosCola[enCola] = minutosCola.get(enCola, 0.0) + duracion
        reloj = minuto
        enSistema += cambioSistema
        enCola += cambioCola
        serie.append([minuto, enSistema, enCola])

    # Desde el último evento hasta T el banco queda vacío
    if tiempoObservado > reloj:
        minutosSistema[0] = minutosSistema.get(0, 0.0) + (tiempoObservado - reloj)
        minutosCola[0] = minutosCola.get(0, 0.0) + (tiempoObservado - reloj)
        serie.append([tiempoObservado, 0, 0])

    return minutosSistema, minutosCola, serie


def calcularMedidas(clientes: list[dict], numeroServidores: int, duracionJornada: float) -> dict:
    if not clientes:
        raise ValueError("La jornada no tuvo clientes")

    cantidadClientes = len(clientes)
    ultimaSalida = max(cliente["terminacionServicio"] for cliente in clientes)
    # T = el mayor entre la duración de la jornada y la salida del último cliente
    tiempoObservado = max(duracionJornada, ultimaSalida)

    tiempoTotalSistema = sum(cliente["tiempoTotal"] for cliente in clientes)
    tiempoTotalCola = sum(cliente["tiempoEspera"] for cliente in clientes)
    esperaMaxima = max(cliente["tiempoEspera"] for cliente in clientes)

    minutosSistema, minutosCola, serie = recorrerLineaDeTiempo(clientes, tiempoObservado)

    # Ocio = T − minutos que la caja pasó atendiendo (incluye el rato vacío al final)
    minutosAtendiendo = [0.0] * numeroServidores
    for cliente in clientes:
        minutosAtendiendo[cliente["servidor"] - 1] += cliente["tiempoServicio"]
    ocioPorServidor = [tiempoObservado - ocupado for ocupado in minutosAtendiendo]

    probabilidadSistema = {personas: minutos / tiempoObservado for personas, minutos in minutosSistema.items()}
    probabilidadCola = {personas: minutos / tiempoObservado for personas, minutos in minutosCola.items()}

    esperasPrioritarios = [cliente["tiempoEspera"] for cliente in clientes if cliente.get("prioritario")]
    esperasNormales = [cliente["tiempoEspera"] for cliente in clientes if not cliente.get("prioritario")]

    return {
        "clientesAtendidos": cantidadClientes,
        "clientesPrioritarios": len(esperasPrioritarios),
        "L": tiempoTotalSistema / tiempoObservado,
        "Lq": tiempoTotalCola / tiempoObservado,
        "tiempoTotalSistema": tiempoTotalSistema,
        "W": tiempoTotalSistema / cantidadClientes,
        "tiempoTotalCola": tiempoTotalCola,
        "Wq": tiempoTotalCola / cantidadClientes,
        "esperaMaxima": esperaMaxima,
        "WqPrioritarios": sum(esperasPrioritarios) / len(esperasPrioritarios) if esperasPrioritarios else None,
        "WqNormales": sum(esperasNormales) / len(esperasNormales) if esperasNormales else None,
        "personasAlLlegar": sum(cliente.get("personasAlLlegar", 0) for cliente in clientes) / cantidadClientes,
        "longitudMaximaSistema": max(minutosSistema),
        "longitudMaximaCola": max(minutosCola),
        "ocioTotal": sum(ocioPorServidor),
        "ocioPorServidor": ocioPorServidor,
        "utilizacion": sum(minutosAtendiendo) / (numeroServidores * tiempoObservado),
        "utilizacionPorServidor": [ocupado / tiempoObservado for ocupado in minutosAtendiendo],
        "ultimaSalida": ultimaSalida,
        "tiempoObservado": tiempoObservado,
        "probabilidadSistema": probabilidadSistema,
        "probabilidadCola": probabilidadCola,
        "serie": serie,
    }


# ---------------------------------------------------------------------------
# 2. Resumen de VARIAS corridas: promedio e intervalo de confianza del 95 %
# ---------------------------------------------------------------------------
def valorT95(gradosLibertad: int) -> float:
    """t de Student para el 95 % (α/2 = 0.025), exacto para cualquier número de corridas."""
    return float(distribucionT.ppf(0.975, gradosLibertad))


def promedioConIntervalo(valores: list[float]) -> dict:
    """Promedio, mínimo, máximo e intervalo de confianza del 95 %:  x̄ ± t · S / √n."""
    cantidad = len(valores)
    media = sum(valores) / cantidad
    if cantidad < 2:
        return {"promedio": media, "minimo": media, "maximo": media,
                "limiteInferior": media, "limiteSuperior": media}
    desviacion = math.sqrt(sum((valor - media) ** 2 for valor in valores) / (cantidad - 1))
    margen = valorT95(cantidad - 1) * desviacion / math.sqrt(cantidad)
    return {"promedio": media, "minimo": min(valores), "maximo": max(valores),
            "limiteInferior": media - margen, "limiteSuperior": media + margen}


# Medidas que son un solo número y se promedian entre corridas
MEDIDAS_NUMERICAS = [
    "clientesAtendidos", "clientesPrioritarios", "L", "Lq", "tiempoTotalSistema", "W",
    "tiempoTotalCola", "Wq", "WqPrioritarios", "WqNormales", "esperaMaxima", "personasAlLlegar",
    "longitudMaximaSistema", "longitudMaximaCola", "ocioTotal",
    "utilizacion", "ultimaSalida",
]


def resumirCorridas(medidasPorCorrida: list[dict]) -> dict:
    """Por cada medida: promedio entre corridas, mínimo, máximo e intervalo de confianza.
    Las corridas sin dato (None, p. ej. ningún prioritario) no se cuentan."""
    resumen = {}
    for nombre in MEDIDAS_NUMERICAS:
        valores = [medidas[nombre] for medidas in medidasPorCorrida if medidas[nombre] is not None]
        resumen[nombre] = promedioConIntervalo(valores) if valores else None

    numeroServidores = len(medidasPorCorrida[0]["ocioPorServidor"])
    resumen["ocioPorServidor"] = [
        promedioConIntervalo([medidas["ocioPorServidor"][caja] for medidas in medidasPorCorrida])
        for caja in range(numeroServidores)
    ]
    resumen["utilizacionPorServidor"] = [
        promedioConIntervalo([medidas["utilizacionPorServidor"][caja] for medidas in medidasPorCorrida])
        for caja in range(numeroServidores)
    ]
    resumen["probabilidadSistema"] = promediarDistribucion(medidasPorCorrida, "probabilidadSistema")
    resumen["probabilidadCola"] = promediarDistribucion(medidasPorCorrida, "probabilidadCola")
    return resumen


def promediarDistribucion(medidasPorCorrida: list[dict], clave: str) -> dict[int, float]:
    """Promedia P(n) entre corridas. Si en una corrida nunca hubo n personas, cuenta como 0."""
    longitudes = set()
    for medidas in medidasPorCorrida:
        longitudes.update(medidas[clave])
    return {
        personas: sum(medidas[clave].get(personas, 0.0) for medidas in medidasPorCorrida) / len(medidasPorCorrida)
        for personas in sorted(longitudes)
    }
