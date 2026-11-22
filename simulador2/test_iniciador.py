"""Pruebas del simulador 2.

Correr desde la carpeta del proyecto:
    python3 -m unittest discover -s simulador2 -v
"""

import json
import random
import unittest
from datetime import time
from unittest.mock import patch

from scipy.stats import kstest

import iniciador


def jornadaDePrueba(inicio=time(8, 0), fin=time(12, 0), tasaLlegada=5.0, tasaServicio=1.0) -> dict:
    """Una jornada armada a mano para las pruebas."""
    return {
        1: {
            "inicio": inicio,
            "fin": fin,
            "tiempoEntreTomasDeDatos": 5,
            "tasaLlegada": tasaLlegada,
            "tasaServicio": tasaServicio,
        }
    }


# ---------------------------------------------------------------------------
# 1. Funciones pequeñas: se compara contra un resultado que se sabe de memoria
# ---------------------------------------------------------------------------
class PruebasConversionHoras(unittest.TestCase):

    def test_convertirAMinutos(self):
        self.assertEqual(iniciador.convertirAMinutos(time(0, 0)), 0)
        self.assertEqual(iniciador.convertirAMinutos(time(8, 0)), 480)
        self.assertEqual(iniciador.convertirAMinutos(time(16, 30)), 990)

    def test_duracionDeLasJornadas(self):
        manana = iniciador.convertirAMinutos(time(12, 0)) - iniciador.convertirAMinutos(time(8, 0))
        tarde = iniciador.convertirAMinutos(time(16, 30)) - iniciador.convertirAMinutos(time(14, 0))
        self.assertEqual(manana, 240)
        self.assertEqual(tarde, 150)


# ---------------------------------------------------------------------------
# 2. Lo aleatorio: no se sabe qué número sale, pero sí cómo se comporta
# ---------------------------------------------------------------------------
class PruebasExponencial(unittest.TestCase):

    def test_formulaConUnAleatorioConocido(self):
        # Si R = 0.5 → x = -media · ln(0.5) = media · 0.6931
        with patch("iniciador.random.random", return_value=0.5):
            r, x = iniciador.generarExponencial(2.0)
        self.assertEqual(r, 0.5)
        self.assertAlmostEqual(x, 1.3863, places=4)

    def test_nuncaDaNegativo(self):
        random.seed(1)
        for _ in range(10_000):
            _, x = iniciador.generarExponencial(3.5)
            self.assertGreaterEqual(x, 0)

    def test_elPromedioSeAcercaALaMedia(self):
        # Con muchos números, el promedio de los tiempos debe parecerse a la media pedida
        random.seed(1)
        tiempos = [iniciador.generarExponencial(3.5)[1] for _ in range(100_000)]
        promedio = sum(tiempos) / len(tiempos)
        self.assertAlmostEqual(promedio, 3.5, delta=0.05)


