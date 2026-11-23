"""Pruebas del calendario, las quincenas, los promedios móviles, las categorías, la semilla
y las estimaciones de «Planifica tu visita».

Correr desde la carpeta del proyecto:
    python3 -m unittest discover -s simulador2 -v
"""

import random
import tempfile
import time as reloj
import unittest
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

import analisisLlegadas
import calendario
import iniciador
import planificacion

# 6 conteos estimados (9:10–9:40, Poisson con la media observada) + 24 observados (9:40–11:40)
CONTEOS_MANANA = [7, 10, 4, 5, 9, 6, 7, 9, 8, 6, 4, 7, 5, 11, 8, 2, 4, 6, 3, 1, 3, 9, 6, 4, 8, 7, 2, 3, 4, 3]
CONTEOS_TARDE = [3, 3, 2, 3, 3, 7, 9, 4, 7, 6, 4, 4, 6, 3, 7, 4, 8, 5, 3, 5, 9, 3, 7, 6, 4, 2, 3, 3, 2, 0]
HABITUAL = [{"inicio": "08:00", "fin": "12:00"}, {"inicio": "14:00", "fin": "16:30"}]


def configuracionDePrueba(**cambios) -> dict:
    """Lunes a viernes con el horario habitual; sábado y domingo cerrados."""
    configuracion = {
        "zonaHoraria": "America/Bogota",
        "horarioSemanal": [{"abierto": True, "jornadas": HABITUAL} for _ in range(5)]
                          + [{"abierto": False, "jornadas": [{"inicio": "08:00", "fin": "12:00"}]},
                             {"abierto": False, "jornadas": []}],
        "excepciones": [],
        "factorQuincena": 1.3,
        "minutosPorFranja": 60,
        "modeloLlegadas": "jornada",
        "entrada": {
            "numeroServidores": 5, "distribucionServicio": "uniforme", "tiempoEntreTomasDeDatos": 5,
            "proporcionVanACaja": 1, "proporcionPrioritarios": 0.05, "factorLlegadas": 1, "numeroCorridas": 5,
            "alfa": 0.05, "limiteIntentos": 10, "semilla": 12345, "compararConCiw": False,
            "jornadas": [
                {"inicio": "08:00", "fin": "12:00", "conteos": CONTEOS_MANANA, "inicioConteos": "09:10",
                 "minutosPorCliente": 6, "servicioMinimo": 1, "servicioMaximo": 11},
                {"inicio": "14:00", "fin": "16:30", "conteos": CONTEOS_TARDE, "inicioConteos": "14:00",
                 "minutosPorCliente": 6, "servicioMinimo": 1, "servicioMaximo": 11},
            ],
        },
    }
    configuracion.update(cambios)
    return configuracion


# ---------------------------------------------------------------------------
# 1. Quincenas
# ---------------------------------------------------------------------------
class PruebasQuincena(unittest.TestCase):

    def diasDeQuincena(self, anio, mes):
        return [dia for dia in range(1, 32) if self.existe(anio, mes, dia) and calendario.esQuincena(date(anio, mes, dia))]

    @staticmethod
    def existe(anio, mes, dia):
        try:
            date(anio, mes, dia)
            return True
        except ValueError:
            return False

    def test_diciembre(self):
        self.assertEqual(self.diasDeQuincena(2026, 12), [1, 2, 3, 4, 12, 13, 14, 15, 16, 17, 18, 28, 29, 30, 31])

    def test_mesDe30Dias(self):
        self.assertEqual(self.diasDeQuincena(2026, 11)[-4:], [27, 28, 29, 30])

    def test_febreroNormalYBisiesto(self):
        self.assertEqual(self.diasDeQuincena(2026, 2)[-4:], [25, 26, 27, 28])
        self.assertEqual(self.diasDeQuincena(2028, 2)[-4:], [26, 27, 28, 29])
        self.assertFalse(calendario.esQuincena(date(2028, 2, 25)))

    def test_bordes(self):
        for dia, esperado in [(4, True), (5, False), (11, False), (12, True), (18, True), (19, False)]:
            with self.subTest(dia=dia):
                self.assertEqual(calendario.esQuincena(date(2026, 12, dia)), esperado)

    def test_tipoDeDia(self):
        self.assertEqual(calendario.tipoDeDia(date(2026, 12, 15)), "quincena")
        self.assertEqual(calendario.tipoDeDia(date(2026, 12, 7)), "regular")


