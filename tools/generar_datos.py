"""Genera todos los archivos de data/ a partir de lo descargado de RSSSF y ESPN.

Uso:  python tools/generar_datos.py
Antes hay que haber corrido tools/descargar_rsssf.py y tools/descargar_espn.py.

Cómo combina las fuentes:
  - 1960–2004: solo RSSSF (resultados, goleadores; formaciones de algunas finales).
  - 2005–2024: RSSSF es la base (lista completa de partidos) y cada partido se completa
    con el detalle de ESPN (goles con minuto y asistencia, formaciones, árbitro, público).
  - 2025 en adelante: solo ESPN.
Al final imprime un control de calidad por edición.
"""
import collections
import datetime
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import equipos as E  # noqa: E402
import leer_espn  # noqa: E402
import leer_rsssf  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
CACHE = RAIZ / "tools" / "cache"

ORDEN_FASES = ["Fase previa", "Primera fase previa", "Segunda fase previa", "Tercera fase previa",
               "Primera fase", "Fase de grupos", "Segunda fase", "Tercera fase", "Octavos de final",
               "Cuartos de final", "Semifinales", "Tercer puesto", "Final"]


def anios_rsssf():
    res = []
    for f in (CACHE / "rsssf").glob("copa*.html"):
        m = re.match(r"copa(\d+)\.html$", f.name)
        if m:
            n = int(m.group(1))
            res.append(n if n > 100 else (1900 + n if n >= 60 else 2000 + n))
    return sorted(res)


def anios_espn():
    return sorted(int(d.name) for d in (CACHE / "espn").glob("*") if (d / "calendario.json").exists())


def dias(a, b):
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


# ---------------------------------------------------------------- clubes
def asignar_clubes_rsssf(rs, cat):
    R = E.Resolutor(rs)
    sin_pais = set()
    for a, r in rs.items():
        for p in r["partidos"]:
            for lado in ("local", "visitante"):
                crudo = p[lado]
                pais = R.pais(a, p, crudo)
                if not pais:
                    sin_pais.add(f"{a}|{crudo}")
                p[lado + "_id"] = cat.id_de(crudo, pais, r["ciudades"].get(crudo))
    return sin_pais


def emparejar(rs_ed, es_ed, espn_a_club):
    """Empareja partidos ESPN con RSSSF de la misma edición (fecha ±2 días, mismo resultado).
    Devuelve {id_espn: partido_rsssf} y suma votos espn_equipo -> club."""
    pares = {}
    usados = set()
    jugados = [p for p in es_ed["partidos"] if p["jugado"]]
    # 1ra pasada: fecha + resultado, solo si hay un único candidato
    for pe in jugados:
        cand = [pr for pr in rs_ed["partidos"] if pr.get("fecha") and pr["gl"] is not None
                and dias(pr["fecha"], pe["fecha"]) <= 2 and (pr["gl"], pr["gv"]) == (pe["gl"], pe["gv"])]
        if len(cand) == 1 and id(cand[0]) not in usados:
            pares[pe["espn"]] = cand[0]
            usados.add(id(cand[0]))
            espn_a_club[pe["local_espn"]][cand[0]["local_id"]] += 1
            espn_a_club[pe["visitante_espn"]][cand[0]["visitante_id"]] += 1
    return pares, usados


def emparejar_por_club(rs_ed, es_ed, pares, usados, mapa):
    """2da pasada: con los clubes ya conocidos, emparejar por fecha y clubes."""
    for pe in es_ed["partidos"]:
        if not pe["jugado"] or pe["espn"] in pares:
            continue
        l, v = mapa.get(pe["local_espn"]), mapa.get(pe["visitante_espn"])
        cand = [pr for pr in rs_ed["partidos"] if id(pr) not in usados and pr.get("fecha")
                and dias(pr["fecha"], pe["fecha"]) <= 3 and {pr["local_id"], pr["visitante_id"]} == {l, v}]
        if cand:
            pr = min(cand, key=lambda x: dias(x["fecha"], pe["fecha"]))
            pares[pe["espn"]] = pr
            usados.add(id(pr))


# ---------------------------------------------------------------- partidos
def goles_rsssf(p):
    return [{"jugador": g["jugador"], "min": g.get("min"), "tipo": g.get("tipo"), "equipo": g["lado"]}
            for g in p.get("goles", [])]


def goles_espn(p):
    res = []
    for g in p.get("goles", []):
        x = {"jugador": g["jugador"], "jid": g.get("jid"), "min": g["min"], "equipo": g["lado"]}
        if g.get("extra"):
            x["extra"] = g["extra"]
        if g.get("tipo"):
            x["tipo"] = g["tipo"]
        if g.get("asistencia"):
            x["asistencia"], x["aid"] = g["asistencia"], g.get("aid")
        res.append(x)
    return res


