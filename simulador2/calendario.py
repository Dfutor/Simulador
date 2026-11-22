"""Reglas del calendario del establecimiento: días de atención, excepciones, quincenas y franjas horarias.

Es la única fuente de estas reglas. La API, la simulación por fechas y la vista del cliente las usan;
el front solo muestra lo que devuelven.

La configuración es un diccionario (JSON):
    horarioSemanal: 7 días, de lunes (0) a domingo (6): {"abierto": bool, "jornadas": [{"inicio", "fin"}]}
    excepciones:    [{"fecha": "AAAA-MM-DD", "motivo": str, "abierto": bool, "jornadas": [...]}]
                    tienen prioridad sobre el horario semanal (festivos, cierres, aperturas extraordinarias)
    zonaHoraria:    nombre IANA, p. ej. "America/Bogota"
"""

import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_A_BUSCAR = 366   # la próxima fecha abierta se busca, como mucho, un año hacia adelante


def aMinutos(hora: str | time) -> int:
    """'08:30' (o '08:30:00') → 510 minutos desde la medianoche."""
    if isinstance(hora, str):
        hora = time.fromisoformat(hora)
    return hora.hour * 60 + hora.minute


def aHora(minutos: float) -> str:
    """510 → '08:30'."""
    minutos = round(minutos)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


# ---------------------------------------------------------------------------
# Quincena
# ---------------------------------------------------------------------------
def esQuincena(fecha: date) -> bool:
    """Días 1 a 4, días 12 a 18 (los tres antes del 15, el 15 y los tres después) y los últimos cuatro del mes."""
    ultimoDia = calendar.monthrange(fecha.year, fecha.month)[1]
    return fecha.day <= 4 or 12 <= fecha.day <= 18 or fecha.day > ultimoDia - 4


def tipoDeDia(fecha: date) -> str:
    return "quincena" if esQuincena(fecha) else "regular"


# ---------------------------------------------------------------------------
# Horarios
# ---------------------------------------------------------------------------
def revisarJornadas(jornadas: list[dict]) -> None:
    """Cada jornada termina después de empezar y no se cruza ni se toca con otra.
    Dos jornadas pegadas (12:00–12:00) deben ser una sola: entre jornadas el banco cierra y se vacía."""
    ordenadas = sorted(jornadas, key=lambda jornada: aMinutos(jornada["inicio"]))
    for jornada in ordenadas:
        if aMinutos(jornada["fin"]) <= aMinutos(jornada["inicio"]):
            raise ValueError(f"La jornada {aHora(aMinutos(jornada['inicio']))}–{aHora(aMinutos(jornada['fin']))} "
                             "debe terminar después de empezar")
    for anterior, siguiente in zip(ordenadas, ordenadas[1:]):
        if aMinutos(siguiente["inicio"]) < aMinutos(anterior["fin"]):
            raise ValueError(f"Las jornadas {aHora(aMinutos(anterior['inicio']))}–{aHora(aMinutos(anterior['fin']))} y "
                             f"{aHora(aMinutos(siguiente['inicio']))}–{aHora(aMinutos(siguiente['fin']))} se superponen")
        if aMinutos(siguiente["inicio"]) == aMinutos(anterior["fin"]):
            raise ValueError(f"Las jornadas que terminan y empiezan a las {aHora(aMinutos(anterior['fin']))} "
                             "están pegadas: únelas en una sola jornada")


def normalizarJornadas(jornadas: list[dict]) -> list[dict]:
    """Ordenadas y con la hora como 'HH:MM'."""
    return [{"inicio": aHora(aMinutos(jornada["inicio"])), "fin": aHora(aMinutos(jornada["fin"]))}
            for jornada in sorted(jornadas, key=lambda jornada: aMinutos(jornada["inicio"]))]


def claveHorario(jornadas: list[dict]) -> str:
    """'08:00-12:00,14:00-16:30': identifica un horario para reutilizar su simulación."""
    return ",".join(f"{jornada['inicio']}-{jornada['fin']}" for jornada in normalizarJornadas(jornadas))


def buscarExcepcion(configuracion: dict, fecha: date) -> dict | None:
    texto = fecha.isoformat()
    return next((excepcion for excepcion in configuracion.get("excepciones", [])
                 if str(excepcion["fecha"]) == texto), None)


def horarioDelDia(configuracion: dict, fecha: date) -> dict:
    """Si la fecha tiene una excepción, manda la excepción; si no, el horario semanal de ese día."""
    excepcion = buscarExcepcion(configuracion, fecha)
    if excepcion is not None:
        origen, motivo = "excepcion", excepcion.get("motivo") or ""
        abierto, jornadas = excepcion["abierto"], excepcion.get("jornadas", [])
    else:
        dia = configuracion["horarioSemanal"][fecha.weekday()]
        origen, motivo = "semanal", ""
        abierto, jornadas = dia["abierto"], dia.get("jornadas", [])
    abierto = bool(abierto and jornadas)
    return {
        "fecha": fecha.isoformat(),
        "diaSemana": DIAS_SEMANA[fecha.weekday()],
        "abierto": abierto,
        "jornadas": normalizarJornadas(jornadas) if abierto else [],
        "origen": origen,
        "motivo": motivo,
        "tipoDia": tipoDeDia(fecha),
    }


def siguienteFechaAbierta(configuracion: dict, fecha: date) -> date | None:
    """La primera fecha DESPUÉS de `fecha` en la que se atiende, según el calendario configurado."""
    for dias in range(1, DIAS_A_BUSCAR + 1):
        candidata = fecha + timedelta(days=dias)
        if horarioDelDia(configuracion, candidata)["abierto"]:
            return candidata
    return None


def diasDelMes(configuracion: dict, anio: int, mes: int) -> list[dict]:
    ultimoDia = calendar.monthrange(anio, mes)[1]
    return [horarioDelDia(configuracion, date(anio, mes, dia)) for dia in range(1, ultimoDia + 1)]


def horariosDistintos(configuracion: dict) -> list[list[dict]]:
    """Todos los horarios con los que se puede abrir (semanales y excepciones), sin repetir."""
    candidatos = [dia["jornadas"] for dia in configuracion["horarioSemanal"] if dia["abierto"] and dia["jornadas"]]
    candidatos += [excepcion["jornadas"] for excepcion in configuracion.get("excepciones", [])
                   if excepcion["abierto"] and excepcion.get("jornadas")]
    porClave = {claveHorario(jornadas): normalizarJornadas(jornadas) for jornadas in candidatos}
    return [porClave[clave] for clave in sorted(porClave)]


def hoy(configuracion: dict) -> date:
    """La fecha de hoy en la zona horaria del establecimiento (no la del servidor ni la del cliente)."""
    return datetime.now(ZoneInfo(configuracion["zonaHoraria"])).date()


# ---------------------------------------------------------------------------
# Franjas horarias de análisis
# ---------------------------------------------------------------------------
def franjasDeJornada(inicio: int, fin: int, minutosPorFranja: int) -> list[tuple[int, int]]:
    """Corta [inicio, fin) en franjas alineadas con el reloj (minutos desde la medianoche).
    08:00–12:00 en franjas de 60 → 08–09, 09–10, 10–11, 11–12;  14:00–16:30 → 14–15, 15–16, 16–16:30."""
    franjas = []
    desde = inicio
    while desde < fin:
        hasta = min(fin, (desde // minutosPorFranja + 1) * minutosPorFranja)
        franjas.append((desde, hasta))
        desde = hasta
    return franjas
