"""Lee lo descargado de ESPN (tools/cache/espn/<año>) y lo deja en el mismo formato que leer_rsssf.

No se usa solo: lo llama tools/generar_datos.py. Para revisar una temporada:
    python tools/leer_espn.py 2025
    python tools/leer_espn.py --copa sudamericana 2025
"""
import datetime
import json
import re

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


def fecha_local(iso):
    """ESPN da la hora en UTC; los partidos nocturnos de Sudamérica caen al día siguiente en UTC."""
    t = datetime.datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") - datetime.timedelta(hours=4)
    return t.strftime("%Y-%m-%d")


def nombre_fase(evento, copa="libertadores"):
    slug = evento.get("season", {}).get("slug", "")
    nota = evento["competitions"][0].get("altGameNote") or ""
    if copa == "sudamericana":
        slug = re.sub(r"^copa-sudamericana-+", "", slug)
    for patron, nombre in (FASES_SUD if copa == "sudamericana" else FASES):
        if re.search(patron, slug):
            if nombre == "Fase de grupos":
                m = re.search(r"Group\s+(\w+)", nota)
                return f"Fase de grupos — Grupo {m.group(1)}" if m else nombre
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
            "espn": e["id"], "fase": nombre_fase(e, copa), "temporada_espn": (e.get("season") or {}).get("year"), "fecha": fecha_local(e["date"]), "hora_utc": e["date"],
            "local_espn": lados["home"]["team"]["id"], "visitante_espn": lados["away"]["team"]["id"],
            "local": lados["home"]["team"]["displayName"], "visitante": lados["away"]["team"]["displayName"],
            "gl": int(lados["home"]["score"]) if estado.get("completed") else None,
            "gv": int(lados["away"]["score"]) if estado.get("completed") else None,
            "jugado": bool(estado.get("completed")),
            "estadio": (comp.get("venue") or {}).get("fullName"),
            "ciudad": ((comp.get("venue") or {}).get("address") or {}).get("city"),
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
    p["goles"] = goles
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
