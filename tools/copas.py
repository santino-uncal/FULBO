"""Las copas que tiene la página y dónde vive cada cosa de cada una.

Lo usan todos los scripts de tools/. Para elegir la copa, los scripts aceptan --copa sudamericana
(o mundial, intercontinental o champions; sin nada, es la Libertadores).
Las copas que no tienen "rsssf" toman de Wikipedia las ediciones viejas (las que ESPN no tiene).
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
    # El Mundial de Clubes de la FIFA: 2000 (sale de Wikipedia) y 2005 en adelante (ESPN).
    # La edición es la de la FIFA: la "2020" se jugó en febrero de 2021.
    "mundial": {
        "nombre": "Mundial de Clubes",
        "desde": 2000,
        "wikipedia": {2000: "2000_FIFA_Club_World_Championship"},
        "cache_wikipedia": CACHE / "wikipedia-mundial",
        "espn": "fifa.cwc",
        "espn_desde": 2005,
        "cache_espn": CACHE / "espn-mundial",
        "data": RAIZ / "data" / "mundial",
        "ns": "MUN",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_mundial.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_mundial.json",
    },
    # La Copa Intercontinental (Europa contra Sudamérica, 1960-2004, sale de Wikipedia) y la Copa Intercontinental
    # de la FIFA (desde 2024, ESPN).
    "intercontinental": {
        "nombre": "Copa Intercontinental",
        "desde": 1960,
        "wikipedia": {a: f"{a}_Intercontinental_Cup" for a in range(1960, 2005) if a not in (1975, 1978)},
        "cache_wikipedia": CACHE / "wikipedia-intercontinental",
        "espn": "fifa.intercontinental_cup",
        "espn_desde": 2024,
        "cache_espn": CACHE / "espn-intercontinental",
        "data": RAIZ / "data" / "intercontinental",
        "ns": "INT",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_intercontinental.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_intercontinental.json",
    },
    # La Champions League (ESPN): por ahora solo las últimas temporadas. Cada edición se nombra por el año en que
    # empieza la temporada (la 2024/25 es 2024, como la etiqueta ESPN). Se bajan los años calendario que la tocan
    # (espn_anios) y se queda con las temporadas de "ediciones". No incluye las fases previas (ESPN las tiene aparte).
    "champions": {
        "nombre": "Champions League",
        "desde": 2024,
        "espn": "uefa.champions",
        "espn_anios": [2024, 2025, 2026],
        "ediciones": [2024, 2025],
        "cache_espn": CACHE / "espn-champions",
        "data": RAIZ / "data" / "champions",
        "ns": "UCL",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_champions.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_champions.json",
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