# ---------------------------------------------------------------------------
# 3. El modelo con números fijos: la tabla se puede hacer a mano (como en Excel)
# ---------------------------------------------------------------------------
class PruebasModeloAMano(unittest.TestCase):
    """El azar se reemplaza por tiempos fijos, en el orden en que se piden:
    primero todas las llegadas de la jornada (la última ya cae después del cierre)
    y luego los servicios, en el orden en que se atiende."""

    def simular(self, llegadas, servicios, numeroServidores=1):
        falsos = [(0.5, t) for t in llegadas + servicios]
        with patch("iniciador.generarExponencial", side_effect=falsos):
            return iniciador.modelo(jornadaDePrueba(), numeroServidores=numeroServidores)

    def test_tablaCalculadaAMano(self):
        # Cliente | Llega | Inicio | Espera | Servicio | Fin | Ocio
        #    1    |   2   |   2    |   0    |    5     |  7  |  2
        #    2    |   3   |   7    |   4    |    1     |  8  |  0
        #    3    |  10   |  10    |   0    |    2     | 12  |  2
        clientes = self.simular([2, 1, 7, 999], [5, 1, 2])
        esperado = [
            # (llegada, inicio, espera, servicio, fin, ocio)
            (2, 2, 0, 5, 7, 2),
            (3, 7, 4, 1, 8, 0),
            (10, 10, 0, 2, 12, 2),
        ]
        self.assertEqual(len(clientes), 3)
        for cliente, (llegada, inicio, espera, servicio, fin, ocio) in zip(clientes, esperado):
            with self.subTest(cliente=cliente["cliente"]):
                self.assertEqual(cliente["momentoLlegada"], llegada)
                self.assertEqual(cliente["inicioServicio"], inicio)
                self.assertEqual(cliente["tiempoEspera"], espera)
                self.assertEqual(cliente["tiempoServicio"], servicio)
                self.assertEqual(cliente["terminacionServicio"], fin)
                self.assertEqual(cliente["tiempoOcio"], ocio)
                self.assertEqual(cliente["tiempoTotal"], espera + servicio)

    def test_dosCajasTresClientes(self):
        # Cliente | Llega | Caja | Inicio | Espera | Servicio | Fin | Ocio
        #    1    |   1   |  1   |   1    |   0    |   10     | 11  |  1   (las dos libres → caja 1)
        #    2    |   2   |  2   |   2    |   0    |   10     | 12  |  2   (caja 2 libre)
        #    3    |   3   |  1   |  11    |   8    |    3     | 14  |  0   (caja 1 se libera primero)
        clientes = self.simular([1, 1, 1, 999], [10, 10, 3], numeroServidores=2)
        esperado = [
            # (llegada, caja, inicio, espera, fin, ocio)
            (1, 1, 1, 0, 11, 1),
            (2, 2, 2, 0, 12, 2),
            (3, 1, 11, 8, 14, 0),
        ]
        self.assertEqual(len(clientes), 3)
        for cliente, (llegada, caja, inicio, espera, fin, ocio) in zip(clientes, esperado):
            with self.subTest(cliente=cliente["cliente"]):
                self.assertEqual(cliente["momentoLlegada"], llegada)
                self.assertEqual(cliente["servidor"], caja)
                self.assertEqual(cliente["inicioServicio"], inicio)
                self.assertEqual(cliente["tiempoEspera"], espera)
                self.assertEqual(cliente["terminacionServicio"], fin)
                self.assertEqual(cliente["tiempoOcio"], ocio)

    def test_dosCajasCuatroClientes(self):
        # Cliente | Llega | Caja | Inicio | Espera | Servicio | Fin | Ocio caja | Cajas libres en
        #    1    |  2    |  1   |  2     |  0     |   5      |  7  |   2       | [7, 0]
        #    2    |  3    |  2   |  3     |  0     |   1      |  4  |   3       | [7, 4]
        #    3    |  4    |  2   |  4     |  0     |   2      |  6  |   0       | [7, 6]
        #    4    |  4.5  |  2   |  6     |  1.5   |   1      |  7  |   0       | [7, 7]
        clientes = self.simular([2, 1, 1, 0.5, 999], [5, 1, 2, 1], numeroServidores=2)
        esperado = [
            # (caja, llegada, inicio, espera, fin, ocio)
            (1, 2, 2, 0, 7, 2),
            (2, 3, 3, 0, 4, 3),
            (2, 4, 4, 0, 6, 0),
            (2, 4.5, 6, 1.5, 7, 0),
        ]
        self.assertEqual(len(clientes), 4)
        for cliente, (caja, llegada, inicio, espera, fin, ocio) in zip(clientes, esperado):
            with self.subTest(cliente=cliente["cliente"]):
                self.assertEqual(cliente["servidor"], caja)
                self.assertEqual(cliente["momentoLlegada"], llegada)
                self.assertEqual(cliente["inicioServicio"], inicio)
                self.assertEqual(cliente["tiempoEspera"], espera)
                self.assertEqual(cliente["terminacionServicio"], fin)
                self.assertEqual(cliente["tiempoOcio"], ocio)

    def test_elPrioritarioPasaPrimero(self):
        # Una caja. El 3 es prioritario: cuando la caja se libera (min 11) pasa antes que el 2.
        # Cliente | Prior. | Llega | Inicio | Espera | Servicio | Fin | Personas al llegar
        #    1    |   No   |   1   |   1    |   0    |   10     | 11  |   0
        #    2    |   No   |   2   |  12    |  10    |    2     | 14  |   1
        #    3    |   Sí   |   3   |  11    |   8    |    1     | 12  |   2
        falsos = [(0.5, t) for t in [1, 1, 1, 999, 10, 1, 2]]
        with patch("iniciador.generarExponencial", side_effect=falsos), \
             patch("iniciador.random.random", side_effect=[0.9, 0.9, 0.01]):
            clientes = iniciador.modelo(jornadaDePrueba(), proporcionPrioritarios=0.05)

        esperado = [(False, 1, 0, 11, 0), (False, 12, 10, 14, 1), (True, 11, 8, 12, 2)]
        for cliente, (prioritario, inicio, espera, fin, personas) in zip(clientes, esperado):
            with self.subTest(cliente=cliente["cliente"]):
                self.assertEqual(cliente["prioritario"], prioritario)
                self.assertEqual(cliente["inicioServicio"], inicio)
                self.assertEqual(cliente["tiempoEspera"], espera)
                self.assertEqual(cliente["terminacionServicio"], fin)
                self.assertEqual(cliente["personasAlLlegar"], personas)


