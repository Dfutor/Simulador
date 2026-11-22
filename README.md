El objetivo de este proyecto es crear un simulador de filas de un banco

El banco en cuestion es el banco BBVA.

## Referencia

Coss Bu, Raúl. *Simulación: un enfoque práctico*. México: Limusa. El documento [Levantamiento_de_requrimientos_Cap1COSBUS.md](Levantamiento_de_requrimientos_Cap1COSBUS.md) sigue sus etapas (capítulo 1) y sus pruebas estadísticas (capítulo 3).

## Estructura

| Carpeta | Qué hay |
|---|---|
| `simulador2/` | Back en Python: el modelo, las pruebas estadísticas y la API (FastAPI) |
| `front/` | Front en Vue 3 + Vite: asistente por pasos, gráficas (ECharts), banco en 3D (Three.js + Tweakpane) |

## Iniciar con Docker (recomendado)

Solo se necesita [Docker](https://docs.docker.com/get-docker/) (con Docker Compose, que ya viene incluido). En la carpeta del proyecto:

```bash
docker compose up --build -d
```

- Aplicación: http://localhost:8080
- Manual de usuario: http://localhost:8080/manual/
- API y su documentación: http://localhost:8000/docs (también en http://localhost:8080/docs)

| Comando | Para qué |
|---|---|
| `docker compose up -d` | Iniciar (sin recompilar) |
| `docker compose up --build -d` | Iniciar recompilando tras cambiar el código |
| `docker compose logs -f` | Ver los registros |
| `docker compose down` | Detener |

Se levantan dos contenedores: `back` (Python + FastAPI) y `front` (Vue compilado y servido con nginx, que reenvía `/api` al back).

## Instalar sin Docker (una sola vez)

```bash
python3 -m venv .venv
.venv/bin/pip install -r simulador2/requirements.txt
cd front && npm install && npm run build && cd ..
```

## Usar

```bash
.venv/bin/python simulador2/api.py      # abrir http://localhost:8000
```

La aplicación tiene dos experiencias que comparten la misma configuración y los mismos resultados del motor:

**Administración** (http://localhost:8080), pestaña *Simulación*:

1. **Llegadas:** jornadas, horarios, hora del primer conteo y personas contadas en cada intervalo. La prueba chi-cuadrada de Poisson se revisa mientras se escribe. Debajo, la tendencia: promedio móvil simple y ponderado (ventana configurable, 3 por defecto) y la categoría de cada franja (pico, valle o normal) según una prueba χ² de homogeneidad.
2. **Servicio:** tiempo medio de atención por jornada y número de cajas.
3. **Prueba KS:** corridas, nivel de significancia α, límite de intentos, semilla y validación con Ciw. Sin semilla, se toma el reloj del computador en milisegundos.
4. **Resultados:** semilla usada (para repetir la simulación), veredicto contra las metas, cajas necesarias, banco animado, gráficas, tablas y pruebas.

Pestaña *Establecimiento*: días y horarios de atención, excepciones (festivos, cierres, aperturas extraordinarias), zona horaria, largo de las franjas y aumento de quincena. **Guardar y publicar** simula cada horario distinto en día regular y en quincena con los parámetros de los pasos 1 a 3 y guarda las estimaciones. También compara dos fechas con histogramas.

**Cliente** (http://localhost:8080/#/visita): elige una fecha en el calendario y ve si se atiende, si es quincena, la espera estimada en la fila por franja horaria y la franja recomendada. Si la fecha está cerrada, muestra la próxima fecha con atención.

La configuración y las estimaciones se guardan en `simulador2/datos/` (en Docker, en el volumen `datos`).

El botón **Manual de usuario** abre el manual integral en `/manual/`, con su índice, capturas y anexos. El build prepara esta página a partir de [`docs/auditoria/`](docs/auditoria/). Para compartirla en un servidor, usa el dominio del simulador seguido de `/manual/`. Si se ejecuta con FastAPI sin Docker, la ruta local es http://localhost:8000/manual/.

El ícono de herramienta abre los ajustes: tema, letra, estilo de las gráficas, metas (resultados óptimos), qué variables se piden y qué resultados se muestran. Se guardan en el navegador.

La documentación de la API queda en http://localhost:8000/docs.

## Desarrollar

```bash
.venv/bin/python simulador2/api.py              # terminal 1: API en el puerto 8000
cd front && npm run dev                         # terminal 2: front con recarga en vivo (usa la API del puerto 8000)
cd simulador2 && ../.venv/bin/python -m unittest  # pruebas del back
```
