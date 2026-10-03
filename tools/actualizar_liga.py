"""Baja de ESPN un torneo de la liga argentina (por ahora, el Clausura 2026) y arma data/ligas/argentina/<torneo>.js.

Uso:  py tools/actualizar_liga.py                 (los torneos de TORNEOS que no terminaron)
      py tools/actualizar_liga.py 2026-clausura   (solo ese)
      py tools/actualizar_liga.py todos           (todos, también los terminados)

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
    # 2025: igual que 2026 (dos torneos con zonas, tabla anual, promedios y cupos). Los promedios de 2025 son
    # 2023 (Copa de la Liga y Liga Profesional), 2024 y 2025. Descendieron Godoy Cruz (tabla anual) y San Martín de
    # San Juan (promedios). Lanús fue a la Libertadores 2026 por ganar la Sudamericana 2025: un lugar aparte ("extra")
    "2025-apertura": {"nombre": "Torneo Apertura 2025", "anio": 2025, "slug": "apertura", "fechas": 16, "pasan": 8,
                      "zonas_de": "clausura"},
    "2025-clausura": {"nombre": "Torneo Clausura 2025", "anio": 2025, "slug": "clausura", "fechas": 16, "pasan": 8,
                      "anual": [("arg.1", r"^torneo-apertura$")],
                      "promedios": {2023: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")],
                                    2024: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")]},
                      "descensos": True,
                      # en noviembre de 2025 la AFA le dio un título al primero de la tabla anual
                      "titulo_anual": "Campeón de Liga 2025",
                      "cupos": {"anio": 2026, "libertadores": 6, "sudamericana": 6,
                                "campeones": [("Torneo Apertura 2025", "arg.1", r"^apertura---final$"),
                                              ("Torneo Clausura 2025", "arg.1", r"^clausura---final$"),
                                              ("Copa Argentina 2025", "arg.copa", r"^final$"),
                                              ("Copa Sudamericana 2025", "conmebol.sudamericana", r"(^|-)final$", "extra")]}},
    # Las zonas del Apertura 2026 fueron las mismas que las del Clausura (la tabla de ESPN ya muestra solo las del
    # Clausura): "zonas_de" usa las de ese torneo. armar() controla que cada club tenga 2 partidos interzonales
    "2026-apertura": {"nombre": "Torneo Apertura 2026", "anio": 2026, "slug": "apertura", "fechas": 16, "pasan": 8,
                      "zonas_de": "clausura"},
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
                      "descensos": True,
                      # Cupos para las copas del año que viene (reglamento de la AFA, marzo de 2026): a la Libertadores
                      # van los tres campeones del año y los mejores de la tabla anual hasta completar 6; a la
                      # Sudamericana, los 6 siguientes. Si un campeón ya entra por la tabla, su lugar pasa al
                      # siguiente; los que descienden no juegan copas. Los campeones salen de la final de ESPN
                      "cupos": {"anio": 2027, "libertadores": 6, "sudamericana": 6,
                                "campeones": [("Torneo Apertura 2026", "arg.1", r"^apertura---final$"),
                                              ("Torneo Clausura 2026", "arg.1", r"^clausura---final$"),
                                              ("Copa Argentina 2026", "arg.copa", r"^final$")]}},
}
# Puntos descontados por sanciones: {(año, id de ESPN): puntos}. Por ahora, ninguno
DESCUENTOS = {}
PLAYOFFS = [("round-of-16", "Octavos de final"), ("quarter", "Cuartos de final"), ("semi", "Semifinales"),
            ("final", "Final")]
# Clubes que no están en data/equipos.js (no jugaron copas internacionales): id y nombre. Los demás se toman de ahí
CLUBES_NUEVOS = {
    "2975": ("instituto", "Instituto"),
    "11972": ("gimnasia-mendoza", "Gimnasia (Mendoza)"),
    "7845": ("san-martin-san-juan", "San Martín de San Juan"),
    "9739": ("aldosivi", "Aldosivi"),
    "10158": ("sarmiento", "Sarmiento"),
    "19685": ("estudiantes-rio-cuarto", "Estudiantes de Río Cuarto"),
}

# Nombres que en la liga se confunden (en data/equipos.js están como en las copas)
NOMBRES = {"gimnasia-y-esgrima": "Gimnasia (La Plata)"}


def hora_argentina(iso):
    return datetime.datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") - datetime.timedelta(hours=3)


def bajar(anio, slug, con_zonas=True):
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
    if con_zonas and not zonas.exists():
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


def campeon(liga, anio, patron, club):
    """El ganador de una final de ESPN (también si se definió por penales), o None si todavía no se jugó.
    club: la función que convierte el equipo de ESPN en nuestro id (y suma el club a la lista)."""
    for e in calendario(liga, anio).get("events", []):
        if re.search(patron, (e.get("season") or {}).get("slug", "")) and e["status"]["type"].get("completed"):
            ganador = [c for c in e["competitions"][0]["competitors"] if c.get("winner")]
            if ganador:
                return club(ganador[0]["team"])
    return None


def repartir_fechas(partidos, cantidad):
    """Le pone a cada partido de la fase regular su número de fecha (fecha_n). ESPN no lo dice, así que se recorren
    los partidos en el orden en que se jugaron (o se van a jugar):
    - Si los dos clubes deben un partido de una fecha ya cerrada, es un partido postergado: va a esa fecha.
    - Si no, va a la fecha en curso, salvo que alguno de los dos ya haya jugado en ella (o que ya esté completa):
      entonces empieza la fecha siguiente. Así se separan también las fechas pegadas (una que termina el lunes y
      otra que empieza el martes).
    Los partidos sin jugar con día a confirmar ESPN los pone todos juntos un domingo: quedan bien igual."""
    por_fecha = max(1, len({c for p in partidos for c in (p["local"], p["visitante"])}) // 2)
    fechas = []   # [{clubes}, ...]; la última es la que está en curso
    for p in sorted(partidos, key=lambda p: p["hora_utc"]):
        par = {p["local"], p["visitante"]}
        debe = [n for n, clubes in enumerate(fechas[:-1]) if not par & clubes]
        if debe:
            n = debe[0]
        elif not fechas or par & fechas[-1] or len(fechas[-1]) >= 2 * por_fecha:
            fechas.append(set())
            n = len(fechas) - 1
        else:
            n = len(fechas) - 1
        fechas[n] |= par
        p["fecha_n"] = n + 1
    if len(fechas) != cantidad:
        print(f"  ojo: salieron {len(fechas)} fechas (se esperaban {cantidad})", flush=True)
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
    eventos = bajar(cfg["anio"], cfg["slug"], con_zonas="zonas_de" not in cfg)
    carpeta = CACHE / str(cfg["anio"])
    zonas_espn = json.loads((carpeta / f"zonas-{cfg.get('zonas_de', cfg['slug'])}.json").read_text(encoding="utf-8"))
    # control: con las zonas bien puestas, cada club juega 2 partidos contra la otra zona en la fase regular
    zona_de = {i: z for z, ids in zonas_espn.items() for i in ids}
    interzonales = {}
    for e in eventos:
        ids = [c["team"]["id"] for c in e["competitions"][0]["competitors"]]
        if e["season"]["slug"].startswith("torneo-") and zona_de.get(ids[0]) != zona_de.get(ids[1]):
            for i in ids:
                interzonales[i] = interzonales.get(i, 0) + 1
    raros = {i: n for i, n in interzonales.items() if n > 2}
    if raros:
        print(f"  ojo: clubes con más de 2 partidos contra la otra zona (¿zonas equivocadas?): {raros}", flush=True)
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
        if estado.get("name") == "STATUS_FINAL_AET":   # (los que se definieron por penales no dicen si hubo alargue)
            p["alargue"] = True
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
    if cfg.get("titulo_anual"):
        datos["titulo_anual"] = cfg["titulo_anual"]
    if cfg.get("cupos"):
        cupos = dict(cfg["cupos"])
        # extra: un lugar que no es de la liga (el campeón de la Sudamericana va a la Libertadores por la Conmebol)
        cupos["campeones"] = [{"titulo": titulo, "club": campeon(liga, cfg["anio"], patron, club), **({"extra": True} if extra else {})}
                              for titulo, liga, patron, *extra in cfg["cupos"]["campeones"]]
        datos["cupos"] = cupos
    DATOS.mkdir(parents=True, exist_ok=True)
    # si no cambió nada desde la última vez, queda la hora de antes (así un torneo terminado no cambia cada noche)
    archivo = DATOS / f"{clave}.js"
    if archivo.exists():
        t = archivo.read_text(encoding="utf-8")
        antes = json.JSONDecoder().raw_decode(t[t.index("] = ") + 4:])[0]
        if {**antes, "actualizado": None} == {**json.loads(json.dumps(datos)), "actualizado": None}:
            datos["actualizado"] = antes["actualizado"]
    js = ("/* Generado por tools/actualizar_liga.py — no editar a mano */\n"
          "window.LIGA = window.LIGA || {};\n"
          f"window.LIGA[{json.dumps(clave)}] = {json.dumps(datos, ensure_ascii=False, separators=(',', ':'))};\n")
    (DATOS / f"{clave}.js").write_text(js, encoding="utf-8")
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


def escribir_indice():
    """El índice de torneos de la liga (para la lista de la página), en orden."""
    indice = [{"clave": c, "nombre": t["nombre"]} for c, t in TORNEOS.items() if (DATOS / f"{c}.js").exists()]
    (DATOS / "indice.js").write_text("/* Generado por tools/actualizar_liga.py — no editar a mano */\n"
                                     f"window.LIGA_INDICE = {json.dumps(indice, ensure_ascii=False)};\n", encoding="utf-8")


def terminado(clave):
    """Si el torneo ya tiene campeón (la final jugada en los datos), no hace falta volver a bajarlo cada noche."""
    archivo = DATOS / f"{clave}.js"
    if not archivo.exists():
        return False
    t = archivo.read_text(encoding="utf-8")
    d = json.JSONDecoder().raw_decode(t[t.index("] = ") + 4:])[0]
    return any(r["nombre"] == "Final" and all("gl" in p for p in r["partidos"]) for r in d["playoffs"])


def main():
    """Sin nada, los torneos que no terminaron; con nombres (o "todos"), esos."""
    pedidos = [a for a in sys.argv[1:] if a in TORNEOS]
    if not pedidos:
        pedidos = list(TORNEOS) if "todos" in sys.argv else [c for c in TORNEOS if not terminado(c)]
    # (los torneos que usan las zonas de otro van después: ese otro baja las zonas)
    for clave in sorted(pedidos, key=lambda c: "zonas_de" in TORNEOS[c]):
        armar(clave)
    escribir_indice()


if __name__ == "__main__":
    main()