# ---------------------------------------------------------------------------
# 4. El modelo con azar: reglas que SIEMPRE se deben cumplir, salga lo que salga
# ---------------------------------------------------------------------------
class PruebasReglasDelModelo(unittest.TestCase):

    def setUp(self):
        random.seed(42)   # misma semilla → mismos resultados en cada corrida
        self.clientes = iniciador.modelo(jornadaDePrueba())

    def test_nadieLlegaDespuesDelCierre(self):
        for c in self.clientes:
            self.assertLessEqual(c["momentoLlegada"], 240)

    def test_nadieEsperaTiempoNegativo(self):
        for c in self.clientes:
            self.assertGreaterEqual(c["tiempoEspera"], 0)
            self.assertGreaterEqual(c["tiempoOcio"], 0)

    def test_unaSolaCaja_nadieEmpiezaAntesDeQueSalgaElAnterior(self):
        for anterior, actual in zip(self.clientes, self.clientes[1:]):
            inicioActual = actual["terminacionServicio"] - actual["tiempoServicio"]
            self.assertGreaterEqual(inicioActual + 1e-9, anterior["terminacionServicio"])

    def test_lasLlegadasVanEnOrden(self):
        llegadas = [c["momentoLlegada"] for c in self.clientes]
        self.assertEqual(llegadas, sorted(llegadas))

    def test_losClientesSeNumeranDesdeUno(self):
        self.assertEqual([c["cliente"] for c in self.clientes],
                         list(range(1, len(self.clientes) + 1)))


# ---------------------------------------------------------------------------
# 5. Elegir caja: el for contra la fórmula de SI / O del video (2 cajas)
# ---------------------------------------------------------------------------
def elegirCajaComoVideo(cajaLibreEn: list[float], momentoLlegada: float) -> int:
    """La regla del Excel del video, escrita con if:
    SI (la caja 1 ya está libre cuando llega) O (la caja 1 se libera antes que la 2) → caja 1
    SI NO → caja 2
    """
    if cajaLibreEn[0] <= momentoLlegada or cajaLibreEn[0] <= cajaLibreEn[1]:
        return 0
    return 1


def espera(cajaLibreEn: list[float], caja: int, momentoLlegada: float) -> float:
    return max(momentoLlegada, cajaLibreEn[caja]) - momentoLlegada


class PruebasElegirCaja(unittest.TestCase):

    def test_ejemploDelTablero(self):
        # caja1 libre en 11, caja2 en 4, caja3 en 9 → la caja 2 (posición 1)
        self.assertEqual(iniciador.elegirCaja([11, 4, 9]), 1)

    def test_otrosCasos(self):
        casos = [
            ([0, 0], 0),             # banco vacío → caja 1
            ([5, 5, 5], 0),          # empate → la primera
            ([7, 3], 1),             # la caja 2 se libera antes
            ([2, 8, 1, 6, 4], 2),    # 5 cajas → la caja 3
            ([9], 0),                # una sola caja → siempre esa
        ]
        for tablero, esperado in casos:
            with self.subTest(tablero=tablero):
                self.assertEqual(iniciador.elegirCaja(tablero), esperado)

    def test_casosDelVideo(self):
        # (tablero, llegada, caja con el for, caja con el video)
        casos = [
            ([10, 4], 6, 1, 1),   # caja 1 ocupada, caja 2 libre      → los dos eligen caja 2
            ([10, 12], 6, 0, 0),  # las dos ocupadas, la 1 sale antes → los dos eligen caja 1
            ([3, 1], 6, 1, 0),    # LAS DOS libres → el for elige la 2, el video la 1
        ]
        for tablero, llegada, conFor, conVideo in casos:
            with self.subTest(tablero=tablero, llegada=llegada):
                self.assertEqual(iniciador.elegirCaja(tablero), conFor)
                self.assertEqual(elegirCajaComoVideo(tablero, llegada), conVideo)
                # Aunque elijan distinta caja, el cliente espera lo mismo
                self.assertEqual(espera(tablero, conFor, llegada),
                                 espera(tablero, conVideo, llegada))

    def test_miles_de_casos_al_azar_misma_espera(self):
        # 10 000 situaciones al azar: el for y el video SIEMPRE dan la misma espera
        random.seed(7)
        for _ in range(10_000):
            tablero = [random.uniform(0, 20), random.uniform(0, 20)]
            llegada = random.uniform(0, 20)
            cajaFor = iniciador.elegirCaja(tablero)
            cajaVideo = elegirCajaComoVideo(tablero, llegada)
            self.assertAlmostEqual(espera(tablero, cajaFor, llegada),
                                   espera(tablero, cajaVideo, llegada))