# ---------------------------------------------------------------------------
# 2. Horario semanal, excepciones y próxima fecha abierta
# ---------------------------------------------------------------------------
class PruebasCalendario(unittest.TestCase):

    def setUp(self):
        self.configuracion = configuracionDePrueba()

    def test_diaLaboralYDiaCerrado(self):
        lunes = calendario.horarioDelDia(self.configuracion, date(2026, 12, 7))
        domingo = calendario.horarioDelDia(self.configuracion, date(2026, 12, 6))
        self.assertTrue(lunes["abierto"])
        self.assertEqual(lunes["diaSemana"], "lunes")
        self.assertEqual(lunes["jornadas"], HABITUAL)
        self.assertFalse(domingo["abierto"])
        self.assertEqual(domingo["jornadas"], [])

    def test_activarUnDiaCambiaLaDisponibilidad(self):
        sabado = date(2026, 12, 5)
        self.assertFalse(calendario.horarioDelDia(self.configuracion, sabado)["abierto"])
        self.configuracion["horarioSemanal"][5]["abierto"] = True
        self.assertTrue(calendario.horarioDelDia(self.configuracion, sabado)["abierto"])

    def test_cierreExcepcionalTienePrioridad(self):
        self.configuracion["excepciones"] = [{"fecha": "2026-12-08", "motivo": "Festivo", "abierto": False, "jornadas": []}]
        martes = calendario.horarioDelDia(self.configuracion, date(2026, 12, 8))
        self.assertFalse(martes["abierto"])
        self.assertEqual((martes["origen"], martes["motivo"]), ("excepcion", "Festivo"))

    def test_aperturaExtraordinaria(self):
        self.configuracion["excepciones"] = [{"fecha": "2026-12-06", "motivo": "Jornada especial", "abierto": True,
                                              "jornadas": [{"inicio": "09:00", "fin": "13:00"}]}]
        domingo = calendario.horarioDelDia(self.configuracion, date(2026, 12, 6))
        self.assertTrue(domingo["abierto"])
        self.assertEqual(domingo["jornadas"], [{"inicio": "09:00", "fin": "13:00"}])

    def test_siguienteFechaAbiertaSaltaFinDeSemanaYFestivo(self):
        sabado = date(2026, 12, 5)
        self.assertEqual(calendario.siguienteFechaAbierta(self.configuracion, sabado), date(2026, 12, 7))
        self.configuracion["excepciones"] = [{"fecha": "2026-12-07", "motivo": "Festivo", "abierto": False, "jornadas": []}]
        siguiente = calendario.siguienteFechaAbierta(self.configuracion, sabado)
        self.assertEqual(siguiente, date(2026, 12, 8))
        self.assertTrue(calendario.horarioDelDia(self.configuracion, siguiente)["abierto"])

    def test_sinNingunDiaAbiertoNoHaySiguiente(self):
        for dia in self.configuracion["horarioSemanal"]:
            dia["abierto"] = False
        self.assertIsNone(calendario.siguienteFechaAbierta(self.configuracion, date(2026, 12, 5)))

    def test_jornadasQueSeSuperponenOSeTocan(self):
        calendario.revisarJornadas(HABITUAL)
        casos = [
            ([{"inicio": "08:00", "fin": "12:00"}, {"inicio": "11:00", "fin": "13:00"}], "se superponen"),
            ([{"inicio": "08:00", "fin": "12:00"}, {"inicio": "12:00", "fin": "13:00"}], "pegadas"),
            ([{"inicio": "12:00", "fin": "08:00"}], "terminar después"),
        ]
        for jornadas, mensaje in casos:
            with self.subTest(mensaje=mensaje), self.assertRaisesRegex(ValueError, mensaje):
                calendario.revisarJornadas(jornadas)

    def test_horariosDistintosNoSeRepiten(self):
        self.configuracion["excepciones"] = [
            {"fecha": "2026-12-24", "motivo": "", "abierto": True, "jornadas": [{"inicio": "08:00", "fin": "11:00"}]},
            {"fecha": "2026-12-31", "motivo": "", "abierto": True, "jornadas": [{"inicio": "08:00", "fin": "11:00"}]},
        ]
        self.assertEqual(calendario.horariosDistintos(self.configuracion),
                         [[{"inicio": "08:00", "fin": "11:00"}], HABITUAL])

    def test_diasDelMes(self):
        dias = calendario.diasDelMes(self.configuracion, 2028, 2)
        self.assertEqual(len(dias), 29)
        self.assertEqual(sum(dia["abierto"] for dia in dias), 21)


