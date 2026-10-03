"""Baja de ESPN un torneo de la liga argentina (por ahora, el Clausura 2026) y arma data/ligas/argentina/<torneo>.js.

Uso:  py tools/actualizar_liga.py                 (los torneos de TORNEOS)
      py tools/actualizar_liga.py 2026-clausura   (solo ese)

La tabla de posiciones no se guarda: la calcula la página con los resultados. Por eso alcanza con correr este
script una vez por día (lo hace la tarea programada) para que la tabla quede al día.

Guarda en tools/cache/espn-liga-argentina/<año>/ lo mismo que descargar_espn.py (calendario.json y el detalle de
cada partido terminado) más zonas.json (los clubes de cada zona, de la tabla de ESPN).
ESPN no dice a qué fecha pertenece cada partido: se deduce (ver repartir_fechas).
"""
import datetime
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from descargar_espn import pedir, recortar   # noqa: E402
from leer_espn import completar   # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "tools" / "cache" / "espn-liga-argentina"
DATOS = RAIZ / "data" / "ligas" / "argentina"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/arg.1"
ESCUDO = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/{}.png&h=120&w=120"

# slug: cómo llama ESPN a la fase regular ("torneo-clausura") y a los playoffs ("clausura---round-of-16")
TORNEOS = {
    "2026-clausura": {"nombre": "Torneo Clausura 2026", "anio": 2026, "slug": "clausura", "fechas": 16,
                      "pasan": 8,   # los 8 primeros de cada zona juegan los octavos de final
                      # La tabla anual suma la fase de zonas del Apertura y del Clausura (sin playoffs): acá, lo que
                      # se jugó antes de este torneo en el año. La página le suma este torneo
                      "anual": [("arg.1", r"^torneo-apertura$")],
                      # Los promedios: puntos dividido partidos de las tres últimas temporadas (fases regulares;
                      # los recién ascendidos, solo los partidos que jugaron en Primera). Acá, las temporadas
                      # anteriores; la del año es la tabla anual
                      "promedios": {2024: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")],
                                    2025: [("arg.1", r"^torneo-(apertura|clausura)$")]},
                      # Descienden el último de la tabla anual y el peor promedio (si es el mismo club, el
                      # anteúltimo de la tabla anual)
                      "descensos": True},
}
# Puntos descontados por sanciones: {(año, id de ESPN): puntos}. Por ahora, ninguno
DESCUENTOS = {}
PLAYOFFS = [("round-of-16", "Octavos de final"), ("quarter", "Cuartos de final"), ("semi", "Semifinales"),
            ("final", "Final")]
# Clubes que no están en data/equipos.js (no jugaron copas internacionales): id y nombre. Los demás se toman de ahí
CLUBES_NUEVOS = {
    "2975": ("instituto", "Instituto"),
    "11972": ("gimnasia-mendoza", "Gimnasia (Mendoza)"),
    "9739": ("aldosivi", "Aldosivi"),
    "10158": ("sarmiento", "Sarmiento"),
    "19685": ("estudiantes-rio-cuarto", "Estudiantes de Río Cuarto"),
}

# Nombres que en la liga se confunden (en data/equipos.js están como en las copas)
NOMBRES = {"gimnasia-y-esgrima": "Gimnasia (La Plata)"}


def hora_argentina(iso):
    return datetime.datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") - datetime.timedelta(hours=3)


def bajar(anio, slug):
    """El calendario del año, el detalle de los partidos terminados del torneo y las zonas."""
    carpeta = CACHE / str(anio)
    carpeta.mkdir(parents=True, exist_ok=True)
    cal = pedir(f"{ESPN}/scoreboard?dates={anio}&limit=1000")
    (carpeta / "calendario.json").write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
    eventos = [e for e in cal.get("events", []) if slug in (e.get("season") or {}).get("slug", "")]
    nuevos = 0
    for e in eventos:
        archivo = carpeta / f"{e['id']}.json"
        if not e["status"]["type"].get("completed") or archivo.exists():
            continue
        try:
            archivo.write_text(json.dumps(recortar(pedir(f"{ESPN}/summary?event={e['id']}")), ensure_ascii=False),
                               encoding="utf-8")
            nuevos += 1
            time.sleep(0.4)
        except Exception as x:   # se vuelve a pedir la próxima vez
            print(f"  no se pudo bajar el partido {e['id']} ({x})", flush=True)
    # Las zonas: la tabla de ESPN tiene dos grupos de 15 mientras se juega la fase regular. Se guardan la primera
    # vez (en los playoffs la tabla puede cambiar de forma)
    zonas = carpeta / f"zonas-{slug}.json"
    if not zonas.exists():
        tabla = pedir(f"{ESPN.replace('/site/v2/', '/v2/')}/standings?season={anio}")
        z = {g["name"].split()[-1]: [x["team"]["id"] for x in g["standings"]["entries"]] for g in tabla.get("children", [])}
        if len(z) == 2 and all(len(v) >= 10 for v in z.values()):
            zonas.write_text(json.dumps(z), encoding="utf-8")
    print(f"{anio} {slug}: {len(eventos)} partidos en el calendario, {nuevos} detalles nuevos", flush=True)
    return eventos