# ---------------------------------------------------------------------------
# 6. Medidas de efectividad (medidas.py) calculadas a mano
# ---------------------------------------------------------------------------
import medidas


class PruebasMedidasAMano(unittest.TestCase):
    """Misma tabla de 2 cajas de PruebasModeloAMano, con la puerta abierta 10 minutos.

    Cliente | Llega | Caja | Inicio | Espera | Servicio | Fin | En sistema
       1    |   1   |  1   |   1    |   0    |   10     | 11  |   10
       2    |   2   |  2   |   2    |   0    |   10     | 12  |   10
       3    |   3   |  1   |  11    |   8    |    3     | 14  |   11

    T = max(10 de puerta, 14 última salida) = 14 minutos observados.

    Personas en el sistema a lo largo del tiempo:
        [0, 1) → 0   [1, 2) → 1   [2, 3) → 2   [3, 11) → 3   [11, 12) → 2   [12, 14) → 1
    Personas en la cola: solo el cliente 3 de 3 a 11 → 1; el resto del tiempo 0.
    """

    def setUp(self):
        falsos = [(0.5, t) for t in [1, 1, 1, 999, 10, 10, 3]]
        with patch("iniciador.generarExponencial", side_effect=falsos):
            clientes = iniciador.modelo(jornadaDePrueba(), numeroServidores=2)
        self.m = medidas.calcularMedidas(clientes, numeroServidores=2, duracionJornada=10)

    def test_tiempos(self):
        self.assertEqual(self.m["clientesAtendidos"], 3)
        self.assertEqual(self.m["tiempoTotalSistema"], 31)        # 10 + 10 + 11
        self.assertAlmostEqual(self.m["W"], 31 / 3)
        self.assertEqual(self.m["tiempoTotalCola"], 8)            # solo esperó el cliente 3
        self.assertAlmostEqual(self.m["Wq"], 8 / 3)
        self.assertEqual(self.m["esperaMaxima"], 8)

    def test_longitudes(self):
        self.assertEqual(self.m["tiempoObservado"], 14)
        self.assertAlmostEqual(self.m["L"], 31 / 14)
        self.assertAlmostEqual(self.m["Lq"], 8 / 14)
        self.assertEqual(self.m["longitudMaximaSistema"], 3)
        self.assertEqual(self.m["longitudMaximaCola"], 1)

    def test_tablaDeLongitudes(self):
        sistema = self.m["probabilidadSistema"]
        self.assertAlmostEqual(sistema[0], 1 / 14)
        self.assertAlmostEqual(sistema[1], 3 / 14)    # [1,2) y [12,14)
        self.assertAlmostEqual(sistema[2], 2 / 14)    # [2,3) y [11,12)
        self.assertAlmostEqual(sistema[3], 8 / 14)    # [3,11)
        self.assertAlmostEqual(sum(sistema.values()), 1)

        cola = self.m["probabilidadCola"]
        self.assertAlmostEqual(cola[0], 6 / 14)
        self.assertAlmostEqual(cola[1], 8 / 14)

    def test_LCoincideConLaTablaDeLongitudes(self):
        # L = Σ n · P(n): dos formas de calcular lo mismo deben dar igual
        sistema = self.m["probabilidadSistema"]
        self.assertAlmostEqual(sum(n * p for n, p in sistema.items()), self.m["L"])

    def test_ocio(self):
        # Caja 1 atiende 10 + 3 = 13 de 14 min → ocio 1.  Caja 2 atiende 10 → ocio 4.
        self.assertEqual(self.m["ocioPorServidor"], [1, 4])
        self.assertEqual(self.m["ocioTotal"], 5)
        self.assertAlmostEqual(self.m["utilizacion"], 23 / 28)