class PruebasFranjas(unittest.TestCase):

    def test_franjasAlineadasConElReloj(self):
        self.assertEqual(calendario.franjasDeJornada(480, 720, 60), [(480, 540), (540, 600), (600, 660), (660, 720)])
        # 14:00–16:30: la última franja es más corta y respeta el cierre
        self.assertEqual(calendario.franjasDeJornada(840, 990, 60), [(840, 900), (900, 960), (960, 990)])
        # 09:30–11:00 en franjas de 60: la primera va hasta la hora en punto
        self.assertEqual(calendario.franjasDeJornada(570, 660, 60), [(570, 600), (600, 660)])


# ---------------------------------------------------------------------------
# 3. Promedios móviles y categorías
# ---------------------------------------------------------------------------
class PruebasPromediosMoviles(unittest.TestCase):

    def test_simpleCalculadoAMano(self):
        # (2+4+6)/3 = 4,  (4+6+8)/3 = 6
        self.assertEqual(analisisLlegadas.promedioMovilSimple([2, 4, 6, 8], 3), [None, None, 4, 6])

    def test_ponderadoCalculadoAMano(self):
        # (1·2 + 2·4 + 3·6)/6 = 28/6,  (1·4 + 2·6 + 3·8)/6 = 40/6
        resultado = analisisLlegadas.promedioMovilPonderado([2, 4, 6, 8], 3)
        self.assertEqual(resultado[:2], [None, None])
        self.assertAlmostEqual(resultado[2], 28 / 6)
        self.assertAlmostEqual(resultado[3], 40 / 6)

    def test_ventanaConfigurable(self):
        self.assertEqual(analisisLlegadas.promedioMovilSimple([1, 3, 5], 2), [None, 2, 4])
        self.assertEqual(analisisLlegadas.promedioMovilSimple([1, 3, 5], 4), [None, None, None])

    def test_conVentanaDeUnoElPonderadoEsElDato(self):
        self.assertEqual(analisisLlegadas.promedioMovilPonderado([3, 1, 4], 1), [3, 1, 4])

    def test_ordenTemporalYSinMezclarJornadas(self):
        resultado = analisisLlegadas.analizarLlegadas(configuracionDePrueba()["entrada"], 60, 3)
        manana, tarde = resultado["jornadas"]
        self.assertEqual([intervalo["desde"] for intervalo in manana["intervalos"][:3]], ["09:10", "09:15", "09:20"])
        self.assertEqual(manana["intervalos"][-1]["hasta"], "11:40")
        # La tarde empieza su propia ventana: no arrastra conteos de la mañana
        self.assertEqual([intervalo["promedioSimple"] for intervalo in tarde["intervalos"][:2]], [None, None])
        self.assertAlmostEqual(tarde["intervalos"][2]["promedioSimple"], (3 + 3 + 2) / 3)

    def test_conteosQueNoCabenEnLaJornada(self):
        jornada = {"inicio": "08:00", "fin": "09:00", "conteos": [1] * 13, "inicioConteos": None}
        with self.assertRaisesRegex(ValueError, "no caben"):
            analisisLlegadas.ubicarConteos(jornada, 5)


