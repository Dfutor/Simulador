"""Estimaciones por fecha para «Planifica tu visita».

Calcular y mostrar van separados:
  - El administrador PUBLICA: se simula una vez cada escenario distinto (horario del día × tipo de día)
    y se guarda junto con la huella de la configuración, la semilla y la versión del modelo.
  - El cliente CONSULTA una fecha: el calendario dice si se atiende y qué escenario le toca,
    y se lee la estimación ya calculada. No se vuelve a simular en cada consulta.

Continuidad de la fila: cada jornada se simula completa (la fila de las 9:55 sigue ahí a las 10:05)
y DESPUÉS los clientes se agrupan en franjas según su hora de llegada.
"""

import hashlib
import json
import os
import random
from datetime import date, datetime, time, timezone
from pathlib import Path

from analisisLlegadas import CATEGORIAS, llegadasEnElMinuto, perfilDeLlegadas
from calendario import (aHora, aMinutos, claveHorario, franjasDeJornada, horarioDelDia, horariosDistintos,
                        siguienteFechaAbierta)
from iniciador import VERSION_MODELO, armarJornadas, resolverSemilla, simularCorridas
from medidas import promedioConIntervalo

CARPETA_DATOS = Path(os.environ.get("CARPETA_DATOS", Path(__file__).resolve().parent / "datos"))
ARCHIVO_CONFIGURACION = "establecimiento.json"
ARCHIVO_ESTIMACIONES = "estimaciones.json"
TIPOS_DE_DIA = ("regular", "quincena")


# ---------------------------------------------------------------------------
# 1. Un día concreto convertido en jornadas para el modelo
# ---------------------------------------------------------------------------
def unirTramosIguales(tramos: list[list[float]]) -> list[list[float]]:
    """Tramos vecinos con la misma tasa se juntan: con tasa constante el modelo usa exactamente el generador original."""
    unidos = []
    for tramo in tramos:
        if unidos and abs(unidos[-1][2] - tramo[2]) < 1e-12:
            unidos[-1][1] = tramo[1]
        else:
            unidos.append(list(tramo))
    return unidos


def jornadasDelEscenario(configuracion: dict, jornadasDelDia: list[dict], tipoDia: str, perfil: dict) -> dict:
    """Las jornadas de un día, listas para `modelo`, con la tasa y la categoría de cada franja.
    λ de una franja = tasa observada · proporción que va a caja · factor de quincena (si es quincena)."""
    entrada = configuracion["entrada"]
    observadas = armarJornadas(entrada)   # de aquí salen los parámetros de servicio de cada jornada observada
    factor = configuracion["factorQuincena"] if tipoDia == "quincena" else 1
    escala = entrada["proporcionVanACaja"] * factor
    jornadas = {}
    for numero, jornadaDelDia in enumerate(jornadasDelDia, start=1):
        inicio, fin = aMinutos(jornadaDelDia["inicio"]), aMinutos(jornadaDelDia["fin"])
        franjas = []
        for desde, hasta in franjasDeJornada(inicio, fin, configuracion["minutosPorFranja"]):
            llegadas = llegadasEnElMinuto(perfil, desde, configuracion["modeloLlegadas"])
            franjas.append({"desde": desde - inicio, "hasta": hasta - inicio, "categoria": llegadas["categoria"],
                            "tasaLlegada": llegadas["tasa"] * escala, "ventana": llegadas["ventana"]})
        tramos = unirTramosIguales([[franja["desde"], franja["hasta"], franja["tasaLlegada"]] for franja in franjas])
        servicio = observadas[servicioDeLaJornada(franjas, perfil) + 1]
        jornadas[numero] = {
            "inicio": time.fromisoformat(jornadaDelDia["inicio"]),
            "fin": time.fromisoformat(jornadaDelDia["fin"]),
            "tiempoEntreTomasDeDatos": entrada["tiempoEntreTomasDeDatos"],
            "tasaLlegada": sum((hasta - desde) * tasa for desde, hasta, tasa in tramos) / (fin - inicio),
            "tramos": tramos,
            "tasaServicio": servicio["tasaServicio"],
            "distribucionServicio": servicio["distribucionServicio"],
            "servicioMinimo": servicio["servicioMinimo"],
            "servicioMaximo": servicio["servicioMaximo"],
            "franjas": franjas,
        }
    return jornadas