class PruebasEjemploDeLaDefensa(unittest.TestCase):
    """El ejemplo resuelto a mano de la guía de defensa del manual (una caja, el 3 es prioritario).

    Cliente | Llega | Servicio | Inicio | Fin | Espera
       1    |   0   |    4     |   0    |  4  |   0
       2    |   1   |    3     |   6    |  9  |   5
       3 ★  |   2   |    2     |   4    |  6  |   2    ← a los 4 min pasa antes que el 2
       4    |   3   |    1     |   9    | 10  |   6
    T = max(5 de puerta, 10 última salida) = 10.
    """

    def test_tablaYMedidas(self):
        clientes = [{"cliente": numero, "momentoLlegada": llegada, "prioritario": numero == 3}
                    for numero, llegada in enumerate((0, 1, 2, 3), 1)]
        servicios = iter((4, 2, 3, 1))   # en el orden en que se atiende: 1, 3, 2, 4
        iniciador.atender(clientes, 1, lambda: (0.0, next(servicios)))
        self.assertEqual([(c["inicioServicio"], c["terminacionServicio"], c["tiempoEspera"]) for c in clientes],
                         [(0, 4, 0), (6, 9, 5), (4, 6, 2), (9, 10, 6)])

        m = medidas.calcularMedidas(clientes, numeroServidores=1, duracionJornada=5)
        self.assertEqual((m["Wq"], m["W"], m["Lq"], m["L"], m["utilizacion"]), (3.25, 5.75, 1.3, 2.3, 1.0))


class PruebasResumenCorridas(unittest.TestCase):

    def test_promedioConIntervalo(self):
        r = medidas.promedioConIntervalo([2, 4, 6])
        # media 4, S = 2, t(2 grados) = 4.303 → 4 ± 4.303 · 2 / √3
        self.assertEqual(r["promedio"], 4)
        self.assertEqual((r["minimo"], r["maximo"]), (2, 6))
        self.assertAlmostEqual(r["limiteInferior"], 4 - 4.303 * 2 / 3 ** 0.5, places=3)
        self.assertAlmostEqual(r["limiteSuperior"], 4 + 4.303 * 2 / 3 ** 0.5, places=3)

    def test_valorTIgualALaTabla(self):
        # Valores de la tabla t de Student (95 %, dos colas)
        for gradosLibertad, valorTabla in [(1, 12.706), (9, 2.262), (29, 2.045), (120, 1.980)]:
            with self.subTest(gradosLibertad=gradosLibertad):
                self.assertAlmostEqual(medidas.valorT95(gradosLibertad), valorTabla, places=3)

    def test_promediarDistribucion_cuentaCeroSiNoAparece(self):
        corridas = [{"p": {0: 0.5, 1: 0.5}}, {"p": {0: 1.0}}]
        self.assertEqual(medidas.promediarDistribucion(corridas, "p"), {0: 0.75, 1: 0.25})

    def test_simulacionCompletaConAzar(self):
        # 5 corridas de una jornada: el resumen trae todas las medidas y P(n) suma 1
        random.seed(3)
        r = iniciador.simularCorridas(jornadaDePrueba(), numeroServidores=3, numeroCorridas=5)
        self.assertEqual(len(r["medidas"][1]), 5)
        resumen = medidas.resumirCorridas(r["medidas"][1])
        for clave in medidas.MEDIDAS_NUMERICAS:
            self.assertIn(clave, resumen)
        self.assertIsNone(resumen["WqPrioritarios"])   # sin prioritarios no hay dato
        self.assertEqual(len(resumen["ocioPorServidor"]), 3)
        self.assertAlmostEqual(sum(resumen["probabilidadSistema"].values()), 1)
        self.assertAlmostEqual(sum(resumen["probabilidadCola"].values()), 1)


# ---------------------------------------------------------------------------
# 7. Prueba de Kolmogorov-Smirnov y repetición de corridas rechazadas
# ---------------------------------------------------------------------------
import pruebaKS

PASA = {"llegada": {"pasa": True}, "servicio": {"pasa": True}, "pasa": True}
FALLA = {"llegada": {"pasa": False}, "servicio": {"pasa": True}, "pasa": False}