def formaciones_rsssf(p):
    """Formaciones de RSSSF (solo nombres): asignarlas a local/visitante por parecido del nombre."""
    crudas = p.get("formaciones_crudas") or {}
    res = {}
    for i, (clave, f) in enumerate(crudas.items()):
        n = E.normalizar(clave)
        sim = {lado: difflib.SequenceMatcher(None, n, E.normalizar(p[lado])).ratio() for lado in ("local", "visitante")}
        lado = max(sim, key=sim.get) if max(sim.values()) > 0.5 else ("local", "visitante")[min(i, 1)]
        if lado in res:
            lado = "visitante" if lado == "local" else "local"
        res[lado] = {"titulares": [{"nombre": t} for t in f["titulares"]],
                     "suplentes": [{"nombre": c["entra"], "min": c["min"], "por": c["sale"], "jugo": True}
                                   for c in f["cambios"]],
                     "dt": f.get("dt")}
    return res


def limpiar(d):
    return {k: v for k, v in d.items() if v not in (None, [], {}, "")}


def partido_final(p, local, visitante, fuente_goles, espn=None):
    x = {"fecha": p.get("fecha"), "local": local, "visitante": visitante, "gl": p.get("gl"), "gv": p.get("gv"),
         "pen_l": p.get("pen_l"), "pen_v": p.get("pen_v"), "estadio": p.get("estadio"),
         "ciudad": p.get("ciudad"), "arbitro": p.get("arbitro"), "publico": p.get("publico"),
         "notas": p.get("notas"), "llave": p.get("llave"), "goles": fuente_goles,
         "formaciones": p.get("formaciones_final")}
    if espn:
        x["espn"] = espn
    return limpiar(x)


# ---------------------------------------------------------------- campeón
def ganador_llave(partidos):
    """Ganador de una llave (1, 2 o 3 partidos). Devuelve (ganador, perdedor) o (None, None)."""
    jug = [p for p in partidos if p.get("gl") is not None]
    if not jug:
        return None, None
    a, b = jug[0]["local"], jug[0]["visitante"]
    desempate = [p for p in jug if "desempate" in (p.get("notas") or "").lower() or p.get("_desempate")]
    ult = desempate[-1] if desempate else jug[-1]
    if desempate or len(jug) == 1:
        if ult["gl"] != ult["gv"]:
            return (ult["local"], ult["visitante"]) if ult["gl"] > ult["gv"] else (ult["visitante"], ult["local"])
        if ult.get("pen_l") is not None:
            return (ult["local"], ult["visitante"]) if ult["pen_l"] > ult["pen_v"] else (ult["visitante"], ult["local"])
        return None, None
    ga = sum(p["gl"] if p["local"] == a else p["gv"] for p in jug)
    gb = sum(p["gv"] if p["local"] == a else p["gl"] for p in jug)
    if ga != gb:
        return (a, b) if ga > gb else (b, a)
    if ult.get("pen_l") is not None:
        gana_local = ult["pen_l"] > ult["pen_v"]
        g = ult["local"] if gana_local else ult["visitante"]
        return (g, b if g == a else a)
    return None, None


# ---------------------------------------------------------------- planteles
def armar_planteles(partidos):
    """Planteles a partir de formaciones y goles: quién jugó, cuántos partidos, goles y asistencias."""
    pl = collections.defaultdict(dict)

    def ficha(club, jid, nombre):
        clave = jid or nombre
        return pl[club].setdefault(clave, {"id": jid, "nombre": nombre, "pj": 0, "tit": 0, "goles": 0,
                                           "asist": 0, "num": collections.Counter(), "pos": collections.Counter()})

    for p in partidos:
        for lado in ("local", "visitante"):
            club = p[lado]
            f = (p.get("formaciones") or {}).get(lado)
            if f:
                for j in f.get("titulares", []):
                    x = ficha(club, j.get("id"), j["nombre"])
                    x["pj"] += 1
                    x["tit"] += 1
                    if j.get("num"):
                        x["num"][j["num"]] += 1
                    if j.get("pos"):
                        x["pos"][j["pos"]] += 1
                for j in f.get("suplentes", []):
                    x = ficha(club, j.get("id"), j["nombre"])
                    if j.get("jugo"):
                        x["pj"] += 1
                    if j.get("num"):
                        x["num"][j["num"]] += 1
                    if j.get("pos") and j["pos"] != "SUB":
                        x["pos"][j["pos"]] += 1
        for g in p.get("goles", []):
            if g.get("tipo") == "ec" or not g.get("jugador"):
                continue
            club = p[g["equipo"]]
            ficha(club, g.get("jid"), g["jugador"])["goles"] += 1
            if g.get("asistencia"):
                ficha(club, g.get("aid"), g["asistencia"])["asist"] += 1
    res = {}
    for club, jugadores in pl.items():
        lista = []
        for x in jugadores.values():
            x["num"] = x["num"].most_common(1)[0][0] if x["num"] else None
            x["pos"] = x["pos"].most_common(1)[0][0] if x["pos"] else None
            lista.append(limpiar(x))
        lista.sort(key=lambda j: (-j["pj"], -j["goles"], j.get("nombre") or ""))
        res[club] = lista
    return res