class PruebasCategorias(unittest.TestCase):

    def test_datosDelDocumento(self):
        entrada = configuracionDePrueba()["entrada"]
        manana = analisisLlegadas.clasificarFranjas(entrada["jornadas"][0], 5, 60, 0.05)
        tarde = analisisLlegadas.clasificarFranjas(entrada["jornadas"][1], 5, 60, 0.05)
        # Mañana: X² = 5,49 con 2 g.l. (p = 0,064) → no hay diferencia; 08–09 no se observó
        self.assertAlmostEqual(manana["homogeneidad"]["estadistico"], 5.487, places=3)
        self.assertFalse(manana["homogeneidad"]["rechaza"])
        self.assertEqual([franja["categoria"] for franja in manana["franjas"]], ["sinDatos", "normal", "normal", "normal"])
        self.assertAlmostEqual(manana["tasaNormal"], 171 / 30)
        # Tarde: X² = 8,94 (p = 0,011) → 16:00–16:30 es valle (z = −2,50 < −2,39 con Bonferroni)
        self.assertTrue(tarde["homogeneidad"]["rechaza"])
        self.assertEqual([franja["categoria"] for franja in tarde["franjas"]], ["normal", "normal", "valle"])
        self.assertAlmostEqual(tarde["franjas"][2]["tasa"], 14 / 6)
        self.assertAlmostEqual(tarde["tasaNormal"], 121 / 24)

    def test_valleNormalYPicoEvidentes(self):
        # Media 5: la franja de 2 queda muy por debajo (z = −4,6), la de 8 muy por encima (z = +4,6)
        jornada = {"inicio": "08:00", "fin": "11:00", "conteos": [2] * 12 + [5] * 12 + [8] * 12, "inicioConteos": None}
        clasificacion = analisisLlegadas.clasificarFranjas(jornada, 5, 60, 0.05)
        self.assertEqual([franja["categoria"] for franja in clasificacion["franjas"]], ["valle", "normal", "pico"])
        self.assertEqual([franja["tasa"] for franja in clasificacion["franjas"]], [2, 5, 8])

    def test_unaFranjaAltaDejaALasDemasPorDebajoDeLaMedia(self):
        # Se compara contra la media del día: con [2, 12, 2] la media es 5,3 y las franjas de 2 son valle
        jornada = {"inicio": "08:00", "fin": "11:00", "conteos": [2] * 12 + [12] * 12 + [2] * 12, "inicioConteos": None}
        franjas = analisisLlegadas.clasificarFranjas(jornada, 5, 60, 0.05)["franjas"]
        self.assertEqual([franja["categoria"] for franja in franjas], ["valle", "pico", "valle"])

    def test_franjaDeQuincenaConservaSuCategoria(self):
        # El tipo de día solo escala la tasa; la categoría de la franja no cambia
        configuracion = configuracionDePrueba()
        perfil = analisisLlegadas.perfilDeLlegadas(configuracion["entrada"], 60)
        regular = planificacion.jornadasDelEscenario(configuracion, HABITUAL, "regular", perfil)
        quincena = planificacion.jornadasDelEscenario(configuracion, HABITUAL, "quincena", perfil)
        for numero in (1, 2):
            self.assertEqual([franja["categoria"] for franja in regular[numero]["franjas"]],
                             [franja["categoria"] for franja in quincena[numero]["franjas"]])
            self.assertAlmostEqual(quincena[numero]["tasaLlegada"], regular[numero]["tasaLlegada"] * 1.3)


# ---------------------------------------------------------------------------
# 4. Semilla
# ---------------------------------------------------------------------------
class PruebasSemilla(unittest.TestCase):

    def entrada(self, semilla):
        entrada = configuracionDePrueba()["entrada"]
        entrada.update(semilla=semilla, numeroCorridas=3)
        return entrada

    def test_sinSemillaSeTomaElReloj(self):
        antes = reloj.time_ns() // 1_000_000
        with patch("builtins.print"):
            resultado = iniciador.simular(self.entrada(None))
        despues = reloj.time_ns() // 1_000_000
        self.assertTrue(antes <= resultado["semilla"] <= despues)
        self.assertFalse(resultado["semillaManual"])

    def test_laSemillaManualTienePrioridad(self):
        with patch("builtins.print"):
            resultado = iniciador.simular(self.entrada(777))
        self.assertEqual(resultado["semilla"], 777)
        self.assertTrue(resultado["semillaManual"])

    def test_laSemillaUsadaReproduceLaSimulacion(self):
        with patch("builtins.print"):
            primera = iniciador.simular(self.entrada(None))
            repetida = iniciador.simular(self.entrada(primera["semilla"]))
        self.assertEqual([jornada["medidasPorCorrida"] for jornada in primera["jornadas"]],
                         [jornada["medidasPorCorrida"] for jornada in repetida["jornadas"]])

    def test_cajasNecesariasDevuelveLaSemilla(self):
        entrada = self.entrada(5)
        entrada["jornadas"] = entrada["jornadas"][:1]
        entrada["jornadas"][0].update(minutosPorCliente=1)
        entrada["distribucionServicio"] = "exponencial"
        with patch("builtins.print"):
            self.assertEqual(iniciador.buscarCajasNecesarias(entrada, 30)["semilla"], 5)


