"""Las copas que tiene la página y dónde vive cada cosa de cada una.

Lo usan todos los scripts de tools/. Para elegir la copa, los scripts aceptan --copa sudamericana
(o mundial, intercontinental, champions o europa; sin nada, es la Libertadores).
Las copas que no tienen "rsssf" toman de Wikipedia las ediciones viejas (las que ESPN no tiene).
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "tools" / "cache"

def paginas_champions(a):
    """Las páginas de Wikipedia de la Copa de Campeones / Champions 1955/56-2000/01 y a qué fase corresponde cada una.
    'Eliminatorias': la fase sale del título de cada sección (ronda preliminar, primera ronda… final).
    Hasta 1990/91 cada temporada es una sola página (todo por eliminación directa) más la de la final."""
    temporada = f"{a}–{str(a + 1)[2:] if a != 1999 else '2000'}"
    base = f"{temporada} European Cup" if a <= 1991 else f"{temporada} UEFA Champions League"
    if a <= 1990:
        return [(base, "Eliminatorias"), (f"{a + 1} European Cup final", "Final")]
    if a <= 1993:   # primera y segunda ronda (32 y 16 equipos), grupos y final (1993/94: con semifinales)
        paginas = [(f"{base} first round", "Dieciseisavos de final"), (f"{base} second round", "Octavos de final"),
                   (f"{base} group stage", "Fase de grupos")]
        paginas += [(f"{base} knockout stage", "Eliminatorias")] if a == 1993 else []
    elif a >= 1999:   # dos fases de grupos
        paginas = [(f"{base} first group stage", "Fase de grupos"), (f"{base} second group stage", "Segunda fase de grupos"),
                   (f"{base} knockout stage", "Eliminatorias")]
    else:
        paginas = [(f"{base} group stage", "Fase de grupos"), (f"{base} knockout stage", "Eliminatorias")]
    # la final tiene su propia página (en la de eliminatorias hay solo un link)
    return paginas + [(f"{a + 1} {'European Cup' if a <= 1991 else 'UEFA Champions League'} final", "Final")]


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
    # La Copa de Campeones de Europa (1955/56) y la Champions League (desde 1992/93). Cada edición se nombra por el año en que
    # empieza la temporada (la 2024/25 es 2024, como la etiqueta ESPN). 1955/56-2000/01 sale de Wikipedia (una página
    # por fase, ver paginas_champions; hasta 1990/91, una por temporada); desde 2001/02, de ESPN: se bajan los años calendario que tocan las temporadas
    # (espn_anios) y se queda con las de "ediciones". No se cargan las rondas clasificatorias.
    "champions": {
        "nombre": "Champions League",
        "desde": 1955,
        "wikipedia": {a: paginas_champions(a) for a in range(1955, 2001)},
        "cache_wikipedia": CACHE / "wikipedia-champions",
        "espn": "uefa.champions",
        "espn_anios": list(range(2001, 2027)),
        "ediciones": list(range(1955, 2026)),
        "cache_espn": CACHE / "espn-champions",
        "data": RAIZ / "data" / "champions",
        "ns": "UCL",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_champions.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_champions.json",
    },
    # La Europa League (Copa UEFA hasta 2009, ESPN): por ahora solo las últimas temporadas. Como en la Champions, cada
    # edición se nombra por el año en que empieza la temporada y no se cargan las rondas clasificatorias.
    "europa": {
        "nombre": "Europa League",
        "desde": 2024,
        "espn": "uefa.europa",
        "espn_anios": [2024, 2025, 2026],
        "ediciones": [2024, 2025],
        "cache_espn": CACHE / "espn-europa",
        "data": RAIZ / "data" / "europa",
        "ns": "UEL",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_europa.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_europa.json",
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
