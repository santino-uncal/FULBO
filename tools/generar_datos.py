"""Genera todos los archivos de data/ a partir de lo descargado de RSSSF, Wikipedia y ESPN, para todas las copas.

Uso:  python tools/generar_datos.py
Antes hay que haber corrido tools/descargar_rsssf.py y tools/descargar_espn.py (con y sin --copa sudamericana).

Cómo combina las fuentes (en las dos copas):
  - hasta 2004: solo RSSSF (resultados, goleadores; formaciones de algunas finales).
  - 2005–2024: RSSSF es la base (lista completa de partidos) y cada partido se completa
    con el detalle de ESPN (goles con minuto y asistencia, formaciones, árbitro, público).
  - 2025 en adelante: solo ESPN.
La Champions League sale toda de ESPN (solo las temporadas de "ediciones" en copas.py).
El Mundial de Clubes y la Copa Intercontinental toman de Wikipedia lo que ESPN no tiene (la Intercontinental
1960-2004 y el Mundial 2000); lo demás sale de ESPN.
Los clubes son uno solo para todas las copas (data/equipos.js). La Libertadores queda en data/ y cada una de
las otras en su carpeta (data/sudamericana/, data/mundial/…). Cada edición se identifica por (copa, año).
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
import generar_estadisticas  # noqa: E402
import generar_historial  # noqa: E402
import descargar_planteles  # noqa: E402
import leer_rsssf  # noqa: E402
import leer_wikipedia  # noqa: E402
from copas import COPAS, prefijo_js  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
CACHE = RAIZ / "tools" / "cache"

ORDEN_FASES = ["Fase previa", "Primera fase previa", "Segunda fase previa", "Tercera fase previa",
               "Treintaidosavos de final", "Dieciseisavos de final", "Primera fase", "Fase de grupos", "Fase de liga", "Segunda fase de grupos", "Segunda fase", "Tercera fase", "Playoffs de octavos",
               "Primera ronda", "Copa África-Asia-Pacífico", "Segunda ronda", "Derbi de las Américas", "Copa Challenger",
               "Octavos de final",
               "Cuartos de final", "Semifinales", "Quinto puesto", "Tercer puesto", "Final"]


def anios_rsssf(clave):
    copa = COPAS[clave]
    if "rsssf" not in copa:
        return []
    return [a for a in range(copa["desde"], datetime.date.today().year + 1)
            if (copa["cache_rsssf"] / copa["rsssf"](a)).exists()]


def anios_espn(clave):
    return sorted(int(d.name) for d in COPAS[clave]["cache_espn"].glob("*") if (d / "calendario.json").exists())


def dias(a, b):
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def repartir_por_temporada(es, corregir=True):
    """ESPN agrupa por año calendario: la final 2020 (jugada en enero de 2021) viene con 2021.
    Cada partido trae su temporada, pero hasta 2015 ESPN la etiqueta corrida un año (en la Libertadores y la
    Sudamericana): se corrige con el corrimiento de la mayoría del calendario. En el Mundial de Clubes la
    etiqueta ya es la edición de la FIFA (corregir=False): la "2020" se jugó en febrero de 2021.
    Las temporadas que quedan sin partidos (el Mundial 2024 no existió) se descartan."""
    nuevo = {a: {"anio": a, "partidos": [], "equipos": dict(r["equipos"])} for a, r in es.items()}
    vistos = set()
    for a, r in es.items():
        etiquetas = collections.Counter(p["temporada_espn"] for p in r["partidos"] if p["temporada_espn"])
        corrimiento = a - etiquetas.most_common(1)[0][0] if etiquetas and corregir else 0
        for p in r["partidos"]:
            t = (p["temporada_espn"] + corrimiento) if p["temporada_espn"] else a
            if p["espn"] in vistos or t not in nuevo:
                continue
            vistos.add(p["espn"])
            nuevo[t]["partidos"].append(p)
    return {a: r for a, r in nuevo.items() if r["partidos"]}


# ---------------------------------------------------------------- clubes
def asignar_clubes_rsssf(rs, cat):
    """rs: {(copa, año): edición de RSSSF}. Primero toda la Libertadores y después la Sudamericana, que para
    adivinar el país de un club aprende también de lo que se sabe por la Libertadores."""
    sin_pais = set()
    for clave in COPAS:
        R = E.Resolutor({k: r for k, r in rs.items() if k[0] in ("libertadores", clave)})
        for k, r in rs.items():
            if k[0] != clave:
                continue
            for p in r["partidos"]:
                for lado in ("local", "visitante"):
                    crudo = p[lado]
                    pais = R.pais(k, p, crudo)
                    if not pais:
                        sin_pais.add(f"{k[0]} {k[1]}|{crudo}")
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


def mismo_resultado(pr, pe, local_espn):
    """¿El partido de RSSSF y el de ESPN terminaron igual? (sirve para no unir la ida con la vuelta)"""
    if pr["gl"] is None or pe["gl"] is None:
        return True
    goles = (pr["gl"], pr["gv"]) if pr["local_id"] == local_espn else (pr["gv"], pr["gl"])
    return goles == (pe["gl"], pe["gv"])


def emparejar_por_club(rs_ed, es_ed, pares, usados, mapa):
    """2da pasada: con los clubes ya conocidos, emparejar por fecha y clubes."""
    for pe in es_ed["partidos"]:
        if not pe["jugado"] or pe["espn"] in pares:
            continue
        l, v = mapa.get(pe["local_espn"]), mapa.get(pe["visitante_espn"])
        cand = [pr for pr in rs_ed["partidos"] if id(pr) not in usados and pr.get("fecha")
                and dias(pr["fecha"], pe["fecha"]) <= 3 and {pr["local_id"], pr["visitante_id"]} == {l, v}]
        iguales = [pr for pr in cand if mismo_resultado(pr, pe, l)]
        # Si el resultado no coincide pero hay otro partido de RSSSF con el mismo cruce y resultado
        # (con la fecha mal), ese es el verdadero: lo empareja la pasada flexible.
        otro = any(id(pr) not in usados and {pr["local_id"], pr["visitante_id"]} == {l, v}
                   and pr["gl"] is not None and mismo_resultado(pr, pe, l) for pr in rs_ed["partidos"])
        cand = iguales or ([] if otro else cand)
        if cand:
            pr = min(cand, key=lambda x: dias(x["fecha"], pe["fecha"]))
            pares[pe["espn"]] = pr
            usados.add(id(pr))


def emparejar_flexible(rs_ed, es_ed, pares, usados, mapa):
    """3ra pasada: mismo resultado y al menos un club en común, aunque la fecha de RSSSF esté mal
    o RSSSF haya confundido un homónimo (Nacional URU / PAR). En esos casos manda ESPN:
    se corrigen el club y la fecha del partido de RSSSF."""
    for pe in es_ed["partidos"]:
        if not pe["jugado"] or pe["espn"] in pares:
            continue
        l, v = mapa.get(pe["local_espn"]), mapa.get(pe["visitante_espn"])
        if not l or not v:
            continue
        cand = []
        for pr in rs_ed["partidos"]:
            if id(pr) in usados or pr["gl"] is None:
                continue
            if (pr["gl"], pr["gv"]) == (pe["gl"], pe["gv"]) and (pr["local_id"] == l or pr["visitante_id"] == v):
                cand.append(pr)
            elif (pr["gl"], pr["gv"]) == (pe["gv"], pe["gl"]) and (pr["local_id"] == v or pr["visitante_id"] == l):
                cand.append(pr)  # RSSSF tiene local y visitante al revés
        if not cand:
            continue
        pr = min(cand, key=lambda x: dias(x["fecha"], pe["fecha"]) if x.get("fecha") else 999)
        if (pr["gl"], pr["gv"]) != (pe["gl"], pe["gv"]) or pr["local_id"] == v:
            # dar vuelta el partido de RSSSF para que coincida con ESPN
            pr["gl"], pr["gv"] = pr["gv"], pr["gl"]
            pr["pen_l"], pr["pen_v"] = pr.get("pen_v"), pr.get("pen_l")
            for g in pr.get("goles", []):
                g["lado"] = "visitante" if g["lado"] == "local" else "local"
        pr["local_id"], pr["visitante_id"], pr["fecha"] = l, v, pe["fecha"]
        pares[pe["espn"]] = pr
        usados.add(id(pr))


# ---------------------------------------------------------------- partidos
def goles_rsssf(p):
    """Goles de RSSSF o Wikipedia (Wikipedia trae el tiempo de descuento: 90+2 es min 90, extra 2)."""
    return [{"jugador": g["jugador"], "min": g.get("min"), "tipo": g.get("tipo"), "equipo": g["lado"],
             **({"extra": g["extra"]} if g.get("extra") else {})} for g in p.get("goles", [])]


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


def cuadra(goles, p):
    """Si la lista de goles coincide con el resultado de cada equipo."""
    local = sum(g["equipo"] == "local" for g in goles)
    return (local, len(goles) - local) == (p.get("gl") or 0, p.get("gv") or 0)


def tanda_espn(p, invertido=False):
    """Tanda de penales de ESPN, remate por remate (invertido: ESPN tomó como local al otro equipo)."""
    tanda = p.get("tanda") or []
    if not tanda:
        return None
    return [{"jugador": t["jugador"], "jid": t.get("jid"), "gol": t["gol"],
             "equipo": ("visitante" if t["lado"] == "local" else "local") if invertido else t["lado"]}
            for t in tanda]


def tanda_cuadra(x):
    """La tanda solo se muestra si los goles suman lo mismo que el resultado de los penales."""
    t = x.get("tanda")
    if t and (sum(1 for r in t if r["gol"] and r["equipo"] == "local") != x.get("pen_l") or
              sum(1 for r in t if r["gol"] and r["equipo"] == "visitante") != x.get("pen_v")):
        del x["tanda"]
    return x


def formaciones_rsssf(p):
    """Formaciones de RSSSF (solo nombres): asignarlas a local/visitante por parecido del nombre.
    Las de Wikipedia ya vienen armadas (con número, posición y cambios) y separadas en local y visitante."""
    if p.get("formaciones"):
        return p["formaciones"]
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
         "formaciones": p.get("formaciones_final"), "tanda": p.get("tanda_final")}
    if espn:
        x["espn"] = espn
    return tanda_cuadra(limpiar(x))


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
def base_club(id_):
    """'nacional-par' -> 'nacional': clubes homónimos de distinto país."""
    return re.sub(r"-(arg|bra|uru|par|chi|col|per|ecu|bol|ven|mex)$", "", id_)


def corregir_homonimos(partidos):
    """A veces un partido de grupos queda con el homónimo equivocado (Nacional URU / PAR, River ARG / URU).
    Se nota porque el grupo queda con un equipo de más, o con un partido de un club contra sí mismo."""
    grupos = collections.defaultdict(list)
    for p in partidos:
        if p["fase"].startswith("Fase de grupos — "):
            grupos[p["fase"]].append(p)
    for nombre, ps in grupos.items():
        cuenta = collections.Counter(x for p in ps for x in (p["local"], p["visitante"]))
        if len(cuenta) > 4:
            # el que sobra es el homónimo que además juega en otro grupo (o, si no, el que menos aparece)
            for x in list(cuenta):
                otros = [y for y in cuenta if y != x and base_club(y) == base_club(x)]
                if not otros:
                    continue
                y = otros[0]
                en_otro = any(x in (p["local"], p["visitante"]) for g, qs in grupos.items() if g != nombre for p in qs)
                if en_otro or cuenta[x] < cuenta[y]:
                    for p in ps:
                        for lado in ("local", "visitante"):
                            if p[lado] == x:
                                p[lado] = y
                    cuenta = collections.Counter(z for p in ps for z in (p["local"], p["visitante"]))
        for p in ps:
            if p["local"] == p["visitante"]:
                # el otro partido entre los dos homónimos dice quién es quién (la vuelta es al revés)
                rival = next((y for y in cuenta if y != p["local"] and base_club(y) == base_club(p["local"])), None)
                ida = next((q for q in ps if q is not p and {q["local"], q["visitante"]} == {p["local"], rival}), None)
                if rival and ida:
                    p["local"], p["visitante"] = ida["visitante"], ida["local"]


def armar_planteles(partidos):
    """Planteles a partir de formaciones y goles: quién jugó, cuántos partidos, goles y asistencias."""
    pl = collections.defaultdict(dict)

    def ficha(club, jid, nombre):
        if not nombre:   # alguna formación de ESPN trae jugadores sin nombre: no se suman al plantel
            return nueva(jid, nombre)
        return pl[club].setdefault(jid or nombre, nueva(jid, nombre))

    def nueva(jid, nombre):
        return {"id": jid, "nombre": nombre, "pj": 0, "tit": 0, "goles": 0,
                "asist": 0, "num": collections.Counter(), "pos": collections.Counter()}

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
# País de los clubes europeos de ESPN: el prefijo de su ficha ("esp.real_zaragoza") o el país de su estadio
PREFIJOS_ESPN = {"eng": "ENG", "ger": "GER", "esp": "ESP", "fra": "FRA", "ita": "ITA", "ned": "NED", "por": "POR",
                 "gre": "GRE", "sco": "SCO", "bel": "BEL", "tur": "TUR", "rus": "RUS", "den": "DEN", "aut": "AUT",
                 "sui": "SUI", "nor": "NOR", "rom": "ROU", "ukr": "UKR", "swe": "SWE", "fin": "FIN", "pol": "POL",
                 "wal": "WAL", "irl": "IRL", "cze": "CZE", "cyp": "CYP", "svk": "SVK", "svn": "SVN", "cro": "CRO",
                 "bul": "BUL", "aze": "AZE", "blr": "BLR", "hun": "HUN", "isr": "ISR", "ltu": "LTU"}
PAISES_INGLES = dict(leer_wikipedia.NOMBRES_PAIS, **{
    "türkiye": "TUR", "turkiye": "TUR", "czechia": "CZE", "bosnia and herzegovina": "BIH", "bosnia-herzegovina": "BIH",
    "north macedonia": "MKD", "macedonia": "MKD", "moldova": "MDA", "belarus": "BLR", "georgia": "GEO",
    "armenia": "ARM", "azerbaijan": "AZE", "kazakhstan": "KAZ", "israel": "ISR", "serbia": "SRB", "croatia": "CRO",
    "montenegro": "MNE", "kosovo": "KOS", "estonia": "EST", "latvia": "LVA", "lithuania": "LTU",
    "faroe islands": "FRO", "gibraltar": "GIB", "andorra": "AND", "san marino": "SMR", "liechtenstein": "LIE",
    "united kingdom": None, "germany": "GER"})
# Países de antes que abarcan a los de hoy (Spartak Moscú es URS en Wikipedia y RUS en ESPN)
PAISES_VIEJOS = {"URS": {"RUS", "UKR", "BLR", "GEO", "ARM", "AZE", "MDA", "LTU", "LVA", "EST", "KAZ"},
                 "TCH": {"CZE", "SVK"}, "YUG": {"SRB", "CRO", "SVN", "BIH", "MKD", "MNE", "FRY", "KOS"},
                 "FRY": {"SRB", "MNE"}, "GDR": {"GER"}}


def paises_espn(es, eids):
    fichas = json.loads((CACHE / "espn_equipos.json").read_text(encoding="utf-8"))         if (CACHE / "espn_equipos.json").exists() else {}
    estadios = collections.defaultdict(collections.Counter)
    for k in es:
        for p in es[k]["partidos"]:
            if p.get("pais_estadio") and not p["fase"].startswith("Final"):
                estadios[p["local_espn"]][p["pais_estadio"].lower()] += 1
    res = {}
    for eid in eids:
        pais = PREFIJOS_ESPN.get(fichas.get(eid, "").split(".")[0])
        if not pais and estadios[eid]:
            pais = PAISES_INGLES.get(estadios[eid].most_common(1)[0][0])
        if pais:
            res[eid] = pais
    return res


def club_europeo(cat, nombre, pais):
    """El club del catálogo que corresponde a un club europeo de ESPN: el mismo nombre (normalizado) en un país
    compatible, o si no hay, uno solo del mismo país cuyo nombre contenga al otro ('Zaragoza' / 'Real Zaragoza')."""
    def compatible(i):
        p = cat.ajustes.get("pais_club", {}).get(i) or cat.clubes[i]["pais"]
        return pais is None or p is None or p == pais or pais in PAISES_VIEJOS.get(p, ()) or             cat.clubes[i]["pais"] == pais or pais in PAISES_VIEJOS.get(cat.clubes[i]["pais"], ())
    norm = E.normalizar(nombre)
    exacto = [i for i in cat.clubes if compatible(i) and any(E.normalizar(n) == norm for n in cat.nombres[i])]
    if len(exacto) == 1 or (exacto and pais is None):
        return max(exacto, key=lambda i: sum(cat.nombres[i].values()))
    if not pais or exacto:
        return None
    palabras = set(norm.split())
    parecidos = [i for i in cat.clubes if compatible(i) and cat.clubes[i]["pais"] is not None and any(
        (set(E.normalizar(n).split()) <= palabras or palabras <= set(E.normalizar(n).split())) and E.normalizar(n)
        for n in cat.nombres[i])]
    return parecidos[0] if len(parecidos) == 1 else None


def main():
    cat = E.Catalogo()
    ajustes = E.cargar_ajustes()
    # Cada edición es (copa, año): ("libertadores", 1986), ("sudamericana", 2005)…
    rs, es = {}, {}
    for clave in COPAS:
        rs.update({(clave, a): leer_rsssf.leer(a, clave) for a in anios_rsssf(clave)})
        rs.update({(clave, a): leer_wikipedia.leer(a, clave) for a in leer_wikipedia.anios(clave)})
        es.update({(clave, a): r for a, r in repartir_por_temporada(
            {a: leer_espn.leer(a, clave) for a in anios_espn(clave)}, "rsssf" in COPAS[clave]).items()
            if a in COPAS[clave].get("ediciones", [a])})   # la Champions: solo las temporadas elegidas
    sin_pais = asignar_clubes_rsssf(rs, cat)

    # ESPN -> club: votos por emparejamiento de partidos
    votos = collections.defaultdict(collections.Counter)
    pares_por_anio = {}
    for k in es:
        if k in rs:
            pares_por_anio[k] = emparejar(rs[k], es[k], votos)
    mapa = {eid: v.most_common(1)[0][0] for eid, v in votos.items()}
    mapa.update({eid: ajustes.get("unir", {}).get(i, i) for eid, i in ajustes.get("espn", {}).items()})
    for k, (pares, usados) in pares_por_anio.items():
        emparejar_por_club(rs[k], es[k], pares, usados, mapa)
    # Clubes de ESPN que nunca aparecieron en RSSSF (ediciones nuevas)
    # (solo los que juegan en alguna edición: el calendario de ESPN trae también los de temporadas que no se cargan)
    info_espn = {}
    for k in es:
        info_espn.update(es[k]["equipos"])
    juegan = {p[lado] for k in es for p in es[k]["partidos"] for lado in ("local_espn", "visitante_espn")}
    info_espn = {eid: t for eid, t in info_espn.items() if eid in juegan}
    # los clubes de ESPN que solo juegan la Copa UEFA / Europa League, con su país (ficha de ESPN o estadio)
    otras = {p[lado] for k in es if k[0] != "europa" for p in es[k]["partidos"] for lado in ("local_espn", "visitante_espn")}
    solo_europa = {eid for eid in info_espn if eid not in otras}
    paises_auto = paises_espn(es, solo_europa)
    for eid, t in info_espn.items():
        if t["nombre"].startswith("TBD"):  # partido futuro con rival todavía no definido
            mapa[eid] = cat.id_de("A definir", None)
            continue
        if eid not in mapa and eid in solo_europa:
            # Copa UEFA / Europa League: ESPN no se cruza con Wikipedia (no hay temporadas en común), así que se busca
            # el club por nombre y país (ver club_europeo)
            pais = ajustes.get("pais_espn", {}).get(eid) or paises_auto.get(eid)
            mapa[eid] = club_europeo(cat, t["nombre"], pais) or cat.id_de(t["nombre"], pais)
            if mapa[eid].endswith("-xx") and mapa[eid][:-3] in cat.clubes:   # sin país, chocó con un club del mismo nombre: es ese
                cat.clubes.pop(mapa[eid], None)
                mapa[eid] = mapa[eid][:-3]
            cat.asegurar(mapa[eid], t["nombre"], pais)["espn"].add(eid)
            continue
        if eid not in mapa:
            # buscar un club con el mismo nombre; si no hay, es un club nuevo
            norm = E.normalizar(t["nombre"])
            por_nombre = [i for i in cat.clubes if any(E.normalizar(n) == norm for n in cat.nombres[i])]
            mapa[eid] = por_nombre[0] if len(por_nombre) == 1 else \
                cat.id_de(t["nombre"], ajustes.get("pais_espn", {}).get(eid))
        cat.asegurar(mapa[eid], t["nombre"], ajustes.get("pais_espn", {}).get(eid))["espn"].add(eid)
    for k, (pares, usados) in pares_por_anio.items():
        emparejar_flexible(rs[k], es[k], pares, usados, mapa)

    ediciones, indice, control = {}, {clave: [] for clave in COPAS}, []
    for ek in sorted(set(rs) | set(es), key=lambda x: (list(COPAS).index(x[0]), x[1])):
        clave, a = ek   # (la edición se llama ek: más abajo k se usa para otras cosas)
        partidos = []
        faltan_espn = 0
        if ek in rs:
            pares = pares_por_anio.get(ek, ({}, set()))[0]
            por_rsssf = {id(pr): pe_id for pe_id, pr in pares.items()}
            espn_por_id = {p["espn"]: p for p in es.get(ek, {"partidos": []})["partidos"]}
            # Cómo llama ESPN a cada fase de RSSSF (para los partidos que ESPN no tiene)
            votos = collections.defaultdict(collections.Counter)
            for pr in rs[ek]["partidos"]:
                pe = espn_por_id.get(por_rsssf.get(id(pr)))
                if pe:
                    votos[pr["fase"]][pe["fase"]] += 1
            fase_espn = {f: c.most_common(1)[0][0] for f, c in votos.items()}
            for pr in rs[ek]["partidos"]:
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
                    # ESPN a veces anota un gol al otro equipo (Caracas-Peñarol 2012): si sus goles no cuadran
                    # con el resultado de cada equipo y los de RSSSF sí, quedan los de RSSSF
                    if len(ge) == (pr["gl"] or 0) + (pr["gv"] or 0) and (cuadra(ge, pr) or not cuadra(goles, pr)):
                        goles = ge
                    if pe.get("formaciones"):
                        f = pe["formaciones"]
                        forms = {("visitante" if l == "local" else "local") if invertido else l: v
                                 for l, v in f.items()}
                    extra = {k: pe.get(k) for k in ("estadio", "ciudad", "arbitro", "publico", "fecha")}
                    extra["tanda_final"] = tanda_espn(pe, invertido)
                elif ek in es and pr["gl"] is not None:
                    faltan_espn += 1
                base = dict(pr)
                for k, v in extra.items():
                    if v:
                        base[k] = v
                base["formaciones_final"] = forms
                local, visitante = pr["local_id"], pr["visitante_id"]
                if pe:
                    # Si RSSSF confundió un club (Nacional URU / PAR, Universitario PER / Sucre), manda ESPN
                    el, ev = mapa.get(pe["local_espn"]), mapa.get(pe["visitante_espn"])
                    if invertido:
                        el, ev = ev, el
                    # (solo si el otro equipo coincide: si no coincide ninguno, el emparejamiento es dudoso)
                    if el and el != "a-definir" and ev == visitante:
                        local = el
                    if ev and ev != "a-definir" and el == local:
                        visitante = ev
                x = partido_final(base, local, visitante, goles, pe["espn"] if pe else None)
                # Desde 2005 ESPN nombra las fases de forma más prolija y uniforme que RSSSF
                x["fase"] = pe["fase"] if pe else fase_espn.get(pr["fase"], pr["fase"])
                # En algunas temporadas ESPN no dice el grupo: se toma el de RSSSF
                m = re.search(r"Grupo\s+(\w+)", pr["fase"])
                if x["fase"] == "Fase de grupos" and m:
                    x["fase"] = f"Fase de grupos — Grupo {m.group(1)}"
                partidos.append(x)
            # Partidos que ESPN tiene y RSSSF no (p. ej. una página de RSSSF incompleta)
            emparejados = set(pares)
            for pe in es.get(ek, {"partidos": []})["partidos"]:
                if pe["jugado"] and pe["espn"] not in emparejados:
                    base = dict(pe)
                    base["formaciones_final"] = pe.get("formaciones")
                    base["tanda_final"] = tanda_espn(pe)
                    if clave != "europa":   # (en la Copa UEFA 2004-2008 Wikipedia trae solo la fase de grupos)
                        base["notas"] = "solo en ESPN"
                    x = partido_final(base, mapa[pe["local_espn"]], mapa[pe["visitante_espn"]],
                                      goles_espn(pe), pe["espn"])
                    x["fase"] = pe["fase"]
                    partidos.append(x)
        else:
            series = {}
            for pe in es[ek]["partidos"]:
                base = dict(pe)
                base["formaciones_final"] = pe.get("formaciones")
                base["tanda_final"] = tanda_espn(pe)
                if pe.get("serie"):
                    base["llave"] = series.setdefault(pe["serie"], len(series) + 1)
                if not pe["jugado"]:
                    # (un partido viejo sin resultado no se jugó: en el Mundial 2020 Auckland City se bajó por la pandemia)
                    viejo = "rsssf" not in COPAS[clave] and pe["fecha"] < datetime.date.today().isoformat()
                    if viejo and clave in ("champions", "europa"):
                        continue   # en las copas europeas es un partido postergado: ESPN tiene también el reprogramado
                    base["notas"] = "no se jugó" if viejo else "a jugarse"
                x = partido_final(base, mapa[pe["local_espn"]], mapa[pe["visitante_espn"]],
                                  goles_espn(pe), pe["espn"])
                x["fase"] = pe["fase"]
                partidos.append(x)

        # Resultados definidos por escritorio (ver "resultados" en equipos_ajustes.json)
        for p in partidos:
            if p.get("espn") in ajustes.get("resultados", {}):
                p.update(ajustes["resultados"][p["espn"]])
        corregir_homonimos(partidos)
        # Partidos de grupos que quedaron sin grupo: se ubican por el grupo de sus dos equipos
        grupo_de = {}
        for p in partidos:
            if p["fase"].startswith("Fase de grupos — "):
                grupo_de[p["local"]] = grupo_de[p["visitante"]] = p["fase"]
        for p in partidos:
            if p["fase"] == "Fase de grupos" and grupo_de.get(p["local"]) and \
                    grupo_de.get(p["local"]) == grupo_de.get(p["visitante"]):
                p["fase"] = grupo_de[p["local"]]

        # Agrupar por fase, en orden cronológico de la fase
        fases = collections.OrderedDict()
        for p in sorted(partidos, key=lambda p: (p.get("fecha") or "9999")):
            fases.setdefault(p.pop("fase"), []).append(p)
        orden = sorted(fases, key=lambda f: (next((i for i, n in enumerate(ORDEN_FASES) if f.startswith(n)), 50),
                                             min(p.get("fecha") or "9999" for p in fases[f]), f))
        if clave in ("champions", "europa"):
            # La Champions cambió mucho de formato (en 1991-1993 los octavos se jugaban antes de los grupos): las
            # etapas van por fecha (cada grupo con su etapa) y la final al último
            inicio = collections.defaultdict(lambda: "9999")
            for f in fases:
                etapa = f.split(" — ")[0]
                inicio[etapa] = min(inicio[etapa], min(p.get("fecha") or "9999" for p in fases[f]))
            orden = sorted(fases, key=lambda f: (f.startswith("Final"), inicio[f.split(" — ")[0]], f))
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
        fijo = ajustes.get("campeones" if clave == "libertadores" else f"campeones_{clave}", {}).get(str(a))
        if fijo:
            campeon, sub = fijo
        todos = [p for f in orden for p in fases[f]]
        nota = ajustes.get("notas_ediciones", {}).get(f"{clave} {a}")   # aclaración a mano (final no jugada…)
        ed = {"anio": a, "campeon": campeon, "subcampeon": sub, **({"nota": nota} if nota else {}),
              "fuentes": ([("RSSSF" if "rsssf" in COPAS[clave] else "Wikipedia")] if ek in rs else []) +
                         (["ESPN"] if ek in es else []),
              "fases": [{"nombre": f, "partidos": fases[f]} for f in orden],
              "planteles": armar_planteles(todos)}
        ediciones[ek] = ed
        jugados = [p for p in todos if p.get("gl") is not None]
        goles = sum(p["gl"] + p["gv"] for p in jugados)
        con_autor = sum(len(p.get("goles", [])) for p in jugados)
        control.append((f"{clave[:3]} {a}", len(todos), len(jugados), goles, con_autor,
                        sum(1 for p in todos if p.get("formaciones")),
                        sum(1 for p in jugados for g in p.get("goles", []) if g.get("asistencia")),
                        faltan_espn, campeon, sub))
        indice[clave].append({"anio": a, "campeon": campeon, "subcampeon": sub})

    # -------- escribir archivos
    clubes = cat.exportar()
    for i, c in clubes.items():
        for eid in c.get("espn", []):
            t = info_espn.get(eid, {})
            if t.get("color"):
                c.setdefault("colores", [f"#{t['color']}", f"#{t.get('color2') or 'ffffff'}"])
    unificar_estadios(ediciones)
    ajustar_finales(ediciones)
    # Estadio "de siempre" de cada club, para las ediciones viejas que no traen estadios (antes de 2005):
    # donde más veces jugó de local en la primera edición en que hay datos de su cancha
    # (el Mundial y la Intercontinental no cuentan: casi todo se juega en cancha neutral)
    for ek in sorted(ediciones, key=lambda x: (list(COPAS).index(x[0]), x[1])):   # primero la Libertadores
        if "rsssf" not in COPAS[ek[0]]:
            continue
        cuenta = {}
        for f in ediciones[ek]["fases"]:
            for p in f["partidos"]:
                if p.get("estadio") and not f["nombre"].startswith("Final"):   # las finales pueden ser en cancha neutral
                    k = p["estadio"] + (f", {p['ciudad']}" if p.get("ciudad") else "")
                    cuenta.setdefault(p["local"], {}).setdefault(k, 0)
                    cuenta[p["local"]][k] += 1
        for club, canchas in cuenta.items():
            if club in clubes and "estadio" not in clubes[club]:
                clubes[club]["estadio"] = max(canchas, key=canchas.get)
    # Planteles completos de Transfermarkt (bajados con tools/descargar_planteles.py)
    for clave in COPAS:
        planteles_tm = descargar_planteles.cargar_tm(clave)
        for (c, a), ed in ediciones.items():
            if c == clave and str(a) in planteles_tm:
                descargar_planteles.mezclar(ed["planteles"], planteles_tm[str(a)], ed)
    for (clave, a), ed in ediciones.items():
        ns = COPAS[clave]["ns"]
        carpeta = COPAS[clave]["data"] / "ediciones"
        carpeta.mkdir(parents=True, exist_ok=True)
        escribir(carpeta / f"{a}.js", f"window.{ns}.ediciones = window.{ns}.ediciones || {{}};\nwindow.{ns}.ediciones[{a}] = ",
                 ed, clave)
    escribir(DATA / "equipos.js", "window.LIB.equipos = ", clubes)
    for clave in COPAS:
        escribir(COPAS[clave]["data"] / "indice.js", f"window.{COPAS[clave]['ns']}.indice = ", indice[clave], clave)
    (DATA / "jugadores.js").unlink(missing_ok=True)
    escribir_sitemap({clave: [a for c, a in sorted(ediciones) if c == clave] for clave in COPAS})
    entrenadores_de_formaciones(ediciones)
    for clave in COPAS:
        generar_historial.main(clave)   # historial.js: la ficha de cada club
        generar_estadisticas.main(clave)   # estadisticas.js: estadísticas históricas (usa historial.js)

    # -------- control de calidad
    print(f"{'edición':>9} {'part':>5} {'jug':>4} {'goles':>6} {'c/autor':>8} {'formac':>7} {'asist':>6} {'sinESPN':>8}  campeón / subcampeón")
    for a, n, j, g, ca, fo, asi, fe, c, s in control:
        print(f"{a:>9} {n:>5} {j:>4} {g:>6} {ca:>8} {fo:>7} {asi:>6} {fe:>8}  {c} / {s}")
    print(f"\n{len(clubes)} clubes. Sin país: {sorted(i for i, c in clubes.items() if not c['pais'])}")
    if sin_pais:
        print("Nombres sin país (revisar equipos_ajustes.json):", sorted(sin_pais))


URL_SITIO = "https://santino-uncal.github.io/FULBO/"  # dirección publicada en GitHub Pages


def unificar_estadios(ediciones):
    """Mismo nombre y ciudad para cada estadio (ver tools/estadios.json). Los que no están en la
    lista quedan como vienen, sin el 'Estadio' de adelante."""
    lista = json.loads((RAIZ / "tools" / "estadios.json").read_text(encoding="utf-8"))["estadios"]
    mapa = {crudo: (nombre, ciudad) for nombre, ciudad, crudos in lista for crudo in crudos}
    for (copa, _), ed in ediciones.items():
        for f in ed["fases"]:
            for p in f["partidos"]:
                if not p.get("estadio"):
                    continue
                crudo = next((c for c in (f"{copa}|{p['estadio']}", p["estadio"]) if c in mapa), None)   # el de la copa, primero
                if crudo:
                    p["estadio"], p["ciudad"] = mapa[crudo]
                else:
                    p["estadio"] = re.sub(r"^Est[aá]dio\s+", "", p["estadio"])


def ajustar_finales(ediciones):
    """Correcciones a mano de partidos de final (ver tools/finales_ajustes.json) y partidos repetidos fuera."""
    for ed in ediciones.values():
        for f in ed["fases"]:
            vistos, unicos = set(), []
            for p in f["partidos"]:
                clave = (p["local"], p["visitante"], p.get("fecha"), p.get("gl"), p.get("gv"))
                if clave not in vistos:
                    vistos.add(clave)
                    unicos.append(p)
            f["partidos"] = unicos
    ajustes = json.loads((RAIZ / "tools" / "finales_ajustes.json").read_text(encoding="utf-8"))["partidos"]
    for aj in ajustes:
        ed = ediciones.get((aj.get("copa", "libertadores"), aj["anio"]))
        fase = next((f for f in ed["fases"] if f["nombre"] == aj["fase"]), None) if ed else None
        elegidos = [p for p in (fase or {}).get("partidos", [])
                    if all(p.get(k) == aj[k] for k in ("local", "fecha", "gl", "gv") if k in aj)]
        if not elegidos:
            print("  finales_ajustes.json: no se encontró", aj)
            continue
        for p in elegidos:
            if aj.get("borrar"):
                fase["partidos"].remove(p)
                continue
            if aj.get("invertir"):   # la fuente puso los equipos al revés: el resultado y los goles quedan como están
                p["local"], p["visitante"] = p["visitante"], p["local"]
            if "goles" in aj:
                p["goles"] = [g for g in p.get("goles") or [] if g.get("jugador") in aj["goles"]]
            for k, destino in (("estadio", "estadio"), ("ciudad", "ciudad"), ("nueva_fecha", "fecha")):
                if k in aj:
                    p[destino] = aj[k]


def entrenadores_de_formaciones(ediciones):
    """En las copas sin Transfermarkt (Mundial e Intercontinental), el entrenador de cada club sale de las formaciones
    de Wikipedia, que dicen quién dirigió cada partido. Escribe data/<copa>/entrenadores.js y el archivo de
    entrenadores por partido que usan las estadísticas (solo si hay algún dato)."""
    for clave in COPAS:
        if "tm" in COPAS[clave]:
            continue   # las copas de la Conmebol los bajan de Transfermarkt (descargar_entrenadores.py)
        por_club, por_partido = {}, {}
        for (c, anio), ed in sorted(ediciones.items()):
            if c != clave:
                continue
            for f in ed["fases"]:
                for p in f["partidos"]:
                    for lado, form in (p.get("formaciones") or {}).items():
                        dt = form.get("dt")
                        if not dt:
                            continue
                        lista = por_club.setdefault(str(anio), {}).setdefault(p[lado], [])
                        if dt not in lista:
                            lista.append(dt)
                        por_partido.setdefault(str(anio), {}).setdefault(
                            f'{p.get("fecha")}|{p["local"]}|{p["visitante"]}', {})[lado] = dt
        if not por_club:
            continue
        ns = COPAS[clave]["ns"]
        (COPAS[clave]["data"] / "entrenadores.js").write_text(
            "/* Generado por tools/generar_datos.py (fuente: formaciones de Wikipedia) — no editar a mano */\n" +
            prefijo_js(clave) + f"window.{ns}.entrenadores = " + json.dumps(por_club, ensure_ascii=False, separators=(",", ":")) +
            ";\n", encoding="utf-8")
        COPAS[clave]["entrenadores_partidos"].write_text(json.dumps(por_partido, ensure_ascii=False, separators=(",", ":")),
                                                         encoding="utf-8")


def escribir_sitemap(anios):
    """sitemap.xml: la lista de páginas que se le pasa a Google (la portada con el mapa, cada continente, y la
    portada, las estadísticas y cada edición de cada copa). anios: {copa: [años]}. En el XML el & se escribe &amp;"""
    urls = [URL_SITIO] + [f"{URL_SITIO}?continente={c}" for c in ("sudamerica", "europa")]
    for clave, lista in anios.items():
        copa = "" if clave == "libertadores" else f"copa={clave}&amp;"   # (la Libertadores sin copa=: los links viejos)
        urls += [f"{URL_SITIO}?copa={clave}", f"{URL_SITIO}?{copa}estadisticas"]
        urls += [f"{URL_SITIO}?{copa}edicion={a}" for a in lista]
    (RAIZ / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")


def escribir(ruta, prefijo, datos, clave="libertadores"):
    cuerpo = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    ruta.write_text("/* Generado por tools/generar_datos.py — no editar a mano */\n" + prefijo_js(clave)
                    + prefijo + cuerpo + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
