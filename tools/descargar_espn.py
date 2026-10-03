"""Descarga de ESPN los partidos de la Libertadores (o de la Sudamericana) 2005 en adelante.

Uso:  python tools/descargar_espn.py            (todas las temporadas)
      python tools/descargar_espn.py 2025 2026  (solo esas)
      python tools/descargar_espn.py --copa sudamericana [años]
      python tools/descargar_espn.py --copa europa fichas   (solo el país de los clubes, ver fichas_de_equipos)

Guarda en tools/cache/espn/<año>/ (la Sudamericana, en tools/cache/espn-sudamericana/<año>/):
  calendario.json     — la lista de partidos de la temporada
  <id_partido>.json   — el detalle de cada partido (solo lo que usamos)
  grupos.json         — el grupo de cada club, solo si los partidos no lo dicen (Mundial de Clubes 2025)
Los partidos ya descargados y terminados no se vuelven a pedir (salvo los que se definieron por penales
y se bajaron antes de que se guardara la tanda).
"""
import json
import re
import time
import urllib.request

from copas import COPAS, copa_de_argumentos

PRIMER_ANIO = 2005
CACHE = BASE = None   # los define main() según la copa


def pedir(url, intentos=4):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url)  # ESPN rechaza identificaciones que no conoce
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # corte de red o límite de pedidos: esperar y reintentar
            if i == intentos - 1 or getattr(e, "code", None) == 404:   # (si no existe, no tiene sentido insistir)
                raise
            time.sleep(5 * (i + 1))


def recortar(d):
    """Del detalle de ESPN se queda solo con lo que usa la web."""
    return {
        "header": d.get("header"),
        "gameInfo": d.get("gameInfo"),
        "keyEvents": [k for k in d.get("keyEvents", [])
                      if k.get("scoringPlay") or k["type"]["type"] in ("red-card", "yellow-card", "substitution")],
        "rosters": [{
            "team": r.get("team"),
            "formation": r.get("formation"),
            "roster": [{
                "id": p["athlete"].get("id"),
                "nombre": p["athlete"].get("displayName"),
                "camiseta": p.get("jersey"),
                "titular": p.get("starter"),
                "entro": p.get("subbedIn"),
                "salio": p.get("subbedOut"),
                "posicion": (p.get("position") or {}).get("abbreviation"),
            } for p in r.get("roster", [])],
        } for r in d.get("rosters", [])],
        "shootout": d.get("shootout") or [],   # la tanda de penales, remate por remate
    }


def falta_tanda(evento, archivo):
    """Partidos con penales descargados antes de que se guardara la tanda: hay que volver a pedirlos."""
    if not archivo.exists():
        return False
    if all(c.get("shootoutScore") is None for c in evento["competitions"][0]["competitors"]):
        return False
    return "shootout" not in json.loads(archivo.read_text(encoding="utf-8"))


def temporada(anio, ligas=None, saltear=None):
    """ligas: las "ligas" de ESPN que tocan ese año (la Europa League era "uefa.uefa" hasta 2008/09): sus calendarios
    se juntan en uno solo. saltear: fases (slug de ESPN) de las que no se baja el detalle (las clasificatorias)."""
    carpeta = CACHE / str(anio)
    carpeta.mkdir(parents=True, exist_ok=True)
    liga_de = {}
    cal = None
    for liga in ligas or [BASE]:
        c = pedir(f"{liga}/scoreboard?dates={anio}&limit=1000")
        for e in c.get("events", []):
            liga_de[e["id"]] = liga
            e["_liga"] = liga.rsplit("/", 1)[-1]   # (las clasificatorias europeas desde 2020 son otra liga: ver leer_espn.previa_uefa)
        if cal is None:
            cal = c
        else:
            cal["events"] = cal.get("events", []) + c.get("events", [])
    (carpeta / "calendario.json").write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
    eventos = cal.get("events", [])
    sin_grupo = [e for e in eventos if "group" in (e.get("season") or {}).get("slug", "")
                 and "Group" not in (e["competitions"][0].get("altGameNote") or "")]
    if sin_grupo:
        tabla = pedir(f"{BASE.replace('/site/v2/', '/v2/')}/standings?season={anio}")
        grupos = {x["team"]["id"]: g["name"].split()[-1] for g in tabla.get("children", [])
                  for x in g["standings"]["entries"]}
        (carpeta / "grupos.json").write_text(json.dumps(grupos), encoding="utf-8")
    nuevos = 0
    for e in eventos:
        terminado = e["status"]["type"].get("completed")
        archivo = carpeta / f"{e['id']}.json"
        if not terminado or (archivo.exists() and not falta_tanda(e, archivo)):
            continue
        if saltear and re.search(saltear, (e.get("season") or {}).get("slug", "")):
            continue
        try:
            detalle = pedir(f"{liga_de[e['id']]}/summary?event={e['id']}")
        except Exception as x:   # ESPN falla cada tanto: ese partido se vuelve a pedir la próxima vez
            print(f"  {anio}: no se pudo bajar el partido {e['id']} ({x})", flush=True)
            continue
        archivo.write_text(json.dumps(recortar(detalle), ensure_ascii=False), encoding="utf-8")
        nuevos += 1
        time.sleep(0.4)
    print(f"{anio}: {len(eventos)} partidos en el calendario, {nuevos} detalles nuevos", flush=True)


def fichas_de_equipos():
    """El país de cada club de ESPN sale de su ficha: el slug empieza con el país ('esp.real_zaragoza').
    Se guarda en tools/cache/espn_equipos.json ({id: slug}, para todas las copas) y lo usa generar_datos.py
    para los clubes que solo aparecen en ESPN."""
    archivo = CACHE.parent / "espn_equipos.json"
    fichas = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    ids = set()
    for cal in CACHE.glob("*/calendario.json"):
        for e in json.loads(cal.read_text(encoding="utf-8")).get("events", []):
            ids.update(c["team"]["id"] for c in e["competitions"][0]["competitors"])
    faltan = sorted(ids - set(fichas))
    for i, eid in enumerate(faltan):
        try:
            fichas[eid] = pedir(f"{BASE}/teams/{eid}")["team"].get("slug") or ""
        except Exception:
            continue
        if i % 50 == 49:
            archivo.write_text(json.dumps(fichas, indent=0, sort_keys=True), encoding="utf-8")
    archivo.write_text(json.dumps(fichas, indent=0, sort_keys=True), encoding="utf-8")
    print(f"fichas de clubes: {len(faltan)} nuevas", flush=True)


def main():
    global CACHE, BASE
    clave, args = copa_de_argumentos()
    CACHE = COPAS[clave]["cache_espn"]
    BASE = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{COPAS[clave]['espn']}"
    desde = COPAS[clave].get("espn_desde", PRIMER_ANIO)
    anios = [int(a) for a in args if a.isdigit()] or COPAS[clave].get("espn_anios") or list(range(desde, time.localtime().tm_year + 1))
    raiz = "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    ligas = COPAS[clave].get("espn_ligas")   # {liga: años}
    if args == ["fichas"]:   # solo las fichas de los clubes (el país)
        anios = []
    for a in anios:
        temporada(a, [raiz + l for l, anios_liga in ligas.items() if a in anios_liga] if ligas else None,
                  COPAS[clave].get("espn_saltear"))
    fichas_de_equipos()


if __name__ == "__main__":
    main()
