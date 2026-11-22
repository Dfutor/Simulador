"""Análisis de los conteos observados: promedios móviles y categoría de cada franja (pico, valle o normal).

Las categorías salen de los datos con una prueba, no de porcentajes supuestos:
  1. Prueba χ² de homogeneidad de tasas Poisson entre franjas:  X² = Σ (Sₖ − nₖ·x̄)² / (nₖ·x̄),  k − 1 grados de libertad.
     Si no se rechaza, no hay evidencia de que la tasa cambie dentro de la jornada: todas las franjas son normales.
  2. Solo si se rechaza, cada franja se compara con la media:  z = (Sₖ − nₖ·x̄) / √(nₖ·x̄),
     con corrección de Bonferroni (α / k) porque se hacen k comparaciones.  z > crítico → pico,  z < −crítico → valle.
Las franjas sin conteos quedan "sinDatos": su tasa es un supuesto (la de la jornada), no una observación.

Los promedios móviles son solo descriptivos: no reemplazan la tasa de llegadas del modelo.
"""

from scipy.stats import chi2, norm

from calendario import aHora, aMinutos, franjasDeJornada

CATEGORIAS = ["valle", "normal", "pico", "sinDatos"]
ESPERADAS_MINIMAS = 5


# ---------------------------------------------------------------------------
# Promedios móviles
# ---------------------------------------------------------------------------
def promedioMovilSimple(valores: list[float], ventana: int) -> list[float | None]:
    """PMSₜ = (xₜ + xₜ₋₁ + … + xₜ₋ₖ₊₁) / k.  Los primeros k − 1 puntos no tienen ventana completa (None)."""
    return [None if posicion + 1 < ventana else sum(valores[posicion + 1 - ventana:posicion + 1]) / ventana
            for posicion in range(len(valores))]


def promedioMovilPonderado(valores: list[float], ventana: int) -> list[float | None]:
    """PMPₜ = (k·xₜ + (k−1)·xₜ₋₁ + … + 1·xₜ₋ₖ₊₁) / (1 + 2 + … + k): la observación más reciente pesa más."""
    sumaPesos = ventana * (ventana + 1) / 2
    resultado = []
    for posicion in range(len(valores)):
        if posicion + 1 < ventana:
            resultado.append(None)
            continue
        tramo = valores[posicion + 1 - ventana:posicion + 1]
        resultado.append(sum(peso * valor for peso, valor in enumerate(tramo, start=1)) / sumaPesos)
    return resultado


# ---------------------------------------------------------------------------
# Conteos ubicados en el reloj y categorías por franja
# ---------------------------------------------------------------------------
def ubicarConteos(jornada: dict, minutosIntervalo: float) -> list[tuple[float, float, int]]:
    """Cada conteo con su hora: (desde, hasta, personas), en minutos desde la medianoche.
    Los conteos empiezan en `inicioConteos` (si no se indica, cuando abre la jornada)."""
    inicioJornada, finJornada = aMinutos(jornada["inicio"]), aMinutos(jornada["fin"])
    inicio = aMinutos(jornada.get("inicioConteos") or jornada["inicio"])
    conteos = jornada["conteos"]
    fin = inicio + len(conteos) * minutosIntervalo
    if inicio < inicioJornada or fin > finJornada + 1e-9:
        raise ValueError(f"Los {len(conteos)} conteos de {minutosIntervalo:g} min desde las {aHora(inicio)} terminan "
                         f"a las {aHora(fin)}: no caben en la jornada {aHora(inicioJornada)}–{aHora(finJornada)}")
    return [(inicio + posicion * minutosIntervalo, inicio + (posicion + 1) * minutosIntervalo, conteo)
            for posicion, conteo in enumerate(conteos)]


def clasificarFranjas(jornada: dict, minutosIntervalo: float, minutosPorFranja: int, alfa: float) -> dict:
    """Franjas de la jornada con su categoría y su tasa (personas por intervalo de conteo)."""
    ubicados = ubicarConteos(jornada, minutosIntervalo)
    franjas = [{"desde": desde, "hasta": hasta, "conteos": []}
               for desde, hasta in franjasDeJornada(aMinutos(jornada["inicio"]), aMinutos(jornada["fin"]), minutosPorFranja)]
    for desde, _, conteo in ubicados:   # cada conteo va a la franja donde empieza
        next(franja for franja in franjas if franja["desde"] <= desde < franja["hasta"])["conteos"].append(conteo)

    todos = [conteo for _, _, conteo in ubicados]
    media = sum(todos) / len(todos)
    observadas = [franja for franja in franjas if franja["conteos"]]
    cantidad = len(observadas)

    homogeneidad = {"estadistico": None, "gradosLibertad": cantidad - 1, "critico": None, "valorP": None,
                    "rechaza": False, "zCritico": None, "advertencia": ""}
    if cantidad >= 2 and media > 0:
        estadistico = sum((sum(franja["conteos"]) - len(franja["conteos"]) * media) ** 2 / (len(franja["conteos"]) * media)
                          for franja in observadas)
        homogeneidad.update(
            estadistico=float(estadistico),
            critico=float(chi2.ppf(1 - alfa, cantidad - 1)),
            valorP=float(chi2.sf(estadistico, cantidad - 1)),
            zCritico=float(norm.ppf(1 - alfa / (2 * cantidad))),
        )
        homogeneidad["rechaza"] = homogeneidad["valorP"] < alfa
        if any(len(franja["conteos"]) * media < ESPERADAS_MINIMAS for franja in observadas):
            homogeneidad["advertencia"] = ("Alguna franja espera menos de 5 llegadas: la aproximación χ² es débil. "
                                           "Usa franjas más largas o más conteos.")
    elif cantidad < 2:
        homogeneidad["advertencia"] = "Los conteos caen en una sola franja: no se puede comparar entre franjas."

    for franja in franjas:
        observaciones = len(franja["conteos"])
        franja["observaciones"] = observaciones
        franja["media"] = sum(franja["conteos"]) / observaciones if observaciones else None
        franja["z"] = None
        if not observaciones:
            franja["categoria"] = "sinDatos"
            continue
        franja["z"] = (sum(franja["conteos"]) - observaciones * media) / (observaciones * media) ** 0.5 if media > 0 else 0.0
        if homogeneidad["rechaza"] and franja["z"] > homogeneidad["zCritico"]:
            franja["categoria"] = "pico"
        elif homogeneidad["rechaza"] and franja["z"] < -homogeneidad["zCritico"]:
            franja["categoria"] = "valle"
        else:
            franja["categoria"] = "normal"

    # Tasa de las franjas normales y sin datos: la media de los conteos normales (= la de la jornada si nada se rechaza)
    normales = [conteo for franja in franjas if franja["categoria"] == "normal" for conteo in franja["conteos"]]
    tasaNormal = sum(normales) / len(normales) if normales else media
    for franja in franjas:
        franja["tasa"] = franja["media"] if franja["categoria"] in ("pico", "valle") else tasaNormal

    return {"media": media, "tasaNormal": tasaNormal, "homogeneidad": homogeneidad, "franjas": franjas,
            "ubicados": ubicados}


