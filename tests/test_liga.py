"""Pruebas de la liga argentina: el reparto de los partidos en fechas (tools/actualizar_liga.py) y los datos de
data/ligas/argentina/ (cada club juega una vez por fecha, todos los clubes tienen nombre y escudo).

Correr todas:  py -m unittest discover tests   (o doble clic en probar.bat)
"""
import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from actualizar_liga import repartir_fechas  # noqa: E402

DATOS = RAIZ / "data" / "ligas" / "argentina"


def cargar(ruta):
    linea = ruta.read_text(encoding="utf-8").rstrip().splitlines()[-1]
    return json.loads(linea.split(" = ", 1)[1].rstrip(";"))


def partido(local, visitante, dia):
    return {"local": local, "visitante": visitante, "hora_utc": f"2026-08-{dia:02d}T22:00Z"}


class RepartirFechas(unittest.TestCase):
    def test_postergado(self):
        # cuatro clubes, tres fechas (fin de semana del 1, del 8 y del 15). A-B de la fecha 1 se juega el miércoles 12
        ps = [partido("C", "D", 1),
              partido("A", "C", 8), partido("B", "D", 8),
              partido("A", "D", 15), partido("B", "C", 15),
              partido("A", "B", 12)]
        repartir_fechas(ps, 3)
        self.assertEqual([p["fecha_n"] for p in ps], [1, 2, 2, 3, 3, 1])

    def test_fecha_con_dia_libre(self):
        # una fecha jugada viernes y lunes (con el sábado y el domingo sin partidos) sigue siendo una sola
        ps = [partido("A", "B", 7), partido("C", "D", 10), partido("A", "C", 14), partido("B", "D", 14)]
        repartir_fechas(ps, 2)
        self.assertEqual([p["fecha_n"] for p in ps], [1, 1, 2, 2])


class DatosLiga(unittest.TestCase):
    def test_torneos(self):
        indice = cargar(DATOS / "indice.js")
        self.assertTrue(indice)
        for t in indice:
            with self.subTest(torneo=t["clave"]):
                d = cargar(DATOS / f"{t['clave']}.js")
                ids = {i for zona in d["zonas"].values() for i in zona}
                self.assertEqual(len(ids), sum(len(z) for z in d["zonas"].values()), "un club en dos zonas")
                for f in d["fechas"]:
                    clubes = [c for p in f["partidos"] for c in (p["local"], p["visitante"])]
                    self.assertEqual(len(clubes), len(set(clubes)), f"fecha {f['numero']}: un club juega dos veces")
                    self.assertTrue(set(clubes) <= ids, f"fecha {f['numero']}: club fuera de las zonas")
                for p in [p for f in d["fechas"] for p in f["partidos"]] + [p for r in d["playoffs"] for p in r["partidos"]]:
                    self.assertEqual("gl" in p, "gv" in p)
                    if "gl" in p and p.get("goles"):   # los goles cuadran con el resultado
                        self.assertEqual(sum(g["equipo"] == "local" for g in p["goles"]), p["gl"], p)
                        self.assertEqual(sum(g["equipo"] == "visitante" for g in p["goles"]), p["gv"], p)
                for cid, c in d["clubes"].items():
                    self.assertTrue(c["nombre"], cid)
                    self.assertTrue(c["escudo"] and (RAIZ / c["escudo"]).exists(), f"falta el escudo de {cid}")


if __name__ == "__main__":
    unittest.main()