# ---------------------------------------------------------------------------
# 5. Llegadas por tramos y simulación por franjas
# ---------------------------------------------------------------------------
class PruebasLlegadasPorTramos(unittest.TestCase):

    def test_unSoloTramoEsElGeneradorOriginal(self):
        jornadas = {1: {"inicio": time(8, 0), "fin": time(12, 0), "tiempoEntreTomasDeDatos": 5,
                        "tasaLlegada": 5.0, "tasaServicio": 1.0}}
        random.seed(3)
        original = iniciador.modelo(jornadas, 3)
        jornadas[1]["tramos"] = [[0, 240, 5.0]]
        random.seed(3)
        conTramo = iniciador.modelo(jornadas, 3)
        self.assertEqual(original, conTramo)

    def test_cadaTramoLlegaASuRitmo(self):
        # 60 min a 2 por minuto y 60 min a 0,5 por minuto: en promedio 120 y 30 llegadas
        random.seed(9)
        primeras, segundas = [], []
        for _ in range(400):
            llegadas = iniciador.generarLlegadasPorTramos(1, [(0, 60, 0.5), (60, 120, 2.0)], 0)
            primeras.append(sum(1 for llegada in llegadas if llegada["momentoLlegada"] < 60))
            segundas.append(sum(1 for llegada in llegadas if llegada["momentoLlegada"] >= 60))
            self.assertTrue(all(0 < llegada["momentoLlegada"] <= 120 for llegada in llegadas))
        self.assertAlmostEqual(sum(primeras) / 400, 120, delta=3)
        self.assertAlmostEqual(sum(segundas) / 400, 30, delta=1.5)

    def test_unirTramosIguales(self):
        self.assertEqual(planificacion.unirTramosIguales([[0, 60, 5], [60, 120, 5], [120, 150, 2]]),
                         [[0, 120, 5], [120, 150, 2]])

    def test_tramoSinLlegadas(self):
        # Una franja con tasa cero no recibe a nadie, pero la jornada sigue (antes: división por cero)
        random.seed(4)
        llegadas = iniciador.generarLlegadasPorTramos(1, [(0, 60, None), (60, 120, 1.0)], 0)
        self.assertTrue(llegadas)
        self.assertTrue(all(60 < llegada["momentoLlegada"] <= 120 for llegada in llegadas))
        jornadas = {1: {"inicio": time(8, 0), "fin": time(10, 0), "tiempoEntreTomasDeDatos": 5,
                        "tasaLlegada": 5.0, "tasaServicio": 1.0, "tramos": [[0, 60, 0.0], [60, 120, 10.0]]}}
        clientes = iniciador.modelo(jornadas, 3)
        self.assertTrue(all(cliente["momentoLlegada"] > 60 for cliente in clientes))

    def test_publicarConUnaFranjaVacia(self):
        # Una hora sin nadie y otra llena, con tasa por franja: la hora vacía queda como valle con tasa cero
        configuracion = configuracionDePrueba(modeloLlegadas="franja")
        configuracion["entrada"] = {**configuracion["entrada"], "numeroCorridas": 2, "jornadas": [
            {"inicio": "08:00", "fin": "10:00", "conteos": [0] * 12 + [10] * 12, "inicioConteos": "08:00",
             "minutosPorCliente": 6, "servicioMinimo": 1, "servicioMaximo": 11}]}
        with patch("builtins.print"):
            estimaciones = planificacion.publicar(configuracion)
        franjas = estimaciones["escenarios"]["regular|08:00-12:00,14:00-16:30"]["jornadas"][0]["franjas"]
        self.assertEqual(franjas[0]["categoria"], "valle")
        self.assertEqual(franjas[0]["clientes"], 0)


