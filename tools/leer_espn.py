"""Lee lo descargado de ESPN (tools/cache/espn/<año>) y lo deja en el mismo formato que leer_rsssf.

No se usa solo: lo llama tools/generar_datos.py. Para revisar una temporada:
    python tools/leer_espn.py 2025
    python tools/leer_espn.py --copa sudamericana 2025
"""
import datetime
import json
import re
import unicodedata

from copas import COPAS, copa_de_argumentos

FASES = [
    (r"play-?off|first-stage|second-stage|third-stage|qualif|preliminary", "Fase previa"),
    (r"group", "Fase de grupos"),
    (r"round-of-16", "Octavos de final"),
    (r"quarter", "Cuartos de final"),
    (r"semi", "Semifinales"),
    (r"third", "Tercer puesto"),
    (r"^final", "Final"),
]
PREVIAS = {"first-stage": "Primera fase previa", "second-stage": "Segunda fase previa",
           "third-stage": "Tercera fase previa"}
# La Sudamericana: 2016 viene como "copa-sudamericana---first-phase" (se saca ese comienzo antes de comparar)
FASES_SUD = [
    (r"^preliminary", "Fase previa"),
    (r"^first-(phase|stage)", "Primera fase"),
    (r"^second-(phase|stage)", "Segunda fase"),
    (r"group", "Fase de grupos"),
    (r"knockout-round-playoffs", "Playoffs de octavos"),
    (r"round-of-16", "Octavos de final"),
    (r"quarter", "Cuartos de final"),
    (r"semi", "Semifinales"),
    (r"^finals?$", "Final"),
]


# Mundial de Clubes: el partido del campeón de Oceanía contra el del país organizador se llamó "playoff" (2007-2019)
# y "first round" (2020-2023); los cuartos de final, "second round" desde 2020. 2025: grupos y eliminación directa
FASES_MUN = [
    (r"qualifying|play-in", "Fase previa"),
    (r"^playoffs?$|first-round", "Primera ronda"),
    (r"quarter", "Cuartos de final"),
    (r"second-round", "Segunda ronda"),
    (r"group", "Fase de grupos"),
    (r"round-of-16", "Octavos de final"),
    (r"semi", "Semifinales"),
    (r"fifth", "Quinto puesto"),
    (r"third", "Tercer puesto"),
    (r"^final", "Final"),
]
# Copa Intercontinental de la FIFA (desde 2024): cada partido tiene su nombre. La "second round" son dos partidos:
# la Copa África-Asia-Pacífico (septiembre-octubre) y el Derbi de las Américas (diciembre)
FASES_INT = [
    (r"first-round", "Primera ronda"),
    (r"second-round", "Copa África-Asia-Pacífico"),
    (r"playoff", "Copa Challenger"),
    (r"^final", "Final"),
]
# Champions League: desde 2024/25, una fase de liga de 36 equipos (una sola tabla), playoffs y eliminación directa.
# En 2001/02 y 2002/03 hubo dos fases de grupos ("2001-second-phase"). Las rondas clasificatorias no se cargan
FASES_UCL = [
    (r"qualif|preliminary|^play-?off-round$|^playoffs$", "Fase previa"),   # el playoff de agosto (2009-2023) es clasificatorio
    (r"second-phase", "Segunda fase de grupos"),
    (r"league", "Fase de liga"),
    (r"group", "Fase de grupos"),
    (r"knockout-round-playoffs", "Playoffs de octavos"),
    (r"round-of-16", "Octavos de final"),
    (r"quarter", "Cuartos de final"),
    (r"semi", "Semifinales"),
    (r"^final", "Final"),
]

# Copa UEFA y Europa League: ESPN usó nombres distintos según la época (y "uefa.uefa" y "uefa.europa" se contradicen:
# "second-round" es la segunda ronda de 48 equipos en 2001-2003 y los dieciseisavos desde 2009), así que el slug se
# traduce primero según la temporada (ver slug_uel) y después pasa por esta tabla
FASES_UEL = [
    (r"qualif|preliminary|^play-?off-round$|^playoffs$", "Fase previa"),
    (r"^grupos$|group", "Fase de grupos"),
    (r"league", "Fase de liga"),
    (r"knockout-round-playoffs", "Playoffs de octavos"),
    (r"^primera$", "Primera ronda"),
    (r"^segunda$", "Segunda ronda"),
    (r"^dieciseisavos$|round-of-32", "Dieciseisavos de final"),
    (r"^octavos$|round-of-16", "Octavos de final"),
    (r"quarter", "Cuartos de final"),
    (r"semi", "Semifinales"),
    (r"^final", "Final"),
]