class PruebasKS(unittest.TestCase):

    def test_valorCriticoComoElLibro(self):
        # n > 35: 1.22/√n, 1.36/√n y 1.63/√n para α = 0.10, 0.05 y 0.01
        for alfa, coeficiente in [(0.10, 1.22), (0.05, 1.36), (0.01, 1.63)]:
            with self.subTest(alfa=alfa):
                self.assertAlmostEqual(pruebaKS.valorCriticoKS(100, alfa), coeficiente / 10, places=3)

    def test_valorCriticoConPocosDatos(self):
        # Tabla K-S: n = 5 → 0.565 y n = 10 → 0.410 con α = 0.05
        self.assertAlmostEqual(pruebaKS.valorCriticoKS(5, 0.05), 0.565, places=2)
        self.assertAlmostEqual(pruebaKS.valorCriticoKS(10, 0.05), 0.410, places=2)

    def test_numerosParejosPasan(self):
        numeros = [(i + 0.5) / 50 for i in range(50)]
        r = pruebaKS.pruebaKS(numeros, 0.05)
        self.assertAlmostEqual(r["D"], 0.01)
        self.assertTrue(r["pasa"])

    def test_numerosAmontonadosFallan(self):
        self.assertFalse(pruebaKS.pruebaKS([i / 1000 for i in range(50)], 0.05)["pasa"])

    def test_separarAleatorios(self):
        clientes = [{"aleatorioLlegada": 0.1, "aleatorioServicio": 0.7},
                    {"aleatorioLlegada": 0.4, "aleatorioServicio": 0.2}]
        self.assertEqual(iniciador.separarAleatorios(clientes), ([0.1, 0.4], [0.7, 0.2]))


class PruebasRepeticionPorKS(unittest.TestCase):

    def test_laCorridaRechazadaSeRepite(self):
        with patch("iniciador.validarUniformidadPruebaKS", side_effect=[FALLA, PASA, PASA]), \
             patch("builtins.print"):
            r = iniciador.simularCorridas(jornadaDePrueba(), 2, numeroCorridas=2)
        self.assertEqual(len(r["medidas"][1]), 2)
        self.assertEqual([(x["corrida"], x["intento"]) for x in r["rechazos"]], [(1, 1)])
        self.assertEqual([x["intentos"] for x in r["ks"]], [2, 1])
        self.assertEqual(iniciador.corridasAceptadas, [])

    def test_seDetieneAlPasarElLimite(self):
        with patch("iniciador.validarUniformidadPruebaKS", return_value=FALLA), \
             patch("builtins.print"):
            with self.assertRaises(iniciador.UniformidadRechazada):
                iniciador.simularCorridas(jornadaDePrueba(), 2, numeroCorridas=3, limiteIntentos=4)
        self.assertEqual(iniciador.corridasAceptadas, [])

    def test_simularDesdeJSON(self):
        entrada = {
            "numeroServidores": 3, "tiempoEntreTomasDeDatos": 5, "proporcionVanACaja": 1,
            "proporcionPrioritarios": 0.05, "factorLlegadas": 1.3, "numeroCorridas": 4,
            "alfa": 0.05, "limiteIntentos": 10, "semilla": 1, "compararConCiw": True,
            "jornadas": [{"inicio": "08:00", "fin": "12:00", "conteos": CONTEOS_MANANA, "minutosPorCliente": 13.5}],
        }
        with patch("builtins.print"):
            resultado = iniciador.simular(entrada)
        json.dumps(resultado)
        jornada = resultado["jornadas"][0]
        self.assertEqual(len(resultado["ks"]), 4)
        self.assertAlmostEqual(jornada["tasaLlegada"], 130 / 24 * 1.3)
        self.assertTrue(all(corrida["pasa"] for corrida in resultado["ks"]))
        self.assertIn("Wq", jornada["ciw"])
        self.assertEqual(len(jornada["medidasPorCorrida"]), 4)


class PruebasContraSciPy(unittest.TestCase):
    """La prueba KS propia debe dar la misma D que scipy.stats.kstest."""

    def test_mismaDQueScipy(self):
        random.seed(5)
        for cantidad in (10, 50, 400):
            numeros = [random.random() for _ in range(cantidad)]
            with self.subTest(cantidad=cantidad):
                self.assertAlmostEqual(pruebaKS.pruebaKS(numeros, 0.05)["D"],
                                       kstest(numeros, "uniform").statistic)


# ---------------------------------------------------------------------------
# 8. Prueba chi-cuadrada de Poisson sobre los conteos observados
# ---------------------------------------------------------------------------
import pruebaPoisson

CONTEOS_MANANA = [7, 9, 8, 6, 4, 7, 5, 11, 8, 2, 4, 6, 3, 1, 3, 9, 6, 4, 8, 7, 2, 3, 4, 3]