class PruebasSimulacionPorFranjas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.configuracion = configuracionDePrueba()
        perfil = analisisLlegadas.perfilDeLlegadas(cls.configuracion["entrada"], 60)
        cls.jornadas = planificacion.jornadasDelEscenario(cls.configuracion, HABITUAL, "regular", perfil)
        random.seed(21)
        with patch("builtins.print"):
            cls.corridas = iniciador.simularCorridas(cls.jornadas, 5, 5, 0.05, 10, 0.05)["clientesPorCorrida"]
        random.seed(21)
        with patch("builtins.print"):
            cls.escenario = planificacion.simularEscenario(cls.configuracion, cls.jornadas)

    def test_cadaClienteCaeEnUnaSolaFranja(self):
        for numero, jornada in enumerate(self.escenario["jornadas"], start=1):
            total = sum(len([cliente for cliente in clientes if cliente["jornada"] == numero]) for clientes in self.corridas)
            self.assertAlmostEqual(sum(franja["clientes"] for franja in jornada["franjas"]) * len(self.corridas), total)

    def test_laFilaSeArrastraEntreFranjas(self):
        # Llega más gente de la que se atiende: si cada franja empezara vacía, las esperas serían parecidas
        esperas = [franja["Wq"]["promedio"] for franja in self.escenario["jornadas"][0]["franjas"]]
        self.assertEqual(esperas, sorted(esperas))
        self.assertGreater(esperas[-1], 3 * esperas[0])

    def test_lasEsperasSalenDelMotor(self):
        # La espera de la franja 10:00–11:00 es el promedio, entre corridas, de los clientes que llegaron en ella
        porCorrida = []
        for clientes in self.corridas:
            enFranja = [cliente for cliente in clientes if cliente["jornada"] == 1 and 120 <= cliente["momentoLlegada"] < 180]
            porCorrida.append(sum(cliente["tiempoEspera"] for cliente in enFranja) / len(enFranja))
        self.assertAlmostEqual(self.escenario["jornadas"][0]["franjas"][2]["Wq"]["promedio"], sum(porCorrida) / len(porCorrida))

    def test_nuncaHayMasClientesEnCajaQueCajas(self):
        for clientes in self.corridas:
            for numero in (1, 2):
                eventos = sorted([(cliente["inicioServicio"], 1) for cliente in clientes if cliente["jornada"] == numero]
                                 + [(cliente["terminacionServicio"], -1) for cliente in clientes if cliente["jornada"] == numero],
                                 key=lambda evento: (evento[0], evento[1]))
                enCaja = 0
                for _, cambio in eventos:
                    enCaja += cambio
                    self.assertLessEqual(enCaja, 5)
        for jornada in self.escenario["jornadas"]:
            self.assertLessEqual(jornada["utilizacion"]["maximo"], 1)

    def test_histogramaConIntervalosDelMismoLargo(self):
        histograma = self.escenario["histogramas"]
        intervalosPorDia = 240 // 5 + 150 // 5
        self.assertEqual(sum(histograma["todas"].values()), intervalosPorDia * len(self.corridas))
        partes = sum(sum(histograma[categoria].values()) for categoria in analisisLlegadas.CATEGORIAS)
        self.assertEqual(partes, sum(histograma["todas"].values()))