# ---------------------------------------------------------------- principal
def main():
    cat = E.Catalogo()
    ajustes = E.cargar_ajustes()
    rs = {a: leer_rsssf.leer(a) for a in anios_rsssf()}
    es = {a: leer_espn.leer(a) for a in anios_espn()}
    sin_pais = asignar_clubes_rsssf(rs, cat)

    # ESPN -> club: votos por emparejamiento de partidos
    votos = collections.defaultdict(collections.Counter)
    pares_por_anio = {}
    for a in es:
        if a in rs:
            pares_por_anio[a] = emparejar(rs[a], es[a], votos)
    mapa = {eid: v.most_common(1)[0][0] for eid, v in votos.items()}
    mapa.update(ajustes.get("espn", {}))
    for a, (pares, usados) in pares_por_anio.items():
        emparejar_por_club(rs[a], es[a], pares, usados, mapa)
    # Clubes de ESPN que nunca aparecieron en RSSSF (ediciones nuevas)
    info_espn = {}
    for a in es:
        info_espn.update(es[a]["equipos"])
    for eid, t in info_espn.items():
        if eid not in mapa:
            # buscar un club con el mismo nombre; si no hay, es un club nuevo
            norm = E.normalizar(t["nombre"])
            por_nombre = [i for i in cat.clubes if any(E.normalizar(n) == norm for n in cat.nombres[i])]
            mapa[eid] = por_nombre[0] if len(por_nombre) == 1 else \
                cat.id_de(t["nombre"], ajustes.get("pais_espn", {}).get(eid))
        cat.clubes[mapa[eid]]["espn"].add(eid)

    ediciones, indice, control = {}, [], []
    for a in sorted(set(rs) | set(es)):
        partidos = []
        faltan_espn = 0
        if a in rs:
            pares = pares_por_anio.get(a, ({}, set()))[0]
            por_rsssf = {id(pr): pe_id for pe_id, pr in pares.items()}
            espn_por_id = {p["espn"]: p for p in es.get(a, {"partidos": []})["partidos"]}
            for pr in rs[a]["partidos"]:
                pe = espn_por_id.get(por_rsssf.get(id(pr)))
                goles = goles_rsssf(pr)
                forms = formaciones_rsssf(pr) or None
                extra = {}
                if pe:
                    invertido = mapa.get(pe["local_espn"]) == pr["visitante_id"] and \
                        mapa.get(pe["visitante_espn"]) == pr["local_id"]
                    ge = goles_espn(pe)
                    if invertido:  # ESPN tomó como local al otro (cancha neutral)
                        for g in ge:
                            g["equipo"] = "visitante" if g["equipo"] == "local" else "local"
                    if len(ge) == (pr["gl"] or 0) + (pr["gv"] or 0):
                        goles = ge
                    if pe.get("formaciones"):
                        f = pe["formaciones"]
                        forms = {("visitante" if l == "local" else "local") if invertido else l: v
                                 for l, v in f.items()}
                    extra = {k: pe.get(k) for k in ("estadio", "ciudad", "arbitro", "publico")}
                elif a in es and pr["gl"] is not None:
                    faltan_espn += 1
                base = dict(pr)
                for k, v in extra.items():
                    if v:
                        base[k] = v
                base["formaciones_final"] = forms
                x = partido_final(base, pr["local_id"], pr["visitante_id"], goles, pe["espn"] if pe else None)
                # Desde 2005 ESPN nombra las fases de forma más prolija y uniforme que RSSSF
                x["fase"] = pe["fase"] if pe else pr["fase"]
                partidos.append(x)
            # Partidos que ESPN tiene y RSSSF no (p. ej. una página de RSSSF incompleta)
            emparejados = set(pares)
            for pe in es.get(a, {"partidos": []})["partidos"]:
                if pe["jugado"] and pe["espn"] not in emparejados:
                    base = dict(pe)
                    base["formaciones_final"] = pe.get("formaciones")
                    base["notas"] = "solo en ESPN"
                    x = partido_final(base, mapa[pe["local_espn"]], mapa[pe["visitante_espn"]],
                                      goles_espn(pe), pe["espn"])
                    x["fase"] = pe["fase"]
                    partidos.append(x)
        else:
            series = {}
            for pe in es[a]["partidos"]:
                base = dict(pe)
                base["formaciones_final"] = pe.get("formaciones")
                if pe.get("serie"):
                    base["llave"] = series.setdefault(pe["serie"], len(series) + 1)
                if not pe["jugado"]:
                    base["notas"] = "a jugarse"
                x = partido_final(base, mapa[pe["local_espn"]], mapa[pe["visitante_espn"]],
                                  goles_espn(pe), pe["espn"])
                x["fase"] = pe["fase"]
                partidos.append(x)

        # Agrupar por fase, en orden cronológico de la fase
        fases = collections.OrderedDict()
        for p in sorted(partidos, key=lambda p: (p.get("fecha") or "9999")):
            fases.setdefault(p.pop("fase"), []).append(p)
        orden = sorted(fases, key=lambda f: (next((i for i, n in enumerate(ORDEN_FASES) if f.startswith(n)), 50),
                                             min(p.get("fecha") or "9999" for p in fases[f]), f))
        for i, p in enumerate(p for f in orden for p in fases[f]):
            p["id"] = f"{a}-{i + 1:03d}"
        # Campeón: ganador de la final (o ajuste manual)
        finales = [p for f in orden if f.startswith("Final") for p in fases[f]]
        for p in finales:
            if "desempate" in (p.get("notas") or "").lower():
                p["_desempate"] = True
        campeon, sub = ganador_llave(finales)
        for p in finales:
            p.pop("_desempate", None)
        fijo = ajustes.get("campeones", {}).get(str(a))
        if fijo:
            campeon, sub = fijo
        todos = [p for f in orden for p in fases[f]]
        ed = {"anio": a, "campeon": campeon, "subcampeon": sub,
              "fuentes": (["RSSSF"] if a in rs else []) + (["ESPN"] if a in es else []),
              "fases": [{"nombre": f, "partidos": fases[f]} for f in orden],
              "planteles": armar_planteles(todos)}
        ediciones[a] = ed
        jugados = [p for p in todos if p.get("gl") is not None]
        goles = sum(p["gl"] + p["gv"] for p in jugados)
        con_autor = sum(len(p.get("goles", [])) for p in jugados)
        control.append((a, len(todos), len(jugados), goles, con_autor,
                        sum(1 for p in todos if p.get("formaciones")),
                        sum(1 for p in jugados for g in p.get("goles", []) if g.get("asistencia")),
                        faltan_espn, campeon, sub))
        indice.append({"anio": a, "campeon": campeon, "subcampeon": sub})

    # -------- escribir archivos
    clubes = cat.exportar()
    for i, c in clubes.items():
        for eid in c.get("espn", []):
            t = info_espn.get(eid, {})
            if t.get("color"):
                c.setdefault("colores", [f"#{t['color']}", f"#{t.get('color2') or 'ffffff'}"])
    (DATA / "ediciones").mkdir(parents=True, exist_ok=True)
    for a, ed in ediciones.items():
        escribir(DATA / "ediciones" / f"{a}.js",
                 f"window.LIB.ediciones = window.LIB.ediciones || {{}};\nwindow.LIB.ediciones[{a}] = ", ed)
    escribir(DATA / "equipos.js", "window.LIB.equipos = ", clubes)
    escribir(DATA / "indice.js", "window.LIB.indice = ", indice)
    (DATA / "jugadores.js").unlink(missing_ok=True)

    # -------- control de calidad
    print(f"{'año':>5} {'part':>5} {'jug':>4} {'goles':>6} {'c/autor':>8} {'formac':>7} {'asist':>6} {'sinESPN':>8}  campeón / subcampeón")
    for a, n, j, g, ca, fo, asi, fe, c, s in control:
        print(f"{a:>5} {n:>5} {j:>4} {g:>6} {ca:>8} {fo:>7} {asi:>6} {fe:>8}  {c} / {s}")
    print(f"\n{len(clubes)} clubes. Sin país: {sorted(i for i, c in clubes.items() if not c['pais'])}")
    if sin_pais:
        print("Nombres sin país (revisar equipos_ajustes.json):", sorted(sin_pais))


def escribir(ruta, prefijo, datos):
    cuerpo = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    ruta.write_text("/* Generado por tools/generar_datos.py — no editar a mano */\nwindow.LIB = window.LIB || {};\n"
                    + prefijo + cuerpo + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
