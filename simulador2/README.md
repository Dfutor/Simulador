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
| `calendario.py` | Reglas del calendario (única fuente): horario semanal, excepciones, quincena, próxima fecha abierta y franjas |
| `analisisLlegadas.py` | Promedios móviles (simple y ponderado) y categoría de cada franja con la prueba χ² de homogeneidad |
| `planificacion.py` | Simulación por fecha agrupada por franja, publicación de estimaciones, almacenamiento JSON y consultas del cliente |
| `api.py` | FastAPI: valida la entrada con Pydantic, define los valores por defecto y sirve el front compilado |
| `test_iniciador.py` | Tablas a mano, reglas del modelo, KS contra `scipy.stats.kstest`, Poisson, Ciw y API |
| `test_planificacion.py` | Calendario, quincenas (bisiestos), promedios móviles, categorías, semilla, continuidad de la fila y API nueva |

## API

| Ruta | Qué hace |
|---|---|
| `GET /api/entrada-por-defecto` | Valores por defecto de todas las variables (los del estudio) |
| `POST /api/simular` | Simula y devuelve resultados por jornada, la prueba KS, Poisson y, si se pide, Ciw |
| `POST /api/cajas-necesarias` | Simula con 1, 2, 3… cajas hasta cumplir la meta de espera |
| `POST /api/poisson` | Prueba de Poisson de unos conteos |
| `POST /api/analisis-llegadas` | Promedios móviles y categoría (pico, valle, normal) de cada franja |
| `GET /api/establecimiento` | Configuración del establecimiento y estado de la publicación |
| `PUT /api/establecimiento` | Valida, guarda y publica las estimaciones de todos los escenarios |
| `GET /api/calendario/{año}/{mes}` | Días del mes: si se atiende, tipo de día y excepciones |
| `GET /api/visita/{fecha}` | Espera estimada por franja y recomendación; si está cerrado, la próxima fecha abierta |
| `GET /api/comparar-dias?fechaA&fechaB&categoria` | Histograma simulado de llegadas por intervalo de dos fechas |

Documentación interactiva en `/docs`. Errores: `422` si la entrada no es válida o una jornada queda sin clientes, y `409` si una corrida supera el límite de intentos de la prueba KS.

Las simulaciones se atienden de a una (candado `candadoSimulacion`): el modelo usa el generador `random` y la lista global `corridasAceptadas`, y dos peticiones al mismo tiempo mezclarían sus resultados.

## Entrada

- λ = promedio de los conteos · `proporcionVanACaja` · `factorLlegadas` (llegadas por intervalo).
- Servicio (`distribucionServicio`): **uniforme** entre `servicioMinimo` y `servicioMaximo` (por defecto 1–25 min, como el documento) o **exponencial** con media `minutosPorCliente`.
- μ = `tiempoEntreTomasDeDatos` ÷ media del servicio (servicios por caja por intervalo).
- `factorLlegadas`: 1 en un día normal, 1,3 en quincena.
- `inicioConteos`: hora del primer conteo de la jornada (la mañana del estudio se contó de 9:40 a 11:40). Ubica los conteos en el reloj; no cambia la tasa del modelo original.
- `semilla`: si viene vacía, `resolverSemilla` toma el reloj en milisegundos. La respuesta trae `semilla` y `versionModelo`: con las mismas dos y los mismos datos, el resultado se repite.

## Planifica tu visita

- **Tipo de día** (`calendario.esQuincena`): días 1 a 4, 12 a 18 y los últimos cuatro del mes. Solo escala las llegadas por `factorQuincena`, que es un **supuesto** (no se contó ningún día de quincena).
- **Categoría de franja** (`analisisLlegadas.clasificarFranjas`): prueba χ² de homogeneidad de tasas Poisson entre franjas; si se rechaza, cada franja es pico o valle cuando |z| supera el crítico con Bonferroni. Las franjas sin conteos quedan «sin datos». Con los datos del estudio: la mañana no muestra diferencias (p = 0,12) y en la tarde 16:00–16:30 es valle (p = 0,011).
- **Modelo de llegadas** (`modeloLlegadas`): `jornada` = una tasa por jornada (el original, por defecto); `franja` = λ constante por tramos con la tasa de las franjas pico y valle (`generarLlegadasPorTramos`, exacto por la falta de memoria de la exponencial).
- **Continuidad de la fila:** cada jornada se simula completa y después los clientes se agrupan por su hora de llegada. Entre jornadas el banco cierra (como en el modelo original).
- **Publicación:** un escenario por horario distinto × tipo de día, sembrado con `semilla|clave`. Se guarda con una huella de la configuración: si algo cambia, las estimaciones dejan de valer y se vuelven a publicar.

## Validación KS (Coss Bu, 3.5)

En cada corrida se separan los `aleatorioLlegada` y los `aleatorioServicio` y se prueba cada lista contra U(0, 1). Si alguna falla, la corrida se descarta y se repite; si se pasa de `limiteIntentos`, la simulación se detiene con error. Las corridas aceptadas se acumulan en `corridasAceptadas` (global) y la lista se vacía al terminar.

Valor crítico: c(α)/√n para n > 35 (1,22, 1,36 y 1,63 con α = 0,10, 0,05 y 0,01) y la aproximación de la tabla para n ≤ 35.

## Validación con Ciw

Ciw reproduce el banco con las mismas tasas, el cierre de la puerta y las dos clases de prioridad. Sus registros se convierten al mismo formato de cliente y pasan por `calcularMedidas`, así que las fórmulas son idénticas. Con 600 corridas, las dos implementaciones tienen la misma media y la misma desviación en ocupación, clientes y hora de salida.
