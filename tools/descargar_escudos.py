"""Descarga el escudo de cada club de data/equipos.js desde TheSportsDB (API gratuita).

Uso:  python tools/descargar_escudos.py
Si un club figura con otro nombre en la API, poné "nombre_api" en equipos.js.
Guarda assets/escudos/<id>.png y no vuelve a bajar los que ya existen.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "escudos"
API = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="


def leer_equipos():
    texto = (RAIZ / "data" / "equipos.js").read_text(encoding="utf-8")
    cuerpo = re.search(r"window\.LIB\.equipos\s*=\s*(\{.*\});", texto, re.S).group(1)
    return json.loads(cuerpo)


def buscar_escudo(nombre, pais):
    with urllib.request.urlopen(API + urllib.parse.quote(nombre), timeout=20) as r:
        equipos = json.load(r).get("teams") or []
    futbol = [e for e in equipos if e.get("strSport") == "Soccer"]
    # Si hay varios con el mismo nombre (p. ej. "Nacional"), priorizar el país correcto
    paises = {"ARG": "Argentina", "BRA": "Brazil", "URU": "Uruguay", "PAR": "Paraguay",
              "CHI": "Chile", "COL": "Colombia", "PER": "Peru", "ECU": "Ecuador",
              "BOL": "Bolivia", "VEN": "Venezuela", "MEX": "Mexico"}
    futbol.sort(key=lambda e: e.get("strCountry") != paises.get(pais))
    return futbol[0]["strBadge"] if futbol and futbol[0].get("strBadge") else None


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    for id_, eq in leer_equipos().items():
        archivo = DESTINO / f"{id_}.png"
        if archivo.exists():
            continue
        url = buscar_escudo(eq.get("nombre_api", eq["nombre"]), eq.get("pais"))
        if not url:
            print(f"  ✗ {eq['nombre']}: no encontrado, hay que buscarlo a mano")
            continue
        urllib.request.urlretrieve(url + "/small", archivo)
        print(f"  ✓ {eq['nombre']}")
        time.sleep(2)  # la API gratuita limita la cantidad de pedidos por minuto


if __name__ == "__main__":
    main()