# ---------------------------------------------------------------------------
# 6. Publicación, consulta del cliente y comparación de días
# ---------------------------------------------------------------------------
class PruebasPublicacion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.configuracion = configuracionDePrueba(excepciones=[
            {"fecha": "2026-12-08", "motivo": "Festivo", "abierto": False, "jornadas": []},
            {"fecha": "2026-12-13", "motivo": "Apertura extraordinaria", "abierto": True,
             "jornadas": [{"inicio": "09:00", "fin": "12:00"}]},
        ])
        with patch("builtins.print"):
            cls.estimaciones = planificacion.publicar(cls.configuracion)

    def test_unEscenarioPorHorarioYTipoDeDia(self):
        self.assertEqual(sorted(self.estimaciones["escenarios"]), [
            "quincena|08:00-12:00,14:00-16:30", "quincena|09:00-12:00",
            "regular|08:00-12:00,14:00-16:30", "regular|09:00-12:00"])
        self.assertEqual(self.estimaciones["semilla"], 12345)

    def test_mismaSemillaMismasEstimaciones(self):
        with patch("builtins.print"):
            otra = planificacion.publicar(self.configuracion)
        self.assertEqual(otra["escenarios"], self.estimaciones["escenarios"])

    def test_fechaAbiertaConRecomendacion(self):
        visita = planificacion.consultarFecha(self.configuracion, self.estimaciones, date(2026, 12, 7))
        self.assertTrue(visita["abierto"])
        self.assertEqual([(franja["desde"], franja["hasta"]) for franja in visita["franjas"]], [
            ("08:00", "09:00"), ("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00"),
            ("14:00", "15:00"), ("15:00", "16:00"), ("16:00", "16:30")])   # respeta el cierre de 12 a 14
        esperas = [franja["Wq"]["promedio"] for franja in visita["franjas"]]
        self.assertEqual(visita["recomendada"], esperas.index(min(esperas)))
        self.assertTrue(visita["vigente"])

    def test_quincenaUsaSuPropioEscenario(self):
        regular = planificacion.consultarFecha(self.configuracion, self.estimaciones, date(2026, 12, 9))
        quincena = planificacion.consultarFecha(self.configuracion, self.estimaciones, date(2026, 12, 15))
        self.assertEqual((regular["tipoDia"], quincena["tipoDia"]), ("regular", "quincena"))
        self.assertGreater(sum(franja["clientes"] for franja in quincena["franjas"]),
                           sum(franja["clientes"] for franja in regular["franjas"]))

    def test_fechaCerradaDaLaSiguienteAbierta(self):
        festivo = planificacion.consultarFecha(self.configuracion, self.estimaciones, date(2026, 12, 8))
        self.assertFalse(festivo["abierto"])
        self.assertEqual(festivo["motivo"], "Festivo")
        self.assertEqual(festivo["siguienteAbierta"]["fecha"], "2026-12-09")
        sabado = planificacion.consultarFecha(self.configuracion, self.estimaciones, date(2026, 12, 12))
        self.assertEqual(sabado["siguienteAbierta"]["fecha"], "2026-12-13")   # la apertura extraordinaria del domingo

    def test_aperturaExtraordinariaTieneEstimacion(self):
        domingo = planificacion.consultarFecha(self.configuracion, self.estimaciones, date(2026, 12, 13))
        self.assertEqual([franja["desde"] for franja in domingo["franjas"]], ["09:00", "10:00", "11:00"])

    def test_siCambiaLaConfiguracionLasEstimacionesNoValen(self):
        cambiada = configuracionDePrueba()
        cambiada["entrada"]["numeroServidores"] = 6
        visita = planificacion.consultarFecha(cambiada, self.estimaciones, date(2026, 12, 7))
        self.assertTrue(visita["sinEstimacion"])
        self.assertEqual(visita["franjas"], [])

    def test_compararDosDias(self):
        comparacion = planificacion.compararDias(self.configuracion, self.estimaciones,
                                                 [date(2026, 12, 7), date(2026, 12, 15)], "todas")
        self.assertEqual(comparacion["origen"], "simulacion")
        for serie in comparacion["series"]:
            self.assertEqual(len(serie["relativas"]), len(comparacion["clases"]))   # mismas clases
            self.assertAlmostEqual(sum(serie["relativas"]), 1)
        self.assertGreater(comparacion["series"][1]["media"], comparacion["series"][0]["media"])   # quincena: +30 %
        self.assertEqual(comparacion["observado"]["n"], 60)   # los 60 conteos del estudio, como referencia

    def test_compararConUnDiaCerrado(self):
        comparacion = planificacion.compararDias(self.configuracion, self.estimaciones,
                                                 [date(2026, 12, 7), date(2026, 12, 6)], "valle")
        self.assertFalse(comparacion["series"][1]["abierto"])
        self.assertEqual(comparacion["series"][1]["n"], 0)   # sin datos ficticios


