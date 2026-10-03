"""Descarga de Wikipedia (en inglés) el texto de las ediciones que ESPN no tiene: la Copa Intercontinental
1960-2004, el Mundial de Clubes 2000, la Champions League 1955/56-2000/01 y la Copa UEFA 1971/72-2000/01.

Uso:  python tools/descargar_wikipedia.py --copa intercontinental
      python tools/descargar_wikipedia.py --copa mundial
      python tools/descargar_wikipedia.py --copa champions
      python tools/descargar_wikipedia.py --copa europa
Guarda el código de cada página (wikitexto) en tools/cache/wikipedia-<copa>/<año>.txt y no vuelve a bajar
las que ya existen. En la Champions cada temporada son varias páginas (una por fase): se guardan juntas en el
mismo archivo, cada una precedida por un renglón "@@ETAPA <fase>@@" que lee tools/leer_wikipedia.py. Los textos de Wikipedia se pueden copiar citando la fuente (licencia CC BY-SA).
"""
import re
import time
import urllib.parse
import urllib.request

from copas import COPAS, copa_de_argumentos

BASE = "https://en.wikipedia.org/w/index.php?action=raw&title="
# Wikipedia pide que los programas se identifiquen
UA = "FULBO-historia/1.0 (https://santino-uncal.github.io/FULBO/)"


def bajar(titulo, saltos=3):
    req = urllib.request.Request(BASE + urllib.parse.quote(titulo), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        texto = r.read().decode("utf-8")
    m = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", texto, re.I)   # la página se mudó: se sigue a la nueva
    return bajar(m.group(1), saltos - 1) if m and saltos else texto


def con_subpaginas(texto):
    """Las clasificatorias de la Europa League 2009-2017 tienen los partidos en otras páginas, que se nombran desde la
    principal ("… qualifying (first and second round matches)"): se bajan y se ponen a continuación."""
    # ("{{#lst:Página|Q1}}" y "{{Main|1=Página#Matches}}": la misma página dos veces)
    subs = re.findall(r"(\d{4}–\d{2} UEFA [^|=\[\]{}#\n]*?\([^()\n]*matches\))", texto)
    for sub in dict.fromkeys(subs):
        texto += "\n" + bajar(sub)
        time.sleep(1)
    return texto


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
        paginas = titulo if isinstance(titulo, list) else [(titulo, None)]
        partes = []
        for t, etapa in paginas:
            texto = con_subpaginas(bajar(t))
            partes.append((f"@@ETAPA {etapa}@@\n" if etapa else "") + texto)
            time.sleep(1)
        archivo.write_text("\n".join(partes), encoding="utf-8")
        print(f"  ✓ {anio}")
        time.sleep(1)


if __name__ == "__main__":
    main()
