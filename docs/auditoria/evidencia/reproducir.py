"""Reproduce cálculos de la auditoría del banco. Ejecutar con la .venv del proyecto."""
import argparse
import contextlib
import csv
import hashlib
import io
import json
import platform
import random
import statistics
import subprocess
import sys
import warnings
from datetime import date
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "simulador2"))

import ciw
import scipy
from numpy.random import default_rng
from scipy.stats import chi2, kstwo, kstest
from starlette.responses import JSONResponse
from analisisLlegadas import analizarLlegadas, clasificarFranjas
from api import CONTEOS_MANANA, CONTEOS_TARDE, Entrada, Establecimiento
from iniciador import (JornadaSinClientes, armarJornadas, atender, buscarCajasNecesarias, modelo,
                       simular, validarUniformidadPruebaKS)
from medidas import calcularMedidas, promedioConIntervalo
from planificacion import compararDias, consultarFecha, publicar
from pruebaKS import valorCriticoKS
from pruebaPoisson import pruebaChiCuadradaPoisson
from validacionCiw import compararMedida, simularJornadaConCiw


def resumen(datos):
    return [{k: j["resumen"][k]["promedio"] for k in ("Wq", "W", "L", "Lq", "utilizacion", "ultimaSalida", "clientesAtendidos")}
            | {"WqIC": j["resumen"]["Wq"], "Poisson": j["poisson"]}
            for j in datos["jornadas"]]


def error_de(funcion):
    try:
        salida = funcion()
    except Exception as error:
        return {"excepcion": type(error).__name__, "mensaje": str(error)}
    return {"salida": salida}


def traza_manual():
    clientes = [{"cliente": i, "momentoLlegada": a, "prioritario": i == 3}
                for i, a in enumerate((0, 1, 2, 3), 1)]
    servicios = iter((4, 2, 3, 1))
    atender(clientes, 1, lambda: (0.0, next(servicios)))
    medidas = calcularMedidas(clientes, 1, 5)
    assert medidas["Wq"] == 3.25 and medidas["L"] == 2.3 and medidas["Lq"] == 1.3
    return {"clientes": clientes, "medidas": medidas}


def traza_sembrada():
    entrada = {"tiempoEntreTomasDeDatos": 2, "proporcionVanACaja": 1, "factorLlegadas": 1,
               "distribucionServicio": "uniforme", "jornadas": [{"inicio": "08:00", "fin": "08:08",
               "conteos": [1, 1, 1, 1], "servicioMinimo": 2, "servicioMaximo": 3}]}
    semilla = 1
    random.seed(semilla)
    clientes = modelo(armarJornadas(entrada), 1, 0.25)
    medidas = calcularMedidas(clientes, 1, 8)
    assert [c["cliente"] for c in sorted(clientes, key=lambda c: c["inicioServicio"])] == [1, 2, 3, 5, 4]
    assert abs(medidas["Wq"] - 1.2434858813970833) < 1e-10
    assert abs(medidas["Lq"] - len(clientes) / medidas["tiempoObservado"] * medidas["Wq"]) < 1e-10
    return {"semilla": semilla, "entrada": entrada, "clientes": clientes, "medidas": medidas}


def experimento_ks(entrada, n=900):
    """Compara las mismas réplicas crudas antes y después del filtro existente."""
    estudio = {}
    configuraciones = [
        ("manana", entrada["jornadas"][0]),
        ("cierre_5_min", {**entrada["jornadas"][0], "fin": "08:05:00"}),
    ]
    for nombre, datos in configuraciones:
        random.seed(7321)
        jornadas = armarJornadas({**entrada, "jornadas": [datos]})
        vacias = llegadas = servicios = ambos = 0
        brutas = []
        filtradas = []
        duracion = 240 if nombre == "manana" else 5
        for _ in range(n):
            try:
                clientes = modelo(jornadas, 5, 0.05)
            except JornadaSinClientes:
                vacias += 1
                continue
            ks = validarUniformidadPruebaKS(clientes, 0.05)
            llegadas += not ks["llegada"]["pasa"]
            servicios += not ks["servicio"]["pasa"]
            ambos += not ks["pasa"]
            wq = calcularMedidas(clientes, 5, duracion)["Wq"]
            brutas.append((len(clientes), wq))
            if ks["pasa"]:
                filtradas.append((len(clientes), wq))

        def medias(pares):
            return dict(zip(("n", "Wq"), map(statistics.mean, zip(*pares))))

        estudio[nombre] = {"intentos": n, "vacias": vacias, "rechazo_llegada": llegadas,
                            "rechazo_servicio": servicios, "rechazo_union": ambos,
                            "crudas": medias(brutas), "filtradas": medias(filtradas)}
    return estudio