# ---------------------------------------------------------------------------
# 7. API
# ---------------------------------------------------------------------------
class PruebasAPIEstablecimiento(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        import api
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        parche = patch.object(planificacion, "CARPETA_DATOS", Path(carpeta.name))
        parche.start()
        self.addCleanup(parche.stop)
        self.cliente = TestClient(api.app)

    def configuracion(self):
        configuracion = self.cliente.get("/api/establecimiento").json()["configuracion"]
        configuracion["entrada"].update(numeroCorridas=3, semilla=4)
        return configuracion

    def test_porDefectoLunesAViernes(self):
        estado = self.cliente.get("/api/establecimiento").json()
        self.assertFalse(estado["guardada"])
        abiertos = [dia["abierto"] for dia in estado["configuracion"]["horarioSemanal"]]
        self.assertEqual(abiertos, [True] * 5 + [False, False])

    def test_guardarPublicaYSeConserva(self):
        configuracion = self.configuracion()
        configuracion["excepciones"] = [{"fecha": "2026-12-08", "motivo": "Festivo", "abierto": False, "jornadas": []}]
        with patch("builtins.print"):
            respuesta = self.cliente.put("/api/establecimiento", json=configuracion)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertTrue(respuesta.json()["publicacion"]["vigente"])
        self.assertEqual(respuesta.json()["publicacion"]["semilla"], 4)
        estado = self.cliente.get("/api/establecimiento").json()
        self.assertTrue(estado["guardada"])
        self.assertEqual(estado["configuracion"]["excepciones"][0]["motivo"], "Festivo")
        dias = self.cliente.get("/api/calendario/2026/12").json()["dias"]
        self.assertFalse(dias[7]["abierto"])     # 8 de diciembre
        self.assertTrue(dias[8]["abierto"])      # 9 de diciembre
        with patch("builtins.print"):
            visita = self.cliente.get("/api/visita/2026-12-08").json()
        self.assertEqual(visita["siguienteAbierta"]["fecha"], "2026-12-09")

    def test_rechazaHorariosInvalidos(self):
        casos = {
            "se superponen": lambda c: c["horarioSemanal"][0].update(
                jornadas=[{"inicio": "08:00", "fin": "12:00"}, {"inicio": "11:00", "fin": "15:00"}]),
            "al menos una jornada": lambda c: c["horarioSemanal"][0].update(jornadas=[]),
            "misma fecha": lambda c: c.update(excepciones=[{"fecha": "2026-12-08", "abierto": False}] * 2),
            "Zona horaria": lambda c: c.update(zonaHoraria="Marte/Olympus"),
            "múltiplo": lambda c: c.update(minutosPorFranja=7),
            "al menos un día": lambda c: [dia.update(abierto=False) for dia in c["horarioSemanal"]],
        }
        for mensaje, romper in casos.items():
            with self.subTest(mensaje=mensaje):
                configuracion = self.configuracion()
                romper(configuracion)
                respuesta = self.cliente.put("/api/establecimiento", json=configuracion)
                self.assertEqual(respuesta.status_code, 422)
                self.assertIn(mensaje, str(respuesta.json()["detail"]))

    def test_visitaSinPublicarPublicaSola(self):
        with patch("builtins.print"):
            visita = self.cliente.get("/api/visita/2026-12-07").json()
        self.assertTrue(visita["abierto"])
        self.assertEqual(len(visita["franjas"]), 7)
        self.assertIsNotNone(visita["recomendada"])

    def test_compararLaMismaFechaDa422(self):
        respuesta = self.cliente.get("/api/comparar-dias", params={"fechaA": "2026-12-07", "fechaB": "2026-12-07"})
        self.assertEqual(respuesta.status_code, 422)

    def test_analisisDeLlegadas(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        respuesta = self.cliente.post("/api/analisis-llegadas", json={"entrada": entrada, "ventana": 4})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["ventana"], 4)
        entrada["jornadas"][0]["inicioConteos"] = "11:50"   # 30 conteos no caben desde las 11:50
        self.assertEqual(self.cliente.post("/api/analisis-llegadas", json={"entrada": entrada}).status_code, 422)

    def test_simularDevuelveLaSemillaUsada(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        entrada["numeroCorridas"] = 2
        with patch("builtins.print"):
            resultado = self.cliente.post("/api/simular", json=entrada).json()
        self.assertIsInstance(resultado["semilla"], int)
        self.assertEqual(resultado["versionModelo"], iniciador.VERSION_MODELO)


if __name__ == "__main__":
    unittest.main()
