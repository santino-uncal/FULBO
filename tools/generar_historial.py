"""Arma data/historial.js: el historial de cada club en la Copa (ediciones, títulos, partidos, goleadores…).

Se calcula a partir de data/ediciones/*.js, así la página no tiene que cargar todas las ediciones para
mostrar la ficha de un equipo. Lo llama generar_datos.py al final; también se puede correr solo:
    python tools/generar_historial.py
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"


def leer_ediciones():
    eds = {}
    for ruta in (DATA / "ediciones").glob("*.js"):
        texto = ruta.read_text(encoding="utf-8")
        cuerpo = texto[texto.index("] = ") + 4:].rstrip().rstrip(";")
        ed = json.loads(cuerpo)
        eds[ed["anio"]] = ed
    return dict(sorted(eds.items()))


def ficha_vacia():
    return {"pj": 0, "g": 0, "e": 0, "p": 0, "gf": 0, "gc": 0}


def sumar(f, a, b):
    f["pj"] += 1
    f["gf"] += a
    f["gc"] += b
    f["g" if a > b else "p" if a < b else "e"] += 1


def main():
    eds = leer_ediciones()
    clubes = {}
    club = lambda id_: clubes.setdefault(id_, {"ediciones": [], "total": ficha_vacia(), "rivales": {},
                                               "goleadores": {}, "mayorVictoria": None, "peorDerrota": None})
    for anio, ed in eds.items():
        por_edicion = {}   # club -> {anio, fase, pj…}
        for fase in ed["fases"]:
            etapa = re.sub(r" — .*$", "", fase["nombre"])
            for p in fase["partidos"]:
                for lado, id_ in (("local", p["local"]), ("visitante", p["visitante"])):
                    if not id_ or id_ == "a-definir":
                        continue
                    c = club(id_)
                    e = por_edicion.setdefault(id_, {"anio": anio, **ficha_vacia()})
                    e["fase"] = etapa   # la última fase que jugó (las fases vienen en orden)
                    if p.get("gl") is None or p.get("gv") is None:
                        continue   # partido sin jugar
                    a, b = (p["gl"], p["gv"]) if lado == "local" else (p["gv"], p["gl"])
                    rival = p["visitante"] if lado == "local" else p["local"]
                    sumar(e, a, b)
                    sumar(c["total"], a, b)
                    fr = c["rivales"].setdefault(rival, {**ficha_vacia(), "partidos": []})
                    sumar(fr, a, b)
                    # Cada partido contra ese rival: [año, fase, goles a favor, en contra, 1 si fue local, penales…]
                    pen = [p.get("pen_l"), p.get("pen_v")][::1 if lado == "local" else -1]
                    fr["partidos"].append([anio, fase["nombre"], a, b, int(lado == "local")] +
                                          (pen if p.get("pen_l") is not None else []))
                    resumen = {"anio": anio, "fase": fase["nombre"], "rival": rival, "gf": a, "gc": b,
                               "local": lado == "local"}
                    # Mayor diferencia; a igual diferencia, la de más goles
                    clave = lambda r: (r["gf"] - r["gc"], r["gf"])
                    if a > b and (not c["mayorVictoria"] or clave(resumen) > clave(c["mayorVictoria"])):
                        c["mayorVictoria"] = resumen
                    clave_d = lambda r: (r["gc"] - r["gf"], r["gc"])
                    if a < b and (not c["peorDerrota"] or clave_d(resumen) > clave_d(c["peorDerrota"])):
                        c["peorDerrota"] = resumen
                for g in p.get("goles", []):
                    id_ = p.get(g.get("equipo"))
                    if not id_ or g.get("tipo") == "ec" or not g.get("jugador"):
                        continue   # los goles en contra no suman al goleador
                    gol = club(id_)["goleadores"].setdefault(g.get("jid") or g["jugador"],
                                                             {"nombre": g["jugador"], "n": 0, "anios": set()})
                    gol["n"] += 1
                    gol["anios"].add(anio)
        for id_, e in por_edicion.items():
            if id_ == ed.get("campeon"):
                e["fase"] = "Campeón"
            elif id_ == ed.get("subcampeon"):
                e["fase"] = "Subcampeón"
            clubes[id_]["ediciones"].append(e)

    salida = {}
    for id_, c in clubes.items():
        if id_ == "a-definir":
            continue
        # Todos los rivales (la página muestra los 10 más frecuentes y el resto con "Ver todos")
        rivales = sorted(c["rivales"].items(), key=lambda x: (-x[1]["pj"], -x[1]["g"]))
        goleadores = sorted(c["goleadores"].values(), key=lambda x: (-x["n"], x["nombre"]))[:15]
        salida[id_] = {
            "ediciones": c["ediciones"],
            "titulos": [e["anio"] for e in c["ediciones"] if e["fase"] == "Campeón"],
            "finales": [e["anio"] for e in c["ediciones"] if e["fase"] == "Subcampeón"],
            "total": c["total"],
            "mayorVictoria": c["mayorVictoria"],
            "peorDerrota": c["peorDerrota"],
            "rivales": [{"id": r, **f} for r, f in rivales],
            "goleadores": [{"nombre": g["nombre"], "n": g["n"], "anios": [min(g["anios"]), max(g["anios"])]}
                           for g in goleadores],
        }
    cuerpo = json.dumps(salida, ensure_ascii=False, separators=(",", ":"))
    (DATA / "historial.js").write_text(
        "/* Generado por tools/generar_historial.py — no editar a mano */\nwindow.LIB = window.LIB || {};\n"
        "window.LIB.historial = " + cuerpo + ";\n", encoding="utf-8")
    print(f"historial.js: {len(salida)} clubes")


if __name__ == "__main__":
    main()
