"""Arma data/estadisticas.js: las estadísticas históricas de toda la Copa (goleadores de siempre, goleador de
cada edición, goleadores por instancia, títulos por club y país, goleadas, etc.).

Se calcula a partir de data/ediciones/*.js, así la página no tiene que cargar todas las ediciones.
Lo llama generar_datos.py al final; también se puede correr solo:
    python tools/generar_estadisticas.py
"""
import json
import re
from collections import defaultdict

from generar_historial import DATA, leer_ediciones

# Instancias de mata-mata (las "Semifinales — Grupo N" de los años 60-80 eran grupos, no cuentan)
INSTANCIAS = ["Octavos de final", "Cuartos de final", "Semifinales", "Final"]


def instancia(nombre_fase):
    base = re.sub(r" — Desempate$", "", nombre_fase)
    return base if base in INSTANCIAS else None


def goles_validos(ed):
    """Cada gol con autor (sin los goles en contra), con el partido y la fase donde se hizo."""
    for fase in ed["fases"]:
        for p in fase["partidos"]:
            for g in p.get("goles") or []:
                id_ = p.get(g.get("equipo"))
                if id_ and g.get("tipo") != "ec" and g.get("jugador"):
                    yield g, p, fase["nombre"], id_


def juntar_carreras(unidades):
    """unidades: {(nombre, club): {anio: goles}}. Devuelve jugadores con sus clubes.

    En los años viejos las fuentes traen solo el apellido: dos "Silva" pueden ser personas distintas,
    incluso en el mismo club con años de diferencia. Por eso cada nombre en cada club se corta en tramos
    sin huecos largos, y los tramos de un mismo nombre se juntan solo si parecen la misma carrera:
    nunca en dos clubes el mismo año y sin huecos largos entre un club y el siguiente.
    """
    por_nombre = defaultdict(list)
    for (nombre, club), por_anio in unidades.items():
        hueco_club = 10 if " " in nombre.strip() else 8   # en el mismo club se tolera un hueco más largo
        tramo = None
        for anio in sorted(por_anio):
            if tramo is None or anio - max(tramo["anios"]) > hueco_club:
                tramo = {"club": club, "n": 0, "anios": set()}
                por_nombre[nombre].append(tramo)
            tramo["n"] += por_anio[anio]
            tramo["anios"].add(anio)
    jugadores = []
    for nombre, lista in por_nombre.items():
        hueco_max = 6 if " " in nombre.strip() else 3
        # Si el mismo nombre aparece en dos clubes a la vez en más de un año, es un apellido común
        # (varios "Da Silva"): no se juntan clubes, cada uno queda por separado
        clubes_por_anio = defaultdict(set)
        for u in lista:
            for a in u["anios"]:
                clubes_por_anio[a].add(u["club"])
        comun = sum(len(c) > 1 for c in clubes_por_anio.values()) > 1
        lista.sort(key=lambda u: (min(u["anios"]), -u["n"]))   # a igual año, primero el tramo con más goles
        carreras = []
        for u in lista:
            destino = None
            for c in carreras:
                if (not comun and not c["anios"] & u["anios"] and min(u["anios"]) - max(c["anios"]) <= hueco_max
                        and max(u["anios"]) - min(c["anios"]) <= 18):
                    destino = c
                    break
            if destino is None:
                carreras.append({"nombre": nombre, "n": 0, "anios": set(), "clubes": []})
                destino = carreras[-1]
            destino["n"] += u["n"]
            destino["anios"] |= u["anios"]
            if u["club"] not in destino["clubes"]:
                destino["clubes"].append(u["club"])
        jugadores += carreras
    return jugadores


def resumen_jugador(j):
    return {"nombre": j["nombre"], "n": j["n"], "clubes": j["clubes"],
            "anios": [min(j["anios"]), max(j["anios"])], "ediciones": len(j["anios"])}


def ranking(unidades, cuantos):
    jugadores = sorted(juntar_carreras(unidades), key=lambda j: (-j["n"], min(j["anios"]), j["nombre"]))
    return [resumen_jugador(j) for j in jugadores[:cuantos]]


def sumar(unidades, nombre, club, anio):
    u = unidades.setdefault((nombre, club), {})
    u[anio] = u.get(anio, 0) + 1


def partido_corto(p, anio, fase):
    return {"anio": anio, "fase": fase, "fecha": p.get("fecha"), "local": p["local"], "visitante": p["visitante"],
            "gl": p["gl"], "gv": p["gv"]}


