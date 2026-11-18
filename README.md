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

1. **Llegadas:** jornadas, horarios y personas contadas en cada intervalo. La prueba chi-cuadrada de Poisson se revisa mientras se escribe.
2. **Servicio:** tiempo medio de atención por jornada y número de cajas.
3. **Prueba KS:** corridas, nivel de significancia α, límite de intentos, semilla y validación con Ciw.
4. **Resultados:** veredicto contra las metas, cajas necesarias, banco animado, gráficas, tablas y pruebas.

El ícono de herramienta abre los ajustes: tema, letra, estilo de las gráficas, metas (resultados óptimos), qué variables se piden y qué resultados se muestran. Se guardan en el navegador.

La documentación de la API queda en http://localhost:8000/docs.

## Desarrollar

```bash
.venv/bin/python simulador2/api.py              # terminal 1: API en el puerto 8000
cd front && npm run dev                         # terminal 2: front con recarga en vivo (usa la API del puerto 8000)
cd simulador2 && ../.venv/bin/python -m unittest  # pruebas del back
```