def calendario(liga, anio):
    """El calendario de un año de una liga de ESPN ("arg.1", "arg.copa_lpf"). Los años terminados se bajan una
    sola vez; el año del torneo en curso ya lo bajó bajar()."""
    archivo = CACHE / str(anio) / ("calendario.json" if liga == "arg.1" else f"calendario-{liga}.json")
    if not archivo.exists() or (anio >= datetime.date.today().year and liga != "arg.1"):
        archivo.parent.mkdir(parents=True, exist_ok=True)
        cal = pedir(f"{ESPN.rsplit('/', 1)[0]}/{liga}/scoreboard?dates={anio}&limit=1000")
        archivo.write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
    return json.loads(archivo.read_text(encoding="utf-8"))


def sumar(anio, fuentes):
    """Puntos, partidos y goles de cada club (id de ESPN) en los partidos terminados de esas fases:
    {id: [pts, pj, g, e, p, gf, gc]}. fuentes: [(liga, patrón del slug de la fase)]."""
    t = {}
    for liga, patron in fuentes:
        for e in calendario(liga, anio).get("events", []):
            if not re.search(patron, (e.get("season") or {}).get("slug", "")) or not e["status"]["type"].get("completed"):
                continue
            c = e["competitions"][0]["competitors"]
            for a, b in ((c[0], c[1]), (c[1], c[0])):
                ga, gb = int(a["score"]), int(b["score"])
                f = t.setdefault(a["team"]["id"], [0] * 7)
                r = 2 if ga > gb else 3 if ga == gb else 4
                f[0] += {2: 3, 3: 1, 4: 0}[r]
                f[1] += 1
                f[r] += 1
                f[5] += ga
                f[6] += gb
    for (a, eid), pts in DESCUENTOS.items():
        if a == anio and eid in t:
            t[eid][0] -= pts
    return t


def repartir_fechas(partidos, cantidad):
    """Le pone a cada partido de la fase regular su número de fecha. ESPN no lo dice, así que:
    1. Se ordenan por día y se cortan en tandas donde hay un día sin partidos.
    2. Tandas vecinas sin clubes repetidos se juntan (una fecha que se jugó con un día libre en el medio).
    3. Si quedan más tandas que fechas, las más chicas (partidos postergados sueltos) se pegan a la anterior.
    4. Si en una tanda un club juega dos veces, uno de esos partidos es postergado: va a la fecha en la que a los
       dos clubes les falta un partido.
    Los partidos sin jugar con día a confirmar ESPN los pone todos juntos un domingo: quedan bien igual."""
    orden = sorted(partidos, key=lambda p: p["hora_utc"])
    tandas = []
    for p in orden:
        dia = hora_argentina(p["hora_utc"]).date()
        if tandas and (dia - tandas[-1]["ultimo"]).days <= 1:
            tandas[-1]["partidos"].append(p)
        else:
            tandas.append({"partidos": [p]})
        tandas[-1]["ultimo"] = dia
    clubes = lambda t: {c for p in t for c in (p["local"], p["visitante"])}
    juntas = []
    for t in tandas:
        if juntas and not clubes(juntas[-1]) & clubes(t["partidos"]):
            juntas[-1] += t["partidos"]
        else:
            juntas.append(list(t["partidos"]))
    while len(juntas) > cantidad:   # sobran tandas: la más chica (partidos postergados sueltos) va con la anterior
        i = min(range(len(juntas)), key=lambda k: (len(juntas[k]), -k))   # (si empatan, la más tardía)
        sueltos = juntas.pop(i)
        juntas[max(i - 1, 0)].extend(sueltos)   # (si era la primera, va con la siguiente)
    for n, t in enumerate(juntas, 1):
        for p in t:
            p["fecha_n"] = n
    # partidos postergados: el club que juega dos veces en una fecha
    total = max(len(juntas), cantidad)
    for _ in range(3):
        for n in range(1, total + 1):
            en_fecha = [p for p in partidos if p["fecha_n"] == n]
            cuenta = {}
            for p in en_fecha:
                for c in (p["local"], p["visitante"]):
                    cuenta[c] = cuenta.get(c, 0) + 1
            for p in sorted(en_fecha, key=lambda p: p["hora_utc"], reverse=True):
                if cuenta[p["local"]] < 2 and cuenta[p["visitante"]] < 2:
                    continue
                jugadas = lambda c: {q["fecha_n"] for q in partidos if c in (q["local"], q["visitante"])}
                libres = [f for f in range(1, total + 1) if f not in jugadas(p["local"]) | jugadas(p["visitante"])]
                if libres:
                    cuenta[p["local"]] -= 1
                    cuenta[p["visitante"]] -= 1
                    p["fecha_n"] = min(libres, key=lambda f: abs(f - n))
    return partidos


