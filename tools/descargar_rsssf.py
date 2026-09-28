"""Descarga de RSSSF (rsssf.org) las páginas de cada edición de la Libertadores (o de la Sudamericana).

Uso:  python tools/descargar_rsssf.py
      python tools/descargar_rsssf.py --copa sudamericana
Guarda tools/cache/rsssf/copaNN.html (la Sudamericana, tools/cache/rsssf-sudamericana/sudamcupNN.html)
y no vuelve a bajar las que ya existen.
Los datos de RSSSF son de Juan Pablo Andrés, Pablo Ciullini y Frank Ballesteros (Libertadores) y de
Karel Stokkermans, Osvaldo José Gorgazzi y otros (Sudamericana); se pueden copiar citando a los autores.
"""
import time
import urllib.request

from copas import COPAS, copa_de_argumentos

BASE = "https://www.rsssf.org/sacups/"


def main():
    clave, _ = copa_de_argumentos()
    copa = COPAS[clave]
    cache = copa["cache_rsssf"]
    cache.mkdir(parents=True, exist_ok=True)
    for anio in range(copa["desde"], time.localtime().tm_year + 1):
        archivo = cache / copa["rsssf"](anio)
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
