"""Las copas que tiene la página y dónde vive cada cosa de cada una.

Lo usan todos los scripts de tools/. Para elegir la copa, los scripts aceptan --copa sudamericana
(sin nada, es la Libertadores).
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "tools" / "cache"

COPAS = {
    "libertadores": {
        "nombre": "Copa Libertadores",
        "desde": 1960,
        "rsssf": lambda a: f"copa{a}.html" if a >= 2010 else f"copa{a % 100:02d}.html",
        "cache_rsssf": CACHE / "rsssf",
        "espn": "conmebol.libertadores",
        "cache_espn": CACHE / "espn",
        "data": RAIZ / "data",
        "ns": "LIB",                      # variable de la página: window.LIB.indice, window.LIB.ediciones…
        "tm": ("copa-libertadores", "CLI"),   # Transfermarkt
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm.json",
    },
    "sudamericana": {
        "nombre": "Copa Sudamericana",
        "desde": 2002,
        "rsssf": lambda a: f"sudamcup{a}.html" if a >= 2010 else f"sudamcup{a % 100:02d}.html",
        "cache_rsssf": CACHE / "rsssf-sudamericana",
        "espn": "conmebol.sudamericana",
        "cache_espn": CACHE / "espn-sudamericana",
        "data": RAIZ / "data" / "sudamericana",
        "ns": "SUD",
        "tm": ("copa-sudamericana", "CS"),
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_sudamericana.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_sudamericana.json",
    },
}


def copa_de_argumentos(argv=None):
    """Lee '--copa sudamericana' de la línea de comandos. Devuelve (clave, resto de los argumentos)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    clave = "libertadores"
    if "--copa" in argv:
        i = argv.index("--copa")
        clave = argv[i + 1]
        del argv[i:i + 2]
    if clave not in COPAS:
        raise SystemExit(f"Copa desconocida: {clave} (opciones: {', '.join(COPAS)})")
    return clave, argv


def prefijo_js(clave):
    """Primera línea de cada archivo de datos: crea la variable de la copa (window.LIB o window.SUD)."""
    ns = COPAS[clave]["ns"]
    return f"window.{ns} = window.{ns} || {{}};\n"