def previa_uefa(slug, qual):
    """Las rondas clasificatorias de las copas europeas. Hasta 2019 ESPN las tiene en la misma "liga" que la copa
    ('qualifying-second-round', 'first-qualifying-round', 'play-off-round'…); desde 2020, en una liga aparte
    ("uefa.champions_qual"…: qual, ver "_liga" en descargar_espn.py), donde se llaman 'first-round', 'playoff-round'…
    Devuelve None si no es una ronda clasificatoria."""
    if not qual and not re.search(r"qualif|preliminary|^play-?off-round$|^playoffs$", slug):
        return None
    for patron, nombre in ((r"preliminary", "Ronda preliminar"), (r"first", "Primera fase previa"),
                           (r"second", "Segunda fase previa"), (r"third", "Tercera fase previa"),
                           (r"play-?off", "Playoff de clasificación")):
        if re.search(patron, slug):
            return nombre
    return "Fase previa"   # la Copa UEFA 2001-2010: todas las rondas son 'qualifying-round' (las separa generar_datos.py)


def slug_uel(slug, temporada):
    """'2004-second-round' (grupos de la Copa UEFA 2004-2008) / '2009-first-round' (grupos de la Europa League) ->
    'grupos'; first/second/third/fourth-round -> la ronda según la temporada."""
    if re.match(r"^\d{4}-.*round$", slug):
        return "grupos"
    vieja = (temporada or 0) < 2009   # la Copa UEFA
    return {"first-round": "primera", "second-round": "segunda" if vieja else "dieciseisavos",
            "third-round": "dieciseisavos" if vieja else "octavos", "fourth-round": "octavos"}.get(slug, slug)


def fecha_local(iso):
    """ESPN da la hora en UTC; los partidos nocturnos de Sudamérica caen al día siguiente en UTC."""
    t = datetime.datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") - datetime.timedelta(hours=4)
    return t.strftime("%Y-%m-%d")


def nombre_fase(evento, copa="libertadores", grupos=None):
    """grupos: {id de ESPN del club: letra}, para las temporadas en que el partido no dice el grupo (Mundial 2025)."""
    slug = evento.get("season", {}).get("slug", "")
    nota = evento["competitions"][0].get("altGameNote") or ""
    if copa in ("champions", "europa", "conference"):
        previa = previa_uefa(slug, (evento.get("_liga") or "").endswith("_qual"))
        if previa:
            return previa
    if copa == "recopa":
        return "Final"   # la Recopa es solo la final (ESPN la llama "2026-conmebol-recopa")
    if copa == "sudamericana":
        slug = re.sub(r"^copa-sudamericana-+", "", slug)
    if copa == "europa":
        slug = slug_uel(slug, evento.get("season", {}).get("year"))
    tabla = {"sudamericana": FASES_SUD, "mundial": FASES_MUN, "intercontinental": FASES_INT,
             "champions": FASES_UCL, "europa": FASES_UEL, "conference": FASES_UCL}.get(copa, FASES)
    for patron, nombre in tabla:
        if nombre == "Copa África-Asia-Pacífico" and re.search(patron, slug) and evento["date"][5:7] == "12":
            return "Derbi de las Américas"
        if re.search(patron, slug):
            if nombre in ("Fase de grupos", "Segunda fase de grupos"):
                m = re.search(r"Group\s+(\w+)", nota)
                letra = m.group(1) if m else (grupos or {}).get(evento["competitions"][0]["competitors"][0]["team"]["id"])
                return f"{nombre} — Grupo {letra}" if letra else nombre
            if nombre == "Fase previa" and slug in PREVIAS:
                return PREVIAS[slug]
            return nombre
    return slug or "?"


def minuto(clock):
    """"90'+7'" -> (90, 7)"""
    m = re.match(r"(\d+)'?(?:\+(\d+))?", (clock or {}).get("displayValue", ""))
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None


