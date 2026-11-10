"""Prueba chi-cuadrada de bondad de ajuste: ¿los conteos por intervalo son Poisson? — Coss Bu, cap. 3."""

from scipy.stats import chi2, poisson

ESPERADAS_MINIMAS = 5


def agruparClases(clases: list[dict]) -> list[dict]:
    """Junta clases vecinas hasta que cada una espere al menos 5 observaciones."""
    agrupadas = []
    actual = None
    for clase in clases:
        if actual is None:
            actual = dict(clase)
        else:
            actual["hasta"] = clase["hasta"]
            actual["observadas"] += clase["observadas"]
            actual["esperadas"] += clase["esperadas"]
        if actual["esperadas"] >= ESPERADAS_MINIMAS:
            agrupadas.append(actual)
            actual = None
    if actual is not None:
        if agrupadas:
            ultima = agrupadas[-1]
            ultima["hasta"] = actual["hasta"]
            ultima["observadas"] += actual["observadas"]
            ultima["esperadas"] += actual["esperadas"]
        else:
            agrupadas.append(actual)
    return agrupadas


def pruebaChiCuadradaPoisson(conteos: list[int], alfa: float) -> dict:
    cantidadIntervalos = len(conteos)
    media = sum(conteos) / cantidadIntervalos
    mayorConteo = max(conteos)

    clases = []
    for valor in range(mayorConteo + 1):
        clases.append({
            "desde": valor,
            "hasta": valor,
            "observadas": conteos.count(valor),
            "esperadas": float(cantidadIntervalos * poisson.pmf(valor, media)),
        })
    # La última clase es "mayorConteo o más" para que las esperadas sumen el total
    clases[-1]["hasta"] = None
    clases[-1]["esperadas"] = float(cantidadIntervalos * poisson.sf(mayorConteo - 1, media))

    clases = agruparClases(clases)
    estadistico = float(sum((clase["observadas"] - clase["esperadas"]) ** 2 / clase["esperadas"] for clase in clases))
    gradosLibertad = len(clases) - 2          # clases − 1 − 1 parámetro estimado (λ)
    varianza = sum((conteo - media) ** 2 for conteo in conteos) / (cantidadIntervalos - 1)

    resultado = {
        "media": media,
        "varianza": varianza,
        "clases": clases,
        "estadistico": estadistico,
        "gradosLibertad": gradosLibertad,
        "critico": None,
        "pasa": None,
    }
    if gradosLibertad >= 1:
        resultado["critico"] = float(chi2.ppf(1 - alfa, gradosLibertad))
        resultado["pasa"] = bool(estadistico < resultado["critico"])
    return resultado