def main():
    eds = leer_ediciones()
    equipos_js = (DATA / "equipos.js").read_text(encoding="utf-8")
    equipos = json.loads(equipos_js[equipos_js.index(".equipos = ") + 11:].rstrip().rstrip(";"))

    goleadores = {}                               # (nombre, club) -> {n, anios}
    asistidores = {}
    por_instancia = {i: {} for i in INSTANCIAS}
    goleador_edicion = []
    goles_edicion = []
    en_un_partido = []                            # jugadores con varios goles en un mismo partido
    partidos = []                                 # todos los partidos jugados, para goleadas

    for anio, ed in eds.items():
        # Goleador de la edición: igual que en la página, se cuenta por id de jugador (o nombre + club)
        cuenta = {}
        for g, p, fase, club in goles_validos(ed):
            sumar(goleadores, g["jugador"], club, anio)
            if instancia(fase):
                sumar(por_instancia[instancia(fase)], g["jugador"], club, anio)
            clave = g.get("jid") or f'{g["jugador"]}|{club}'
            cuenta.setdefault(clave, {"nombre": g["jugador"], "equipo": club, "n": 0})["n"] += 1
        if cuenta:
            maximo = max(c["n"] for c in cuenta.values())
            goleador_edicion.append({"anio": anio, "n": maximo, "jugadores": sorted(
                [{"nombre": c["nombre"], "equipo": c["equipo"]} for c in cuenta.values() if c["n"] == maximo],
                key=lambda c: c["nombre"])})

        n_partidos = n_goles = 0
        for fase in ed["fases"]:
            for p in fase["partidos"]:
                if p.get("gl") is None or p.get("gv") is None:
                    continue
                n_partidos += 1
                n_goles += p["gl"] + p["gv"]
                partidos.append(partido_corto(p, anio, fase["nombre"]))
                por_autor = defaultdict(int)
                for g in p.get("goles") or []:
                    club = p.get(g.get("equipo"))
                    if g.get("asistencia") and club:
                        sumar(asistidores, g["asistencia"], club, anio)
                    if club and g.get("tipo") != "ec" and g.get("jugador"):
                        por_autor[(g.get("jid") or g["jugador"], g["jugador"], club)] += 1
                for (_, nombre, club), n in por_autor.items():
                    if n >= 3:
                        en_un_partido.append({"nombre": nombre, "equipo": club, "n": n,
                                              "partido": partido_corto(p, anio, fase["nombre"])})
        goles_edicion.append({"anio": anio, "partidos": n_partidos, "goles": n_goles})

    # Títulos y finales por club y por país
    titulos = defaultdict(lambda: {"titulos": [], "finales": []})
    for anio, ed in eds.items():
        if ed.get("campeon"):
            titulos[ed["campeon"]]["titulos"].append(anio)
        if ed.get("subcampeon"):
            titulos[ed["subcampeon"]]["finales"].append(anio)
    clubes_titulos = sorted(({"id": id_, **t} for id_, t in titulos.items()),
                            key=lambda c: (-len(c["titulos"]), -len(c["finales"]), c["titulos"][:1] or [9999]))
    paises = defaultdict(lambda: {"titulos": 0, "finales": 0, "clubes": set()})
    for c in clubes_titulos:
        pais = equipos.get(c["id"], {}).get("pais", "?")
        paises[pais]["titulos"] += len(c["titulos"])
        paises[pais]["finales"] += len(c["finales"])
        if c["titulos"]:
            paises[pais]["clubes"].add(c["id"])
    paises_titulos = sorted(({"pais": p, "titulos": v["titulos"], "finales": v["finales"],
                              "clubes": len(v["clubes"])} for p, v in paises.items()),
                            key=lambda x: (-x["titulos"], -x["finales"]))

    # Clubes con más partidos en la historia (sale de historial.js, que ya está calculado)
    hist_js = (DATA / "historial.js").read_text(encoding="utf-8")
    historial = json.loads(hist_js[hist_js.index(".historial = ") + 13:].rstrip().rstrip(";"))
    clubes_partidos = sorted(({"id": id_, "ediciones": len(h["ediciones"]), **h["total"]}
                              for id_, h in historial.items()), key=lambda c: (-c["pj"], -c["g"]))[:25]

    goleadas = sorted(partidos, key=lambda p: (-abs(p["gl"] - p["gv"]), -(p["gl"] + p["gv"]), p["anio"]))[:15]
    mas_goles = sorted(partidos, key=lambda p: (-(p["gl"] + p["gv"]), p["anio"]))[:15]
    en_un_partido.sort(key=lambda x: (-x["n"], x["partido"]["anio"]))

    salida = {
        "goleadores": ranking(goleadores, 50),
        "asistidores": ranking(asistidores, 25),
        "goleadorEdicion": goleador_edicion,
        "porInstancia": {i: ranking(u, 15) for i, u in por_instancia.items()},
        "clubesTitulos": clubes_titulos,
        "paisesTitulos": paises_titulos,
        "clubesPartidos": clubes_partidos,
        "goleadas": goleadas,
        "masGoles": mas_goles,
        "tripletes": en_un_partido[:40],
        "tripletesTotal": len(en_un_partido),
        "golesEdicion": goles_edicion,
    }
    cuerpo = json.dumps(salida, ensure_ascii=False, separators=(",", ":"))
    (DATA / "estadisticas.js").write_text(
        "/* Generado por tools/generar_estadisticas.py — no editar a mano */\nwindow.LIB = window.LIB || {};\n"
        "window.LIB.estadisticas = " + cuerpo + ";\n", encoding="utf-8")
    print(f"estadisticas.js: {len(goleador_edicion)} ediciones, {len(partidos)} partidos")


if __name__ == "__main__":
    main()