def analizarLlegadas(entrada: dict, minutosPorFranja: int, ventana: int) -> dict:
    """Para cada jornada: los conteos en orden con su hora, los promedios móviles y la categoría de su franja.
    Los promedios se calculan dentro de cada jornada: nunca se juntan conteos de jornadas o fechas distintas."""
    minutosIntervalo = entrada["tiempoEntreTomasDeDatos"]
    jornadas = []
    for numero, jornada in enumerate(entrada["jornadas"], start=1):
        clasificacion = clasificarFranjas(jornada, minutosIntervalo, minutosPorFranja, entrada["alfa"])
        ubicados = clasificacion["ubicados"]
        conteos = [conteo for _, _, conteo in ubicados]
        simple = promedioMovilSimple(conteos, ventana)
        ponderado = promedioMovilPonderado(conteos, ventana)
        categoriaDe = lambda minuto: next(franja["categoria"] for franja in clasificacion["franjas"]
                                          if franja["desde"] <= minuto < franja["hasta"])
        jornadas.append({
            "numero": numero,
            "inicio": aHora(aMinutos(jornada["inicio"])),
            "fin": aHora(aMinutos(jornada["fin"])),
            "media": clasificacion["media"],
            "homogeneidad": clasificacion["homogeneidad"],
            "intervalos": [{"desde": aHora(desde), "hasta": aHora(hasta), "conteo": conteo,
                            "promedioSimple": simple[posicion], "promedioPonderado": ponderado[posicion],
                            "categoria": categoriaDe(desde)}
                           for posicion, (desde, hasta, conteo) in enumerate(ubicados)],
            "franjas": [{"desde": aHora(franja["desde"]), "hasta": aHora(franja["hasta"]),
                         "observaciones": franja["observaciones"], "media": franja["media"], "z": franja["z"],
                         "categoria": franja["categoria"], "tasa": franja["tasa"]}
                        for franja in clasificacion["franjas"]],
        })
    return {"ventana": ventana, "minutosPorFranja": minutosPorFranja, "fechasObservadas": 1, "jornadas": jornadas}


def perfilDeLlegadas(entrada: dict, minutosPorFranja: int) -> dict:
    """Lo que necesita la simulación por fechas: para cada jornada observada, su ventana de reloj y sus franjas."""
    ventanas = []
    todos = []
    for posicion, jornada in enumerate(entrada["jornadas"]):
        clasificacion = clasificarFranjas(jornada, entrada["tiempoEntreTomasDeDatos"], minutosPorFranja, entrada["alfa"])
        todos += jornada["conteos"]
        ventanas.append({
            "posicion": posicion,
            "desde": aMinutos(jornada["inicio"]),
            "hasta": aMinutos(jornada["fin"]),
            "media": clasificacion["media"],
            "franjas": [{key: franja[key] for key in ("desde", "hasta", "categoria", "tasa")}
                        for franja in clasificacion["franjas"]],
            "conteosPorCategoria": {
                categoria: [conteo for franja in clasificacion["franjas"] if franja["categoria"] == categoria
                            for conteo in franja["conteos"]]
                for categoria in CATEGORIAS
            },
        })
    return {"ventanas": ventanas, "mediaGeneral": sum(todos) / len(todos)}


def llegadasEnElMinuto(perfil: dict, minuto: int, modeloLlegadas: str) -> dict:
    """Tasa (personas por intervalo de conteo) y categoría para un minuto del reloj.
    - Dentro de una jornada observada: la categoría de su franja; la tasa es la de la jornada (modelo "jornada",
      el original) o la de la franja (modelo "franja").
    - Fuera de toda jornada observada: sin datos; se supone la media de todos los conteos."""
    for ventana in perfil["ventanas"]:
        if ventana["desde"] <= minuto < ventana["hasta"]:
            franja = next(franja for franja in ventana["franjas"] if franja["desde"] <= minuto < franja["hasta"])
            tasa = franja["tasa"] if modeloLlegadas == "franja" else ventana["media"]
            return {"tasa": tasa, "categoria": franja["categoria"], "ventana": ventana["posicion"]}
    return {"tasa": perfil["mediaGeneral"], "categoria": "sinDatos", "ventana": None}