def servicioDeLaJornada(franjas: list[dict], perfil: dict) -> int:
    """El servicio es el de la jornada observada que más franjas comparte con esta; si ninguna, el de la primera."""
    ventanas = [franja["ventana"] for franja in franjas if franja["ventana"] is not None]
    return max(set(ventanas), key=ventanas.count) if ventanas else perfil["ventanas"][0]["posicion"]


# ---------------------------------------------------------------------------
# 2. Simular un escenario y agrupar por franja según la hora de llegada
# ---------------------------------------------------------------------------
def resumirFranja(clientesPorCorrida: list[list[dict]]) -> dict:
    """Promedio entre corridas de la espera en fila, el servicio y el tiempo total de los que llegaron en la franja.
    Una corrida en la que nadie llegó en esa franja no aporta dato."""
    porCorrida = {"Wq": [], "servicio": [], "W": []}
    for clientes in clientesPorCorrida:
        if not clientes:
            continue
        porCorrida["Wq"].append(sum(cliente["tiempoEspera"] for cliente in clientes) / len(clientes))
        porCorrida["servicio"].append(sum(cliente["tiempoServicio"] for cliente in clientes) / len(clientes))
        porCorrida["W"].append(sum(cliente["tiempoTotal"] for cliente in clientes) / len(clientes))
    resumen = {medida: promedioConIntervalo(valores) if valores else None for medida, valores in porCorrida.items()}
    resumen["clientes"] = sum(len(clientes) for clientes in clientesPorCorrida) / len(clientesPorCorrida)
    resumen["corridasConClientes"] = len(porCorrida["Wq"])
    return resumen


