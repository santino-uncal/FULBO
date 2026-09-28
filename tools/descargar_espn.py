"""Descarga de ESPN los partidos de la Libertadores (o de la Sudamericana) 2005 en adelante.

Uso:  python tools/descargar_espn.py            (todas las temporadas)
      python tools/descargar_espn.py 2025 2026  (solo esas)
      python tools/descargar_espn.py --copa sudamericana [años]

Guarda en tools/cache/espn/<año>/ (la Sudamericana, en tools/cache/espn-sudamericana/<año>/):
  calendario.json     — la lista de partidos de la temporada
  <id_partido>.json   — el detalle de cada partido (solo lo que usamos)
Los partidos ya descargados y terminados no se vuelven a pedir.
"""
import json
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
            if i == intentos - 1:
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
    }


def temporada(anio):
    carpeta = CACHE / str(anio)
    carpeta.mkdir(parents=True, exist_ok=True)
    cal = pedir(f"{BASE}/scoreboard?dates={anio}&limit=1000")
    (carpeta / "calendario.json").write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
    eventos = cal.get("events", [])
    nuevos = 0
    for e in eventos:
        terminado = e["status"]["type"].get("completed")
        archivo = carpeta / f"{e['id']}.json"
        if not terminado or archivo.exists():
            continue
        archivo.write_text(json.dumps(recortar(pedir(f"{BASE}/summary?event={e['id']}")), ensure_ascii=False),
                           encoding="utf-8")
        nuevos += 1
        time.sleep(0.4)
    print(f"{anio}: {len(eventos)} partidos en el calendario, {nuevos} detalles nuevos", flush=True)


def main():
    global CACHE, BASE
    clave, args = copa_de_argumentos()
    CACHE = COPAS[clave]["cache_espn"]
    BASE = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{COPAS[clave]['espn']}"
    anios = [int(a) for a in args] or list(range(PRIMER_ANIO, time.localtime().tm_year + 1))
    for a in anios:
        temporada(a)


if __name__ == "__main__":
    main()
