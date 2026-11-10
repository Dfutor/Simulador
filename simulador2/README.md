# Simulador 2 — back

Una fila (los prioritarios pasan primero), varias cajas y varias jornadas por día. Cada corrida se valida con la prueba de Kolmogorov-Smirnov antes de usarla. Instalación y uso: ver el [README del proyecto](../README.md).

## Archivos

| Archivo | Qué hace |
|---|---|
| `iniciador.py` | Modelo de un día (`modelo`), corridas con validación KS (`simularCorridas`), entrada/salida JSON (`simular`) y búsqueda de cajas (`buscarCajasNecesarias`) |
| `pruebaKS.py` | Prueba K-S y su valor crítico según α (Coss Bu, 3.5) |
| `pruebaPoisson.py` | Chi-cuadrada de bondad de ajuste de los conteos a una Poisson (SciPy) |
| `medidas.py` | Medidas de una jornada y su resumen entre corridas con IC 95 % (t de Student de SciPy) |
| `validacionCiw.py` | El mismo banco simulado con Ciw y comparado medida por medida (t de Welch) |
| `api.py` | FastAPI: valida la entrada con Pydantic, define los valores por defecto y sirve el front compilado |
| `test_iniciador.py` | Tablas a mano, reglas del modelo, KS contra `scipy.stats.kstest`, Poisson, Ciw y API |

## API

| Ruta | Qué hace |
|---|---|
| `GET /api/entrada-por-defecto` | Valores por defecto de todas las variables (los del estudio) |
| `POST /api/simular` | Simula y devuelve resultados por jornada, la prueba KS, Poisson y, si se pide, Ciw |
| `POST /api/cajas-necesarias` | Simula con 1, 2, 3… cajas hasta cumplir la meta de espera |
| `POST /api/poisson` | Prueba de Poisson de unos conteos |

Documentación interactiva en `/docs`. Errores: `422` si la entrada no es válida o una jornada queda sin clientes, y `409` si una corrida supera el límite de intentos de la prueba KS.

Las simulaciones se atienden de a una (candado `candadoSimulacion`): el modelo usa el generador `random` y la lista global `corridasAceptadas`, y dos peticiones al mismo tiempo mezclarían sus resultados.

## Entrada

- λ = promedio de los conteos · `proporcionVanACaja` · `factorLlegadas` (llegadas por intervalo).
- Servicio (`distribucionServicio`): **uniforme** entre `servicioMinimo` y `servicioMaximo` (por defecto 1–25 min, como el documento) o **exponencial** con media `minutosPorCliente`.
- μ = `tiempoEntreTomasDeDatos` ÷ media del servicio (servicios por caja por intervalo).
- `factorLlegadas`: 1 en un día normal, 1,3 en quincena.

## Validación KS (Coss Bu, 3.5)

En cada corrida se separan los `aleatorioLlegada` y los `aleatorioServicio` y se prueba cada lista contra U(0, 1). Si alguna falla, la corrida se descarta y se repite; si se pasa de `limiteIntentos`, la simulación se detiene con error. Las corridas aceptadas se acumulan en `corridasAceptadas` (global) y la lista se vacía al terminar.

Valor crítico: c(α)/√n para n > 35 (1,22, 1,36 y 1,63 con α = 0,10, 0,05 y 0,01) y la aproximación de la tabla para n ≤ 35.

## Validación con Ciw

Ciw reproduce el banco con las mismas tasas, el cierre de la puerta y las dos clases de prioridad. Sus registros se convierten al mismo formato de cliente y pasan por `calcularMedidas`, así que las fórmulas son idénticas. Con 600 corridas, las dos implementaciones tienen la misma media y la misma desviación en ocupación, clientes y hora de salida.
