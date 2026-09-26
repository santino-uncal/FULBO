"""Descarga el escudo de cada club de data/equipos.js.

Uso:  python tools/descargar_escudos.py
Orden de búsqueda:
  1. ESPN (clubes que jugaron desde 2005: tienen id de ESPN en equipos.js)
  2. TheSportsDB (API gratuita), buscando por nombre y país
Guarda assets/escudos/<id>.png (120x120 aprox.) y no vuelve a bajar los que ya existen.
Al final lista los que no encontró, para buscarlos a mano o dejar que la web muestre las iniciales.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from equipos import normalizar  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "escudos"
ESPN = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/{}.png&h=120&w=120"
TSDB = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="
PAISES = {"ARG": "Argentina", "BRA": "Brazil", "URU": "Uruguay", "PAR": "Paraguay", "CHI": "Chile",
          "COL": "Colombia", "PER": "Peru", "ECU": "Ecuador", "BOL": "Bolivia", "VEN": "Venezuela", "MEX": "Mexico"}


def leer_equipos():
    texto = (RAIZ / "data" / "equipos.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.LIB\.equipos\s*=\s*(\{.*\});", texto, re.S).group(1))


def bajar(url, archivo):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
        datos = r.read()
    if len(datos) < 500:  # respuesta vacía o imagen "no disponible"
        return False
    archivo.write_bytes(datos)
    return True


def buscar_tsdb(eq):
    """Busca en TheSportsDB probando variantes del nombre; exige que coincida el país."""
    nombres = [eq["nombre"], re.sub(r"\s*\(.*\)", "", eq["nombre"])]
    for nombre in dict.fromkeys(nombres):
        with urllib.request.urlopen(TSDB + urllib.parse.quote(nombre), timeout=20) as r:
            equipos = json.load(r).get("teams") or []
        time.sleep(2)  # la API gratuita limita la cantidad de pedidos por minuto
        for t in equipos:
            if t.get("strSport") != "Soccer" or not t.get("strBadge"):
                continue
            if eq.get("pais") and t.get("strCountry") != PAISES.get(eq["pais"]):
                continue
            if normalizar(t["strTeam"]) == normalizar(nombre) or normalizar(nombre) in normalizar(t["strTeam"]):
                return t["strBadge"] + "/small"
    return None


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    faltan = []
    for id_, eq in leer_equipos().items():
        archivo = DESTINO / f"{id_}.png"
        if archivo.exists():
            continue
        ok = False
        for eid in reversed(eq.get("espn", [])):
            try:
                ok = bajar(ESPN.format(eid), archivo)
            except Exception:
                ok = False
            if ok:
                print(f"  ✓ {eq['nombre']} (ESPN)", flush=True)
                break
        if not ok:
            try:
                url = buscar_tsdb(eq)
                ok = bool(url) and bajar(url, archivo)
            except Exception:
                ok = False
            if ok:
                print(f"  ✓ {eq['nombre']} (TheSportsDB)", flush=True)
        if not ok:
            faltan.append(f"{id_} ({eq['nombre']}, {eq.get('pais')})")
        time.sleep(0.3)
    print(f"\nNo encontrados ({len(faltan)}):", *faltan, sep="\n  ")


if __name__ == "__main__":
    main()