def leer(anio, copa="libertadores"):
    carpeta = COPAS[copa]["cache_espn"] / str(anio)
    cal = json.loads((carpeta / "calendario.json").read_text(encoding="utf-8"))
    grupos = json.loads((carpeta / "grupos.json").read_text(encoding="utf-8")) if (carpeta / "grupos.json").exists() else {}
    partidos, equipos = [], {}
    for e in cal.get("events", []):
        comp = e["competitions"][0]
        lados = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in lados or "away" not in lados:
            continue
        for c in comp["competitors"]:
            t = c["team"]
            equipos[t["id"]] = {"nombre": t.get("displayName"), "corto": t.get("shortDisplayName"),
                                "color": t.get("color"), "color2": t.get("alternateColor"),
                                "escudo": t.get("logo")}
        estado = e["status"]["type"]
        p = {
            "espn": e["id"], "fase": nombre_fase(e, copa, grupos), "temporada_espn": (e.get("season") or {}).get("year"), "fecha": fecha_local(e["date"]), "hora_utc": e["date"],
            "local_espn": lados["home"]["team"]["id"], "visitante_espn": lados["away"]["team"]["id"],
            "local": lados["home"]["team"]["displayName"], "visitante": lados["away"]["team"]["displayName"],
            "gl": int(lados["home"]["score"]) if estado.get("completed") else None,
            "gv": int(lados["away"]["score"]) if estado.get("completed") else None,
            "jugado": bool(estado.get("completed")),
            "estadio": (comp.get("venue") or {}).get("fullName"),
            "ciudad": ((comp.get("venue") or {}).get("address") or {}).get("city"),
            "pais_estadio": ((comp.get("venue") or {}).get("address") or {}).get("country"),
            "notas": None, "goles": [],
        }
        if lados["home"].get("shootoutScore") is not None:
            p["pen_l"], p["pen_v"] = int(lados["home"]["shootoutScore"]), int(lados["away"]["shootoutScore"])
        serie = comp.get("series") or {}
        if serie.get("totalCompetitions") == 2:
            p["serie"] = "-".join(sorted(x["id"] for x in serie.get("competitors", [])))
        detalle = carpeta / f"{e['id']}.json"
        if detalle.exists():
            completar(p, json.loads(detalle.read_text(encoding="utf-8")))
        partidos.append(p)
    return {"anio": anio, "partidos": partidos, "equipos": equipos}


def apellido(nombre):
    """'Péguy Luyindula' -> 'luyindula' (para reconocer al mismo jugador escrito de dos formas)."""
    t = unicodedata.normalize("NFD", nombre or "").encode("ascii", "ignore").decode().lower().split()
    return t[-1] if t else ""


def sin_goles_repetidos(goles, p):
    """En algunos partidos viejos (2003-2010) ESPN tiene cada gol dos veces, a veces con el nombre escrito distinto
    ('Derlei Derlei' y 'Vanderlei Fernandes Da Silva Derlei') o un minuto corrido. Solo se tocan los equipos con
    más goles que los del resultado: se sacan los repetidos (mismo apellido, mismo minuto ±1) y, si igual sobran,
    se sacan todos los de ese equipo (no se sabe cuáles son los buenos)."""
    for lado, total in (("local", p.get("gl")), ("visitante", p.get("gv"))):
        del_lado = [g for g in goles if g["lado"] == lado]
        if total is None or len(del_lado) <= total:
            continue
        quedan = []
        for g in del_lado:
            if not any(apellido(g["jugador"]) == apellido(q["jugador"]) and g["min"] is not None and q["min"] is not None
                       and abs(g["min"] - q["min"]) <= 1 for q in quedan):
                quedan.append(g)
        if len(quedan) > total:
            quedan = []
        goles = [g for g in goles if g["lado"] != lado or any(g is q for q in quedan)]
    return goles


