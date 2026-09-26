"""Descarga de RSSSF (rsssf.org) las páginas de cada edición de la Libertadores.

Uso:  python tools/descargar_rsssf.py
Guarda tools/cache/rsssf/copaNN.html (no vuelve a bajar las que ya existen).
Los datos de RSSSF son de Juan Pablo Andrés, Pablo Ciullini y Frank Ballesteros;
se pueden copiar citando a los autores.
"""
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "tools" / "cache" / "rsssf"
BASE = "https://www.rsssf.org/sacups/"


def nombre_pagina(anio):
    # RSSSF usa 2 dígitos hasta 2009 (copa60, copa05) y 4 desde 2010 (copa2010)
    return f"copa{anio}.html" if anio >= 2010 else f"copa{anio % 100:02d}.html"


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    for anio in range(1960, time.localtime().tm_year + 1):
        archivo = CACHE / nombre_pagina(anio)
        if archivo.exists():
            continue
        try:
            urllib.request.urlretrieve(BASE + archivo.name, archivo)
            print(f"  ✓ {anio}")
        except Exception:
            print(f"  ✗ {anio}: todavía no está publicada")
        time.sleep(1)


if __name__ == "__main__":
    main()
