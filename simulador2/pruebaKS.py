"""Prueba de Kolmogorov-Smirnov para números U(0, 1) — Coss Bu, sección 3.5."""

import math


def valorCriticoKS(cantidad: int, alfa: float) -> float:
    # cantidad > 35: fórmula del libro, c(α)/√n  → 1.22, 1.36 y 1.63 para α = 0.10, 0.05 y 0.01.
    # cantidad ≤ 35: aproximación de Stephens, coincide con la tabla del libro.
    coeficiente = math.sqrt(-math.log(alfa / 2) / 2)
    raiz = math.sqrt(cantidad)
    if cantidad > 35:
        return coeficiente / raiz
    return coeficiente / (raiz + 0.12 + 0.11 / raiz)


def pruebaKS(numeros: list[float], alfa: float) -> dict:
    """D = máxima distancia entre la acumulada observada y la de U(0, 1).
    Si D < valor crítico, no se rechaza la uniformidad."""
    cantidad = len(numeros)
    ordenados = sorted(numeros)
    distanciaArriba = max((posicion + 1) / cantidad - numero for posicion, numero in enumerate(ordenados))
    distanciaAbajo = max(numero - posicion / cantidad for posicion, numero in enumerate(ordenados))
    estadisticoD = max(distanciaArriba, distanciaAbajo)
    critico = valorCriticoKS(cantidad, alfa)
    return {"n": cantidad, "D": estadisticoD, "critico": critico, "pasa": estadisticoD < critico}