def slug_club(nombre):
    t = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def catalogo():
    """{id de ESPN: id nuestro} y los datos de cada club, de data/equipos.js."""
    t = (RAIZ / "data" / "equipos.js").read_text(encoding="utf-8")
    eq = json.JSONDecoder().raw_decode(t[t.index("equipos = ") + 10:])[0]
    return {e: k for k, v in eq.items() for e in v.get("espn", [])}, eq


def armar(clave):
    cfg = TORNEOS[clave]
    eventos = bajar(cfg["anio"], cfg["slug"])
    carpeta = CACHE / str(cfg["anio"])
    zonas_espn = json.loads((carpeta / f"zonas-{cfg['slug']}.json").read_text(encoding="utf-8"))
    espn_a_club, eq = catalogo()
    clubes = {}

    def club(t):
        eid = t["id"]
        if eid in CLUBES_NUEVOS:
            cid, nombre = CLUBES_NUEVOS[eid]
        elif eid in espn_a_club:
            cid = espn_a_club[eid]
            nombre = eq[cid]["nombre"]
        else:   # un club que no conocemos: se usa el nombre de ESPN (y se avisa para ponerle uno mejor)
            cid, nombre = slug_club(t["displayName"]), t["displayName"]
            print(f"  club nuevo sin nombre propio: {nombre} (ESPN {eid}); sumarlo a CLUBES_NUEVOS", flush=True)
        nombre = NOMBRES.get(cid, nombre)
        if cid not in clubes:
            escudo = RAIZ / "assets" / "escudos" / f"{cid}.png"
            if not escudo.exists():
                try:
                    req = urllib.request.Request(ESCUDO.format(eid), headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        escudo.write_bytes(r.read())
                except Exception as x:
                    print(f"  no se pudo bajar el escudo de {nombre} ({x})", flush=True)
            clubes[cid] = {"nombre": nombre, "escudo": f"assets/escudos/{cid}.png" if escudo.exists() else None,
                           "colores": eq.get(cid, {}).get("colores") or (["#" + t["color"]] if t.get("color") else None)}
        return cid

    regular, playoffs = [], {}
    for e in sorted(eventos, key=lambda e: e["date"]):
        comp = e["competitions"][0]
        lados = {c["homeAway"]: c for c in comp["competitors"]}
        estado = e["status"]["type"]
        hora = hora_argentina(e["date"])
        p = {
            "espn": e["id"], "hora_utc": e["date"],
            "fecha": hora.strftime("%Y-%m-%d") if comp.get("timeValid", True) else None,
            # ESPN pone "TBD" (y una hora inventada) cuando todavía no se sabe el día
            "hora": hora.strftime("%H:%M") if comp.get("timeValid", e.get("timeValid", True)) else None,
            "a_confirmar": not comp.get("timeValid", True),
            "local": club(lados["home"]["team"]), "visitante": club(lados["away"]["team"]),
            "local_espn": lados["home"]["team"]["id"],
            "gl": int(lados["home"]["score"]) if estado.get("completed") else None,
            "gv": int(lados["away"]["score"]) if estado.get("completed") else None,
            "estadio": (comp.get("venue") or {}).get("fullName"),
            "goles": [],
        }
        if estado.get("name") in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_ABANDONED"):
            p["estado"] = {"STATUS_POSTPONED": "Postergado", "STATUS_CANCELED": "Cancelado",
                           "STATUS_SUSPENDED": "Suspendido", "STATUS_ABANDONED": "Suspendido"}[estado["name"]]
        if lados["home"].get("shootoutScore") is not None:
            p["pen_l"], p["pen_v"] = int(lados["home"]["shootoutScore"]), int(lados["away"]["shootoutScore"])
        detalle = carpeta / f"{e['id']}.json"
        if detalle.exists():
            completar(p, json.loads(detalle.read_text(encoding="utf-8")))
        p["goles"] = [{**{k: v for k, v in g.items() if v is not None and k not in ("lado", "aid")}, "equipo": g["lado"]}
                      for g in p["goles"]]
        p.pop("formaciones", None)
        slug = e["season"]["slug"]
        fase = next((n for s, n in PLAYOFFS if re.search(rf"---{s}", slug)), None)
        if fase:
            playoffs.setdefault(fase, []).append(p)
        else:
            regular.append(p)

    repartir_fechas(regular, cfg["fechas"])
    fechas = {}
    for p in regular:
        fechas.setdefault(p["fecha_n"], []).append(p)
    limpio = lambda p: {k: v for k, v in p.items() if k not in ("hora_utc", "local_espn", "fecha_n", "a_confirmar")
                        and v is not None and v is not False and v != []}
    zonas = {}
    for letra, ids in zonas_espn.items():
        zonas[letra] = [club({"id": i, "displayName": i}) for i in ids]
    datos = {
        "clave": clave, "nombre": cfg["nombre"], "anio": cfg["anio"], "pasan": cfg["pasan"],
        "actualizado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "zonas": zonas,
        "fechas": [{"numero": n, "partidos": [limpio(p) for p in sorted(fechas[n], key=lambda p: p["hora_utc"])]}
                   for n in sorted(fechas)],
        "playoffs": [{"nombre": n, "partidos": [limpio(p) for p in playoffs[n]]} for _, n in PLAYOFFS if n in playoffs],
        "clubes": clubes,
    }
    # tabla anual (lo jugado antes en el año) y promedios (las temporadas anteriores), solo de los clubes del torneo
    espn_de = {cid: eid for z in zonas_espn for eid, cid in zip(zonas_espn[z], zonas[z])}   # {id nuestro: id de ESPN}
    if cfg.get("anual"):
        previo = sumar(cfg["anio"], cfg["anual"])
        datos["anual"] = {cid: previo[eid] for cid, eid in espn_de.items() if eid in previo}
    if cfg.get("promedios"):
        datos["promedios"] = {}
        for anio, fuentes in cfg["promedios"].items():
            s = sumar(anio, fuentes)
            datos["promedios"][anio] = {cid: s[eid][:2] for cid, eid in espn_de.items() if eid in s}
    datos["descensos"] = cfg.get("descensos", False)
    DATOS.mkdir(parents=True, exist_ok=True)
    js = ("/* Generado por tools/actualizar_liga.py — no editar a mano */\n"
          "window.LIGA = window.LIGA || {};\n"
          f"window.LIGA[{json.dumps(clave)}] = {json.dumps(datos, ensure_ascii=False, separators=(',', ':'))};\n")
    (DATOS / f"{clave}.js").write_text(js, encoding="utf-8")
    # el índice de torneos de la liga (para la lista de la página)
    indice = [{"clave": c, "nombre": t["nombre"]} for c, t in TORNEOS.items() if (DATOS / f"{c}.js").exists()]
    (DATOS / "indice.js").write_text("/* Generado por tools/actualizar_liga.py — no editar a mano */\n"
                                     f"window.LIGA_INDICE = {json.dumps(indice, ensure_ascii=False)};\n", encoding="utf-8")
    jugados = sum(p["gl"] is not None for p in regular)
    print(f"{cfg['nombre']}: {len(fechas)} fechas, {jugados} de {len(regular)} partidos jugados; "
          f"playoffs: {sum(len(v) for v in playoffs.values())} partidos", flush=True)
    for n in sorted(fechas):
        cuenta = {}
        for p in fechas[n]:
            for c in (p["local"], p["visitante"]):
                cuenta[c] = cuenta.get(c, 0) + 1
        repetidos = [c for c, k in cuenta.items() if k > 1]
        if len(fechas[n]) != 15 or repetidos:
            print(f"  fecha {n}: {len(fechas[n])} partidos{'; repetidos: ' + ', '.join(repetidos) if repetidos else ''}")
    return datos


def main():
    for clave in [a for a in sys.argv[1:] if a in TORNEOS] or list(TORNEOS):
        armar(clave)


if __name__ == "__main__":
    main()