def histogramaDeLlegadas(jornadas: dict, clientesPorCorrida: list[list[dict]]) -> dict:
    """Frecuencia de «personas que llegan en un intervalo» por categoría, con intervalos del mismo largo que los conteos.
    El último intervalo incompleto de cada jornada no se cuenta: sería más corto y no comparable."""
    frecuencias = {categoria: {} for categoria in ["todas", *CATEGORIAS]}
    for clientes in clientesPorCorrida:
        for numero, jornada in jornadas.items():
            largo = jornada["tiempoEntreTomasDeDatos"]
            duracion = jornada["franjas"][-1]["hasta"]
            completos = int(duracion // largo + 1e-9)
            conteos = [0] * completos
            for cliente in clientes:
                if cliente["jornada"] == numero:
                    posicion = int(cliente["momentoLlegada"] // largo)
                    if posicion < completos:
                        conteos[posicion] += 1
            for posicion, conteo in enumerate(conteos):
                inicioIntervalo = posicion * largo
                categoria = next(franja["categoria"] for franja in jornada["franjas"]
                                 if franja["desde"] <= inicioIntervalo < franja["hasta"])
                for clave in ("todas", categoria):
                    frecuencias[clave][conteo] = frecuencias[clave].get(conteo, 0) + 1
    return {categoria: {str(conteo): veces for conteo, veces in sorted(tabla.items())}
            for categoria, tabla in frecuencias.items()}


def simularEscenario(configuracion: dict, jornadas: dict) -> dict:
    entrada = configuracion["entrada"]
    resultado = simularCorridas(jornadas, entrada["numeroServidores"], entrada["numeroCorridas"], entrada["alfa"],
                                entrada["limiteIntentos"], entrada["proporcionPrioritarios"])
    corridas = resultado["clientesPorCorrida"]
    salida = []
    for numero, jornada in jornadas.items():
        inicio = aMinutos(jornada["inicio"])
        ultima = len(jornada["franjas"]) - 1
        franjas = []
        for posicion, franja in enumerate(jornada["franjas"]):
            # La última franja incluye la llegada justo al cerrar la puerta (el modelo la admite)
            enLaFranja = lambda cliente: franja["desde"] <= cliente["momentoLlegada"] < franja["hasta"] or (
                posicion == ultima and cliente["momentoLlegada"] == franja["hasta"])
            clientesPorCorrida = [[cliente for cliente in clientes if cliente["jornada"] == numero and enLaFranja(cliente)]
                                  for clientes in corridas]
            franjas.append({"desde": aHora(inicio + franja["desde"]), "hasta": aHora(inicio + franja["hasta"]),
                            "categoria": franja["categoria"], "tasaLlegada": franja["tasaLlegada"],
                            **resumirFranja(clientesPorCorrida)})
        medidas = resultado["medidas"][numero]
        salida.append({
            "inicio": aHora(inicio),
            "fin": aHora(aMinutos(jornada["fin"])),
            "tasaLlegada": jornada["tasaLlegada"],
            "tasaServicio": jornada["tasaServicio"],
            "Wq": promedioConIntervalo([medida["Wq"] for medida in medidas]),
            "utilizacion": promedioConIntervalo([medida["utilizacion"] for medida in medidas]),
            "franjas": franjas,
        })
    return {"jornadas": salida, "corridas": len(corridas), "histogramas": histogramaDeLlegadas(jornadas, corridas)}


# ---------------------------------------------------------------------------
# 3. Publicar: todos los escenarios de la configuración
# ---------------------------------------------------------------------------
def huellaDe(configuracion: dict) -> str:
    """Identifica la configuración: si cambia algo (horario, cajas, conteos…), las estimaciones dejan de valer."""
    texto = json.dumps({"configuracion": configuracion, "version": VERSION_MODELO}, sort_keys=True, default=str)
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


def claveEscenario(tipoDia: str, jornadas: list[dict]) -> str:
    return f"{tipoDia}|{claveHorario(jornadas)}"


def publicar(configuracion: dict) -> dict:
    """Simula cada horario distinto en día regular y en quincena.
    Cada escenario se siembra con «semilla|clave»: se puede reproducir solo, sin depender de los demás."""
    semilla = resolverSemilla(configuracion["entrada"].get("semilla"))
    perfil = perfilDeLlegadas(configuracion["entrada"], configuracion["minutosPorFranja"])
    escenarios = {}
    for jornadasDelDia in horariosDistintos(configuracion):
        for tipoDia in TIPOS_DE_DIA:
            clave = claveEscenario(tipoDia, jornadasDelDia)
            random.seed(f"{semilla}|{clave}")
            escenarios[clave] = simularEscenario(configuracion,
                                                 jornadasDelEscenario(configuracion, jornadasDelDia, tipoDia, perfil))
    return {
        "huella": huellaDe(configuracion),
        "versionModelo": VERSION_MODELO,
        "semilla": semilla,
        "semillaManual": configuracion["entrada"].get("semilla") is not None,
        "publicadoEn": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corridas": configuracion["entrada"]["numeroCorridas"],
        "modeloLlegadas": configuracion["modeloLlegadas"],
        "escenarios": escenarios,
    }


def resumenPublicacion(estimaciones: dict | None, configuracion: dict) -> dict | None:
    if estimaciones is None:
        return None
    return {key: estimaciones[key] for key in ("versionModelo", "semilla", "semillaManual", "publicadoEn",
                                               "corridas", "modeloLlegadas")} | {
        "escenarios": sorted(estimaciones["escenarios"]),
        "vigente": estimaciones["huella"] == huellaDe(configuracion),
    }


# ---------------------------------------------------------------------------
# 4. Guardar y leer (archivos JSON; no hace falta una base de datos)
# ---------------------------------------------------------------------------
def escribirJSON(nombre: str, datos: dict) -> None:
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
    temporal = CARPETA_DATOS / f".{nombre}.tmp"
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporal, CARPETA_DATOS / nombre)   # reemplazo atómico: nunca queda un archivo a medias


def leerJSON(nombre: str) -> dict | None:
    ruta = CARPETA_DATOS / nombre
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar(configuracion: dict, estimaciones: dict) -> None:
    escribirJSON(ARCHIVO_ESTIMACIONES, estimaciones)
    escribirJSON(ARCHIVO_CONFIGURACION, configuracion)


def cargarConfiguracion() -> dict | None:
    return leerJSON(ARCHIVO_CONFIGURACION)


def cargarEstimaciones() -> dict | None:
    return leerJSON(ARCHIVO_ESTIMACIONES)


# ---------------------------------------------------------------------------
# 5. Consultas del cliente
# ---------------------------------------------------------------------------
def intervalosSeCruzan(primero: dict, segundo: dict) -> bool:
    return primero["limiteInferior"] <= segundo["limiteSuperior"] and segundo["limiteInferior"] <= primero["limiteSuperior"]


def consultarFecha(configuracion: dict, estimaciones: dict, fecha: date) -> dict:
    """Horario, tipo de día y espera estimada por franja de una fecha; si está cerrada, la próxima fecha abierta."""
    dia = horarioDelDia(configuracion, fecha)
    respuesta = {**dia, "franjas": [], "recomendada": None, "similares": [], "siguienteAbierta": None,
                 "sinEstimacion": False, "indicador": "Wq",
                 "corridas": estimaciones["corridas"], "publicadoEn": estimaciones["publicadoEn"],
                 "vigente": estimaciones["huella"] == huellaDe(configuracion)}
    if not dia["abierto"]:
        siguiente = siguienteFechaAbierta(configuracion, fecha)
        respuesta["siguienteAbierta"] = horarioDelDia(configuracion, siguiente) if siguiente else None
        return respuesta

    escenario = estimaciones["escenarios"].get(claveEscenario(dia["tipoDia"], dia["jornadas"]))
    if escenario is None or not respuesta["vigente"]:
        respuesta["sinEstimacion"] = True
        return respuesta

    respuesta["franjas"] = [{**{key: franja[key] for key in ("desde", "hasta", "categoria", "Wq", "servicio", "W", "clientes")},
                             "jornada": numero}
                            for numero, jornada in enumerate(escenario["jornadas"], start=1) for franja in jornada["franjas"]]
    conDato = [posicion for posicion, franja in enumerate(respuesta["franjas"]) if franja["Wq"] is not None]
    if conDato:
        mejor = min(conDato, key=lambda posicion: respuesta["franjas"][posicion]["Wq"]["promedio"])
        respuesta["recomendada"] = mejor
        # Franjas cuya espera no se distingue de la mejor (sus intervalos de confianza del 95 % se cruzan)
        respuesta["similares"] = [posicion for posicion in conDato if posicion != mejor and
                                  intervalosSeCruzan(respuesta["franjas"][posicion]["Wq"], respuesta["franjas"][mejor]["Wq"])]
    return respuesta


def distribucionRelativa(frecuencias: dict[str, int]) -> dict:
    total = sum(frecuencias.values())
    media = sum(int(conteo) * veces for conteo, veces in frecuencias.items()) / total if total else None
    return {"n": total, "media": media,
            "relativas": {int(conteo): veces / total for conteo, veces in frecuencias.items()} if total else {}}


def compararDias(configuracion: dict, estimaciones: dict, fechas: list[date], categoria: str) -> dict:
    """Histograma de llegadas por intervalo para dos fechas, con las mismas clases y frecuencias relativas.
    Son escenarios simulados con el modelo; el día de conteo del estudio va como referencia."""
    series = []
    for fecha in fechas:
        dia = horarioDelDia(configuracion, fecha)
        serie = {"fecha": dia["fecha"], "diaSemana": dia["diaSemana"], "tipoDia": dia["tipoDia"], "abierto": dia["abierto"],
                 "n": 0, "media": None, "relativas": {}}
        escenario = estimaciones["escenarios"].get(claveEscenario(dia["tipoDia"], dia["jornadas"])) if dia["abierto"] else None
        if escenario is not None:
            serie.update(distribucionRelativa(escenario["histogramas"].get(categoria, {})))
        series.append(serie)

    perfil = perfilDeLlegadas(configuracion["entrada"], configuracion["minutosPorFranja"])
    observados = [conteo for ventana in perfil["ventanas"] for clave, conteos in ventana["conteosPorCategoria"].items()
                  if categoria in ("todas", clave) for conteo in conteos]
    observado = distribucionRelativa({str(valor): observados.count(valor) for valor in set(observados)})

    mayor = max([conteo for serie in [*series, observado] for conteo in serie["relativas"]], default=0)
    clases = list(range(mayor + 1))
    for serie in [*series, observado]:
        serie["relativas"] = [serie["relativas"].get(clase, 0.0) for clase in clases]
    return {
        "categoria": categoria,
        "clases": clases,
        "minutosIntervalo": configuracion["entrada"]["tiempoEntreTomasDeDatos"],
        "origen": "simulacion",
        "corridas": estimaciones["corridas"],
        "series": series,
        "observado": observado if observado["n"] else None,
        "fechasObservadas": 1,
    }
