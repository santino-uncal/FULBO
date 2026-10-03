"""Las copas que tiene la página y dónde vive cada cosa de cada una.

Lo usan todos los scripts de tools/. Para elegir la copa, los scripts aceptan --copa sudamericana
(o recopa, mundial, intercontinental, champions, europa, conference o supercopa; sin nada, es la Libertadores).
Las copas que no tienen "rsssf" toman de Wikipedia las ediciones viejas (las que ESPN no tiene).
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "tools" / "cache"

# Las rondas clasificatorias de las copas europeas (desde 1992/93: las "rondas preliminares" de la Copa de Campeones
# de 1956-1979 eran la primera ronda de la copa). Se ven en cada edición, pero no cuentan en las estadísticas
# históricas (como en los registros de la UEFA)
PREVIAS_UEFA = ("Ronda preliminar", "Fase previa", "Primera fase previa", "Segunda fase previa", "Tercera fase previa",
                "Playoff de clasificación")


def es_previa_uefa(clave, fase, anio):
    return clave in ("champions", "europa", "conference") and anio >= 1992 and fase.split(" — ")[0] in PREVIAS_UEFA


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
    # las rondas clasificatorias (desde 1992/93), cada una en su página: una ronda preliminar (1992-1993), una ronda
    # (1994-1996) o dos (1997-2000, cada una una sección)
    if a >= 1992:
        paginas = [(f"{base} preliminary round", "Ronda preliminar") if a <= 1993 else
                   (f"{base} qualifying round", "Fase previa") if a <= 1996 else
                   (f"{base} qualifying rounds", "Eliminatorias")] + paginas
    # la final tiene su propia página (en la de eliminatorias hay solo un link)
    return paginas + [(f"{a + 1} {'European Cup' if a <= 1991 else 'UEFA Champions League'} final", "Final")]


def paginas_uefa(a):
    """Las páginas de Wikipedia de la Copa UEFA 1971/72-2000/01: la de la temporada (cada ronda es una sección) y la de
    la final (con las formaciones). Desde 1999/2000 cada ronda tiene su propia página."""
    temporada = f"{a}–{str(a + 1)[2:] if a != 1999 else '2000'}"
    base = f"{temporada} UEFA Cup"
    final = f"{a + 1} UEFA Cup final"
    if a >= 1999:   # (con la ronda clasificatoria; antes era una sección de la página de la temporada)
        return [(f"{base} qualifying round", "Fase previa"), (f"{base} first round", "Primera ronda"), (f"{base} second round", "Segunda ronda"),
                (f"{base} final phase", "Eliminatorias"), (final, "Final")]
    return [(base, "Eliminatorias"), (final, "Final")]


def pagina_previas(clave, a):
    """La página de Wikipedia con las rondas clasificatorias 2001/02-2019/20 (ESPN las tiene incompletas y muchas sin
    goleadores; desde 2020 están completas en ESPN). Las dos fuentes se emparejan solas, como en la Copa UEFA 2004-2008.
    Cada ronda es una sección ("Eliminatorias"); la Copa UEFA 2001-2003 tuvo una sola ronda ("Fase previa")."""
    temporada = f"{a}–{str(a + 1)[2:]}"
    if clave == "champions":
        return (f"{temporada} UEFA Champions League " + ("qualifying rounds" if a <= 2008 else "qualifying phase and play-off round"),
                "Eliminatorias")
    if a <= 2003:
        return f"{temporada} UEFA Cup qualifying round", "Fase previa"
    return (f"{temporada} UEFA Cup qualifying rounds" if a <= 2008 else
            f"{temporada} UEFA Europa League qualifying phase and play-off round"), "Eliminatorias"


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
    # La Recopa Sudamericana (desde 1989): el campeón de la Libertadores contra el de la Supercopa (1989-1998) o el de la
    # Sudamericana (desde 2003). No se jugó en 1999-2002. Hasta 2014 sale de Wikipedia (una página por año);
    # desde 2015, de ESPN ("conmebol.recopa").
    "recopa": {
        "nombre": "Recopa Sudamericana",
        "desde": 1989,
        "wikipedia": {a: f"{a} Recopa Sudamericana" for a in [*range(1989, 1999), *range(2003, 2015)]},
        "cache_wikipedia": CACHE / "wikipedia-recopa",
        "espn": "conmebol.recopa",
        "espn_desde": 2015,
        "cache_espn": CACHE / "espn-recopa",
        "data": RAIZ / "data" / "recopa",
        "ns": "REC",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_recopa.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_recopa.json",
    },
    # La Supercopa de Europa (desde 1972): el campeón de la Copa de Campeones / Champions contra el de la Recopa de
    # Europa (hasta 1999) o el de la Copa UEFA / Europa League (desde 2000). Cada edición es el año en que se juega
    # (no una temporada). No se jugó en 1974, 1981 y 1985; la de 1972 no la reconoce la UEFA. Hasta 2004 sale de
    # Wikipedia (una página por año); desde 2005, de ESPN ("uefa.super_cup"). La de 2013 sale de las dos:
    # ESPN no trae los goles ni las formaciones.
    "supercopa": {
        "nombre": "Supercopa de Europa",
        "desde": 1972,
        "wikipedia": {a: f"{a} {'European' if a <= 1994 else 'UEFA'} Super Cup"
                      for a in [*range(1972, 2005), 2013] if a not in (1974, 1981, 1985)},
        "cache_wikipedia": CACHE / "wikipedia-supercopa",
        "espn": "uefa.super_cup",
        "espn_desde": 2005,
        "cache_espn": CACHE / "espn-supercopa",
        "data": RAIZ / "data" / "supercopa",
        "ns": "USC",
        "no_oficiales": [1972],   # se ve en la página, pero no cuenta en las estadísticas históricas
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_supercopa.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_supercopa.json",
    },
    # La Copa de Campeones de Europa (1955/56) y la Champions League (desde 1992/93). Cada edición se nombra por el año en que
    # empieza la temporada (la 2024/25 es 2024, como la etiqueta ESPN). 1955/56-2000/01 sale de Wikipedia (una página
    # por fase, ver paginas_champions; hasta 1990/91, una por temporada); desde 2001/02, de ESPN: se bajan los años calendario que tocan las temporadas
    # (espn_anios) y se queda con las de "ediciones". Las rondas clasificatorias: ver PREVIAS_UEFA y pagina_previas.
    "champions": {
        "nombre": "Champions League",
        "desde": 1955,
        "wikipedia": {**{a: paginas_champions(a) for a in range(1955, 2001)},
                      **{a: [pagina_previas("champions", a)] for a in range(2001, 2020)}},
        "cache_wikipedia": CACHE / "wikipedia-champions",
        "espn": "uefa.champions",
        # desde 2020 las rondas clasificatorias son otra liga de ESPN
        "espn_ligas": {"uefa.champions": range(2001, 2028), "uefa.champions_qual": range(2020, 2028)},
        "espn_anios": list(range(2001, 2028)),
        "ediciones": list(range(1955, 2027)),
        "cache_espn": CACHE / "espn-champions",
        "data": RAIZ / "data" / "champions",
        "ns": "UCL",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_champions.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_champions.json",
    },
    # La Copa UEFA (1971/72) y la Europa League (desde 2009/10). Como en la Champions, cada edición se nombra por el año
    # en que empieza la temporada (las rondas clasificatorias, como en la Champions). 1971/72-2000/01 sale de Wikipedia
    # (paginas_uefa); desde 2001/02, de ESPN, que tiene la Copa UEFA ("uefa.uefa", hasta 2008/09) y la Europa League
    # ("uefa.europa") como dos ligas distintas: en 2009 se juntan los dos calendarios (espn_ligas).
    "europa": {
        "nombre": "Europa League",
        "desde": 1971,
        # (y lo que ESPN no tiene completo: las fases de grupos 2004/05-2008/09, sin el detalle de los partidos, y
        # algunos partidos de la primera ronda; lo demás de esas temporadas sale de ESPN)
        "wikipedia": {**{a: paginas_uefa(a) for a in range(1971, 2001)},
                      **{a: ([(f"{a}–{str(a + 1)[2:]} UEFA Cup first round", "Primera ronda")] if a in (2002, 2004, 2006) else []) +
                         ([(f"{a}–{str(a + 1)[2:]} UEFA Cup group stage", "Fase de grupos")] if 2004 <= a <= 2008 else []) +
                         [pagina_previas("europa", a)]   # (las rondas clasificatorias, hasta 2019/20)
                         for a in range(2001, 2020)}},
        "cache_wikipedia": CACHE / "wikipedia-europa",
        "espn": "uefa.europa",
        "espn_ligas": {"uefa.uefa": range(2001, 2010), "uefa.europa": range(2009, 2028), "uefa.europa_qual": range(2020, 2028)},
        "espn_anios": list(range(2001, 2028)),
        "ediciones": list(range(1971, 2027)),
        "cache_espn": CACHE / "espn-europa",
        "data": RAIZ / "data" / "europa",
        "ns": "UEL",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_europa.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_europa.json",
    },
    # La Conference League (desde 2021/22): toda de ESPN ("uefa.europa.conf"; las clasificatorias, "uefa.europa.conf_qual").
    "conference": {
        "nombre": "Conference League",
        "desde": 2021,
        "espn": "uefa.europa.conf",
        "espn_ligas": {"uefa.europa.conf": range(2021, 2028), "uefa.europa.conf_qual": range(2021, 2028)},
        "espn_anios": list(range(2021, 2028)),
        "ediciones": list(range(2021, 2027)),
        "cache_espn": CACHE / "espn-conference",
        "data": RAIZ / "data" / "conference",
        "ns": "UECL",
        "entrenadores_partidos": RAIZ / "tools" / "entrenadores_partidos_conference.json",
        "planteles_tm": RAIZ / "tools" / "planteles_tm_conference.json",
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