def ensayos():
    entrada = Entrada(semilla=12345).model_dump(mode="json")
    config = Establecimiento(entrada=Entrada(semilla=12345)).model_dump(mode="json")
    normal = simular(entrada)
    quincena = simular({**entrada, "factorLlegadas": 1.3})
    reproducida = simular(entrada)
    assert normal == reproducida
    ciw_base = simular({**entrada, "compararConCiw": True})
    analisis = analizarLlegadas(entrada, 60, 3)
    publi = publicar(config)
    fecha_regular = date(2026, 12, 7)
    fecha_quincena = date(2026, 12, 15)
    fechas = {
        str(fecha): consultarFecha(config, publi, fecha)
        for fecha in (date(2026, 12, 5), fecha_regular, fecha_quincena)
    }
    comparacion = compararDias(config, publi, [fecha_regular, fecha_quincena], "todas")
    iguales = compararDias(config, publi, [fecha_regular, date(2026, 12, 9)], "todas")
    assert iguales["series"][0]["relativas"] == iguales["series"][1]["relativas"]
    for fila in [*comparacion["series"], comparacion["observado"]]:
        assert abs(sum(fila["relativas"]) - 1) < 1e-12

    sensibilidad = {}
    for maximo in (25, 15, 10, 8, 7, 6):
        modificada = {**entrada, "jornadas": [dict(j, servicioMaximo=maximo) for j in entrada["jornadas"]]}
        sensibilidad[str(maximo)] = resumen(simular(modificada))
    cajas = {nombre: buscarCajasNecesarias({**entrada, "factorLlegadas": factor}, 10)
             for nombre, factor in (("regular", 1), ("quincena", 1.3))}

    criticos = [
        {"n": n, "codigo": valorCriticoKS(n, 0.05), "exacto": float(kstwo.ppf(0.95, n))}
        for n in (1, 4, 10, 20, 35, 36, 100, 101)
    ]
    corta = [0.14, 0.30, 0.44, 0.80]
    ks = kstest(corta, "uniform", method="exact")
    poisson = {nombre: pruebaChiCuadradaPoisson(c, 0.05)
               for nombre, c in (("manana", CONTEOS_MANANA), ("tarde", CONTEOS_TARDE))}
    for nombre, conteos in (("manana", CONTEOS_MANANA), ("tarde", CONTEOS_TARDE)):
        prueba = poisson[nombre]
        prueba["p_aproximado_auditoria"] = float(chi2.sf(prueba["estadistico"], prueba["gradosLibertad"]))
        muestras = default_rng(12345).poisson(prueba["media"], (999, len(conteos)))
        exceden = sum(pruebaChiCuadradaPoisson(muestra.tolist(), 0.05)["estadistico"] >= prueba["estadistico"]
                      for muestra in muestras)
        prueba["bootstrap_auditoria"] = {"semilla": 12345, "repeticiones": 999, "exceden": int(exceden),
                                         "p": (1 + int(exceden)) / 1000}

    config_cero = {**config, "modeloLlegadas": "franja", "entrada": {**entrada, "numeroCorridas": 2,
        "jornadas": [dict(entrada["jornadas"][0], inicio="08:00", fin="10:00", inicioConteos="08:00",
                          conteos=[0] * 12 + [10] * 12)]}}
    config_cero = Establecimiento.model_validate(config_cero).model_dump(mode="json")
    clasif_cero = clasificarFranjas(config_cero["entrada"]["jornadas"][0], 5, 60, 0.05)
    bordes = clasificarFranjas(dict(entrada["jornadas"][0], inicio="08:00", fin="10:00",
                                    inicioConteos="08:03", conteos=[5] * 22), 5, 60, 0.05)
    random.seed(12345)
    ciw_prioridad_total = error_de(lambda: simularJornadaConCiw(armarJornadas(entrada)[1], 240, 5, 1.0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        nulo = compararMedida([0.0, 0.0], [0.0, 0.0], 0.05)
    conf = promedioConIntervalo([10, 12, 14])
    assert abs(conf["promedio"] - 12) < 1e-12

    aleatorio = random.Random(12345)
    deps = {paquete: version(paquete)
            for paquete in ("fastapi", "starlette", "pydantic", "scipy", "numpy", "ciw", "uvicorn")}
    with patch("iniciador.reloj.time_ns", return_value=1_797_000_000_123_456_789):
        from iniciador import resolverSemilla
        semilla_reloj = resolverSemilla(None)
    return {
        "entorno": {"python": platform.python_version(), "plataforma": platform.platform(), "dependencias": deps},
        "semilla": 12345, "uniformes": [aleatorio.random() for _ in range(10)], "semilla_reloj_controlado": semilla_reloj,
        "entrada": entrada, "normal": resumen(normal), "quincena": resumen(quincena),
        "primer_ks": normal["ks"][0], "rechazos": [len(normal["rechazos"]), len(quincena["rechazos"])],
        "poisson": poisson, "analisis": analisis, "visitas": fechas, "comparacion": comparacion,
        "comparacion_mismo_escenario_igual": True, "publicacion": {k: publi[k] for k in ("huella", "versionModelo", "semilla")},
        "manual": traza_manual(), "traza_sembrada": traza_sembrada(), "ic_ejemplo": conf,
        "ks_sintetico": {"muestra": corta, "D": float(ks.statistic), "p_exacto": float(ks.pvalue)},
        "ks_criticos": criticos, "experimento_ks": experimento_ks(entrada),
        "sensibilidad": sensibilidad, "cajas": cajas,
        "ciw": [j["ciw"] for j in ciw_base["jornadas"]],
        "casos_adversos": {
            "franja_cero": {"franjas": clasif_cero["franjas"], **error_de(lambda: publicar(config_cero))},
            "ciw_prioridad_total": ciw_prioridad_total, "welch_constante": {"p": str(nulo["valorP"]), "coinciden": nulo["coinciden"]},
            "serializar_welch_constante": error_de(lambda: JSONResponse(nulo).body.decode()),
            "poisson_con_negativo": pruebaChiCuadradaPoisson([-1, 3], 0.05),
            "conteo_que_cruza_borde": [i for i in bordes["ubicados"] if i[0] < 540 < i[1]],
        },
    }, normal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", type=Path, required=True, help="Carpeta de resultados, preferiblemente nueva")
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    bitacora = io.StringIO()
    with contextlib.redirect_stdout(bitacora):
        datos, base = ensayos()
    (args.salida / "corridas.log").write_text(bitacora.getvalue(), encoding="utf-8")
    (args.salida / "resultados.json").write_text(json.dumps(datos, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                                               encoding="utf-8")
    campos = list(base["jornadas"][0]["corrida1"]["clientes"][0])
    with (args.salida / "traza-semilla-12345.csv").open("w", newline="", encoding="utf-8") as archivo:
        csv_writer = csv.DictWriter(archivo, fieldnames=campos)
        csv_writer.writeheader()
        for jornada in base["jornadas"]:
            csv_writer.writerows(jornada["corrida1"]["clientes"])
    fuentes = [ruta for ruta in (ROOT / "front/src").rglob("*") if ruta.is_file()]
    fuentes += list((ROOT / "simulador2").glob("*.py"))
    fuentes += [ROOT / p for p in ("simulador2/requirements.txt", "README.md", "simulador2/README.md",
                                  "Levantamiento_de_requrimientos_Cap1COSBUS.md", "front/package-lock.json",
                                  "docker-compose.yml", "By Raúl Coss Bu - Simulación - libgen.li.pdf",
                                  "03_simulacion_monte_carlo.pdf")]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
    huellas = "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}" for p in sorted(fuentes))
    (args.salida / "fuentes.sha256").write_text(f"# HEAD de referencia {revision}. Se auditó el árbol de trabajo.\n{huellas}\n",
                                             encoding="utf-8")
    print(f"Evidencia calculada en {args.salida}")


if __name__ == "__main__":
    main()