class PruebasPoisson(unittest.TestCase):

    def test_conteosDeLaManana(self):
        resultado = pruebaPoisson.pruebaChiCuadradaPoisson(CONTEOS_MANANA, 0.05)
        self.assertAlmostEqual(resultado["media"], 130 / 24)
        self.assertAlmostEqual(resultado["varianza"], 6.949, places=3)
        self.assertTrue(all(clase["esperadas"] >= 5 for clase in resultado["clases"]))
        self.assertAlmostEqual(sum(clase["esperadas"] for clase in resultado["clases"]), 24)
        self.assertEqual(sum(clase["observadas"] for clase in resultado["clases"]), 24)
        self.assertEqual(resultado["gradosLibertad"], len(resultado["clases"]) - 2)
        self.assertTrue(resultado["pasa"])

    def test_conteosQueNoSonPoisson(self):
        # Mitad de intervalos vacíos y mitad con 20 personas: varianza enorme
        resultado = pruebaPoisson.pruebaChiCuadradaPoisson([0] * 30 + [20] * 30, 0.05)
        self.assertFalse(resultado["pasa"])


# ---------------------------------------------------------------------------
# 9. Validación con Ciw, cajas necesarias y API
# ---------------------------------------------------------------------------
import validacionCiw


class PruebasCiw(unittest.TestCase):

    def test_ciwYElSimuladorPropioCoinciden(self):
        jornadas = jornadaDePrueba(tasaLlegada=5.0, tasaServicio=1.5)
        random.seed(11)
        with patch("builtins.print"):
            propio = iniciador.simularCorridas(jornadas, 4, 60, proporcionPrioritarios=0.05)
        comparacion = validacionCiw.compararConCiw(jornadas, 4, 0.05, 0.01, iniciador.duracionJornada, propio["medidas"])
        for medida in ["L", "Wq", "utilizacion"]:
            with self.subTest(medida=medida):
                self.assertTrue(comparacion[1][medida]["coinciden"], comparacion[1][medida]["valorP"])

    def test_welchDetectaUnaDiferenciaReal(self):
        self.assertFalse(validacionCiw.compararMedida([1.0, 1.1, 0.9, 1.0] * 10, [2.0, 2.1, 1.9, 2.0] * 10, 0.05)["coinciden"])

    def test_medidasSinVariacionNoDanNaN(self):
        # Sin varianza no hay t de Welch: el valor p queda vacío y la respuesta se puede enviar en JSON
        iguales = validacionCiw.compararMedida([0.0, 0.0], [0.0, 0.0], 0.05)
        self.assertEqual(iguales, {"valorP": None, "coinciden": True})
        json.dumps(iguales, allow_nan=False)
        self.assertFalse(validacionCiw.compararMedida([1.0, 1.0], [2.0, 2.0], 0.05)["coinciden"])

    def test_todosPrioritarios(self):
        # Con proporción 1 no llega ningún cliente normal: Ciw no debe crear una clase con tasa cero
        random.seed(5)
        clientes = validacionCiw.simularJornadaConCiw(iniciador.armarJornadas({
            "tiempoEntreTomasDeDatos": 5, "proporcionVanACaja": 1, "factorLlegadas": 1, "distribucionServicio": "uniforme",
            "jornadas": [{"inicio": "08:00", "fin": "09:00", "conteos": [3, 4], "servicioMinimo": 1, "servicioMaximo": 3}],
        })[1], 60, 2, 1.0)
        self.assertTrue(clientes)
        self.assertTrue(all(cliente["prioritario"] for cliente in clientes))


class PruebasCajasNecesarias(unittest.TestCase):

    def test_masCajasMenosEspera(self):
        entrada = {
            "tiempoEntreTomasDeDatos": 5, "proporcionVanACaja": 1, "proporcionPrioritarios": 0,
            "factorLlegadas": 1, "numeroCorridas": 5, "alfa": 0.05, "limiteIntentos": 10, "semilla": 3,
            "jornadas": [{"inicio": "08:00", "fin": "12:00", "conteos": CONTEOS_MANANA, "minutosPorCliente": 4}],
        }
        with patch("builtins.print"):
            resultado = iniciador.buscarCajasNecesarias(entrada, metaEsperaMinutos=2)
        esperas = [punto["jornadas"][0]["Wq"] for punto in resultado["curva"]]
        recomendadas = resultado["cajasRecomendadas"]
        self.assertIsNotNone(recomendadas)
        self.assertLessEqual(esperas[recomendadas - 1], 2)
        self.assertGreater(esperas[recomendadas - 2], 2)
        self.assertEqual(len(resultado["curva"]), recomendadas + 1)