def completar(p, d):
    """Goles, asistencias, formaciones, árbitro y público desde el detalle del partido."""
    info = d.get("gameInfo") or {}
    if (info.get("venue") or {}).get("fullName"):
        p["estadio"] = info["venue"]["fullName"]
        p["ciudad"] = (info["venue"].get("address") or {}).get("city") or p.get("ciudad")
    if info.get("attendance"):
        p["publico"] = info["attendance"]
    arb = [o.get("displayName") for o in info.get("officials") or []]
    if arb:
        p["arbitro"] = arb[0]
    goles = []
    for k in d.get("keyEvents", []):
        if not k.get("scoringPlay") or k.get("shootout"):
            continue
        tipo = k["type"]["type"]
        part = [x["athlete"] for x in k.get("participants", [])]
        mi, extra = minuto(k.get("clock"))
        goles.append({
            "jugador": part[0].get("displayName") if part else None,
            "jid": part[0].get("id") if part else None,
            "asistencia": part[1].get("displayName") if len(part) > 1 and tipo != "own-goal" else None,
            "aid": part[1].get("id") if len(part) > 1 and tipo != "own-goal" else None,
            "min": mi, "extra": extra,
            "tipo": "ec" if tipo == "own-goal" else "pen" if tipo.startswith("penalty") else None,
            "lado": "local" if k.get("team", {}).get("id") == p["local_espn"] else "visitante",
        })
    p["goles"] = sin_goles_repetidos(goles, p)
    # Tanda de penales: cada remate en el orden en que se pateó. Por ronda (shotNumber); dentro de la ronda,
    # primero el equipo que abrió la tanda (el del primer remate según la numeración de eventos de ESPN)
    tanda = []
    for eq in d.get("shootout") or []:
        lado = "local" if eq.get("id") == p["local_espn"] else "visitante"
        for t in eq.get("shots", []):
            tanda.append({"ronda": t.get("shotNumber") or 0, "ev": int(t.get("id") or 0), "jugador": t.get("player"),
                          "jid": t.get("playerId"), "gol": bool(t.get("didScore")), "lado": lado})
    if tanda:
        abre = min(tanda, key=lambda t: (t["ronda"], t["ev"]))["lado"]
        tanda.sort(key=lambda t: (t["ronda"], t["lado"] != abre))
        p["tanda"] = [{k: v for k, v in t.items() if k not in ("ronda", "ev")} for t in tanda]
    # Tarjetas rojas y cambios (con minuto)
    rojas, cambios = [], []
    for k in d.get("keyEvents", []):
        tipo = k["type"]["type"]
        part = [x["athlete"] for x in k.get("participants", [])]
        mi, _ = minuto(k.get("clock"))
        if tipo == "red-card" and part:
            rojas.append({"id": part[0].get("id"), "min": mi, "equipo": k.get("team", {}).get("id")})
        if tipo == "substitution" and len(part) == 2:
            cambios.append({"ids": (part[0].get("id"), part[1].get("id")), "min": mi})
    formaciones = {}
    for r in d.get("rosters", []):
        eq = (r.get("team") or {}).get("id")
        jug = r.get("roster", [])
        if not jug:
            continue
        entraron = {j["id"] for j in jug if j.get("entro")}
        f = {"esquema": r.get("formation"), "titulares": [], "suplentes": []}
        for j in jug:
            dato = {"id": j["id"], "nombre": j["nombre"], "num": j.get("camiseta"), "pos": j.get("posicion")}
            (f["titulares"] if j.get("titular") else f["suplentes"]).append(dato)
        # minuto de entrada de cada suplente y a quién reemplazó
        for c in cambios:
            a, b = c["ids"]
            entra, sale = (a, b) if a in entraron else (b, a) if b in entraron else (None, None)
            for s in f["suplentes"]:
                if s["id"] == entra:
                    s["min"], s["por"] = c["min"], sale
        for s in f["suplentes"]:
            s["jugo"] = s["id"] in entraron
        for x in rojas:
            for j in f["titulares"] + f["suplentes"]:
                if j["id"] == x["id"]:
                    j["roja"] = x["min"]
        formaciones["local" if eq == p["local_espn"] else "visitante"] = f
    if formaciones:
        p["formaciones"] = formaciones


if __name__ == "__main__":
    clave, args = copa_de_argumentos()
    for a in [int(x) for x in args] or [2024]:
        r = leer(a, clave)
        for p in r["partidos"]:
            print(f"{p['fase']:<32} {p['fecha']} {p['local']:>26} {p['gl']}-{p['gv']} {p['visitante']:<26} "
                  f"{len(p['goles'])}g {'F' if p.get('formaciones') else '-'}")
        print(len(r["partidos"]), "partidos,", len(r["equipos"]), "equipos")
