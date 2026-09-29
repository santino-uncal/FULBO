"""Pruebas de las funciones de tools/: cada una recibe un dato de ejemplo y se compara con lo que debería devolver.

Correr todas:  py -m unittest discover tests   (o doble clic en probar.bat)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import equipos as E  # noqa: E402
import generar_datos as GD  # noqa: E402
import generar_estadisticas as GE  # noqa: E402
import leer_espn  # noqa: E402
import leer_rsssf  # noqa: E402
import leer_wikipedia  # noqa: E402
from copas import COPAS, copa_de_argumentos, prefijo_js  # noqa: E402


class NombresDeClubes(unittest.TestCase):
    def test_sin_tildes(self):
        self.assertEqual(E.sin_tildes("Peñarol São Paulo Atlético"), "Penarol Sao Paulo Atletico")

    def test_normalizar_saca_relleno_y_abreviaturas(self):
        self.assertEqual(E.normalizar("Club Atlético Peñarol"), "atletico penarol")
        self.assertEqual(E.normalizar("Univ. Católica"), "universidad catolica")
        self.assertEqual(E.normalizar("S.C. Internacional"), "internacional")
        self.assertEqual(E.normalizar("Nacional (Montevideo)"), "nacional")

    def test_limpiar_nombre(self):
        self.assertEqual(E.limpiar_nombre("Tigres UANL (Monterrey)"), "Tigres UANL")
        self.assertEqual(E.limpiar_nombre("Caracas FC"), "Caracas")
        self.assertEqual(E.limpiar_nombre("River Plate"), "River Plate")

    def test_slug(self):
        self.assertEqual(E.slug("São Paulo FC"), "sao-paulo-fc")
        self.assertEqual(E.slug("  Estudiantes de La Plata "), "estudiantes-de-la-plata")


class Copas(unittest.TestCase):
    def test_copa_por_defecto_es_la_libertadores(self):
        self.assertEqual(copa_de_argumentos([]), ("libertadores", []))

    def test_copa_elegida(self):
        self.assertEqual(copa_de_argumentos(["--copa", "sudamericana", "2010"]), ("sudamericana", ["2010"]))

    def test_copa_desconocida_corta(self):
        with self.assertRaises(SystemExit):
            copa_de_argumentos(["--copa", "champions"])

    def test_prefijo_js(self):
        self.assertEqual(prefijo_js("mundial"), "window.MUN = window.MUN || {};\n")

    def test_pagina_de_rsssf(self):
        self.assertEqual(COPAS["libertadores"]["rsssf"](1986), "copa86.html")
        self.assertEqual(COPAS["libertadores"]["rsssf"](2005), "copa05.html")
        self.assertEqual(COPAS["libertadores"]["rsssf"](2015), "copa2015.html")


class LeerRsssf(unittest.TestCase):
    def test_fechas(self):
        self.assertEqual(leer_rsssf.fechas_de("Apr 20 & May 3", 1960), ["1960-04-20", "1960-05-03"])
        self.assertEqual(leer_rsssf.fechas_de("24 Apr", 1970), ["1970-04-24"])

    def test_goles_con_cantidad(self):
        local, visitante = leer_rsssf.leer_goles("[Spencer(4), Borges(2); Alcácer]")
        self.assertEqual([g["jugador"] for g in local], ["Spencer"] * 4 + ["Borges"] * 2)
        self.assertEqual([g["jugador"] for g in visitante], ["Alcácer"])

    def test_goles_con_minuto_penal_y_en_contra(self):
        local, visitante = leer_rsssf.leer_goles("[Francescoli 23pen, Alzamendi 70; Gareca 12og]")
        self.assertEqual(local[0], {"jugador": "Francescoli", "min": 23, "tipo": "pen"})
        self.assertEqual(local[1], {"jugador": "Alzamendi", "min": 70, "tipo": None})
        self.assertEqual(visitante[0]["tipo"], "ec")

    def lados(self, texto, gl, gv, mesa=False):
        return [(g["jugador"], g["lado"]) for g in leer_rsssf.goles_por_lado(texto, gl, gv, mesa)]

    def test_goles_que_cuadran_quedan_igual(self):
        self.assertEqual(self.lados("[Perazzo, Castro; Gildo]", 2, 1),
                         [("Perazzo", "local"), ("Castro", "local"), ("Gildo", "visitante")])

    def test_local_sin_goles_lista_solo_al_visitante(self):
        self.assertEqual(self.lados("[Klinger(2), Pizarro]", 0, 3), [("Klinger", "visitante")] * 2 + [("Pizarro", "visitante")])

    def test_empate_sin_punto_y_coma(self):
        self.assertEqual(self.lados("[Pizzi, Morigi]", 1, 1), [("Pizzi", "local"), ("Morigi", "visitante")])

    def test_gol_en_contra_con_punto_y_coma_de_mas(self):
        self.assertEqual(self.lados("[Miño o/g; Usuriaga]", 2, 0), [("Miño", "local"), ("Usuriaga", "local")])
        goles = leer_rsssf.goles_por_lado("[Morales o/g; Marcelinho, Nelio; Camacho(2)]", 3, 2)
        self.assertEqual([g["lado"] for g in goles], ["local"] * 3 + ["visitante"] * 2)

    def test_desempate_escrito_al_reves(self):
        self.assertEqual(self.lados("[Joya, Sasía; Pelé]", 1, 2), [("Pelé", "local"), ("Joya", "visitante"), ("Sasía", "visitante")])

    def test_partido_ganado_en_mesa_no_se_toca(self):
        self.assertEqual(self.lados("[José Sand; Wellington Paulista, Luiz Otávio]", 3, 0, mesa=True),
                         [("José Sand", "local"), ("Wellington Paulista", "visitante"), ("Luiz Otávio", "visitante")])

    def test_lista_incompleta_del_local_queda_del_local(self):
        self.assertEqual(self.lados("[Marzolini]", 2, 0), [("Marzolini", "local")])

    def test_fases(self):
        self.assertEqual(leer_rsssf.fase_de("Quarter-finals"), ("Cuartos de final", "eliminatoria"))
        self.assertEqual(leer_rsssf.fase_de("Final"), ("Final", "eliminatoria"))
        self.assertEqual(leer_rsssf.fase_de("1/8 Finals", "sudamericana"), ("Octavos de final", "eliminatoria"))
        self.assertEqual(leer_rsssf.fase_de("Cualquier cosa"), (None, None))

    def test_partir_sin_cortar_parentesis(self):
        self.assertEqual(leer_rsssf.partir_arriba("Fillol, Passarella (Tarantini, 60), Alonso"),
                         ["Fillol", "Passarella (Tarantini, 60)", "Alonso"])

    def test_formacion_con_cambios_y_dt(self):
        f = leer_rsssf.leer_formacion("Pumpido, Gordillo (65 Gallego), Alonso (c). Coach: Veira")
        self.assertEqual(f["titulares"], ["Pumpido", "Gordillo", "Alonso"])
        self.assertEqual(f["cambios"], [{"sale": "Gordillo", "entra": "Gallego", "min": 65}])
        self.assertEqual(f["dt"], "Veira")


class LeerWikipedia(unittest.TestCase):
    def test_minuto(self):
        self.assertEqual(leer_wikipedia.minuto("90+2"), (90, 2))
        self.assertEqual(leer_wikipedia.minuto("63"), (63, None))
        self.assertEqual(leer_wikipedia.minuto("?"), (None, None))

    def test_resultado(self):
        self.assertEqual(leer_wikipedia.resultado("2–1"), (2, 1))
        self.assertEqual(leer_wikipedia.resultado("sin jugar"), (None, None))

    def test_fechas(self):
        self.assertEqual(leer_wikipedia.fecha_de("{{Start date|1985|12|8}}"), "1985-12-08")
        self.assertEqual(leer_wikipedia.fecha_de("8 December 1985"), "1985-12-08")
        self.assertEqual(leer_wikipedia.fecha_de("December 8, 1985"), "1985-12-08")

    def test_texto_plano_y_pais(self):
        t = "[[Club Atlético Peñarol|Peñarol]] {{flagicon|URU}}"
        self.assertEqual(leer_wikipedia.texto_plano(t), "Peñarol")
        self.assertEqual(leer_wikipedia.pais_de(t), "URU")
        self.assertEqual(leer_wikipedia.pais_de("{{flagicon|FRG}}"), "GER")   # Alemania Federal = Alemania

    def test_goles(self):
        goles = leer_wikipedia.leer_goles("*[[Michel Platini|Platini]] {{goal|63|pen.}} <br> [[Laudrup]] {{goal|2||8}}",
                                          "local")
        self.assertEqual([(g["jugador"], g["min"], g["tipo"]) for g in goles],
                         [("Platini", 63, "pen"), ("Laudrup", 2, None), ("Laudrup", 8, None)])

    def test_fases(self):
        self.assertEqual(leer_wikipedia.fase_de("Group B", "mundial"), "Fase de grupos — Grupo B")
        self.assertEqual(leer_wikipedia.fase_de("Match for third place", "mundial"), "Tercer puesto")
        self.assertEqual(leer_wikipedia.fase_de("Match details", "intercontinental"), "Final")


class LeerEspn(unittest.TestCase):
    def test_minuto(self):
        self.assertEqual(leer_espn.minuto({"displayValue": "90'+7'"}), (90, 7))
        self.assertEqual(leer_espn.minuto({"displayValue": "34'"}), (34, None))
        self.assertEqual(leer_espn.minuto(None), (None, None))

    def test_fecha_local_de_partido_nocturno(self):
        # 01:30 en UTC es 21:30 del día anterior en Sudamérica
        self.assertEqual(leer_espn.fecha_local("2020-03-05T01:30Z"), "2020-03-04")
        self.assertEqual(leer_espn.fecha_local("2020-03-05T20:00Z"), "2020-03-05")


def partido(local, visitante, gl, gv, **extra):
    return {"local": local, "visitante": visitante, "gl": gl, "gv": gv, **extra}


class GanadorDeLlave(unittest.TestCase):
    def test_partido_unico(self):
        self.assertEqual(GD.ganador_llave([partido("river", "boca", 3, 1)]), ("river", "boca"))

    def test_ida_y_vuelta_por_global(self):
        llave = [partido("river", "boca", 2, 2), partido("boca", "river", 1, 3)]
        self.assertEqual(GD.ganador_llave(llave), ("river", "boca"))

    def test_ida_y_vuelta_por_penales(self):
        llave = [partido("river", "boca", 1, 0), partido("boca", "river", 1, 0, pen_l=4, pen_v=2)]
        self.assertEqual(GD.ganador_llave(llave), ("boca", "river"))

    def test_desempate_manda(self):
        llave = [partido("penarol", "palmeiras", 1, 0), partido("palmeiras", "penarol", 1, 0),
                 partido("penarol", "palmeiras", 2, 1, notas="Desempate")]
        self.assertEqual(GD.ganador_llave(llave), ("penarol", "palmeiras"))

    def test_sin_jugar_o_empate_sin_penales(self):
        self.assertEqual(GD.ganador_llave([partido("a", "b", None, None)]), (None, None))
        self.assertEqual(GD.ganador_llave([partido("a", "b", 1, 1)]), (None, None))


class OtrasDeGenerarDatos(unittest.TestCase):
    def test_dias(self):
        self.assertEqual(GD.dias("2024-01-01", "2024-03-01"), 60)
        self.assertEqual(GD.dias("2024-03-01", "2024-01-01"), 60)

    def test_limpiar_saca_lo_vacio(self):
        self.assertEqual(GD.limpiar({"a": 0, "b": None, "c": [], "d": "", "e": {}, "f": "x"}), {"a": 0, "f": "x"})

    def test_base_club(self):
        self.assertEqual(GD.base_club("nacional-par"), "nacional")
        self.assertEqual(GD.base_club("river-plate"), "river-plate")

    def test_cuadra(self):
        goles = [{"equipo": "local"}, {"equipo": "visitante"}]
        self.assertTrue(GD.cuadra(goles, {"gl": 1, "gv": 1}))
        self.assertFalse(GD.cuadra(goles, {"gl": 2, "gv": 0}))

    def test_tanda_que_cuadra_se_queda(self):
        tanda = [{"gol": True, "equipo": "local"}, {"gol": False, "equipo": "visitante"}]
        self.assertIn("tanda", GD.tanda_cuadra({"pen_l": 1, "pen_v": 0, "tanda": tanda}))

    def test_tanda_que_no_cuadra_se_borra(self):
        tanda = [{"gol": True, "equipo": "local"}, {"gol": False, "equipo": "visitante"}]
        self.assertNotIn("tanda", GD.tanda_cuadra({"pen_l": 4, "pen_v": 2, "tanda": tanda}))


class Estadisticas(unittest.TestCase):
    def test_instancia(self):
        self.assertEqual(GE.instancia("Final"), "Final")
        self.assertEqual(GE.instancia("Cuartos de final — Desempate"), "Cuartos de final")
        self.assertEqual(GE.instancia("Segunda fase"), "Octavos de final")
        self.assertIsNone(GE.instancia("Segunda fase", "sudamericana"))
        self.assertEqual(GE.instancia("Segunda ronda", "mundial"), "Cuartos de final")
        self.assertIsNone(GE.instancia("Fase de grupos — Grupo 3"))

    def test_carrera_de_un_jugador_en_dos_clubes(self):
        carreras = GE.juntar_carreras({("Juan Pérez", "river"): {2000: 3, 2001: 2}, ("Juan Pérez", "boca"): {2003: 4}})
        self.assertEqual(len(carreras), 1)
        self.assertEqual(carreras[0]["n"], 9)
        self.assertEqual(carreras[0]["clubes"], ["river", "boca"])

    def test_mismo_apellido_muy_separado_son_dos_personas(self):
        carreras = GE.juntar_carreras({("Silva", "santos"): {1962: 2}, ("Silva", "gremio"): {1995: 1}})
        self.assertEqual(len(carreras), 2)


if __name__ == "__main__":
    unittest.main()