class PruebasServicioUniforme(unittest.TestCase):

    def test_formulaConUnAleatorioConocido(self):
        # R = 0.5 → x = 1 + 24 · 0.5 = 13
        with patch("iniciador.random.random", return_value=0.5):
            self.assertEqual(iniciador.generarUniforme(1, 25), (0.5, 13.0))

    def test_losServiciosQuedanEntreElMinimoYElMaximo(self):
        jornadas = jornadaDePrueba()
        jornadas[1].update(distribucionServicio="uniforme", servicioMinimo=1, servicioMaximo=25)
        random.seed(8)
        clientes = iniciador.modelo(jornadas, numeroServidores=5)
        servicios = [cliente["tiempoServicio"] for cliente in clientes]
        self.assertTrue(all(1 <= servicio <= 25 for servicio in servicios))
        self.assertAlmostEqual(sum(servicios) / len(servicios), 13, delta=1.5)

    def test_tasaDeServicioUsaLaMediaDeLaUniforme(self):
        entrada = {"tiempoEntreTomasDeDatos": 5, "proporcionVanACaja": 1, "factorLlegadas": 1,
                   "distribucionServicio": "uniforme",
                   "jornadas": [{"inicio": "08:00", "fin": "12:00", "conteos": CONTEOS_MANANA,
                                 "servicioMinimo": 1, "servicioMaximo": 25}]}
        self.assertAlmostEqual(iniciador.armarJornadas(entrada)[1]["tasaServicio"], 5 / 13)


class PruebasJornadaSinClientes(unittest.TestCase):

    def test_errorClaroSiNoLlegaNadie(self):
        # La primera llegada cae después del cierre: la jornada queda vacía
        with patch("iniciador.generarExponencial", return_value=(0.5, 999)):
            with self.assertRaises(iniciador.JornadaSinClientes):
                iniciador.modelo(jornadaDePrueba())


class PruebasAPI(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        import api
        self.cliente = TestClient(api.app)

    def test_entradaPorDefectoSeSimula(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        self.assertEqual(sum(entrada["jornadas"][0]["conteos"]), 130)
        entrada["numeroCorridas"] = 3
        with patch("builtins.print"):
            respuesta = self.cliente.post("/api/simular", json=entrada)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["jornadas"]), 2)

    def test_rechazaEntradaInvalida(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        entrada["alfa"] = 2
        entrada["jornadas"][0]["fin"] = "07:00"
        self.assertEqual(self.cliente.post("/api/simular", json=entrada).status_code, 422)

    def test_poissonRechazaConteosNegativos(self):
        for conteos in ([-1, 3], [0, 0]):
            with self.subTest(conteos=conteos):
                self.assertEqual(self.cliente.post("/api/poisson", json={"conteos": conteos}).status_code, 422)

    def test_valoresPorDefectoComoElDocumento(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        self.assertEqual(entrada["numeroServidores"], 5)
        self.assertEqual(entrada["distribucionServicio"], "uniforme")
        self.assertEqual((entrada["jornadas"][0]["servicioMinimo"], entrada["jornadas"][0]["servicioMaximo"]), (1, 25))

    def test_jornadaSinClientesDa422(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        with patch("iniciador.generarExponencial", return_value=(0.5, 999)):
            respuesta = self.cliente.post("/api/simular", json=entrada)
        self.assertEqual(respuesta.status_code, 422)
        self.assertIn("no recibió ningún cliente", respuesta.json()["detail"])

    def test_peticionesSimultaneasNoSeMezclan(self):
        from concurrent.futures import ThreadPoolExecutor
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        entrada.update(numeroCorridas=5, semilla=99)
        with patch("builtins.print"), ThreadPoolExecutor(max_workers=4) as hilos:
            respuestas = list(hilos.map(lambda _: self.cliente.post("/api/simular", json=entrada).json(), range(4)))
        esperas = {respuesta["jornadas"][0]["resumen"]["Wq"]["promedio"] for respuesta in respuestas}
        self.assertEqual(len(esperas), 1)   # misma semilla → mismo resultado en las 4 peticiones

    def test_limiteDeIntentos(self):
        entrada = self.cliente.get("/api/entrada-por-defecto").json()
        entrada.update(alfa=0.99, limiteIntentos=1)
        with patch("builtins.print"):
            respuesta = self.cliente.post("/api/simular", json=entrada)
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("no pasó la prueba KS", respuesta.json()["detail"])


if __name__ == "__main__":
    unittest.main()
