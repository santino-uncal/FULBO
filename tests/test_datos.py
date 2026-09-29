"""Pruebas de los datos de data/: que lo que muestra la página sea coherente (en las cuatro copas).

Correr todas:  py -m unittest discover tests   (o doble clic en probar.bat)
"""
import json
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from copas import COPAS  # noqa: E402
from generar_historial import leer_ediciones  # noqa: E402

# Ediciones cuyo campeón no jugó la final (la Sudamericana 2016 se le dio al Chapecoense tras el accidente)
CAMPEON_SIN_FINAL = {("sudamericana", 2016)}
# Partidos ganados en los escritorios: los goles son los de la cancha y el resultado, el que se dio por reglamento
GANADOS_EN_MESA = {("libertadores", 1966, "alianza-lima", "universitario"),
                   ("libertadores", 2017, "lanus", "chapecoense"),        # Chapecoense incluyó a un jugador suspendido
                   ("libertadores", 2019, "defensor-sporting", "barcelona")}


def cargar(ruta):
    """Lee un archivo de data/ ('window.LIB.indice = [...];') y devuelve lo que tiene adentro."""
    linea = ruta.read_text(encoding="utf-8").rstrip().splitlines()[-1]
    return json.loads(linea.split(" = ", 1)[1].rstrip(";"))


EQUIPOS = cargar(RAIZ / "data" / "equipos.js")
EDICIONES = {clave: leer_ediciones(clave) for clave in COPAS}


def partidos(clave):
    for anio, ed in EDICIONES[clave].items():
        for fase in ed["fases"]:
            for p in fase["partidos"]:
                yield anio, fase["nombre"], p


def describir(anio, fase, p):
    return f"{anio} {fase}: {p['local']} {p.get('gl')}-{p.get('gv')} {p['visitante']}"


class Catalogo(unittest.TestCase):
    def test_cada_club_tiene_nombre_y_pais(self):
        for id_, eq in EQUIPOS.items():
            if id_ == "a-definir":   # rival todavía no conocido (llaves sin jugar)
                continue
            with self.subTest(club=id_):
                self.assertTrue(eq.get("nombre"))
                self.assertRegex(eq.get("pais") or "", r"^[A-Z]{3}$")

    def test_colores_validos(self):
        for id_, eq in EQUIPOS.items():
            for color in eq.get("colores") or []:
                with self.subTest(club=id_):
                    self.assertRegex(color, r"^#[0-9a-fA-F]{6}$")

    def test_ruta_del_escudo(self):
        # Que el archivo no exista no es un error: la página oculta los escudos que todavía no se descargaron
        for id_, eq in EQUIPOS.items():
            if eq.get("escudo"):
                with self.subTest(club=id_):
                    self.assertEqual(eq["escudo"], f"assets/escudos/{id_}.png")


class Ediciones(unittest.TestCase):
    def test_indice_y_ediciones_coinciden(self):
        for clave, copa in COPAS.items():
            with self.subTest(copa=clave):
                indice = cargar(copa["data"] / "indice.js")
                self.assertEqual([e["anio"] for e in indice], list(EDICIONES[clave]))
                for e in indice:
                    ed = EDICIONES[clave][e["anio"]]
                    self.assertEqual((e["campeon"], e["subcampeon"]), (ed.get("campeon"), ed.get("subcampeon")),
                                     f"{clave} {e['anio']}")

    def test_campeon_jugo_la_final(self):
        for clave in COPAS:
            for anio, ed in EDICIONES[clave].items():
                if not ed.get("campeon") or (clave, anio) in CAMPEON_SIN_FINAL:
                    continue
                with self.subTest(copa=clave, anio=anio):
                    finalistas = {p[lado] for f in ed["fases"] if f["nombre"].startswith("Final")
                                  for p in f["partidos"] for lado in ("local", "visitante")}
                    self.assertIn(ed["campeon"], finalistas)

    def test_clubes_estan_en_el_catalogo(self):
        for clave in COPAS:
            faltan = {p[lado] for _, _, p in partidos(clave) for lado in ("local", "visitante")} - set(EQUIPOS)
            with self.subTest(copa=clave):
                self.assertEqual(faltan, set())

    def test_ids_de_partido_no_se_repiten(self):
        for clave in COPAS:
            ids = [p.get("id") for _, _, p in partidos(clave) if p.get("id")]
            with self.subTest(copa=clave):
                self.assertEqual(len(ids), len(set(ids)))

    def test_resultados_validos(self):
        for clave in COPAS:
            for anio, fase, p in partidos(clave):
                if p.get("gl") is None:
                    continue
                with self.subTest(copa=clave, partido=describir(anio, fase, p)):
                    self.assertTrue(isinstance(p["gl"], int) and p["gl"] >= 0)
                    self.assertTrue(isinstance(p["gv"], int) and p["gv"] >= 0)
                    self.assertNotEqual(p["local"], p["visitante"])

    def test_fechas_validas_y_del_anio(self):
        for clave in COPAS:
            for anio, fase, p in partidos(clave):
                if not p.get("fecha"):
                    continue
                with self.subTest(copa=clave, partido=describir(anio, fase, p)):
                    self.assertRegex(p["fecha"], r"^\d{4}-\d{2}-\d{2}$")
                    # La Libertadores de un año puede terminar a principios del siguiente
                    self.assertIn(int(p["fecha"][:4]), (anio - 1, anio, anio + 1))

    def test_penales_completos(self):
        for clave in COPAS:
            for anio, fase, p in partidos(clave):
                with self.subTest(copa=clave, partido=describir(anio, fase, p)):
                    self.assertEqual(p.get("pen_l") is None, p.get("pen_v") is None)
                    if p.get("pen_l") is not None:
                        self.assertNotEqual(p["pen_l"], p["pen_v"])

    def test_tanda_coincide_con_el_resultado_de_penales(self):
        for clave in COPAS:
            for anio, fase, p in partidos(clave):
                if not p.get("tanda"):
                    continue
                with self.subTest(copa=clave, partido=describir(anio, fase, p)):
                    self.assertEqual(sum(r["gol"] and r["equipo"] == "local" for r in p["tanda"]), p["pen_l"])
                    self.assertEqual(sum(r["gol"] and r["equipo"] == "visitante" for r in p["tanda"]), p["pen_v"])

    def test_goles_cuadran_con_el_resultado(self):
        malos = []
        for clave in COPAS:
            for anio, fase, p in partidos(clave):
                goles = p.get("goles") or []
                if p.get("gl") is None or (clave, anio, p["local"], p["visitante"]) in GANADOS_EN_MESA:
                    continue
                if (sum(g["equipo"] == "local" for g in goles) > p["gl"]
                        or sum(g["equipo"] == "visitante" for g in goles) > p["gv"]):
                    malos.append(f"{clave} {describir(anio, fase, p)}")
        self.assertEqual(malos, [], f"{len(malos)} partidos con goles de más de un lado")


class Portada(unittest.TestCase):
    def test_links_de_copas_de_los_continentes(self):
        """Los links de data/continentes.js a copas cargadas tienen que ser de copas que existen."""
        texto = (RAIZ / "data" / "continentes.js").read_text(encoding="utf-8")
        for copa in re.findall(r"copa=([a-z]+)", texto):
            with self.subTest(copa=copa):
                self.assertIn(copa, COPAS)


if __name__ == "__main__":
    unittest.main()
