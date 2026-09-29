"""Descarga de Wikipedia (en inglés) el texto de las ediciones que ESPN no tiene: la Copa Intercontinental
1960-2004 y el Mundial de Clubes 2000.

Uso:  python tools/descargar_wikipedia.py --copa intercontinental
      python tools/descargar_wikipedia.py --copa mundial
Guarda el código de cada página (wikitexto) en tools/cache/wikipedia-<copa>/<año>.txt y no vuelve a bajar
las que ya existen. Los textos de Wikipedia se pueden copiar citando la fuente (licencia CC BY-SA).
"""
import time
import urllib.parse
import urllib.request

from copas import COPAS, copa_de_argumentos

BASE = "https://en.wikipedia.org/w/index.php?action=raw&title="
# Wikipedia pide que los programas se identifiquen
UA = "FULBO-historia/1.0 (https://santino-uncal.github.io/FULBO/)"


def main():
    clave, _ = copa_de_argumentos()
    copa = COPAS[clave]
    if "wikipedia" not in copa:
        raise SystemExit(f"La {copa['nombre']} no usa Wikipedia")
    cache = copa["cache_wikipedia"]
    cache.mkdir(parents=True, exist_ok=True)
    for anio, titulo in copa["wikipedia"].items():
        archivo = cache / f"{anio}.txt"
        if archivo.exists():
            continue
        req = urllib.request.Request(BASE + urllib.parse.quote(titulo), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            archivo.write_bytes(r.read())
        print(f"  ✓ {anio}")
        time.sleep(1)


if __name__ == "__main__":
    main()
