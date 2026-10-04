"""Baja de ESPN un torneo de la liga argentina (por ahora, el Clausura 2026) y arma data/ligas/argentina/<torneo>.js.

Uso:  py tools/actualizar_liga.py                 (los torneos de TORNEOS que no terminaron)
      py tools/actualizar_liga.py 2026-clausura   (solo ese)
      py tools/actualizar_liga.py todos           (todos, también los terminados)

La tabla de posiciones no se guarda: la calcula la página con los resultados. Por eso alcanza con correr este
script una vez por día (lo hace la tarea programada) para que la tabla quede al día.

Guarda en tools/cache/espn-liga-argentina/<año>/ lo mismo que descargar_espn.py (calendario.json y el detalle de
cada partido terminado) más zonas.json (los clubes de cada zona, de la tabla de ESPN).
ESPN no dice a qué fecha pertenece cada partido: se deduce (ver repartir_fechas).
"""
import datetime
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from descargar_espn import pedir, recortar   # noqa: E402
from leer_espn import completar   # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "tools" / "cache" / "espn-liga-argentina"
DATOS = RAIZ / "data" / "ligas" / "argentina"
A_MANO = RAIZ / "tools" / "a_mano"   # torneos que ESPN no tiene, cargados a mano (ver eventos_a_mano)
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/arg.1"
ESCUDO = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/{}.png&h=120&w=120"

# slug: cómo llama ESPN a la fase regular ("torneo-clausura") y a los playoffs ("clausura---round-of-16")
TORNEOS = {
    # 1995: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 1996 a 2002 (tools/a_mano;
    # RSSSF, sin goles el Clausura y con los goles y sus minutos el Apertura; Wikipedia no tiene estadios ni días). El
    # Torneo Clausura 1995 (febrero-junio; campeón San Lorenzo) cerraba la temporada 1994-95 y fue el último con 2
    # puntos por partido ganado ("puntos_victoria"; también en sumar, por PUNTOS_VICTORIA): su "tabla anual" es la de
    # la temporada, con la tabla del Apertura 1994 (RSSSF; Talleres, con los 2 puntos que le descontaron). Promedios de
    # 1992-93 y 1993-94, de RSSSF. Bajaron los dos últimos (Deportivo Mandiyú y Talleres). A la Copa Conmebol 1995, los
    # dos mejores de la temporada que no iban a otra copa (Wikipedia)
    "1995-clausura": {"nombre": "Torneo Clausura 1995", "anio": 1995, "liga": "a_mano", "slug": "1995-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                      "campeon_tabla": True, "temporada": "1994-95", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue José Oscar Flores "
                                         "(Vélez), con 14 goles.",
                      # la tabla del Apertura 1994 (RSSSF; con 2 puntos por partido ganado): [pts, pj, g, e, p, gf, gc]
                      "anual": {"river-plate": [31, 19, 12, 7, 0, 31, 14], "san-lorenzo": [26, 19, 9, 8, 2, 30, 21],
                                "velez-sarsfield": [24, 19, 9, 6, 4, 28, 16], "newell-s-old-boys": [23, 19, 7, 9, 3, 22, 14],
                                "argentinos-juniors": [22, 19, 8, 6, 5, 24, 19], "belgrano": [21, 19, 7, 7, 5, 25, 18],
                                "lanus": [21, 19, 7, 7, 5, 20, 24], "banfield": [20, 19, 7, 6, 6, 20, 15],
                                "rosario-central": [20, 19, 7, 6, 6, 22, 20], "gimnasia-y-esgrima": [20, 19, 5, 10, 4, 20, 19],
                                "independiente": [19, 19, 7, 5, 7, 29, 28], "racing-club": [19, 19, 6, 7, 6, 15, 18],
                                "boca-juniors": [17, 19, 5, 7, 7, 29, 28], "huracan": [16, 19, 6, 4, 9, 22, 25],
                                "platense": [16, 19, 5, 6, 8, 19, 24], "ferro-carril-oeste": [16, 19, 5, 6, 8, 21, 30],
                                "gimnasia-jujuy": [15, 19, 6, 3, 10, 13, 24], "deportivo-espanol": [12, 19, 3, 6, 10, 16, 26],
                                "deportivo-mandiyu": [11, 19, 1, 9, 9, 19, 31], "talleres": [9, 19, 2, 7, 10, 18, 29]},
                      "anual_texto": "La tabla de la temporada 1994-95: suma el Torneo Apertura 1994 (de RSSSF: no está "
                                     "cargado partido por partido; a Talleres le descontaron 2 puntos) y el Torneo "
                                     "Clausura 1995. Cada partido ganado valía 2 puntos.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1992-93": {"san-lorenzo": [45, 38], "river-plate": [46, 38], "velez-sarsfield": [48, 38],
                                                "boca-juniors": [48, 38], "independiente": [41, 38],
                                                "gimnasia-y-esgrima": [34, 38], "lanus": [37, 38], "racing-club": [36, 38],
                                                "rosario-central": [39, 38], "huracan": [43, 38], "belgrano": [38, 38],
                                                "deportivo-espanol": [41, 38], "ferro-carril-oeste": [38, 38],
                                                "argentinos-juniors": [33, 38], "platense": [28, 38],
                                                "newell-s-old-boys": [25, 38], "deportivo-mandiyu": [37, 38]},
                                    "1993-94": {"san-lorenzo": [44, 38], "river-plate": [45, 38], "velez-sarsfield": [38, 38],
                                                "boca-juniors": [42, 38], "independiente": [48, 38],
                                                "gimnasia-y-esgrima": [37, 38], "lanus": [41, 38], "racing-club": [42, 38],
                                                "rosario-central": [38, 38], "huracan": [43, 38], "banfield": [40, 38],
                                                "belgrano": [35, 38], "deportivo-espanol": [32, 38],
                                                "ferro-carril-oeste": [35, 38], "argentinos-juniors": [36, 38],
                                                "platense": [38, 38], "newell-s-old-boys": [36, 38],
                                                "deportivo-mandiyu": [30, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1996, "anio_sudamericana": 1995, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 1994", "river-plate"),
                                                 ("Campeón del Torneo Clausura 1995", "san-lorenzo")],
                                "sudamericana": [("Tabla de la temporada 1994-95", "gimnasia-y-esgrima"),
                                                 ("Tabla de la temporada 1994-95", "rosario-central")],
                                "nota": "A la Supercopa 1995 fueron invitados Vélez, River, Boca, Racing, Independiente, "
                                        "Estudiantes y Argentinos; por eso no podían jugar la Copa Conmebol. Rosario "
                                        "Central quedó delante de Lanús (los dos con 39 puntos) por diferencia de gol."}},
    # El Torneo Apertura 1995 (agosto-diciembre; campeón Vélez) abría la temporada 1995-96 y fue el primero con 3 puntos
    # por partido ganado
    "1995-apertura": {"nombre": "Torneo Apertura 1995", "anio": 1995, "liga": "a_mano", "slug": "1995-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "goleadores_nota": "Los goles salen partido por partido de RSSSF; su lista de goleadores le da 8 "
                                         "a Trimarchi (Gimnasia de Jujuy) y 8 a Saralegui (Colón).",
                      "anual": [("a_mano", r"^1995-clausura$")],
                      "anual_texto": "La tabla del año 1995: suma el Torneo Clausura 1995 (con 2 puntos por partido "
                                     "ganado, como se jugó) y el Torneo Apertura 1995 (el primero con 3). No daba lugares "
                                     "en las copas: salían de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 1995 no hubo descensos: se definieron al terminar la "
                                       "temporada 1995-96, con el Torneo Clausura 1996."},
    # 1996: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 1997 a 2002 (tools/a_mano;
    # RSSSF, con los goles y sus minutos del Clausura y de algunas fechas del Apertura; Wikipedia no tiene estadios ni
    # días). El Torneo Clausura 1996 (marzo-agosto; campeón Vélez) cerraba la temporada 1995-96: su "tabla anual" es la
    # de la temporada, con el Apertura 1995 (cargado a mano). Para los promedios, cada partido ganado valía 2 puntos
    # (1993-94 y 1994-95, de RSSSF; Racing 1993-94, 42: Wikipedia tiene 41 pero su promedio sale de 42). Bajaron directo
    # los dos últimos (Argentinos y Belgrano). Vélez ganó los dos torneos; el segundo lugar en la Libertadores 1997 lo
    # jugaron los subcampeones (Racing-Gimnasia, en cancha de River, con alargue). A la Copa Conmebol 1996, Rosario
    # Central (el campeón) y el mejor de la temporada que no iba a otra copa (Wikipedia, RSSSF)
    "1996-clausura": {"nombre": "Torneo Clausura 1996", "anio": 1996, "liga": "a_mano", "slug": "1996-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "1995-96", "nombre_anual": "Temporada y copas",
                      "promedios_victoria": 2,
                      "desempate_a_mano": {"fecha": "1996-08-22", "local": "racing-club", "visitante": "gimnasia-y-esgrima",
                                           "gl": 1, "gv": 0, "alargue": True, "estadio": "Cancha de River",
                                           "goles": [{"jugador": "M.A. Delgado", "min": 95, "equipo": "local"}]},
                      "desempate_texto": "Racing (subcampeón del Apertura 1995) y Gimnasia (subcampeón del Clausura 1996) "
                                         "jugaron un partido, en cancha neutral, por el segundo lugar de la Argentina en la "
                                         "Copa Libertadores 1997 (el primero era de Vélez, campeón de los dos torneos).",
                      "anual": [("a_mano", r"^1995-apertura$", 1995)],
                      "anual_texto": "La tabla de la temporada 1995-96: suma el Torneo Apertura 1995 y el Torneo Clausura 1996.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1993-94": {"san-lorenzo": [44, 38], "river-plate": [45, 38], "velez-sarsfield": [38, 38],
                                                "boca-juniors": [42, 38], "independiente": [48, 38],
                                                "gimnasia-y-esgrima": [37, 38], "lanus": [41, 38], "racing-club": [42, 38],
                                                "rosario-central": [38, 38], "huracan": [43, 38], "banfield": [40, 38],
                                                "belgrano": [35, 38], "deportivo-espanol": [32, 38],
                                                "ferro-carril-oeste": [35, 38], "argentinos-juniors": [36, 38],
                                                "platense": [38, 38], "newell-s-old-boys": [36, 38]},
                                    "1994-95": {"san-lorenzo": [56, 38], "river-plate": [49, 38], "velez-sarsfield": [52, 38],
                                                "boca-juniors": [41, 38], "independiente": [37, 38],
                                                "gimnasia-y-esgrima": [49, 38], "lanus": [39, 38], "racing-club": [39, 38],
                                                "rosario-central": [39, 38], "huracan": [29, 38], "banfield": [36, 38],
                                                "belgrano": [36, 38], "deportivo-espanol": [36, 38],
                                                "ferro-carril-oeste": [32, 38], "argentinos-juniors": [34, 38],
                                                "platense": [35, 38], "newell-s-old-boys": [38, 38], "gimnasia-jujuy": [32, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1997, "anio_sudamericana": 1996, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 1996 (lugar aparte)", "river-plate"),
                                                 ("Campeón del Torneo Apertura 1995 y del Torneo Clausura 1996",
                                                  "velez-sarsfield"),
                                                 ("Ganador del partido entre los subcampeones", "racing-club")],
                                "sudamericana": [("Campeón de la Copa Conmebol 1995", "rosario-central"),
                                                 ("Tabla de la temporada 1995-96", "lanus")],
                                "nota": "A la Supercopa 1996 fueron invitados Vélez, River, Boca, Racing, Independiente, "
                                        "Estudiantes y Argentinos; por eso no podían jugar la Copa Conmebol."}},
    # El Torneo Apertura 1996 (agosto-diciembre; campeón River) abría la temporada 1996-97
    "1996-apertura": {"nombre": "Torneo Apertura 1996", "anio": 1996, "liga": "a_mano", "slug": "1996-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF tiene los goles de pocas fechas de este torneo. Según Wikipedia, el "
                                         "goleador fue Gustavo Reggi (Ferro), con 11 goles.",
                      "anual": [("a_mano", r"^1996-clausura$")],
                      "anual_texto": "La tabla del año 1996: suma el Torneo Clausura 1996 y el Torneo Apertura 1996. No "
                                     "daba lugares en las copas: salían de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 1996 no hubo descensos: se definieron al terminar la "
                                       "temporada 1996-97, con el Torneo Clausura 1997."},
    # 1997: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 1998 a 2002 (tools/a_mano;
    # RSSSF, sin goles, y Wikipedia, que del Clausura casi no tiene estadios ni días). El Torneo Clausura 1997
    # (febrero-agosto, con un mes parado por una huelga de futbolistas; campeón River) cerraba la temporada 1996-97: su
    # "tabla anual" es la de la temporada, con el Apertura 1996 (cargado a mano). Para los promedios, cada partido
    # ganado valía todavía 2 puntos ("promedios_victoria"; 1994-95 y 1995-96, de las tablas de RSSSF: la de Wikipedia
    # tiene errores). Bajaron directo los dos últimos (Banfield y Huracán Corrientes). River ganó los dos torneos; el
    # segundo lugar en la Libertadores 1998 lo jugaron en diciembre los subcampeones (Colón-Independiente, en Lanús). A
    # la Copa Conmebol 1997, Lanús (el campeón) y el mejor de la temporada que no iba a otra copa (Wikipedia)
    "1997-clausura": {"nombre": "Torneo Clausura 1997", "anio": 1997, "liga": "a_mano", "slug": "1997-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "1996-97", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. Según Wikipedia, el goleador fue Sergio "
                                         "Martínez (Boca), con 15 goles.",
                      "promedios_victoria": 2,
                      "desempate_a_mano": {"fecha": "1997-12-03", "local": "colon", "visitante": "independiente",
                                           "gl": 1, "gv": 0, "estadio": "Ciudad de Lanús",
                                           "goles": [{"jugador": "Marcelo Saralegui", "equipo": "local"}]},
                      "desempate_texto": "Independiente (subcampeón del Apertura 1996) y Colón (subcampeón del Clausura "
                                         "1997) jugaron un partido, en diciembre y en cancha neutral, por el segundo lugar "
                                         "de la Argentina en la Copa Libertadores 1998 (el primero era de River, campeón "
                                         "de los dos torneos).",
                      "anual": [("a_mano", r"^1996-apertura$", 1996)],
                      "anual_texto": "La tabla de la temporada 1996-97: suma el Torneo Apertura 1996 y el Torneo Clausura 1997.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1994-95": {"san-lorenzo": [56, 38], "river-plate": [49, 38], "velez-sarsfield": [52, 38],
                                                "boca-juniors": [41, 38], "independiente": [37, 38],
                                                "gimnasia-y-esgrima": [49, 38], "lanus": [39, 38], "racing-club": [39, 38],
                                                "rosario-central": [39, 38], "huracan": [29, 38], "banfield": [36, 38],
                                                "deportivo-espanol": [36, 38], "ferro-carril-oeste": [32, 38],
                                                "platense": [35, 38], "newell-s-old-boys": [38, 38], "gimnasia-jujuy": [32, 38]},
                                    "1995-96": {"velez-sarsfield": [57, 38], "lanus": [49, 38], "boca-juniors": [49, 38],
                                                "racing-club": [46, 38], "huracan": [45, 38], "gimnasia-y-esgrima": [43, 38],
                                                "estudiantes-de-la-plata": [44, 38], "rosario-central": [41, 38],
                                                "river-plate": [37, 38], "gimnasia-jujuy": [35, 38], "san-lorenzo": [35, 38],
                                                "colon": [35, 38], "platense": [33, 38], "independiente": [35, 38],
                                                "ferro-carril-oeste": [34, 38], "deportivo-espanol": [33, 38],
                                                "newell-s-old-boys": [33, 38], "banfield": [25, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1998, "anio_sudamericana": 1997, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 1996 y del Torneo Clausura 1997",
                                                  "river-plate"),
                                                 ("Ganador del partido entre los subcampeones", "colon")],
                                "sudamericana": [("Campeón de la Copa Conmebol 1996", "lanus"),
                                                 ("Tabla de la temporada 1996-97", "colon")],
                                "nota": "A la Supercopa 1997 fueron invitados River, Boca, Independiente, Racing, Vélez y "
                                        "Estudiantes; por eso no podían jugar la Copa Conmebol."}},
    # El Torneo Apertura 1997 (agosto-diciembre; campeón River) abría la temporada 1997-98
    "1997-apertura": {"nombre": "Torneo Apertura 1997", "anio": 1997, "liga": "a_mano", "slug": "1997-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. Según Wikipedia, el goleador fue Rubén "
                                         "da Silva (Rosario Central), con 15 goles.",
                      "anual": [("a_mano", r"^1997-clausura$")],
                      "anual_texto": "La tabla del año 1997: suma el Torneo Clausura 1997 y el Torneo Apertura 1997. No "
                                     "daba lugares en las copas: salían de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 1997 no hubo descensos: se definieron al terminar la "
                                       "temporada 1997-98, con el Torneo Clausura 1998."},
    # 1998: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 1999 a 2002 (tools/a_mano;
    # RSSSF, sin goles, y Wikipedia). El Torneo Clausura 1998 (febrero-junio; campeón Vélez) cerraba la temporada
    # 1997-98: su "tabla anual" es la de la temporada, con el Apertura 1997 (cargado a mano).
    # Bajaron directo los dos últimos de los promedios (Deportivo Español y Gimnasia y Tiro; los puntos de 1995-96 y
    # 1996-97, de Wikipedia; San Lorenzo 1996-97, 57, de las tablas de RSSSF: Wikipedia tiene 56 en un lado y 57 en
    # otro). A la Libertadores 1999 fueron los dos campeones; a la Copa Conmebol 1998, los dos mejores de la temporada
    # que no iban a otra copa (Wikipedia)
    "1998-clausura": {"nombre": "Torneo Clausura 1998", "anio": 1998, "liga": "a_mano", "slug": "1998-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "1997-98", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. Según Wikipedia, el goleador fue "
                                         "Roberto Sosa (Gimnasia), con 17 goles.",
                      "anual": [("a_mano", r"^1997-apertura$", 1997)],
                      "anual_texto": "La tabla de la temporada 1997-98: suma el Torneo Apertura 1997 y el Torneo Clausura 1998.",
                      "promedios": {"1995-96": {"velez-sarsfield": [81, 38], "river-plate": [50, 38], "lanus": [69, 38],
                                                "boca-juniors": [68, 38], "gimnasia-y-esgrima": [60, 38],
                                                "independiente": [44, 38], "san-lorenzo": [49, 38], "racing-club": [64, 38],
                                                "rosario-central": [54, 38], "estudiantes-de-la-plata": [59, 38],
                                                "colon": [47, 38], "newell-s-old-boys": [43, 38], "gimnasia-jujuy": [49, 38],
                                                "platense": [44, 38], "ferro-carril-oeste": [43, 38], "huracan": [61, 38],
                                                "deportivo-espanol": [40, 38]},
                                    "1996-97": {"velez-sarsfield": [55, 38], "river-plate": [87, 38], "lanus": [61, 38],
                                                "boca-juniors": [50, 38], "gimnasia-y-esgrima": [50, 38],
                                                "independiente": [71, 38], "san-lorenzo": [57, 38], "racing-club": [59, 38],
                                                "rosario-central": [49, 38], "estudiantes-de-la-plata": [44, 38],
                                                "colon": [61, 38], "newell-s-old-boys": [61, 38], "gimnasia-jujuy": [39, 38],
                                                "platense": [47, 38], "ferro-carril-oeste": [46, 38], "huracan": [38, 38],
                                                "union": [44, 38], "deportivo-espanol": [35, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1999, "anio_sudamericana": 1998, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 1997", "river-plate"),
                                                 ("Campeón del Torneo Clausura 1998", "velez-sarsfield")],
                                "sudamericana": [("Tabla de la temporada 1997-98", "gimnasia-y-esgrima"),
                                                 ("Tabla de la temporada 1997-98", "rosario-central")],
                                "nota": "A la Copa Mercosur 1998 fueron Boca, River, Independiente, Racing, San Lorenzo y "
                                        "Vélez, invitados por la Conmebol (San Lorenzo, en el lugar de Lanús, que no quiso "
                                        "jugarla). A la Copa Conmebol, los dos mejores de la temporada que no iban a otra "
                                        "copa."}},
    # El Torneo Apertura 1998 (agosto-diciembre; campeón Boca, invicto) abría la temporada 1998-99
    "1998-apertura": {"nombre": "Torneo Apertura 1998", "anio": 1998, "liga": "a_mano", "slug": "1998-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. Según Wikipedia, el goleador fue Martín "
                                         "Palermo (Boca), con 20 goles.",
                      "anual": [("a_mano", r"^1998-clausura$")],
                      "anual_texto": "La tabla del año 1998: suma el Torneo Clausura 1998 y el Torneo Apertura 1998. No "
                                     "daba lugares en las copas: salían de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 1998 no hubo descensos: se definieron al terminar la "
                                       "temporada 1998-99, con el Torneo Clausura 1999."},
    # 1999: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 2000 a 2002 (tools/a_mano;
    # RSSSF y Wikipedia; del Clausura, RSSSF no tiene los goles). El Torneo Clausura 1999 (marzo-junio; campeón Boca)
    # cerraba la temporada 1998-99: su "tabla anual" es la de la temporada (con el Apertura 1998, cargado
    # a mano). A Colón le descontaron 3 puntos por los incidentes con Unión. Bajaron directo los dos
    # últimos de los promedios (Platense y Huracán; los puntos de 1996-97 y 1997-98, de RSSSF y Wikipedia): todavía no
    # había Promoción. Boca ganó los dos torneos; el segundo lugar en la Libertadores 2000 lo jugaron los subcampeones
    # (River-Gimnasia, en cancha de Vélez). Los otros dos lugares salieron de una tabla del Apertura 1998, el Clausura
    # 1999 y el Apertura 1999. A la Copa Conmebol 1999, los mejores de la temporada que no iban a otra copa (Wikipedia)
    "1999-clausura": {"nombre": "Torneo Clausura 1999", "anio": 1999, "liga": "a_mano", "slug": "1999-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "1998-99", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. Según Wikipedia, el goleador fue José "
                                         "Luis Calderón (Independiente), con 17 goles.",
                      "descuentos": {"colon": 3},
                      "descuentos_texto": "A Colón se le descontaron 3 puntos (y se le dio perdido el partido) por los incidentes con Unión "
                                          "(fecha 7).",
                      "desempate_a_mano": {"fecha": "1999-06-24", "local": "gimnasia-y-esgrima", "visitante": "river-plate",
                                           "gl": 2, "gv": 3, "estadio": "José Amalfitani (Vélez)"},
                      "desempate_texto": "Gimnasia (subcampeón del Apertura 1998) y River (subcampeón del Clausura 1999) "
                                         "jugaron un partido, en cancha neutral, por el segundo lugar de la Argentina en "
                                         "la Copa Libertadores 2000 (el primero era de Boca, campeón de los dos torneos).",
                      "anual": [("a_mano", r"^1998-apertura$", 1998)],
                      "anual_texto": "La tabla de la temporada 1998-99: suma el Torneo Apertura 1998 y el Torneo Clausura 1999.",
                      "promedios": {"1996-97": {"river-plate": [87, 38], "boca-juniors": [50, 38], "gimnasia-y-esgrima": [50, 38],
                                                "san-lorenzo": [57, 38], "velez-sarsfield": [55, 38], "independiente": [71, 38],
                                                "lanus": [61, 38], "rosario-central": [49, 38], "newell-s-old-boys": [61, 38],
                                                "racing-club": [59, 38], "colon": [61, 38], "estudiantes-de-la-plata": [44, 38],
                                                "gimnasia-jujuy": [39, 38], "union": [44, 38], "ferro-carril-oeste": [46, 38],
                                                "platense": [47, 38], "huracan": [38, 38]},
                                    "1997-98": {"river-plate": [74, 38], "boca-juniors": [73, 38], "gimnasia-y-esgrima": [69, 38],
                                                "san-lorenzo": [62, 38], "velez-sarsfield": [78, 38], "independiente": [56, 38],
                                                "lanus": [65, 38], "rosario-central": [57, 38], "argentinos-juniors": [57, 38],
                                                "newell-s-old-boys": [42, 38], "racing-club": [41, 38], "colon": [38, 38],
                                                "estudiantes-de-la-plata": [49, 38], "gimnasia-jujuy": [52, 38],
                                                "union": [33, 38], "ferro-carril-oeste": [49, 38], "platense": [49, 38],
                                                "huracan": [27, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 2000, "anio_sudamericana": 1999, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 1998 y del Torneo Clausura 1999",
                                                  "boca-juniors"),
                                                 ("Ganador del partido entre los subcampeones", "river-plate"),
                                                 ("Tabla del Apertura 1998, el Clausura 1999 y el Apertura 1999",
                                                  "rosario-central"),
                                                 ("Tabla del Apertura 1998, el Clausura 1999 y el Apertura 1999",
                                                  "san-lorenzo")],
                                "sudamericana": [("Tabla de la temporada 1998-99 (el lugar de Gimnasia, que no la quiso "
                                                  "jugar)", "talleres"),
                                                 ("Tabla de la temporada 1998-99", "rosario-central")],
                                "nota": "A la Copa Mercosur 1999 fueron Boca, River, Independiente, Racing, San Lorenzo "
                                        "y Vélez, invitados por la Conmebol. Los dos últimos lugares de la Libertadores "
                                        "2000 se definieron en diciembre, con el Apertura 1999."}},
    # El Torneo Apertura 1999 (agosto-diciembre; campeón River) abría la temporada 1999-00
    "1999-apertura": {"nombre": "Torneo Apertura 1999", "anio": 1999, "liga": "a_mano", "slug": "1999-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "descuentos": {"san-lorenzo": 3, "velez-sarsfield": 3, "instituto": 3, "belgrano": 3},
                      "descuentos_texto": "Se les descontaron 3 puntos por incidentes a San Lorenzo (fecha 19), Vélez "
                                          "(fecha 15), Instituto (fecha 11) y Belgrano (fecha 19).",
                      "anual": [("a_mano", r"^1999-clausura$")],
                      "anual_texto": "La tabla del año 1999: suma el Torneo Clausura 1999 y el Torneo Apertura 1999 (con "
                                     "los descuentos). No daba lugares en las copas: con este torneo se cerró la tabla del "
                                     "Apertura 1998, el Clausura 1999 y el Apertura 1999, que les dio a Rosario Central y a "
                                     "San Lorenzo los dos últimos lugares de la Argentina en la Libertadores 2000.",
                      "sin_descensos": "En el Torneo Apertura 1999 no hubo descensos: se definieron al terminar la "
                                       "temporada 1999-00, con el Torneo Clausura 2000."},
    # 2000: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 2001 y 2002 (tools/a_mano;
    # RSSSF y Wikipedia). El Torneo Clausura 2000 (febrero-julio; campeón River) cerraba la temporada 1999-00: su "tabla
    # anual" es la de la temporada (con el Apertura 1999, cargado a mano, y sus descuentos a San Lorenzo, Vélez,
    # Instituto y Belgrano). A Boca y a Lanús les descontaron 3 puntos en el Clausura. Bajaron los dos
    # últimos de los promedios (Gimnasia de Jujuy y Ferro; los puntos de 1997-98 y 1998-99, de RSSSF y Wikipedia) y los
    # dos de arriba jugaron la primera Promoción: Belgrano se salvó con Quilmes e Instituto perdió con Almagro. Con la
    # temporada quedaron los cupos de la Copa Mercosur 2000 y de la Libertadores 2001 (Wikipedia)
    "2000-clausura": {"nombre": "Torneo Clausura 2000", "anio": 2000, "liga": "a_mano", "slug": "2000-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "1999-00", "nombre_anual": "Temporada y copas",
                      "descuentos": {"boca-juniors": 3, "lanus": 3},
                      "descuentos_texto": "A Boca (por incidentes en la fecha 13) y a Lanús (en la fecha 5) se les "
                                          "descontaron 3 puntos al terminar el torneo.",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2000-07-20T20:00Z", "fecha": "2000-07-20", "local": "2", "visitante": "2975",
                           "gl": 1, "gv": 0, "estadio": "Tres de Febrero (José Ingenieros)",
                           "goles": [{"jugador": "Maciel", "equipo": "local"}]},
                          {"hora_utc": "2000-07-20T21:00Z", "fecha": "2000-07-20", "local": "2741", "visitante": "belgrano",
                           "gl": 3, "gv": 1, "estadio": "Centenario (Quilmes)",
                           "goles": [{"jugador": "Giampietri", "equipo": "local"},
                                     {"jugador": "Luis Fernando", "tipo": "ec", "equipo": "local"},
                                     {"jugador": "Domínguez", "equipo": "local"}, {"jugador": "Medina", "equipo": "visitante"}]},
                          {"hora_utc": "2000-07-23T20:00Z", "fecha": "2000-07-23", "local": "2975", "visitante": "2",
                           "gl": 1, "gv": 1, "estadio": "Juan Domingo Perón (Córdoba)",
                           "goles": [{"jugador": "Sarría", "equipo": "local"}, {"jugador": "Villalba", "equipo": "visitante"}]},
                          {"hora_utc": "2000-07-23T21:00Z", "fecha": "2000-07-23", "local": "belgrano", "visitante": "2741",
                           "gl": 3, "gv": 1, "estadio": "Chateau Carreras (Córdoba)",
                           "goles": [{"jugador": "Artime", "equipo": "local"},
                                     {"jugador": "Lemos", "tipo": "ec", "equipo": "local"},
                                     {"jugador": "Sosa", "equipo": "local"}, {"jugador": "Milozzi", "equipo": "visitante"}]}]},
                      "ida_y_vuelta": True, "ventaja": ["instituto", "belgrano"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "La primera Promoción. Con el global igualado se quedaba en Primera el equipo de "
                                         "Primera: así se salvó Belgrano. Instituto perdió con Almagro y bajó a la B "
                                         "Nacional; Almagro subió."},
                      "anual": [("a_mano", r"^1999-apertura$", 1999)],
                      "anual_texto": "La tabla de la temporada 1999-00: suma el Torneo Apertura 1999 (con los descuentos a San "
                                     "Lorenzo, Vélez, Instituto y Belgrano) y el Torneo Clausura 2000.",
                      "promedios": {"1997-98": {"boca-juniors": [73, 38], "river-plate": [74, 38], "san-lorenzo": [62, 38],
                                                "velez-sarsfield": [78, 38], "gimnasia-y-esgrima": [69, 38],
                                                "rosario-central": [57, 38], "independiente": [56, 38], "lanus": [65, 38],
                                                "newell-s-old-boys": [42, 38], "argentinos-juniors": [57, 38],
                                                "colon": [38, 38], "racing-club": [41, 38], "union": [33, 38],
                                                "estudiantes-de-la-plata": [49, 38], "gimnasia-jujuy": [52, 38],
                                                "ferro-carril-oeste": [49, 38]},
                                    "1998-99": {"boca-juniors": [89, 38], "river-plate": [59, 38], "san-lorenzo": [61, 38],
                                                "velez-sarsfield": [46, 38], "gimnasia-y-esgrima": [62, 38],
                                                "rosario-central": [57, 38], "independiente": [51, 38], "lanus": [50, 38],
                                                "talleres": [44, 38], "newell-s-old-boys": [52, 38],
                                                "argentinos-juniors": [49, 38], "colon": [49, 38], "racing-club": [55, 38],
                                                "union": [54, 38], "estudiantes-de-la-plata": [45, 38], "belgrano": [44, 38],
                                                "gimnasia-jujuy": [47, 38], "ferro-carril-oeste": [35, 38]}},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2001, "anio_sudamericana": 2000, "nombre_sudamericana": "Copa Mercosur", "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 2000", "boca-juniors"),
                                                 ("Campeón del Torneo Apertura 1999 y del Torneo Clausura 2000",
                                                  "river-plate"),
                                                 ("Tabla de la temporada 1999-00", "san-lorenzo"),
                                                 ("Tabla de la temporada 1999-00", "rosario-central"),
                                                 ("Tabla de la temporada 1999-00", "velez-sarsfield")],
                                "sudamericana": [("Tabla de la temporada 1999-00", "rosario-central"),
                                                 ("Tabla de la temporada 1999-00", "velez-sarsfield"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "independiente"),
                                                 ("Invitado por la Conmebol", "river-plate"),
                                                 ("Invitado por la Conmebol", "san-lorenzo")]}},
    # El Torneo Apertura 2000 (julio-diciembre; campeón Boca) abría la temporada 2000-01
    "2000-apertura": {"nombre": "Torneo Apertura 2000", "anio": 2000, "liga": "a_mano", "slug": "2000-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "anual": [("a_mano", r"^2000-clausura$")],
                      "anual_texto": "La tabla del año 2000: suma el Torneo Clausura 2000 (con los descuentos a Boca y a "
                                     "Lanús) y el Torneo Apertura 2000. No daba lugares en las copas: salían de la tabla "
                                     "de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 2000 no hubo descensos: se definieron al terminar la "
                                       "temporada 2000-01, con el Torneo Clausura 2001."},
    # 2001: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 2002 (tools/a_mano; RSSSF y
    # Wikipedia). El Torneo Clausura 2001 (febrero-junio; campeón San Lorenzo) cerraba la temporada 2000-01: su "tabla
    # anual" es la de la temporada (con el Apertura 2000, cargado a mano). A Los Andes le
    # descontaron 3 puntos al terminar el torneo (Wikipedia). Bajaron los dos últimos de los promedios (Almagro y Los
    # Andes; los puntos de 1998-99 y 1999-00, de RSSSF; River 1998-99, 59, de la tabla de 1998-99 de RSSSF y de
    # Wikipedia) y los dos de arriba jugaron la Promoción y se salvaron: Argentinos con Instituto y Belgrano con Quilmes.
    # Con la temporada quedaron los cupos de la Copa Mercosur 2001 y de la Libertadores 2002 (Wikipedia)
    "2001-clausura": {"nombre": "Torneo Clausura 2001", "anio": 2001, "liga": "a_mano", "slug": "2001-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2000-01", "nombre_anual": "Temporada y copas",
                      "descuentos": {"los-andes": 3},
                      "descuentos_texto": "A Los Andes se le descontaron 3 puntos al terminar el torneo.",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2001-06-13T20:00Z", "fecha": "2001-06-13", "local": "2975",
                           "visitante": "argentinos-juniors", "gl": 0, "gv": 0, "estadio": "Juan Domingo Perón (Córdoba)"},
                          {"hora_utc": "2001-06-13T21:00Z", "fecha": "2001-06-13", "local": "2741", "visitante": "belgrano",
                           "gl": 1, "gv": 0, "estadio": "Centenario (Quilmes)",
                           "goles": [{"jugador": "Alayes", "equipo": "local"}]},
                          {"hora_utc": "2001-06-16T20:00Z", "fecha": "2001-06-16", "local": "argentinos-juniors",
                           "visitante": "2975", "gl": 1, "gv": 1, "estadio": "Arquitecto Ricardo Etcheverri",
                           "goles": [{"jugador": "Zagharián", "equipo": "local"}, {"jugador": "Sánchez", "equipo": "visitante"}]},
                          {"hora_utc": "2001-06-16T21:00Z", "fecha": "2001-06-16", "local": "belgrano", "visitante": "2741",
                           "gl": 1, "gv": 0, "estadio": "Gigante de Alberdi",
                           "goles": [{"jugador": "Mugnaini", "equipo": "local"}]}]},
                      "ida_y_vuelta": True, "ventaja": ["argentinos-juniors", "belgrano"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera: así se "
                                         "salvaron los dos. Instituto y Quilmes siguieron en la B Nacional."},
                      "anual": [("a_mano", r"^2000-apertura$", 2000)],
                      "anual_texto": "La tabla de la temporada 2000-01: suma el Torneo Apertura 2000 y el Torneo Clausura 2001.",
                      "promedios": {"1998-99": {"boca-juniors": [89, 38], "river-plate": [59, 38], "san-lorenzo": [61, 38],
                                                "gimnasia-y-esgrima": [62, 38], "rosario-central": [57, 38],
                                                "talleres": [44, 38], "velez-sarsfield": [46, 38],
                                                "newell-s-old-boys": [52, 38], "independiente": [51, 38], "colon": [49, 38],
                                                "union": [54, 38], "lanus": [50, 38], "estudiantes-de-la-plata": [45, 38],
                                                "racing-club": [55, 38], "argentinos-juniors": [49, 38], "belgrano": [44, 38]},
                                    "1999-00": {"boca-juniors": [74, 38], "river-plate": [86, 38], "san-lorenzo": [69, 38],
                                                "gimnasia-y-esgrima": [49, 38], "rosario-central": [66, 38],
                                                "talleres": [58, 38], "velez-sarsfield": [61, 38],
                                                "newell-s-old-boys": [55, 38], "independiente": [61, 38], "colon": [55, 38],
                                                "chacarita-juniors": [45, 38], "union": [50, 38], "lanus": [48, 38],
                                                "estudiantes-de-la-plata": [39, 38], "racing-club": [45, 38],
                                                "argentinos-juniors": [39, 38], "belgrano": [39, 38]}},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2002, "anio_sudamericana": 2001, "nombre_sudamericana": "Copa Mercosur", "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 2001 y del Torneo Apertura 2000",
                                                  "boca-juniors"),
                                                 ("Campeón del Torneo Clausura 2001", "san-lorenzo"),
                                                 ("Tabla de la temporada 2000-01", "river-plate"),
                                                 ("Tabla de la temporada 2000-01", "talleres"),
                                                 ("Tabla de la temporada 2000-01", "velez-sarsfield")],
                                "sudamericana": [("Tabla de la temporada 2000-01", "san-lorenzo"),
                                                 ("Tabla de la temporada 2000-01", "talleres"),
                                                 ("Tabla de la temporada 2000-01", "velez-sarsfield"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "independiente"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2001 (agosto 2001-febrero 2002: la última fecha se postergó en parte por la crisis de
    # diciembre de 2001; campeón Racing) abría la temporada 2001-02
    "2001-apertura": {"nombre": "Torneo Apertura 2001", "anio": 2001, "liga": "a_mano", "slug": "2001-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "anual": [("a_mano", r"^2001-clausura$")],
                      "anual_texto": "La tabla del año 2001: suma el Torneo Clausura 2001 (con el descuento a Los Andes) y "
                                     "el Torneo Apertura 2001. No daba lugares en las copas: salían de la tabla de la "
                                     "temporada.",
                      "sin_descensos": "En el Torneo Apertura 2001 no hubo descensos: se definieron al terminar la "
                                       "temporada 2001-02, con el Torneo Clausura 2002."},
    # 2002: dos torneos de 20 equipos a una rueda. ESPN no tiene ningún partido de 2002: van todos a mano, en
    # tools/a_mano (resultados y goles de RSSSF, solo con el apellido y sin minutos; estadio, día y hora de Wikipedia).
    # El Torneo Clausura 2002 (febrero-mayo; campeón River) cerraba la temporada 2001-02: su "tabla anual" es la de la
    # temporada (con el Apertura 2001, cargado a mano). Bajaron los dos últimos de los promedios (Argentinos y
    # Belgrano; los puntos de 1999-00 y 2000-01, de RSSSF) y los dos de arriba jugaron la Promoción contra equipos de la
    # B Nacional y se salvaron: Lanús con Huracán de Tres Arroyos y Unión con Gimnasia de Concepción del Uruguay. Con la
    # temporada quedaron definidos los cupos de la Sudamericana 2002 y de la Libertadores 2003 (Wikipedia)
    "2002-clausura": {"nombre": "Torneo Clausura 2002", "anio": 2002, "liga": "a_mano", "slug": "2002-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2001-02", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2002-05-24T00:00Z", "fecha": "2002-05-23", "hora": "21:00", "local": "2974",
                           "visitante": "lanus", "gl": 1, "gv": 2, "estadio": "Ciudad de Vicente López",
                           "goles": [{"jugador": "García", "equipo": "local"}, {"jugador": "Romero", "equipo": "visitante"},
                                     {"jugador": "López", "equipo": "visitante"}]},
                          {"hora_utc": "2002-05-24T00:00Z", "fecha": "2002-05-23", "hora": "21:00", "local": "ger",
                           "visitante": "union", "gl": 3, "gv": 1, "estadio": "Manuel y Ramón Núñez (Concepción del Uruguay)",
                           "goles": [{"jugador": "Leguizamón", "equipo": "local"}, {"jugador": "Fontana", "equipo": "local"},
                                     {"jugador": "Vendakis", "equipo": "local"},
                                     {"jugador": "Nto. Fernández", "equipo": "visitante"}]},
                          {"hora_utc": "2002-05-26T17:30Z", "fecha": "2002-05-26", "hora": "14:30", "local": "lanus",
                           "visitante": "2974", "gl": 1, "gv": 1, "estadio": "Ciudad de Lanús",
                           "goles": [{"jugador": "Hoyos", "equipo": "local"}, {"jugador": "García", "equipo": "visitante"}]},
                          {"hora_utc": "2002-05-26T19:30Z", "fecha": "2002-05-26", "hora": "16:30", "local": "union",
                           "visitante": "ger", "gl": 3, "gv": 0, "estadio": "15 de Abril",
                           "goles": [{"jugador": "Pérezlindo", "equipo": "local"}, {"jugador": "Mazzoni", "equipo": "local"},
                                     {"jugador": "Israilevich", "equipo": "local"}]}]},
                      "ida_y_vuelta": True, "ventaja": ["lanus", "union"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Los dos se "
                                         "salvaron: Huracán de Tres Arroyos y Gimnasia de Concepción del Uruguay "
                                         "siguieron en la B Nacional."},
                      "anual": [("a_mano", r"^2001-apertura$", 2001)],
                      "anual_texto": "La tabla de la temporada 2001-02: suma el Torneo Apertura 2001 y el Torneo Clausura 2002.",
                      "promedios": {"1999-00": {"river-plate": [86, 38], "boca-juniors": [74, 38], "san-lorenzo": [69, 38],
                                                "gimnasia-y-esgrima": [49, 38], "velez-sarsfield": [61, 38],
                                                "colon": [55, 38], "racing-club": [45, 38], "newell-s-old-boys": [55, 38],
                                                "estudiantes-de-la-plata": [39, 38], "talleres": [58, 38],
                                                "chacarita-juniors": [45, 38], "rosario-central": [66, 38],
                                                "independiente": [61, 38], "lanus": [48, 38], "union": [50, 38],
                                                "argentinos-juniors": [39, 38], "belgrano": [39, 38]},
                                    "2000-01": {"river-plate": [78, 38], "boca-juniors": [71, 38], "san-lorenzo": [81, 38],
                                                "gimnasia-y-esgrima": [55, 38], "velez-sarsfield": [56, 38],
                                                "colon": [49, 38], "racing-club": [40, 38], "newell-s-old-boys": [48, 38],
                                                "estudiantes-de-la-plata": [56, 38], "talleres": [61, 38],
                                                "huracan": [55, 38], "chacarita-juniors": [56, 38],
                                                "rosario-central": [41, 38], "independiente": [42, 38], "lanus": [43, 38],
                                                "union": [46, 38], "argentinos-juniors": [43, 38], "belgrano": [37, 38]}},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2003, "anio_sudamericana": 2002, "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 2001", "racing-club"),
                                                 ("Campeón del Torneo Clausura 2002", "river-plate"),
                                                 ("Tabla de la temporada 2001-02", "boca-juniors"),
                                                 ("Tabla de la temporada 2001-02", "gimnasia-y-esgrima")],
                                "sudamericana": [("Campeón de la Copa Mercosur 2001", "san-lorenzo"),
                                                 ("Tabla de la temporada 2001-02", "racing-club"),
                                                 ("Tabla de la temporada 2001-02", "gimnasia-y-esgrima"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2002 (julio-diciembre; campeón Independiente) abría la temporada 2002-03
    "2002-apertura": {"nombre": "Torneo Apertura 2002", "anio": 2002, "liga": "a_mano", "slug": "2002-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True,
                      "anual": [("a_mano", r"^2002-clausura$")],
                      "anual_texto": "La tabla del año 2002: suma el Torneo Clausura 2002 y el Torneo Apertura 2002. No "
                                     "daba lugares en las copas: salían de la tabla de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 2002 no hubo descensos: se definieron al terminar la "
                                       "temporada 2002-03, con el Torneo Clausura 2003."},
    # 2003: dos torneos de 20 equipos a una rueda. El Torneo Clausura 2003 (febrero-julio; campeón River) cerraba la
    # temporada 2002-03: su "tabla anual" es la de la temporada, con el Apertura 2002 (cargado a mano). Los puntos de
    # 2000-01 y 2001-02 para los promedios salen de Wikipedia y de RSSSF. Bajaron los dos últimos de los
    # promedios (Unión y Huracán) y los dos de arriba jugaron la Promoción contra equipos de la B Nacional y se salvaron:
    # Talleres con San Martín de Mendoza y Nueva Chicago con Argentinos. ESPN no tiene esos partidos, van a mano
    # (Wikipedia, RSSSF). Con la temporada quedaron definidos los cupos de la Sudamericana 2003 y de la Libertadores 2004
    "2003-clausura": {"nombre": "Torneo Clausura 2003", "anio": 2003, "slug": "clausura-2003",
                      "patron": r"^torneo-clausura-2003$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2002-03", "nombre_anual": "Temporada y copas",
                      # (ESPN no tiene los goles de casi ningún partido de este torneo)
                      "goleadores_nota": "Según Wikipedia, los goleadores del torneo fueron Luciano Figueroa (Rosario "
                                         "Central), con 17 goles; Roberto Nanni (Vélez), con 15, y Fernando Cavenaghi "
                                         "(River), con 12.",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2003-07-09T20:00Z", "fecha": "2003-07-09", "local": "3", "visitante": "nueva-chicago",
                           "gl": 0, "gv": 1, "estadio": "Nuevo Gasómetro"},
                          {"hora_utc": "2003-07-09T21:00Z", "fecha": "2003-07-09", "local": "smm", "visitante": "talleres",
                           "gl": 0, "gv": 1, "estadio": "Malvinas Argentinas (Mendoza)"},
                          {"hora_utc": "2003-07-13T20:00Z", "fecha": "2003-07-13", "local": "nueva-chicago", "visitante": "3",
                           "gl": 2, "gv": 0, "estadio": "Nuevo Gasómetro"},
                          {"hora_utc": "2003-07-13T21:00Z", "fecha": "2003-07-13", "local": "talleres", "visitante": "smm",
                           "gl": 1, "gv": 0, "estadio": "Chateau Carreras (Córdoba)"}]},
                      "ida_y_vuelta": True, "ventaja": ["talleres", "nueva-chicago"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Los dos se "
                                         "salvaron: Argentinos y San Martín de Mendoza siguieron en la B Nacional. De "
                                         "estos partidos no se cargaron los goles (las fuentes no coinciden)."},
                      "anual": [("a_mano", r"^2002-apertura$", 2002)],
                      "anual_texto": "La tabla de la temporada 2002-03: suma el Torneo Apertura 2002 y el Torneo Clausura 2003.",
                      "promedios": {"2000-01": {"river-plate": [78, 38], "boca-juniors": [71, 38], "san-lorenzo": [81, 38],
                                                "velez-sarsfield": [56, 38], "gimnasia-y-esgrima": [55, 38],
                                                "racing-club": [40, 38], "colon": [49, 38],
                                                "estudiantes-de-la-plata": [56, 38], "newell-s-old-boys": [48, 38],
                                                "lanus": [43, 38], "chacarita-juniors": [56, 38], "independiente": [42, 38],
                                                "rosario-central": [41, 38], "talleres": [61, 38], "union": [46, 38],
                                                "huracan": [55, 38]},
                                    "2001-02": {"river-plate": [84, 38], "boca-juniors": [68, 38], "san-lorenzo": [57, 38],
                                                "velez-sarsfield": [48, 38], "gimnasia-y-esgrima": [64, 38],
                                                "racing-club": [71, 38], "colon": [56, 38],
                                                "estudiantes-de-la-plata": [54, 38], "newell-s-old-boys": [51, 38],
                                                "lanus": [51, 38], "banfield": [48, 38], "chacarita-juniors": [47, 38],
                                                "independiente": [41, 38], "rosario-central": [40, 38], "talleres": [30, 38],
                                                "nueva-chicago": [48, 38], "union": [39, 38], "huracan": [44, 38]}},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2004, "anio_sudamericana": 2003, "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 2003 (lugar aparte)", "boca-juniors"),
                                                 ("Campeón del Torneo Apertura 2002", "independiente"),
                                                 ("Campeón del Torneo Clausura 2003", "river-plate"),
                                                 ("Tabla de la temporada 2002-03", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2002-03", "rosario-central")],
                                "sudamericana": [("Campeón de la Copa Sudamericana 2002", "san-lorenzo"),
                                                 ("Tabla de la temporada 2002-03", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2002-03", "rosario-central"),
                                                 ("Tabla de la temporada 2002-03", "independiente"),
                                                 ("Tabla de la temporada 2002-03", "colon"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2003 (agosto-diciembre; campeón Boca; dos partidos postergados, en 2004) abría la temporada
    # 2003-04
    "2003-apertura": {"nombre": "Torneo Apertura 2003", "anio": 2003, "anios": [2003, 2004], "slug": "apertura-2003",
                      "patron": r"^torneo-apertura-2003$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2003$")],
                      "anual_texto": "La tabla del año 2003: suma el Torneo Clausura 2003 y el Torneo Apertura 2003. No "
                                     "daba lugares en las copas: salían de la tabla de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 2003 no hubo descensos: se definieron al terminar la "
                                       "temporada 2003-04, con el Torneo Clausura 2004."},
    # 2004: dos torneos de 20 equipos a una rueda. El Torneo Clausura 2004 (febrero-junio; campeón River) cerraba la
    # temporada 2003-04: su "tabla anual" es la de la temporada (el Apertura 2003 y el Clausura 2004). Bajaron los dos
    # últimos de los promedios (2001-02, 2002-03 y 2003-04) y los dos de arriba jugaron la Promoción contra equipos de la
    # B Nacional y perdieron: Atlético de Rafaela con Huracán de Tres Arroyos (de local en Mar del Plata) y Talleres con
    # Argentinos (de local en Mendoza). ESPN no tiene esos partidos, van a mano (Wikipedia, La Nueva, La Nación). Con la
    # temporada quedaron definidos los cupos de la Sudamericana 2004 y de la Libertadores 2005, fijos
    "2004-clausura": {"nombre": "Torneo Clausura 2004", "anio": 2004, "slug": "clausura-2004",
                      "patron": r"^torneo-clausura-2004$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2003-04", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2004-06-30T22:00Z", "fecha": "2004-06-30", "local": "2974",
                           "visitante": "atletico-rafaela", "gl": 2, "gv": 1, "estadio": "José María Minella (Mar del Plata)",
                           "arbitro": "Gustavo Bassi",
                           "goles": [{"jugador": "Claudio García", "min": 23, "equipo": "local"},
                                     {"jugador": "Fabián Césaro", "min": 51, "equipo": "visitante"},
                                     {"jugador": "Ezequiel Miralles", "min": 57, "equipo": "local"}]},
                          {"hora_utc": "2004-07-01T22:00Z", "fecha": "2004-07-01", "local": "3", "visitante": "talleres",
                           "gl": 2, "gv": 1, "estadio": "Malvinas Argentinas (Mendoza)",
                           "goles": [{"jugador": "Aldo Osorio", "min": 28, "equipo": "visitante"},
                                     {"jugador": "Jorge Quinteros", "min": 45, "equipo": "local"},
                                     {"jugador": "Jorge Quinteros", "min": 78, "equipo": "local"}]},
                          {"hora_utc": "2004-07-04T19:00Z", "fecha": "2004-07-04", "local": "atletico-rafaela",
                           "visitante": "2974", "gl": 2, "gv": 3, "estadio": "Monumental (Rafaela)", "arbitro": "Gabriel Favale",
                           "goles": [{"jugador": "Gandín", "equipo": "local"},
                                     {"jugador": "Emanuel Villa", "equipo": "local"},
                                     {"jugador": "Cristian Galván", "equipo": "visitante"},
                                     {"jugador": "Jorge Izquierdo", "min": 59, "equipo": "visitante"},
                                     {"jugador": "Jorge Izquierdo", "min": 69, "equipo": "visitante"}]},
                          {"hora_utc": "2004-07-04T20:00Z", "fecha": "2004-07-04", "hora": "17:00", "local": "talleres",
                           "visitante": "3", "gl": 1, "gv": 2, "estadio": "Chateau Carreras (Córdoba)",
                           "goles": [{"jugador": "Gustavo Oberman", "min": 1, "equipo": "visitante"},
                                     {"jugador": "Luciano De Bruno", "min": 68, "tipo": "pen", "equipo": "local"},
                                     {"jugador": "Jorge Quinteros", "min": 88, "tipo": "pen", "equipo": "visitante"}]}]},
                      "ida_y_vuelta": True, "ventaja": ["atletico-rafaela", "talleres"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Los dos "
                                         "perdieron y bajaron: subieron Huracán de Tres Arroyos y Argentinos. De la "
                                         "vuelta en Rafaela no se encontraron los minutos de los goles del primer tiempo."},
                      "anual": [("arg.1", r"^torneo-apertura-2003$", 2003), ("arg.1", r"^torneo-apertura-2003$", 2004)],
                      "anual_texto": "La tabla de la temporada 2003-04: suma el Torneo Apertura 2003 y el Torneo Clausura 2004. "
                                     "A Chacarita se le descontaron 3 puntos por los incidentes en el partido con Boca.",
                      # (ESPN no tiene el Apertura 2001 ni el 2002: los puntos de esas temporadas, de la tabla de
                      # promedios de Wikipedia; Racing y Estudiantes 2001-02, de RSSSF, porque la Wikipedia en inglés
                      # tiene 68 y 51)
                      "promedios": {"2001-02": {"river-plate": [84, 38], "boca-juniors": [68, 38], "san-lorenzo": [57, 38],
                                                "racing-club": [71, 38], "velez-sarsfield": [48, 38], "colon": [56, 38],
                                                "banfield": [48, 38], "newell-s-old-boys": [51, 38],
                                                "gimnasia-y-esgrima": [64, 38], "independiente": [41, 38],
                                                "rosario-central": [40, 38], "lanus": [51, 38],
                                                "estudiantes-de-la-plata": [54, 38], "talleres": [30, 38],
                                                "chacarita-juniors": [47, 38], "nueva-chicago": [48, 38]},
                                    "2002-03": {"river-plate": [79, 38], "boca-juniors": [79, 38], "san-lorenzo": [56, 38],
                                                "racing-club": [53, 38], "velez-sarsfield": [66, 38], "colon": [57, 38],
                                                "banfield": [48, 38], "arsenal-de-sarandi": [49, 38],
                                                "newell-s-old-boys": [49, 38], "gimnasia-y-esgrima": [46, 38],
                                                "independiente": [61, 38], "rosario-central": [62, 38], "lanus": [51, 38],
                                                "estudiantes-de-la-plata": [43, 38], "olimpo": [51, 38],
                                                "talleres": [44, 38], "chacarita-juniors": [41, 38],
                                                "nueva-chicago": [41, 38]}},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2005, "anio_sudamericana": 2004, "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 2003", "boca-juniors"),
                                                 ("Campeón del Torneo Clausura 2004", "river-plate"),
                                                 ("Tabla de la temporada 2003-04", "banfield"),
                                                 ("Tabla de la temporada 2003-04", "san-lorenzo"),
                                                 ("Tabla de la temporada 2003-04", "quilmes")],
                                "sudamericana": [("Tabla de la temporada 2003-04", "banfield"),
                                                 ("Tabla de la temporada 2003-04", "san-lorenzo"),
                                                 ("Tabla de la temporada 2003-04", "quilmes"),
                                                 ("Tabla de la temporada 2003-04", "arsenal-de-sarandi"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2004 (agosto-diciembre; campeón Newell's) abría la temporada 2004-05
    "2004-apertura": {"nombre": "Torneo Apertura 2004", "anio": 2004, "slug": "apertura-2004",
                      "patron": r"^torneo-apertura-2004$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2004$")],
                      "anual_texto": "La tabla del año 2004: suma el Torneo Clausura 2004 y el Torneo Apertura 2004. No "
                                     "daba lugares en las copas: salían de la tabla de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 2004 no hubo descensos: se definieron al terminar la "
                                       "temporada 2004-05, con el Torneo Clausura 2005."},
    # 2005: dos torneos de 20 equipos a una rueda. El Torneo Clausura 2005 (febrero-julio; campeón Vélez) cerraba la
    # temporada 2004-05: su "tabla anual" es la de la temporada (el Apertura 2004 y el Clausura 2005). Bajaron los dos
    # últimos de los promedios (2002-03, 2003-04 y 2004-05) y los dos de arriba jugaron la Promoción contra equipos de la
    # B Nacional y se salvaron: Argentinos con Atlético de Rafaela e Instituto con Huracán. ESPN no tiene esos partidos,
    # van a mano (Wikipedia, La Nueva, Infobae, Página/12). Con la temporada quedaron definidos los cupos de la
    # Sudamericana 2005 y de la Libertadores 2006, fijos
    "2005-clausura": {"nombre": "Torneo Clausura 2005", "anio": 2005, "slug": "clausura-2005",
                      "patron": r"^torneo-clausura-2005$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2004-05", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2005-07-06T23:00Z", "fecha": "2005-07-06", "local": "9747",
                           "visitante": "argentinos-juniors", "gl": 2, "gv": 1, "estadio": "Monumental (Rafaela)",
                           "arbitro": "Gabriel Favale",
                           "goles": [{"jugador": "Sergio Marclay", "min": 57, "equipo": "local"},
                                     {"jugador": "Federico García", "min": 76, "equipo": "local"},
                                     {"jugador": "Leonardo Pisculichi", "min": 80, "tipo": "pen", "equipo": "visitante"}]},
                          {"hora_utc": "2005-07-07T00:00Z", "local": "10", "visitante": "instituto", "gl": 1, "gv": 2,
                           "estadio": "Tomás A. Ducó",
                           "goles": [{"jugador": "Nahuel Fioretto", "equipo": "local"},
                                     {"jugador": "Josemir Lujambio", "equipo": "visitante"},
                                     {"jugador": "Santiago Raymonda", "equipo": "visitante"}]},
                          {"hora_utc": "2005-07-10T20:00Z", "fecha": "2005-07-10", "local": "argentinos-juniors",
                           "visitante": "9747", "gl": 3, "gv": 0, "estadio": "Diego Armando Maradona",
                           "arbitro": "Sergio Pezzotta",
                           "goles": [{"jugador": "Matías Córdoba", "min": 65, "equipo": "local"},
                                     {"jugador": "Matías Córdoba", "min": 85, "equipo": "local"},
                                     {"jugador": "Claudio Marini", "min": 89, "equipo": "local"}]},
                          {"hora_utc": "2005-07-10T21:00Z", "fecha": "2005-07-10", "local": "instituto", "visitante": "10",
                           "gl": 1, "gv": 0, "estadio": "Presidente Perón (Alta Córdoba)", "arbitro": "Rafael Furchi",
                           "goles": [{"jugador": "Santiago Raymonda", "min": 30, "equipo": "local"}]}]},
                      "ida_y_vuelta": True, "ventaja": ["argentinos-juniors", "instituto"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Los dos se "
                                         "salvaron: Atlético de Rafaela y Huracán siguieron en la B Nacional. De la ida "
                                         "Huracán-Instituto no se encontraron el día ni los minutos de los goles."},
                      "anual": [("arg.1", r"^torneo-apertura-2004$", 2004)],
                      "anual_texto": "La tabla de la temporada 2004-05: suma el Torneo Apertura 2004 y el Torneo Clausura 2005.",
                      # (ESPN no tiene el Apertura 2002: los puntos de 2002-03, de la tabla de promedios de Wikipedia)
                      "promedios": {"2002-03": {"river-plate": [79, 38], "boca-juniors": [79, 38],
                                                "velez-sarsfield": [66, 38], "banfield": [48, 38], "san-lorenzo": [56, 38],
                                                "rosario-central": [62, 38], "racing-club": [53, 38],
                                                "newell-s-old-boys": [49, 38], "colon": [57, 38],
                                                "arsenal-de-sarandi": [49, 38], "independiente": [61, 38],
                                                "estudiantes-de-la-plata": [43, 38], "lanus": [51, 38],
                                                "gimnasia-y-esgrima": [46, 38], "olimpo": [51, 38]},
                                    "2003-04": [("arg.1", r"^torneo-apertura-2003$", 2003),
                                                ("arg.1", r"^torneo-apertura-2003$", 2004),
                                                ("arg.1", r"^torneo-clausura-2004$", 2004)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2006, "anio_sudamericana": 2005, "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 2004", "newell-s-old-boys"),
                                                 ("Campeón del Torneo Clausura 2005", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2004-05", "estudiantes-de-la-plata"),
                                                 ("Tabla de la temporada 2004-05", "rosario-central"),
                                                 ("Tabla de la temporada 2004-05", "river-plate")],
                                "sudamericana": [("Campeón de la Copa Sudamericana 2004 (e invitado)", "boca-juniors"),
                                                 ("Tabla de la temporada 2004-05", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2004-05", "estudiantes-de-la-plata"),
                                                 ("Tabla de la temporada 2004-05", "rosario-central"),
                                                 ("Tabla de la temporada 2004-05", "newell-s-old-boys"),
                                                 ("Tabla de la temporada 2004-05", "banfield"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2005 (agosto-diciembre; campeón Boca) abría la temporada 2005-06
    "2005-apertura": {"nombre": "Torneo Apertura 2005", "anio": 2005, "slug": "apertura-2005",
                      "patron": r"^torneo-apertura-2005$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2005$")],
                      "anual_texto": "La tabla del año 2005: suma el Torneo Clausura 2005 y el Torneo Apertura 2005. No "
                                     "daba lugares en las copas: salían de la tabla de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 2005 no hubo descensos: se definieron al terminar la "
                                       "temporada 2005-06, con el Torneo Clausura 2006."},
    # 2006: dos torneos de 20 equipos a una rueda. El Torneo Clausura 2006 (febrero-mayo; campeón Boca, que también
    # había ganado el Apertura 2005) cerraba la temporada 2005-06: su "tabla anual" es la de la temporada. Bajaron los
    # dos últimos de los promedios (2003-04, 2004-05 y 2005-06) y los dos de arriba jugaron la Promoción contra equipos
    # de la B Nacional: Olimpo perdió con Belgrano y Argentinos se salvó con Huracán (empataron el global). ESPN no tiene
    # esos partidos, van a mano (Wikipedia, Infobae, Vermouth Deportivo). Con la temporada quedaron definidos los cupos de
    # la Sudamericana 2006 y de la Libertadores 2007, fijos
    "2006-clausura": {"nombre": "Torneo Clausura 2006", "anio": 2006, "slug": "clausura-2006",
                      "patron": r"^torneo-clausura-2006$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2005-06", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2006-05-31T21:00Z", "fecha": "2006-05-31", "local": "4", "visitante": "olimpo",
                           "gl": 2, "gv": 1, "estadio": "Chateau Carreras (Córdoba)"},
                          {"hora_utc": "2006-05-31T22:00Z", "fecha": "2006-05-31", "local": "10",
                           "visitante": "argentinos-juniors", "gl": 1, "gv": 1, "estadio": "Tomás A. Ducó",
                           "arbitro": "Carlos Maglio",
                           "goles": [{"jugador": "Cristian Ledesma", "min": 20, "equipo": "visitante"},
                                     {"jugador": "Walter Coyette", "min": 22, "equipo": "local"}]},
                          {"hora_utc": "2006-06-04T21:00Z", "fecha": "2006-06-04", "local": "olimpo", "visitante": "4",
                           "gl": 1, "gv": 2, "estadio": "Roberto Carminatti (Bahía Blanca)", "arbitro": "Gabriel Favale",
                           "goles": [{"jugador": "Alejandro Delorte", "min": 3, "equipo": "local"},
                                     {"jugador": "Paolo Frangipane", "equipo": "visitante"},
                                     {"jugador": "Matías Gigli", "min": 66, "equipo": "visitante"}]},
                          {"hora_utc": "2006-06-04T22:00Z", "fecha": "2006-06-04", "local": "argentinos-juniors",
                           "visitante": "10", "gl": 2, "gv": 2, "estadio": "Diego Armando Maradona",
                           "arbitro": "Sergio Pezzotta",
                           "goles": [{"jugador": "Leonel Núñez", "min": 3, "equipo": "local"},
                                     {"jugador": "Héctor Álvarez", "min": 4, "equipo": "visitante"},
                                     {"jugador": "Cristian Ledesma", "min": 40, "tipo": "pen", "equipo": "local"},
                                     {"jugador": "Cristian Alfaro", "min": 43, "equipo": "visitante"}]}]},
                      "ida_y_vuelta": True, "ventaja": ["argentinos-juniors", "olimpo"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera: así se "
                                         "salvó Argentinos. Olimpo perdió y bajó; subió Belgrano. De la ida en Córdoba "
                                         "no se cargaron los goles (Gigli y Frangipane para Belgrano)."},
                      "anual": [("arg.1", r"^torneo-apertura-2005$", 2005)],
                      "anual_texto": "La tabla de la temporada 2005-06: suma el Torneo Apertura 2005 y el Torneo Clausura 2006.",
                      "promedios": {"2003-04": [("arg.1", r"^torneo-apertura-2003$", 2003),
                                                ("arg.1", r"^torneo-apertura-2003$", 2004),
                                                ("arg.1", r"^torneo-clausura-2004$", 2004)],
                                    "2004-05": [("arg.1", r"^torneo-apertura-2004$", 2004),
                                                ("arg.1", r"^torneo-clausura-2005$", 2005)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2007, "anio_sudamericana": 2006, "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 2005 y del Clausura 2006", "boca-juniors"),
                                                 ("Tabla de la temporada 2005-06", "gimnasia-y-esgrima"),
                                                 ("Tabla de la temporada 2005-06", "river-plate"),
                                                 ("Tabla de la temporada 2005-06", "banfield"),
                                                 ("Tabla de la temporada 2005-06", "velez-sarsfield")],
                                "sudamericana": [("Campeón de la Copa Sudamericana 2005 (e invitado)", "boca-juniors"),
                                                 ("Tabla de la temporada 2005-06", "gimnasia-y-esgrima"),
                                                 ("Tabla de la temporada 2005-06", "banfield"),
                                                 ("Tabla de la temporada 2005-06", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2005-06", "lanus"),
                                                 ("Tabla de la temporada 2005-06", "san-lorenzo"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2006 (agosto-diciembre; el último partido, Racing-San Lorenzo, recién en febrero de 2007) abría
    # la temporada 2006-07. Estudiantes y Boca terminaron empatados arriba y jugaron una final (ganó Estudiantes)
    "2006-apertura": {"nombre": "Torneo Apertura 2006", "anio": 2006, "anios": [2006, 2007], "slug": "apertura-2006",
                      "patron": r"^torneo-apertura-2006(---final)?$", "zonas": "unica", "fechas": 19, "pasan": 2,
                      "nombre_playoffs": "Final (desempate)", "playoffs": [(r"---final$", "Final")],
                      "texto_pasan": "Empatados en el primer puesto (44 puntos): definieron el título en una final, "
                                     "en cancha de Vélez",
                      "anual": [("arg.1", r"^torneo-clausura-2006$")],
                      "anual_texto": "La tabla del año 2006: suma el Torneo Clausura 2006 y el Torneo Apertura 2006 (sin la "
                                     "final). No daba lugares en las copas: salían de la tabla de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 2006 no hubo descensos: se definieron al terminar la "
                                       "temporada 2006-07, con el Torneo Clausura 2007."},
    # 2007: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Clausura 2007 (febrero-junio; campeón San
    # Lorenzo) cerraba la temporada 2006-07: su "tabla anual" es la de la temporada (el Apertura 2006 y el Clausura 2007).
    # Bajaron los dos últimos de los promedios (2004-05, 2005-06 y 2006-07) y los dos de arriba jugaron la Promoción
    # contra equipos de la B Nacional y perdieron: Godoy Cruz con Huracán y Nueva Chicago con Tigre (la vuelta se
    # suspendió al final por incidentes; quedó el resultado). Con la temporada quedaron definidos los cupos de la
    # Sudamericana 2007 (Boca y River, invitados) y de la Libertadores 2008, fijos
    "2007-clausura": {"nombre": "Torneo Clausura 2007", "anio": 2007, "slug": "clausura-2007",
                      "patron": r"^torneo-clausura-2007(---promocion)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2006-07", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"---promocion$", "Promoción")],
                      "ida_y_vuelta": True, "ventaja": ["godoy-cruz", "nueva-chicago"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Los dos "
                                         "perdieron y bajaron: subieron Huracán y Tigre. La vuelta en Mataderos se "
                                         "suspendió al final por incidentes y quedó el resultado."},
                      "anual": [("arg.1", r"^torneo-apertura-2006$", 2006), ("arg.1", r"^torneo-apertura-2006$", 2007)],
                      "anual_texto": "La tabla de la temporada 2006-07: suma el Torneo Apertura 2006 (sin la final por "
                                     "el desempate) y el Torneo Clausura 2007.",
                      "promedios": {"2004-05": [("arg.1", r"^torneo-apertura-2004$", 2004),
                                                ("arg.1", r"^torneo-apertura-2004$", 2005),
                                                ("arg.1", r"^torneo-clausura-2005$", 2005)],
                                    "2005-06": [("arg.1", r"^torneo-apertura-2005$", 2005),
                                                ("arg.1", r"^torneo-apertura-2005$", 2006),
                                                ("arg.1", r"^torneo-clausura-2006$", 2006)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2008, "anio_sudamericana": 2007, "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 2007 (lugar aparte)",
                                                  "boca-juniors"),
                                                 ("Campeón del Torneo Apertura 2006", "estudiantes-de-la-plata"),
                                                 ("Campeón del Torneo Clausura 2007", "san-lorenzo"),
                                                 ("Tabla de la temporada 2006-07", "river-plate"),
                                                 ("Tabla de la temporada 2006-07", "arsenal-de-sarandi"),
                                                 ("Tabla de la temporada 2006-07", "lanus")],
                                "sudamericana": [("Tabla de la temporada 2006-07", "estudiantes-de-la-plata"),
                                                 ("Tabla de la temporada 2006-07", "san-lorenzo"),
                                                 ("Tabla de la temporada 2006-07", "arsenal-de-sarandi"),
                                                 ("Tabla de la temporada 2006-07", "lanus"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2007 (agosto-diciembre; campeón Lanús) abría la temporada 2007-08. Sin cupos propios: los de
    # la Libertadores 2009 salieron del promedio de tres torneos (ver el Apertura 2008)
    "2007-apertura": {"nombre": "Torneo Apertura 2007", "anio": 2007, "anios": [2007, 2008], "slug": "apertura-2007",
                      "patron": r"^torneo-apertura-2007$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2007$")],
                      "anual_texto": "La tabla del año 2007: suma el Torneo Clausura 2007 y el Torneo Apertura 2007. No "
                                     "daba lugares en las copas: los de la Libertadores 2009 salieron del promedio del "
                                     "Apertura 2007, el Clausura 2008 y el Apertura 2008.",
                      "sin_descensos": "En el Torneo Apertura 2007 no hubo descensos: se definieron al terminar la "
                                       "temporada 2007-08, con el Torneo Clausura 2008."},
    # 2008: dos torneos de 20 equipos a una rueda. El Torneo Clausura 2008 (febrero-junio; campeón River) cerraba la
    # temporada 2007-08: su "tabla anual" es la de la temporada (el Apertura 2007 y el Clausura 2008). Bajaron los dos
    # últimos de los promedios (2005-06, 2006-07 y 2007-08) y los dos de arriba jugaron la Promoción contra equipos de la
    # B Nacional y se salvaron: Racing con Belgrano y Gimnasia de Jujuy con Unión. Los cupos de la Sudamericana 2008
    # (Boca y River, invitados), fijos
    "2008-clausura": {"nombre": "Torneo Clausura 2008", "anio": 2008, "slug": "clausura-2008",
                      "patron": r"^torneo-clausura-2008(---promocion)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2007-08", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"---promocion$", "Promoción")],
                      "ida_y_vuelta": True, "ventaja": ["racing-club", "gimnasia-jujuy"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Los dos se "
                                         "salvaron: Belgrano y Unión siguieron en la B Nacional."},
                      "anual": [("arg.1", r"^torneo-apertura-2007$", 2007), ("arg.1", r"^torneo-apertura-2007$", 2008)],
                      "anual_texto": "La tabla de la temporada 2007-08: suma el Torneo Apertura 2007 y el Torneo Clausura 2008.",
                      "promedios": {"2005-06": [("arg.1", r"^torneo-apertura-2005$", 2005),
                                                ("arg.1", r"^torneo-apertura-2005$", 2006),
                                                ("arg.1", r"^torneo-clausura-2006$", 2006)],
                                    "2006-07": [("arg.1", r"^torneo-apertura-2006$", 2006),
                                                ("arg.1", r"^torneo-apertura-2006$", 2007),
                                                ("arg.1", r"^torneo-clausura-2007$", 2007)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2008, "fijos": True,
                                "sudamericana": [("Campeón de la Copa Sudamericana 2007 (lugar aparte)", "arsenal-de-sarandi"),
                                                 ("Tabla de la temporada 2007-08", "estudiantes-de-la-plata"),
                                                 ("Tabla de la temporada 2007-08", "san-lorenzo"),
                                                 ("Tabla de la temporada 2007-08", "argentinos-juniors"),
                                                 ("Tabla de la temporada 2007-08", "independiente"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2008 (agosto-diciembre) abría la temporada 2008-09. Boca, San Lorenzo y Tigre terminaron
    # empatados arriba y jugaron un triangular ("triangular"; ganó Boca, por diferencia de gol). Los cupos de la
    # Libertadores 2009 (por el promedio del Apertura 2007, el Clausura 2008 y el Apertura 2008), fijos
    "2008-apertura": {"nombre": "Torneo Apertura 2008", "anio": 2008, "slug": "apertura-2008",
                      "patron": r"^torneo-apertura-2008(---triangular)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "triangular": True, "nombre_playoffs": "Triangular final",
                      "playoffs": [(r"---triangular$", "Triangular final")],
                      "texto_triangular": "Boca, San Lorenzo y Tigre terminaron empatados en el primer puesto, con 39 "
                                          "puntos, y jugaron un triangular a un partido, todos contra todos. Cada uno "
                                          "ganó un partido: Boca salió campeón por diferencia de gol.",
                      "anual": [("arg.1", r"^torneo-clausura-2008$")],
                      "anual_texto": "La tabla del año 2008: suma el Torneo Clausura 2008 y el Torneo Apertura 2008 (sin "
                                     "el triangular).",
                      "sin_descensos": "En el Torneo Apertura 2008 no hubo descensos: se definieron al terminar la "
                                       "temporada 2008-09, con el Torneo Clausura 2009.",
                      "cupos": {"anio": 2009, "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 2007", "lanus"),
                                                 ("Campeón del Torneo Clausura 2008", "river-plate"),
                                                 ("Campeón del Torneo Apertura 2008", "boca-juniors"),
                                                 ("Promedio del Apertura 2007, el Clausura 2008 y el Apertura 2008",
                                                  "san-lorenzo"),
                                                 ("Promedio del Apertura 2007, el Clausura 2008 y el Apertura 2008",
                                                  "estudiantes-de-la-plata")]}},
    # 2009: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Clausura 2009 (febrero-julio; campeón Vélez)
    # cerraba la temporada 2008-09: su "tabla anual" es la de la temporada (el Apertura 2008 y el Clausura 2009). Bajaron
    # los dos últimos de los promedios (2006-07, 2007-08 y 2008-09) y los dos de arriba jugaron la Promoción contra
    # equipos de la B Nacional y se salvaron: Rosario Central con Belgrano, y Gimnasia con Atlético de Rafaela (empataron
    # el global; se quedó el de Primera). Los cupos de la Sudamericana 2009 (Boca y River, invitados), fijos
    "2009-clausura": {"nombre": "Torneo Clausura 2009", "anio": 2009, "slug": "clausura-2009",
                      "patron": r"^torneo-clausura-2009(---promocion)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2008-09", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"---promocion$", "Promoción")],
                      "ida_y_vuelta": True, "ventaja": ["gimnasia-y-esgrima", "rosario-central"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera: así se "
                                         "salvó Gimnasia. Rosario Central también se quedó; Belgrano y Atlético de "
                                         "Rafaela siguieron en la B Nacional."},
                      "anual": [("arg.1", r"^torneo-apertura-2008$", 2008)],
                      "anual_texto": "La tabla de la temporada 2008-09: suma el Torneo Apertura 2008 (sin el triangular "
                                     "final) y el Torneo Clausura 2009.",
                      "promedios": {"2006-07": [("arg.1", r"^torneo-apertura-2006$", 2006),
                                                ("arg.1", r"^torneo-apertura-2006$", 2007),
                                                ("arg.1", r"^torneo-clausura-2007$", 2007)],
                                    "2007-08": [("arg.1", r"^torneo-apertura-2007$", 2007),
                                                ("arg.1", r"^torneo-apertura-2007$", 2008),
                                                ("arg.1", r"^torneo-clausura-2008$", 2008)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2009, "fijos": True,
                                "sudamericana": [("Tabla de la temporada 2008-09", "lanus"),
                                                 ("Tabla de la temporada 2008-09", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2008-09", "san-lorenzo"),
                                                 ("Tabla de la temporada 2008-09", "tigre"),
                                                 ("Invitado por la Conmebol", "boca-juniors"),
                                                 ("Invitado por la Conmebol", "river-plate")]}},
    # El Torneo Apertura 2009 (agosto-diciembre; campeón Banfield) abría la temporada 2009-10. La tabla del año 2009 (el
    # Clausura y el Apertura) daba lugares en la Libertadores 2010. Los cupos, fijos
    "2009-apertura": {"nombre": "Torneo Apertura 2009", "anio": 2009, "slug": "apertura-2009",
                      "patron": r"^torneo-apertura-2009$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2009$")],
                      "anual_texto": "La tabla del año 2009: suma el Torneo Clausura 2009 y el Torneo Apertura 2009.",
                      "sin_descensos": "En el Torneo Apertura 2009 no hubo descensos: se definieron al terminar la "
                                       "temporada 2009-10, con el Torneo Clausura 2010.",
                      "cupos": {"anio": 2010, "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 2009 (lugar aparte)", "estudiantes-de-la-plata"),
                                                 ("Campeón del Torneo Clausura 2009", "velez-sarsfield"),
                                                 ("Campeón del Torneo Apertura 2009", "banfield"),
                                                 ("Tabla del año 2009", "lanus"),
                                                 ("Tabla del año 2009", "colon"),
                                                 ("Tabla del año 2009", "newell-s-old-boys")]}},
    # 2010: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Clausura 2010 (enero-mayo; campeón Argentinos)
    # cerraba la temporada 2009-10: su "tabla anual" es la de la temporada (el Apertura 2009 y el Clausura 2010). Bajaron
    # los dos últimos de los promedios (2007-08, 2008-09 y 2009-10) y los dos de arriba jugaron la Promoción contra
    # equipos de la B Nacional (ESPN la llama "final"): Gimnasia se salvó con Atlético de Rafaela y Rosario Central perdió
    # con All Boys. Los cupos de la Sudamericana 2010, fijos
    "2010-clausura": {"nombre": "Torneo Clausura 2010", "anio": 2010, "slug": "clausura-2010",
                      "patron": r"^torneo-clausura-2010(---final)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2009-10", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"---final$", "Promoción")],
                      "ida_y_vuelta": True, "ventaja": ["gimnasia-y-esgrima", "rosario-central"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. Gimnasia "
                                         "se salvó; Rosario Central perdió y bajó, y subió All Boys."},
                      "anual": [("arg.1", r"^torneo-apertura-2009$", 2009)],
                      "anual_texto": "La tabla de la temporada 2009-10: suma el Torneo Apertura 2009 y el Torneo Clausura 2010.",
                      "promedios": {"2007-08": [("arg.1", r"^torneo-apertura-2007$", 2007),
                                                ("arg.1", r"^torneo-apertura-2007$", 2008),
                                                ("arg.1", r"^torneo-clausura-2008$", 2008)],
                                    "2008-09": [("arg.1", r"^torneo-apertura-2008$", 2008),
                                                ("arg.1", r"^torneo-clausura-2009$", 2009)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2010, "fijos": True,
                                "sudamericana": [("Tabla de la temporada 2009-10", "banfield"),
                                                 ("Tabla de la temporada 2009-10", "argentinos-juniors"),
                                                 ("Tabla de la temporada 2009-10", "estudiantes-de-la-plata"),
                                                 ("Tabla de la temporada 2009-10", "newell-s-old-boys"),
                                                 ("Tabla de la temporada 2009-10", "independiente"),
                                                 ("Tabla de la temporada 2009-10", "velez-sarsfield")]}},
    # El Torneo Apertura 2010 (agosto-diciembre; campeón Estudiantes) abría la temporada 2010-11. La tabla del año 2010
    # (el Clausura y el Apertura) daba lugares en la Libertadores 2011. Los cupos, fijos
    "2010-apertura": {"nombre": "Torneo Apertura 2010", "anio": 2010, "slug": "apertura-2010",
                      "patron": r"^torneo-apertura-2010$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2010$")],
                      "anual_texto": "La tabla del año 2010: suma el Torneo Clausura 2010 y el Torneo Apertura 2010.",
                      "sin_descensos": "En el Torneo Apertura 2010 no hubo descensos: se definieron al terminar la "
                                       "temporada 2010-11, con el Torneo Clausura 2011.",
                      "cupos": {"anio": 2011, "fijos": True,
                                "libertadores": [("Campeón del Torneo Clausura 2010", "argentinos-juniors"),
                                                 ("Campeón del Torneo Apertura 2010", "estudiantes-de-la-plata"),
                                                 ("Tabla del año 2010", "velez-sarsfield"),
                                                 ("Tabla del año 2010", "godoy-cruz"),
                                                 ("Campeón de la Copa Sudamericana 2010", "independiente")]}},
    # 2011: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Clausura 2011 (febrero-junio; campeón Vélez)
    # cerraba la temporada 2010-11: su "tabla anual" es la de la temporada (el Apertura 2010 y el Clausura 2011). Bajaron
    # los dos últimos de los promedios (2008-09, 2009-10 y 2010-11); Huracán y Gimnasia empataron en el lugar de la
    # Promoción y jugaron un desempate (ESPN lo llama "promocion"; ganó Gimnasia). Los dos de arriba jugaron la
    # Promoción contra equipos de la B Nacional y perdieron (River con Belgrano, Gimnasia con San Martín de San Juan): ESPN
    # no tiene esos partidos, van a mano (Wikipedia; los goles, de Goal, Página/12 y Diario de Cuyo). Los cupos de la
    # Sudamericana 2011, fijos
    "2011-clausura": {"nombre": "Torneo Clausura 2011", "anio": 2011, "slug": "clausura-2011",
                      "patron": r"^torneo-clausura-2011(---promocion)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2010-11", "nombre_anual": "Temporada y copas",
                      "desempate": r"---promocion$",
                      "desempate_texto": "Huracán y Gimnasia (La Plata) terminaron empatados en los promedios, en el "
                                         "lugar de la Promoción: lo definieron en un partido, en la cancha de Boca. "
                                         "Huracán, que perdió, bajó directo; Gimnasia jugó la Promoción.",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"^$^", "Promoción")],
                      "playoffs_a_mano": {"Promoción": [
                          {"hora_utc": "2011-06-23T00:00Z", "fecha": "2011-06-22", "hora": "21:00", "local": "4",
                           "visitante": "16", "gl": 2, "gv": 0, "estadio": "Gigante de Alberdi", "arbitro": "Néstor Pitana",
                           "goles": [{"jugador": "César Mansanelli", "min": 25, "tipo": "pen", "equipo": "local"},
                                     {"jugador": "César Pereyra", "min": 49, "equipo": "local"}]},
                          {"hora_utc": "2011-06-26T18:00Z", "fecha": "2011-06-26", "hora": "15:00", "local": "16",
                           "visitante": "4", "gl": 1, "gv": 1, "estadio": "Monumental", "arbitro": "Sergio Pezzotta",
                           "goles": [{"jugador": "Mariano Pavone", "min": 5, "equipo": "local"},
                                     {"jugador": "Guillermo Farré", "min": 61, "equipo": "visitante"}]},
                          {"hora_utc": "2011-06-26T22:10Z", "fecha": "2011-06-26", "hora": "19:10", "local": "7845",
                           "visitante": "9", "gl": 1, "gv": 0, "estadio": "Ingeniero Hilario Sánchez",
                           "goles": [{"jugador": "Roberval", "min": 34, "equipo": "local"}]},
                          {"hora_utc": "2011-06-30T18:00Z", "fecha": "2011-06-30", "hora": "15:00", "local": "9",
                           "visitante": "7845", "gl": 1, "gv": 1, "estadio": "Juan Carmelo Zerillo",
                           "arbitro": "Héctor Baldassi",
                           "goles": [{"jugador": "Sebastián Penco", "min": 2, "equipo": "visitante"},
                                     {"jugador": "Vizcarra", "min": 69, "equipo": "local"}]}]},
                      "ida_y_vuelta": True,
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera. River y "
                                         "Gimnasia perdieron y bajaron; Belgrano y San Martín de San Juan subieron."},
                      "anual": [("arg.1", r"^torneo-apertura-2010$", 2010)],
                      "anual_texto": "La tabla de la temporada 2010-11: suma el Torneo Apertura 2010 y el Torneo Clausura 2011.",
                      "promedios": {"2008-09": [("arg.1", r"^torneo-apertura-2008$", 2008),
                                                ("arg.1", r"^torneo-clausura-2009$", 2009)],
                                    "2009-10": [("arg.1", r"^torneo-apertura-2009$", 2009),
                                                ("arg.1", r"^torneo-clausura-2010$", 2010)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2011, "fijos": True,
                                "sudamericana": [("Campeón de la Copa Sudamericana 2010 (lugar aparte)", "independiente"),
                                                 ("Tabla de la temporada 2010-11", "velez-sarsfield"),
                                                 ("Tabla de la temporada 2010-11", "estudiantes-de-la-plata"),
                                                 ("Tabla de la temporada 2010-11", "godoy-cruz"),
                                                 ("Tabla de la temporada 2010-11", "lanus"),
                                                 ("Tabla de la temporada 2010-11", "arsenal-de-sarandi"),
                                                 ("Tabla de la temporada 2010-11", "argentinos-juniors")]}},
    # El Torneo Apertura 2011 (agosto-diciembre; campeón Boca) abría la temporada 2011-12. La tabla del año 2011 (el
    # Clausura y el Apertura) daba lugares en la Libertadores 2012 y en la Sudamericana 2012. Los cupos, fijos
    "2011-apertura": {"nombre": "Torneo Apertura 2011", "anio": 2011, "slug": "apertura-2011",
                      "patron": r"^torneo-apertura-2011$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True,
                      "anual": [("arg.1", r"^torneo-clausura-2011$")],
                      "anual_texto": "La tabla del año 2011: suma el Torneo Clausura 2011 y el Torneo Apertura 2011.",
                      "sin_descensos": "En el Torneo Apertura 2011 no hubo descensos: se definieron al terminar la "
                                       "temporada 2011-12, con el Torneo Clausura 2012.",
                      "cupos": {"anio": 2012, "fijos": True,
                                "libertadores": [("Campeón del Torneo Clausura 2011", "velez-sarsfield"),
                                                 ("Campeón del Torneo Apertura 2011", "boca-juniors"),
                                                 ("Tabla del año 2011", "lanus"),
                                                 ("Tabla del año 2011", "godoy-cruz"),
                                                 ("Mejor argentino en la Copa Sudamericana 2011", "arsenal-de-sarandi")],
                                "sudamericana": [("Tabla del año 2011", "independiente"),
                                                 ("Tabla del año 2011", "racing-club"),
                                                 ("Tabla del año 2011", "tigre"),
                                                 ("Tabla del año 2011", "argentinos-juniors"),
                                                 ("Tabla del año 2011", "colon"),
                                                 ("Campeón de la Copa Argentina 2011-12 (se jugó en 2012)", "boca-juniors")]}},
    # 2012: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Clausura 2012 (febrero-junio; campeón Arsenal)
    # cerraba la temporada 2011-12: su "tabla anual" es la de la temporada (el Apertura 2011 y el Clausura 2012). Bajaron
    # los dos últimos de los promedios (2009-10, 2010-11 y 2011-12) y los dos de arriba jugaron la Promoción contra
    # equipos de la B Nacional ("promocion"): a ida y vuelta; con el global igualado se quedaba el de Primera ("ventaja",
    # San Martín de San Juan). Los cupos de la Sudamericana 2012 (por la tabla del año 2011), fijos
    "2012-clausura": {"nombre": "Torneo Clausura 2012", "anio": 2012, "slug": "clausura-2012",
                      "patron": r"^torneo-clausura-2012(---promocion)?$", "zonas": "unica", "fechas": 19, "pasan": 0,
                      "campeon_tabla": True, "temporada": "2011-12", "nombre_anual": "Temporada y copas",
                      "nombre_playoffs": "Promoción", "playoffs": [(r"---promocion$", "Promoción")],
                      "ida_y_vuelta": True, "ventaja": ["san-lorenzo", "san-martin-san-juan"],
                      "cuadro": {"bloques": [("Promoción: los equipos de Primera contra los de la B Nacional",
                                              [["Promoción"]])],
                                 "nota": "Con el global igualado se quedaba en Primera el equipo de Primera (ventaja "
                                         "deportiva): así se salvó San Martín de San Juan. Rosario Central e Instituto "
                                         "siguieron en la B Nacional."},
                      "anual": [("arg.1", r"^torneo-apertura-2011$", 2011)],
                      "anual_texto": "La tabla de la temporada 2011-12: suma el Torneo Apertura 2011 y el Torneo Clausura 2012.",
                      "promedios": {"2009-10": [("arg.1", r"^torneo-apertura-2009$", 2009),
                                                ("arg.1", r"^torneo-clausura-2010$", 2010)],
                                    "2010-11": [("arg.1", r"^torneo-apertura-2010$", 2010),
                                                ("arg.1", r"^torneo-clausura-2011$", 2011)]},
                      "descensos": "promedios", "descienden": 2, "promocion": 2,
                      "cupos": {"anio": 2012, "fijos": True,
                                "sudamericana": [("Campeón de la Copa Argentina 2011-12", "boca-juniors"),
                                                 ("Tabla del año 2011 (Clausura 2011 y Apertura 2011)", "independiente"),
                                                 ("Tabla del año 2011 (Clausura 2011 y Apertura 2011)", "racing-club"),
                                                 ("Tabla del año 2011 (Clausura 2011 y Apertura 2011)", "tigre"),
                                                 ("Tabla del año 2011 (Clausura 2011 y Apertura 2011)", "argentinos-juniors"),
                                                 ("Tabla del año 2011 (Clausura 2011 y Apertura 2011)", "colon")]}},
    # El Torneo Inicial 2012 (agosto-diciembre; campeón Vélez; dos partidos postergados, en febrero de 2013) abría la
    # temporada 2012-13. La tabla del año 2012 (el Clausura y el Inicial) daba lugares en la Libertadores 2013. Los
    # cupos, fijos
    "2012-inicial": {"nombre": "Torneo Inicial 2012", "anio": 2012, "anios": [2012, 2013], "slug": "inicial-2012",
                     "patron": r"^torneo-inicial-2012$", "zonas": "unica", "fechas": 19, "pasan": 0,
                     "campeon_tabla": True,
                     "anual": [("arg.1", r"^torneo-clausura-2012$")],
                     "anual_texto": "La tabla del año 2012: suma el Torneo Clausura 2012 y el Torneo Inicial 2012.",
                     "sin_descensos": "En el Torneo Inicial 2012 no hubo descensos: se definieron al terminar la "
                                      "temporada 2012-13, con el Torneo Final 2013.",
                     "cupos": {"anio": 2013, "fijos": True,
                               "libertadores": [("Campeón del Torneo Clausura 2012", "arsenal-de-sarandi"),
                                                ("Campeón del Torneo Inicial 2012", "velez-sarsfield"),
                                                ("Tabla del año 2012", "newell-s-old-boys"),
                                                ("Tabla del año 2012", "boca-juniors"),
                                                ("Mejor argentino en la Copa Sudamericana 2012 (fue finalista)", "tigre")]}},
    # 2013: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Final 2013 (febrero-junio; campeón Newell's)
    # cerraba la temporada 2012-13: su "tabla anual" es la de la temporada (el Inicial 2012 y el Final 2013). Bajaron los
    # tres últimos de los promedios (2010-11, 2011-12 y 2012-13). Después, la Superfinal: el campeón del Inicial 2012
    # (Vélez) contra el del Final 2013 (Newell's); ESPN no la tiene, va a mano (Wikipedia). Los cupos de la Sudamericana
    # 2013, fijos
    "2013-final": {"nombre": "Torneo Final 2013", "anio": 2013, "slug": "final-2013",
                   "patron": r"^torneo-final-2013$", "zonas": "unica", "fechas": 19, "pasan": 0,
                   "campeon_tabla": True, "temporada": "2012-13", "nombre_anual": "Temporada y copas",
                   "nombre_playoffs": "Superfinal", "playoffs": [(r"^$^", "Superfinal 2012-13")],
                   "playoffs_a_mano": {"Superfinal 2012-13": [
                       {"hora_utc": "2013-06-29T21:00Z", "fecha": "2013-06-29", "hora": "18:00",
                        "local": "velez-sarsfield", "visitante": "newell-s-old-boys", "gl": 1, "gv": 0,
                        "estadio": "Estadio Malvinas Argentinas (Mendoza)",
                        "goles": [{"jugador": "Lucas Pratto", "min": 8, "equipo": "local"}]}]},
                   "cuadro": {"bloques": [("Superfinal 2012-13: el campeón del Inicial 2012 contra el del Final 2013",
                                           [["Superfinal 2012-13"]])]},
                   "anual": [("arg.1", r"^torneo-inicial-2012$", 2012), ("arg.1", r"^torneo-inicial-2012$", 2013)],
                   "anual_texto": "La tabla de la temporada 2012-13: suma el Torneo Inicial 2012 y el Torneo Final 2013.",
                   "promedios": {"2010-11": [("arg.1", r"^torneo-apertura-2010$", 2010),
                                             ("arg.1", r"^torneo-clausura-2011$", 2011)],
                                 "2011-12": [("arg.1", r"^torneo-apertura-2011$", 2011),
                                             ("arg.1", r"^torneo-clausura-2012$", 2012)]},
                   "descensos": "promedios", "descienden": 3,
                   "cupos": {"anio": 2013, "fijos": True,
                             "sudamericana": [("Campeón de la temporada 2012-13 (Superfinal)", "velez-sarsfield"),
                                              ("Tabla de la temporada 2012-13", "lanus"),
                                              ("Tabla de la temporada 2012-13", "river-plate"),
                                              ("Tabla de la temporada 2012-13", "racing-club"),
                                              ("Tabla de la temporada 2012-13", "belgrano"),
                                              ("Tabla de la temporada 2012-13", "san-lorenzo")]}},
    # El Torneo Inicial 2013 (agosto-diciembre; campeón San Lorenzo) abría la temporada 2013-14: los descensos se
    # definieron al terminarla, con el Torneo Final 2014. Los cupos de la Libertadores 2014, fijos
    "2013-inicial": {"nombre": "Torneo Inicial 2013", "anio": 2013, "slug": "inicial-2013",
                     "patron": r"^torneo-inicial-2013$", "zonas": "unica", "fechas": 19, "pasan": 0,
                     "campeon_tabla": True,
                     "anual_texto": "La tabla del Torneo Inicial 2013, la primera mitad de la temporada 2013-14 (la "
                                    "tabla de la temporada completa está en el Torneo Final 2014).",
                     "sin_descensos": "En el Torneo Inicial 2013 no hubo descensos: se definieron al terminar la "
                                      "temporada 2013-14, con el Torneo Final 2014.",
                     "cupos": {"anio": 2014, "fijos": True,
                               "libertadores": [("Campeón de la temporada 2012-13 (Superfinal)", "velez-sarsfield"),
                                                ("Campeón del Torneo Final 2013", "newell-s-old-boys"),
                                                ("Campeón del Torneo Inicial 2013", "san-lorenzo"),
                                                ("Campeón de la Copa Argentina 2012-13", "arsenal-de-sarandi"),
                                                ("Campeón de la Copa Sudamericana 2013", "lanus")]}},
    # 2014: dos torneos de 20 equipos a una rueda, sin playoffs. El Torneo Final 2014 (febrero-mayo; campeón River)
    # cerraba la temporada 2013-14: su "tabla anual" es la de la temporada (el Inicial 2013 y el Final 2014). Bajaron
    # los tres últimos de los promedios (2011-12, 2012-13 y 2013-14); Colón y Atlético de Rafaela empataron en el
    # lugar del descenso y jugaron un desempate ("desempate"; ganó Rafaela). Después, la Copa Campeonato 2013-14: el
    # campeón del Inicial (San Lorenzo) contra el del Final (River). Los cupos de la Sudamericana 2014, fijos
    "2014-final": {"nombre": "Torneo Final 2014", "anio": 2014, "slug": "final-2014",
                   "patron": r"^torneo-final-2014($|---)", "zonas": "unica", "fechas": 19, "pasan": 0,
                   "campeon_tabla": True, "temporada": "2013-14", "nombre_anual": "Temporada y copas",
                   "nombre_playoffs": "Copa Campeonato",
                   "playoffs": [(r"---final$", "Copa Campeonato 2013-14")], "desempate": r"---promocion$",
                   "desempate_texto": "Colón y Atlético de Rafaela terminaron empatados en los promedios, en el último "
                                      "lugar del descenso: lo definieron en un partido, en cancha de Colón. Bajó el que "
                                      "perdió.",
                   "cuadro": {"bloques": [("Copa Campeonato 2013-14: el campeón del Inicial 2013 contra el del Final 2014",
                                           [["Copa Campeonato 2013-14"]])]},
                   "anual": [("arg.1", r"^torneo-inicial-2013$", 2013)],
                   "anual_texto": "La tabla de la temporada 2013-14: suma el Torneo Inicial 2013 y el Torneo Final 2014.",
                   "promedios": {"2011-12": [("arg.1", r"^torneo-apertura-2011$", 2011),
                                             ("arg.1", r"^torneo-clausura-2012$", 2012)],
                                 "2012-13": [("arg.1", r"^torneo-inicial-2012$", 2012),
                                             ("arg.1", r"^torneo-inicial-2012$", 2013),
                                             ("arg.1", r"^torneo-final-2013$", 2013)]},
                   "descensos": "promedios", "descienden": 3,
                   "cupos": {"anio": 2014, "fijos": True,
                             "sudamericana": [("Campeón de la Copa Sudamericana 2013 (lugar aparte)", "lanus"),
                                              ("Campeón de la Copa Campeonato 2013-14", "river-plate"),
                                              ("Tabla de la temporada 2013-14", "boca-juniors"),
                                              ("Tabla de la temporada 2013-14", "estudiantes-de-la-plata"),
                                              ("Tabla de la temporada 2013-14", "gimnasia-y-esgrima"),
                                              ("Tabla de la temporada 2013-14", "godoy-cruz"),
                                              ("Tabla de la temporada 2013-14", "rosario-central")]}},
    # El Torneo de Transición 2014 (agosto-diciembre; campeón Racing): sin descensos (en 2015 la liga pasó a 30). La
    # tabla anual 2014 (el Final y el Transición) daba cupos de las copas 2015. Boca y Vélez empataron arriba de todo en
    # la tabla de la temporada 2013-14, que daba un lugar en la Libertadores 2015, y jugaron un desempate en enero de 2015
    # (en ESPN, con este torneo, en el calendario de 2015). Los cupos, fijos
    "2014-transicion": {"nombre": "Torneo de Transición 2014", "anio": 2014, "anios": [2014, 2015],
                        "slug": "transicion-2014", "patron": r"^torneo-de-primera-division-2014(-playoff)?$",
                        "zonas": "unica", "fechas": 19, "pasan": 0, "campeon_tabla": True, "desempate": r"-playoff$",
                        "desempate_texto": "Boca y Vélez terminaron empatados en el primer puesto de la tabla de la "
                                           "temporada 2013-14 (el Inicial 2013 y el Final 2014, 61 puntos cada uno), que "
                                           "daba un lugar en la Copa Libertadores 2015: lo definieron en un partido en Mar "
                                           "del Plata, en enero de 2015.",
                        "anual": [("arg.1", r"^torneo-final-2014$")],
                        "anual_texto": "Suma el Torneo Final 2014 y el Torneo de Transición 2014.",
                        "sin_descensos": "En el Torneo de Transición 2014 no hubo descensos: en 2015 la liga pasó a tener "
                                         "30 equipos.",
                        "cupos": {"anio": 2015, "fijos": True,
                                  "libertadores": [("Campeón de la Copa Libertadores 2014 (lugar aparte)", "san-lorenzo"),
                                                   ("Campeón del Torneo Final 2014", "river-plate"),
                                                   ("Campeón del Torneo de Transición 2014", "racing-club"),
                                                   ("Campeón de la Copa Argentina 2014", "huracan"),
                                                   ("Tabla anual 2014", "estudiantes-de-la-plata"),
                                                   ("Mejor de la temporada 2013-14 (desempate con Vélez)", "boca-juniors")],
                                  "sudamericana": [("Campeón de la Copa Sudamericana 2014 (lugar aparte)", "river-plate"),
                                                   ("Campeón de la Supercopa Argentina 2014", "huracan"),
                                                   ("Tabla anual 2014", "lanus"), ("Tabla anual 2014", "independiente"),
                                                   ("Tabla anual 2014", "tigre"),
                                                   ("Tabla anual 2014", "arsenal-de-sarandi"),
                                                   ("Tabla anual 2014", "belgrano")]}},
    # 2015: el Campeonato 2015 (febrero-noviembre, una sola tabla de 30, 30 fechas con la de clásicos; campeón Boca).
    # Después, dos liguillas ("playoffs"): la Pre-Libertadores (del 4º al 7º: semifinales a un partido y final a ida y
    # vuelta; ganó Racing) y la Pre-Sudamericana (primera ronda a un partido y una segunda a ida y vuelta, con los dos
    # que perdieron la semifinal de la Pre-Libertadores). Los cupos 2016 no siguen la regla de los otros años (el campeón
    # de la Sudamericana argentino mejor ubicado, la liguilla...): van fijos ("fijos"), como los publicó la AFA. Bajaron
    # los dos últimos de los promedios (2012-13, 2013-14, 2014 y 2015): Nueva Chicago y Crucero del Norte
    "2015-primera": {"nombre": "Campeonato 2015", "anio": 2015, "slug": "primera-2015",
                     "patron": r"^campeonato-de-1ra-division-2015$|^pre-", "zonas": "unica", "fechas": 30, "pasan": 0,
                     "campeon_tabla": True, "nombre_playoffs": "Liguillas",
                     "playoffs": [(r"^pre-libertadores-semifinals$", "Pre-Libertadores: semifinales"),
                                  (r"^pre-libertadores-final$", "Pre-Libertadores: final"),
                                  (r"^pre-sudamericana-semifinals$", "Pre-Sudamericana: primera ronda"),
                                  (r"^pre-sudamericana-finals$", "Pre-Sudamericana: segunda ronda")],
                     "ida_y_vuelta": True,
                     "cuadro": {"bloques": [("Liguilla Pre-Libertadores (del 4º al 7º de la tabla)",
                                             [["Pre-Libertadores: semifinales"], ["Pre-Libertadores: final"]])],
                                "nota": "El ganador fue a la Copa Libertadores 2016; los otros tres, a la liguilla "
                                        "Pre-Sudamericana (los que perdieron las semifinales, directo a la segunda ronda; "
                                        "Independiente, a la Sudamericana 2016). En la Pre-Sudamericana, los 4 ganadores de "
                                        "la segunda ronda fueron a la Sudamericana 2016: sus partidos, abajo."},
                     "anual_texto": "La tabla del Campeonato 2015 (no había tabla anual: la temporada era un solo torneo; "
                                    "las liguillas no suman).",
                     "promedios": {"2012-13": [("arg.1", r"^torneo-inicial-2012$", 2012), ("arg.1", r"^torneo-inicial-2012$", 2013),
                                               ("arg.1", r"^torneo-final-2013$", 2013)],
                                   "2013-14": [("arg.1", r"^torneo-inicial-2013$", 2013), ("arg.1", r"^torneo-final-2014$", 2014)],
                                   "2014": [("arg.1", r"^torneo-de-primera-division-2014$", 2014)]},
                     "descensos": "promedios", "descienden": 2,
                     "cupos": {"anio": 2016, "fijos": True,
                               "libertadores": [("Campeón de la Copa Libertadores 2015 (lugar aparte)", "river-plate"),
                                                ("Campeón del Campeonato 2015 (y de la Copa Argentina)", "boca-juniors"),
                                                ("Subcampeón del Campeonato 2015", "san-lorenzo"),
                                                ("Subcampeón de la Copa Argentina 2015 (la ganó Boca)", "rosario-central"),
                                                ("Ganador de la liguilla Pre-Libertadores", "racing-club"),
                                                ("Mejor argentino en la Copa Sudamericana 2015 (fue finalista)", "huracan")],
                               "sudamericana": [("Finalista de la liguilla Pre-Libertadores", "independiente"),
                                                ("Liguilla Pre-Sudamericana", "belgrano"),
                                                ("Liguilla Pre-Sudamericana", "estudiantes-de-la-plata"),
                                                ("Liguilla Pre-Sudamericana", "lanus"),
                                                ("Liguilla Pre-Sudamericana", "banfield")]}},
    # 2016: el Campeonato 2016 (febrero-mayo, de transición: dos zonas de 15, 14 partidos en la zona y 2 interzonales
    # contra el rival clásico; campeón Lanús, que le ganó la final a San Lorenzo). Los segundos de cada zona jugaron por
    # el tercer puesto. ESPN tiene esos dos partidos en la fase regular: van por su id ("playoffs_ids"); las zonas, del
    # grupo de cada partido ("grupos"). Bajó uno solo, el último de los promedios (2013-14, 2014, 2015 y 2016):
    # Argentinos. Cupos 2017 con la tabla general (las dos zonas juntas): a la Libertadores, el campeón, el de la Copa
    # Argentina 2016 (River) y los 4 mejores; a la Sudamericana, los 6 siguientes
    "2016-primera": {"nombre": "Campeonato 2016", "anio": 2016, "slug": "primera-2016",
                     "patron": r"^campeonato-de-1ra-division-2016$", "zonas": "grupos", "fechas": 16, "pasan": 1,
                     "texto_pasan": "El primero de cada zona juega la final",
                     "playoffs_ids": {"448810": "Final", "448823": "Por el tercer puesto"},
                     "cuadro": {"bloques": [("Final", [["Final"]]),
                                            ("Por el tercer puesto (entre los segundos de cada zona)", [["Por el tercer puesto"]])]},
                     "anual_texto": "La tabla general del Campeonato 2016: las dos zonas juntas (no había tabla anual).",
                     "promedios": {"2013-14": [("arg.1", r"^torneo-inicial-2013$", 2013), ("arg.1", r"^torneo-final-2014$", 2014)],
                                   "2014": [("arg.1", r"^torneo-de-primera-division-2014$", 2014)],
                                   "2015": [("arg.1", r"^campeonato-de-1ra-division-2015$", 2015)]},
                     "descensos": "promedios", "descienden": 1,
                     "cupos": {"anio": 2017, "libertadores": 6, "sudamericana": 6,
                               "campeones": [("Campeonato 2016", "arg.1", r"^campeonato-de-1ra-division-2016$", "final"),
                                             ("Copa Argentina 2016", "arg.copa", r"(^|-)final$")]}},
    # 2017: el Campeonato 2016-17 (septiembre de 2016 - junio de 2017, una sola tabla de 30; campeón Boca). Bajaron los
    # cuatro últimos de los promedios (2014, que es el Torneo de Transición, 2015, 2016 y 2016-17). Cupos 2018: a la
    # Libertadores, el campeón, el lugar de la Copa Argentina 2017 (la ganó River, que ya entraba por la tabla: el
    # reglamento se lo pasaba al subcampeón, Atlético Tucumán) y los 4 mejores de la tabla; Independiente, aparte, como
    # campeón de la Sudamericana 2017. Se juega en 2016 y 2017 en ESPN
    "2017-primera-16-17": {"nombre": "Campeonato 2016-17", "anio": 2017, "anios": [2016, 2017], "slug": "primera-16-17",
                           "patron": r"campeonato-de-1ra-division-20162017", "zonas": "unica", "fechas": 30, "pasan": 0,
                           "campeon_tabla": True, "temporada": "2016-17",
                           "anual_texto": "La tabla del Campeonato 2016-17 entero (no había tabla anual: la temporada era un "
                                          "solo torneo).",
                           "promedios": {"2014": [("arg.1", r"^torneo-de-primera-division-2014$", 2014)],
                                         "2015": [("arg.1", r"^campeonato-de-1ra-division-2015$", 2015)],
                                         "2016": [("arg.1", r"^campeonato-de-1ra-division-2016$", 2016)]},
                           "descensos": "promedios", "descienden": 4,
                           "cupos": {"anio": 2018, "libertadores": 6, "sudamericana": 6,
                                     "nota": "River ganó la Copa Argentina 2017, pero como ya entraba a la Libertadores por la "
                                             "tabla, su lugar fue para el subcampeón, Atlético Tucumán.",
                                     "campeones": [("Campeonato 2016-17", None, None),
                                                   ("Subcampeón de la Copa Argentina 2017", "arg.copa", r"(^|-)final$",
                                                    "perdedor"),
                                                   ("Copa Sudamericana 2017", "conmebol.sudamericana", r"(^|-)final$",
                                                    "extra")]}},
    # 2018: la Superliga 2017-18 (septiembre de 2017 - mayo de 2018, una sola tabla de 28; campeón Boca). Bajaron los
    # cuatro últimos de los promedios, que contaban cuatro temporadas: 2015, 2016 (el torneo corto, sin la final),
    # 2016-17 y 2017-18 (la liga pasaba de 28 a 26). Cupos 2019: los campeones de la Superliga y de la Copa Argentina
    # 2018 y los 4 mejores de la tabla a la Libertadores; River, aparte, como campeón de la Libertadores 2018. La
    # Superliga 2018-19, que empezó en agosto de 2018, está en 2019
    "2018-superliga-17-18": {"nombre": "Superliga 2017-18", "anio": 2018, "anios": [2017, 2018], "slug": "superliga-17-18",
                             "patron": r"superliga-argentina-2017-18", "zonas": "unica", "fechas": 27, "pasan": 0,
                             "campeon_tabla": True, "temporada": "2017-18",
                             "anual_texto": "La tabla de la Superliga 2017-18 entera (no había tabla anual: la temporada era un "
                                            "solo torneo).",
                             "promedios": {"2015": [("arg.1", r"^campeonato-de-1ra-division-2015$", 2015)],
                                           "2016": [("arg.1", r"^campeonato-de-1ra-division-2016$", 2016)],
                                           "2016-17": [("arg.1", r"campeonato-de-1ra-division-20162017", 2016),
                                                       ("arg.1", r"campeonato-de-1ra-division-20162017", 2017)]},
                             "descensos": "promedios", "descienden": 4,
                             "cupos": {"anio": 2019, "libertadores": 6, "sudamericana": 6,
                                       "campeones": [("Superliga 2017-18", None, None),
                                                     ("Copa Argentina 2018", "arg.copa", r"(^|-)final$"),
                                                     ("Copa Libertadores 2018", "conmebol.libertadores", r"^finals$", "extra")]}},
    # 2019 (y lo que se jugó de esas temporadas en 2018 y 2020): la Superliga 2018-19 (agosto de 2018 - abril de 2019,
    # una sola tabla de 26; campeón Racing), la Copa de la Superliga 2019 (abril-junio, eliminación directa a ida y
    # vuelta; campeón Tigre) y la Superliga 2019-20 (julio de 2019 - marzo de 2020, una sola tabla de 24; campeón Boca).
    # "temporada": cómo se llama la temporada en los promedios (en vez del año)
    # Superliga 2018-19: descendieron los cuatro últimos de los promedios (2016-17, 2017-18 y 2018-19; la liga pasaba
    # de 26 a 24). No había tabla anual: los cupos para las copas 2020 salían de la tabla de la Superliga, más los
    # campeones de la Copa de la Superliga y de la Copa Argentina (Tigre fue a la Libertadores aunque descendió)
    "2019-superliga-18-19": {"nombre": "Superliga 2018-19", "anio": 2019, "anios": [2018, 2019], "slug": "superliga-18-19",
                             "patron": r"superliga-argentina-2018-19", "zonas": "unica", "fechas": 25, "pasan": 0,
                             "campeon_tabla": True, "temporada": "2018-19",
                             "anual_texto": "La tabla de la Superliga 2018-19 entera (no había tabla anual: la temporada era un "
                                            "solo torneo; la Copa de la Superliga no sumaba).",
                             "promedios": {"2016-17": [("arg.1", r"campeonato-de-1ra-division-20162017", 2016),
                                                       ("arg.1", r"campeonato-de-1ra-division-20162017", 2017)],
                                           "2017-18": [("arg.1", r"superliga-argentina-2017-18", 2017),
                                                       ("arg.1", r"superliga-argentina-2017-18", 2018)]},
                             "descensos": "promedios", "descienden": 4,
                             "cupos": {"anio": 2020, "libertadores": 6, "sudamericana": 6,
                                       # la Copa de la Superliga daba un lugar en la Sudamericana al mejor ubicado
                                       # en ella que no tuviera lugar: Argentinos (semifinalista; el otro, Atlético
                                       # Tucumán, ya iba a la Libertadores)
                                       "sudamericana_titulos": [("Mejor ubicado en la Copa de la Superliga 2019",
                                                                 "argentinos-juniors")],
                                       "campeones": [("Superliga 2018-19", None, None),
                                                     ("Copa de la Superliga 2019", "arg.copa_de_la_superliga", r"^final$"),
                                                     ("Copa Argentina 2019", "arg.copa", r"(^|-)final$")]}},
    # Copa de la Superliga 2019: sin fase regular ("copa"). Los 20 de abajo de la Superliga (7º a 26º) jugaron la
    # primera ronda y los 6 primeros entraron en octavos; todo a ida y vuelta (con gol de visitante y penales) menos la
    # final, en Córdoba. El cuadro arranca en octavos ("cuadro_desde")
    "2019-copa-superliga": {"nombre": "Copa de la Superliga 2019", "anio": 2019, "liga": "arg.copa_de_la_superliga",
                            "slug": "copa-superliga", "patron": r"", "copa": True, "fechas": 0, "pasan": 0,
                            "playoffs": [(r"^first-round$", "Primera ronda"), (r"^round-of-16$", "Octavos de final"),
                                         (r"^quarterfinals$", "Cuartos de final"), (r"^semifinals$", "Semifinales"),
                                         (r"^final$", "Final")],
                            "ida_y_vuelta": True, "gol_visitante": True, "cuadro_desde": "Octavos de final",
                            "nota": "La Copa de la Superliga se jugó después de la Superliga 2018-19, por eliminación directa. "
                                    "Los equipos del 7º al 26º puesto de la Superliga jugaron la primera ronda; los 6 primeros "
                                    "entraron directo en octavos. Todas las series fueron a ida y vuelta (si quedaban iguales en "
                                    "el global, pasaba el que había hecho más goles de visitante y, si seguían iguales, se "
                                    "definían por penales), menos la final, a un partido en Córdoba. El campeón fue a la "
                                    "Copa Libertadores 2020."},
    # Superliga 2019-20: los descensos se anularon (la Copa de la Superliga 2020 se canceló por la pandemia). Los
    # cupos para las copas 2021 se definieron junto con la Copa Diego Maradona: no se cargan
    "2019-superliga-19-20": {"nombre": "Superliga 2019-20", "anio": 2019, "anios": [2019, 2020], "slug": "superliga-19-20",
                             "patron": r"superliga-argentina-2019-20", "zonas": "unica", "fechas": 23, "pasan": 0,
                             "campeon_tabla": True, "temporada": "2019-20",
                             "promedios": {"2017-18": [("arg.1", r"superliga-argentina-2017-18", 2017),
                                                       ("arg.1", r"superliga-argentina-2017-18", 2018)],
                                           "2018-19": [("arg.1", r"superliga-argentina-2018-19", 2018),
                                                       ("arg.1", r"superliga-argentina-2018-19", 2019)]},
                             "sin_descensos": "En la temporada 2019-20 no hubo descensos: la Copa de la Superliga 2020 se "
                                              "canceló por la pandemia después de una fecha y la AFA anuló los descensos."},
    # 2020: el único torneo fue la Copa Diego Maradona (octubre de 2020 - marzo de 2021; en ESPN, dentro de "arg.1" de
    # 2020 y de 2021). Por etapas: la primera fase (6 zonas de 4, ida y vuelta; pasaban los 2 primeros) y la segunda,
    # partida en la Fase Campeón (2 zonas de 6 con los clasificados; los ganadores jugaron la final) y la Fase
    # Complementación (2 zonas de 6 con el resto). Además, la final de la Complementación y un repechaje por un lugar en
    # la Sudamericana 2021. Sin descensos (suspendidos por la pandemia). La Copa de la Superliga 2020 (una sola fecha,
    # se canceló) no se carga
    "2020-maradona": {"nombre": "Copa Diego Maradona 2020", "anio": 2020, "anios": [2020, 2021], "slug": "maradona",
                      "patron": r"copa-diego-armando-maradona",
                      # etapas: (nombre, patrón de la fase en ESPN, cuántos pasan por zona, primera fecha, cuántas
                      # fechas). La Fase Campeón y la Complementación se jugaron en las mismas fechas (7 a 11)
                      "etapas": [("Primera fase", r"group-stage$", 2, 1, 6), ("Fase Campeón", r"fase-campeon$", 1, 7, 5),
                                 ("Fase Complementación", r"fase-complementacion$", 1, 7, 5)],
                      "playoffs": [(r"fase-complementacion-final$", "Final de la Fase Complementación"),
                                   (r"fase-campeon-final$", "Final"),
                                   (r"copa-sudamericana-playoff$", "Repechaje por la Copa Sudamericana")],
                      "fechas": 11, "pasan": 0,
                      # el cuadro no es una eliminación directa común: va en dos partes ("bloques", cada uno con sus
                      # columnas de rondas): la final del torneo, sola, y el camino al lugar en la Sudamericana (la final
                      # de la Complementación y el repechaje, al que fueron su ganador y el subcampeón del torneo)
                      "cuadro": {"bloques": [("Final del torneo", [["Final"]]),
                                             ("Por un lugar en la Copa Sudamericana 2021",
                                              [["Final de la Fase Complementación"], ["Repechaje por la Copa Sudamericana"]])],
                                 "nota": "Al repechaje por un lugar en la Copa Sudamericana 2021 fueron el ganador de la final "
                                         "de la Fase Complementación y el subcampeón del torneo (el que perdió la final)."},
                      "nota": "En 2020 hubo un solo torneo, la Copa Diego Maradona, que empezó en octubre por la pandemia. En la "
                              "primera fase pasaban los dos primeros de cada zona a la Fase Campeón (los ganadores de sus dos "
                              "zonas jugaron la final); el resto jugó la Fase Complementación. Los ganadores de sus dos zonas jugaron otra "
                              "final y el que la ganó "
                              "jugó un repechaje por un lugar en la Sudamericana 2021 contra el subcampeón del torneo.",
                      "sin_descensos": "En 2020 no hubo descensos: la AFA los suspendió por la pandemia."},
    # 2021: la Copa de la Liga (febrero-junio, dos zonas de 13, desde cuartos; campeón Colón) y la Liga Profesional
    # (julio-diciembre, una sola tabla de 26, 25 fechas; campeón River). Sin descensos (la AFA los suspendió en 2020 y
    # 2021 por la pandemia: "sin_descensos"). La tabla anual (Copa y Liga) daba los cupos para las copas 2022
    "2021-copa": {"nombre": "Copa de la Liga 2021", "anio": 2021, "liga": "arg.copa_lpf", "slug": "copa", "patron": r"",
                  "fechas": 13, "pasan": 4},
    "2021-liga": {"nombre": "Liga Profesional 2021", "anio": 2021, "slug": "liga", "patron": r"liga-profesional",
                  "zonas": "unica", "fechas": 25, "pasan": 0, "campeon_tabla": True,
                  "anual": [("arg.copa_lpf", r"^group-stage$")],
                  "anual_texto": "Suma la fase de zonas de la Copa de la Liga 2021 y la Liga Profesional 2021.",
                  "sin_descensos": "En 2021 no hubo descensos: la AFA los suspendió en 2020 y 2021 por la pandemia.",
                  # a la Sudamericana 2022 fue también el subcampeón de la Copa Diego Maradona 2020-21 (Banfield): uno
                  # de los 6 lugares; los otros 5, de la tabla anual
                  "cupos": {"anio": 2022, "libertadores": 6, "sudamericana": 6,
                            "sudamericana_titulos": [("Subcampeón de la Copa Diego Maradona", "arg.1",
                                                      r"copa-diego-armando-maradona---fase-campeon-final", "perdedor")],
                            "campeones": [("Copa de la Liga 2021", "arg.copa_lpf", r"^final$"),
                                          ("Liga Profesional 2021", None, None),
                                          ("Copa Argentina 2021", "arg.copa", r"(^|-)final$")]}},
    # 2022: la Copa de la Liga (febrero-mayo, dos zonas de 14, desde cuartos) y la Liga Profesional (junio-octubre, una
    # sola tabla de 28); Boca ganó las dos. Descendieron los dos últimos de los promedios (Aldosivi y Patronato; no había
    # descenso por tabla anual: "descensos": "promedios"). Los promedios contaban 2019-20 (la Superliga y la única fecha
    # que se jugó de la Copa de la Superliga 2020, que ESPN no tiene: va en PARTIDOS_A_MANO), 2021 y 2022. La tabla anual
    # (Copa y Liga) daba los cupos; Patronato fue a la Libertadores 2023 como campeón de la Copa Argentina aunque descendió
    # (los campeones juegan igual: solo se saltean los descendidos en los lugares de la tabla)
    "2022-copa": {"nombre": "Copa de la Liga 2022", "anio": 2022, "liga": "arg.copa_lpf", "slug": "copa", "patron": r"",
                  "fechas": 14, "pasan": 4},
    "2022-liga": {"nombre": "Liga Profesional 2022", "anio": 2022, "slug": "liga", "patron": r"liga-profesional",
                  "zonas": "unica", "fechas": 27, "pasan": 0, "campeon_tabla": True,
                  "anual": [("arg.copa_lpf", r"^group-stage$")],
                  "anual_texto": "Suma la fase de zonas de la Copa de la Liga 2022 y la Liga Profesional 2022.",
                  "promedios": {"2019-20": [("arg.1", r"superliga-argentina-2019-20", 2019),
                                            ("arg.1", r"superliga-argentina-2019-20", 2020),
                                            ("arg.copa_superliga", r"", 2020)],
                                2021: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")]},
                  "descensos": "promedios",
                  "cupos": {"anio": 2023, "libertadores": 6, "sudamericana": 6,
                            "campeones": [("Copa de la Liga 2022", "arg.copa_lpf", r"^final$"),
                                          ("Liga Profesional 2022", None, None),
                                          ("Copa Argentina 2022", "arg.copa", r"(^|-)final$")]}},
    # 2023: al revés que en 2024, primero la Liga Profesional (enero-julio, una sola tabla de 28, campeón River) y
    # después la Copa de la Liga (octubre-diciembre, dos zonas de 14, desde cuartos de final; campeón Rosario Central).
    # La tabla anual sumó la Liga y la fase de zonas de la Copa; los promedios, 2021, 2022 y 2023. Descendieron Arsenal
    # (último en las dos tablas: por promedios) y Colón, que empató en puntos con Gimnasia en el anteúltimo lugar de la
    # tabla anual y perdió el desempate ("desempate": el partido; el que pierde es el que baja)
    "2023-liga": {"nombre": "Liga Profesional 2023", "anio": 2023, "slug": "liga", "patron": r"liga-profesional",
                  "zonas": "unica", "fechas": 27, "pasan": 0, "campeon_tabla": True},
    "2023-copa": {"nombre": "Copa de la Liga 2023", "anio": 2023, "liga": "arg.copa_lpf", "slug": "copa", "patron": r"",
                  "fechas": 14, "pasan": 4, "desempate": r"^relegation$",
                  "anual": [("arg.1", r"liga-profesional")],
                  "anual_texto": "Suma la Liga Profesional 2023 y la fase de zonas de la Copa de la Liga 2023.",
                  "promedios": {2021: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")],
                                2022: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")]},
                  "descensos": True,
                  "cupos": {"anio": 2024, "libertadores": 6, "sudamericana": 6,
                            # "tabla": el campeón es el primero de la tabla de ese torneo
                            "campeones": [("Liga Profesional 2023", "arg.1", r"liga-profesional", "tabla"),
                                          ("Copa de la Liga 2023", "arg.copa_lpf", r"^final$"),
                                          ("Copa Argentina 2023", "arg.copa", r"(^|-)final$")]}},
    # 2024: la Copa de la Liga (enero-mayo, dos zonas de 14 y desde cuartos de final; en ESPN es otra liga,
    # "arg.copa_lpf") y la Liga Profesional (mayo-diciembre, todos contra todos a una rueda, sin playoffs: el campeón
    # es el primero de la tabla). La tabla anual sumó la fase de zonas de la Copa de la Liga y la Liga entera.
    # Descensos: no hubo (la AFA los anuló en diciembre de 2024). Racing fue a la Libertadores 2025 por ganar la
    # Sudamericana 2024: un lugar aparte
    "2024-copa": {"nombre": "Copa de la Liga 2024", "anio": 2024, "liga": "arg.copa_lpf", "slug": "copa", "patron": r"",
                  "fechas": 14, "pasan": 4},
    "2024-liga": {"nombre": "Liga Profesional 2024", "anio": 2024, "slug": "liga", "patron": r"liga-profesional",
                  "zonas": "unica", "fechas": 27, "pasan": 0, "campeon_tabla": True,
                  "anual": [("arg.copa_lpf", r"^group-stage$")],
                  "anual_texto": "Suma la fase de zonas de la Copa de la Liga 2024 y la Liga Profesional 2024.",
                  "promedios": {2022: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")],
                                2023: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")]},
                  "descensos": False,
                  "descensos_anulados": "En 2024 no hubo descensos: la AFA los anuló en diciembre, cuando decidió que en 2025 la "
                                        "Liga tuviera 30 equipos.",
                  "cupos": {"anio": 2025, "libertadores": 6, "sudamericana": 6,
                            "campeones": [("Copa de la Liga 2024", "arg.copa_lpf", r"^final$"),
                                          ("Liga Profesional 2024", None, None),   # (el primero de la tabla: lo calcula la página)
                                          ("Copa Argentina 2024", "arg.copa", r"(^|-)final$"),
                                          ("Copa Sudamericana 2024", "conmebol.sudamericana", r"(^|-)final$", "extra")]}},
    # 2025: igual que 2026 (dos torneos con zonas, tabla anual, promedios y cupos). Los promedios de 2025 son
    # 2023 (Copa de la Liga y Liga Profesional), 2024 y 2025. Descendieron Godoy Cruz (tabla anual) y San Martín de
    # San Juan (promedios). Lanús fue a la Libertadores 2026 por ganar la Sudamericana 2025: un lugar aparte ("extra")
    "2025-apertura": {"nombre": "Torneo Apertura 2025", "anio": 2025, "slug": "apertura", "fechas": 16, "pasan": 8,
                      "zonas_de": "clausura"},
    "2025-clausura": {"nombre": "Torneo Clausura 2025", "anio": 2025, "slug": "clausura", "fechas": 16, "pasan": 8,
                      "anual": [("arg.1", r"^torneo-apertura$")],
                      "promedios": {2023: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")],
                                    2024: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")]},
                      "descensos": True,
                      # en noviembre de 2025 la AFA le dio un título al primero de la tabla anual
                      "titulo_anual": "Campeón de Liga 2025",
                      "cupos": {"anio": 2026, "libertadores": 6, "sudamericana": 6,
                                "campeones": [("Torneo Apertura 2025", "arg.1", r"^apertura---final$"),
                                              ("Torneo Clausura 2025", "arg.1", r"^clausura---final$"),
                                              ("Copa Argentina 2025", "arg.copa", r"(^|-)final$"),
                                              ("Copa Sudamericana 2025", "conmebol.sudamericana", r"(^|-)final$", "extra")]}},
    # Las zonas del Apertura 2026 fueron las mismas que las del Clausura (la tabla de ESPN ya muestra solo las del
    # Clausura): "zonas_de" usa las de ese torneo. armar() controla que cada club tenga 2 partidos interzonales
    "2026-apertura": {"nombre": "Torneo Apertura 2026", "anio": 2026, "slug": "apertura", "fechas": 16, "pasan": 8,
                      "zonas_de": "clausura"},
    "2026-clausura": {"nombre": "Torneo Clausura 2026", "anio": 2026, "slug": "clausura", "fechas": 16,
                      "pasan": 8,   # los 8 primeros de cada zona juegan los octavos de final
                      # La tabla anual suma la fase de zonas del Apertura y del Clausura (sin playoffs): acá, lo que
                      # se jugó antes de este torneo en el año. La página le suma este torneo
                      "anual": [("arg.1", r"^torneo-apertura$")],
                      # Los promedios: puntos dividido partidos de las tres últimas temporadas (fases regulares;
                      # los recién ascendidos, solo los partidos que jugaron en Primera). Acá, las temporadas
                      # anteriores; la del año es la tabla anual
                      "promedios": {2024: [("arg.copa_lpf", r"^group-stage$"), ("arg.1", r"liga-profesional")],
                                    2025: [("arg.1", r"^torneo-(apertura|clausura)$")]},
                      # Descienden el último de la tabla anual y el peor promedio (si es el mismo club, el
                      # anteúltimo de la tabla anual)
                      "descensos": True,
                      # Cupos para las copas del año que viene (reglamento de la AFA, marzo de 2026): a la Libertadores
                      # van los tres campeones del año y los mejores de la tabla anual hasta completar 6; a la
                      # Sudamericana, los 6 siguientes. Si un campeón ya entra por la tabla, su lugar pasa al
                      # siguiente; los que descienden no juegan copas. Los campeones salen de la final de ESPN
                      "cupos": {"anio": 2027, "libertadores": 6, "sudamericana": 6,
                                "campeones": [("Torneo Apertura 2026", "arg.1", r"^apertura---final$"),
                                              ("Torneo Clausura 2026", "arg.1", r"^clausura---final$"),
                                              ("Copa Argentina 2026", "arg.copa", r"(^|-)final$")]}},
}
# Partidos que ESPN no tiene, cargados a mano: {(liga, año): [(id ESPN local, id ESPN visitante, goles, goles)]}.
# La Copa de la Superliga 2020: solo se jugó la primera fecha (marzo de 2020; Defensa-Estudiantes, en diciembre) antes de
# que se cancelara por la pandemia; cuenta para los promedios de 2022. River-Atlético Tucumán no se jugó: se le dio
# ganado 1-0 a Atlético Tucumán. Fuente: Wikipedia, "Copa de la Superliga 2020"
PARTIDOS_A_MANO = {
    ("arg.copa_superliga", 2020): [("9", "235", 0, 0), ("10374", "18", 1, 3), ("11", "21", 1, 0), ("6756", "5", 1, 4),
                                   ("20", "2635", 1, 1), ("11989", "14", 1, 2), ("16", "9785", 0, 1), ("10", "19", 0, 3),
                                   ("9739", "15", 3, 4), ("12", "3", 0, 1), ("17", "7", 1, 3), ("8950", "8", 2, 1)],
}
# Definiciones por penales que ESPN no tiene: {id del partido de ESPN: (penales del local, del visitante)}. Copa de la
# Superliga 2019, vueltas de la primera ronda (Wikipedia, Ámbito)
PENALES_A_MANO = {"540170": (3, 4), "540167": (3, 2), "540166": (5, 4)}
# Goles que ESPN no tiene: {id del partido de ESPN: [gol, ...]}. Aldosivi 2-1 Huracán (Superliga 2018-19): el gol en
# contra de Saúl Salcedo, a los 17 del segundo tiempo (La Voz de San Justo)
# Banfield 2-3 Defensa y Justicia (Transición 2014): los tres de Defensa (ESPN Deportes, la crónica del partido)
GOLES_A_MANO = {"521397": [{"jugador": "Saúl Salcedo", "min": 62, "tipo": "ec", "equipo": "local"}],
                "399497": [{"jugador": "Emiliano Tellechea", "min": 14, "equipo": "visitante"},
                           {"jugador": "Brian Fernández", "min": 67, "equipo": "visitante"},
                           {"jugador": "Gaspar Servio", "min": 83, "tipo": "ec", "equipo": "visitante"}],
                # Newell's 3-0 Racing (Apertura 2008): el segundo, de Hernán Bernardello (Página/12)
                "246119": [{"jugador": "Hernán Bernardello", "min": 87, "equipo": "local"}],
                # San Lorenzo 1-1 Instituto (Clausura 2006): el de San Lorenzo, de Leonardo Ulloa (La Nueva)
                "194020": [{"jugador": "Leonardo Ulloa", "min": 53, "equipo": "local"}],
                # Argentinos 1-2 Quilmes (Apertura 2005): los dos de Quilmes, de penal, de Miguel Caneo en el segundo
                # tiempo (La Nueva; sin los minutos)
                "187644": [{"jugador": "Miguel Caneo", "tipo": "pen", "equipo": "visitante"},
                           {"jugador": "Miguel Caneo", "tipo": "pen", "equipo": "visitante"}],
                # Nueva Chicago 2-2 River (Clausura 2004): los dos de River (Estadísticas de River Plate)
                "139847": [{"jugador": "Fernando Cavenaghi", "min": 25, "equipo": "visitante"},
                           {"jugador": "José Sand", "min": 77, "equipo": "visitante"}]}
# Goles que ESPN tiene mal o incompletos y se reemplazan todos: {id del partido de ESPN: [gol, ...]}.
# Estudiantes 1-4 Independiente (Clausura 2004; ESPN dice 1-2: ver RESULTADOS_A_MANO) y Atlético de Rafaela 3-1 Rosario
# Central (Clausura 2004; ESPN tiene dos goles de Rafaela, con otros nombres). Historia de Independiente, Wikipedia
GOLES_CORREGIDOS = {"140001": [{"jugador": "Diego Colotto", "min": 49, "equipo": "local"},
                               {"jugador": "Daniel Quinteros", "tipo": "pen", "equipo": "visitante"},
                               {"jugador": "Cristian Giménez", "equipo": "visitante"},
                               {"jugador": "Cristian Giménez", "equipo": "visitante"},
                               {"jugador": "Hernán Losada", "equipo": "visitante"}],
                    "147694": [{"jugador": "Gustavo Semino", "min": 38, "equipo": "local"},
                               {"jugador": "Darío Gandín", "min": 43, "equipo": "local"},
                               {"jugador": "Horacio Carbonari", "min": 62, "equipo": "visitante"},
                               {"jugador": "Emanuel Villa", "min": 69, "equipo": "local"}]}
# Partidos que ESPN pone en la fase regular pero no la son (no suman en la tabla anual ni en los promedios): del
# torneo 2016, la final (Lanús-San Lorenzo) y el desempate por un lugar en las copas (Godoy Cruz-Estudiantes)
NO_SUMAN = {"448823", "448810"}
# Partidos que no se jugaron y la AFA dio por terminados con un resultado (ESPN los tiene como postergados): {id del
# partido de ESPN: (goles del local, del visitante, nota que se muestra en el partido)}. Colón-Atlético de Rafaela, Inicial 2013: Colón no se presentó y se
# le dio ganado 1-0 a Rafaela (Diario de Cuyo); cuenta para los promedios de 2016
RESULTADOS_A_MANO = {"382317": (0, 1, "No se jugó: Colón no se presentó y la AFA le dio el partido ganado 1-0 a "
                                       "Atlético de Rafaela"),
                     # Almagro 3-2 Boca, Clausura 2005: se suspendió a los 18 del segundo tiempo por incidentes y la AFA
                     # les dio el partido perdido a los dos (a Boca 3-2; a Almagro 0-2, ver PIERDEN_LOS_DOS)
                     "186468": (3, 2, "Suspendido por incidentes: la AFA les dio el partido perdido a los dos"),
                     # Estudiantes-Independiente, Clausura 2004: terminó 1-4 (ESPN dice 1-2)
                     "140001": (1, 4, None),
                     # Clausura 2003 (RSSSF): Huracán 1-3 Lanús (ESPN lo tiene al revés, 3-1); Unión 1-3 Nueva Chicago se
                     # suspendió al final y quedó el resultado; Huracán-Olimpo se suspendió a los 30 del segundo tiempo y
                     # los 15 minutos que faltaban se jugaron en noviembre (ganó Olimpo 1-0)
                     "98460": (1, 3, None),
                     "98487": (1, 3, "Se suspendió a los 42 del segundo tiempo por incidentes y quedó el resultado"),
                     "98549": (0, 1, "Se suspendió a los 30 del segundo tiempo por incidentes; los 15 minutos que "
                                     "faltaban se jugaron el 11 de noviembre")}
# Partidos que la AFA les dio perdidos a los dos: {id del partido de ESPN: (goles a favor, en contra) que se le cuentan
# al local}; al visitante se le cuenta el resultado. Almagro-Boca, Clausura 2005: a Almagro, 0-2
PIERDEN_LOS_DOS = {"186468": (0, 2)}
# Puntos descontados por sanciones: {(año, id de ESPN): puntos}. Se restan en la tabla anual (o de la temporada) de ese
# año, no en la del torneo. Colón, temporada 2013-14: 6 puntos que le quitó la FIFA por una deuda con el Atlante
# (Infobae); cuenta para los promedios y lo mandó al desempate con Rafaela
# Con un tercer elemento, el patrón de una fase: se resta solo en las sumas que la incluyen (Chacarita, temporada 2003-04:
# 3 puntos por los incidentes en el partido con Boca; se restan en la temporada, no en la tabla del año 2004)
# Los de 1999 (Colón; San Lorenzo, Vélez, Instituto y Belgrano), el Clausura 2000 (Boca y Lanús) y el Clausura 2001 (Los
# Andes) están en la tabla del torneo ("descuentos" en
# TORNEOS); acá, para la tabla que los suma (el año es el del torneo que muestra esa tabla: los del Apertura 1999, en
# la temporada 1999-00 del Clausura 2000)
# Puntos por partido ganado en los torneos que no daban 3 ({clave del torneo a mano: puntos}): el Clausura 1995 fue el
# último con 2 (se suman así también en la tabla del año 1995)
PUNTOS_VICTORIA = {"1995-clausura": 2}
DESCUENTOS = {(2014, "7"): 6, (2004, "6", r"^torneo-apertura-2003$"): 3, (2000, "5", r"^2000-clausura$"): 3,
              (2000, "12", r"^2000-clausura$"): 3, (2001, "lan", r"^2001-clausura$"): 3,
              (1999, "7", r"^1999-clausura$"): 3, (2000, "18", r"^1999-apertura$"): 3,
              (2000, "21", r"^1999-apertura$"): 3, (2000, "2975", r"^1999-apertura$"): 3,
              (2000, "4", r"^1999-apertura$"): 3}
PLAYOFFS = [("round-of-16", "Octavos de final"), ("quarter", "Cuartos de final"), ("semi", "Semifinales"),
            ("final", "Final")]
# Clubes que no están en data/equipos.js (no jugaron copas internacionales): id y nombre. Los demás se toman de ahí
CLUBES_NUEVOS = {
    "2975": ("instituto", "Instituto"),
    "11972": ("gimnasia-mendoza", "Gimnasia (Mendoza)"),
    "7845": ("san-martin-san-juan", "San Martín de San Juan"),
    "9739": ("aldosivi", "Aldosivi"),
    "10158": ("sarmiento", "Sarmiento"),
    "19685": ("estudiantes-rio-cuarto", "Estudiantes de Río Cuarto"),
    "17814": ("san-martin-tucuman", "San Martín de Tucumán"),
    "6": ("chacarita-juniors", "Chacarita Juniors"),
    "2636": ("olimpo", "Olimpo"),
    "10162": ("temperley", "Temperley"),
    "9747": ("atletico-rafaela", "Atlético de Rafaela"),
    "236": ("nueva-chicago", "Nueva Chicago"),
    "11958": ("crucero-del-norte", "Crucero del Norte"),
    "9786": ("all-boys", "All Boys"),
    "8713": ("san-martin-tucuman", "San Martín de Tucumán"),   # (el mismo club; ESPN le cambió el id)
    "5263": ("gimnasia-jujuy", "Gimnasia y Esgrima (Jujuy)"),
    "5262": ("tiro-federal", "Tiro Federal"),
    "2974": ("huracan-tres-arroyos", "Huracán de Tres Arroyos"),
    "2": ("almagro", "Almagro"),
    "smm": ("san-martin-mendoza", "San Martín (Mendoza)"),   # (no está en ESPN: solo jugó la Promoción 2003)
    "lan": ("los-andes", "Los Andes"),   # (no está en ESPN: 2000-01)
    "fco": ("ferro-carril-oeste", "Ferro Carril Oeste"),
    "des": ("deportivo-espanol", "Deportivo Español"),   # (no está en ESPN: 1997-98)
    "gyt": ("gimnasia-y-tiro", "Gimnasia y Tiro (Salta)"),   # (no está en ESPN: 1997-98)
    "dma": ("deportivo-mandiyu", "Deportivo Mandiyú"),   # (no está en ESPN: 1994-95)
    "hco": ("huracan-corrientes", "Huracán Corrientes"),   # (no está en ESPN: 1996-97)   # (no tiene id de ESPN: 1999-00)
    "ger": ("gimnasia-concepcion", "Gimnasia y Esgrima (Concepción del Uruguay)"),   # (no está en ESPN: Promoción 2002)
}

# Nombres que en la liga se confunden (en data/equipos.js están como en las copas)
NOMBRES = {"gimnasia-y-esgrima": "Gimnasia (La Plata)"}


def eventos_a_mano(clave):
    """Los partidos de un torneo que ESPN no tiene (2002), de tools/a_mano/liga-<clave>.json, con la forma de los de
    ESPN (los clubes, con su id de ESPN), para que el resto funcione igual. Cada uno lleva su fecha (_fecha_n) y el
    partido tal cual (_a_mano: día, hora, goles, nota)."""
    archivo = A_MANO / f"liga-{clave}.json"
    if not archivo.exists():
        return []
    espn_a_club, eq = catalogo()
    id_espn = {**{c: e for e, c in espn_a_club.items()}, **{c: e for e, (c, _) in CLUBES_NUEVOS.items()}}
    eventos = []
    for f in json.loads(archivo.read_text(encoding="utf-8"))["fechas"]:
        for i, p in enumerate(f["partidos"]):
            hora = datetime.datetime.strptime(f"{p['fecha']} {p.get('hora') or '15:00'}", "%Y-%m-%d %H:%M")
            eventos.append({
                "id": f"{clave}-{f['numero']}-{i + 1}", "date": (hora + datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%MZ"),
                "season": {"slug": clave}, "status": {"type": {"completed": True, "name": "STATUS_FULL_TIME"}},
                "competitions": [{"competitors": [
                    {"homeAway": lado, "team": {"id": id_espn[p[lado2]], "displayName": p[lado2]}, "score": p[g]}
                    for lado, lado2, g in (("home", "local", "gl"), ("away", "visitante", "gv"))],
                    "venue": {"fullName": p.get("estadio")}}],
                "_fecha_n": f["numero"], "_a_mano": p})
    return eventos


def hora_argentina(iso):
    return datetime.datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") - datetime.timedelta(hours=3)


def archivo_calendario(liga, anio):
    return CACHE / str(anio) / ("calendario.json" if liga == "arg.1" else f"calendario-{liga}.json")


def bajar(anio, slug, con_zonas=True, liga="arg.1", patron=None):
    """El calendario del año, el detalle de los partidos terminados del torneo y las zonas.
    liga: la de ESPN ("arg.1"; la Copa de la Liga es "arg.copa_lpf"). patron: qué fases del calendario son de este
    torneo (sin nada, las que tienen el slug: "torneo-apertura", "apertura---final"…)."""
    if liga == "a_mano":   # (los partidos de tools/a_mano; slug: la clave del torneo)
        eventos = eventos_a_mano(slug)
        print(f"{anio} {slug}: {len(eventos)} partidos cargados a mano", flush=True)
        return eventos
    base = f"{ESPN.rsplit('/', 1)[0]}/{liga}"
    carpeta = CACHE / str(anio)
    carpeta.mkdir(parents=True, exist_ok=True)
    cal = pedir(f"{base}/scoreboard?dates={anio}&limit=1000")
    archivo_calendario(liga, anio).write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
    patron = re.escape(slug) if patron is None else patron
    eventos = [e for e in cal.get("events", []) if re.search(patron, (e.get("season") or {}).get("slug", ""))]
    nuevos = 0
    for e in eventos:
        archivo = carpeta / f"{e['id']}.json"
        if not e["status"]["type"].get("completed") or archivo.exists():
            continue
        try:
            archivo.write_text(json.dumps(recortar(pedir(f"{base}/summary?event={e['id']}")), ensure_ascii=False),
                               encoding="utf-8")
            nuevos += 1
            time.sleep(0.4)
        except Exception as x:   # se vuelve a pedir la próxima vez
            print(f"  no se pudo bajar el partido {e['id']} ({x})", flush=True)
    # Las zonas: la tabla de ESPN tiene dos grupos de 15 mientras se juega la fase regular. Se guardan la primera
    # vez (en los playoffs la tabla puede cambiar de forma)
    zonas = carpeta / f"zonas-{slug}.json"
    if con_zonas and not zonas.exists():
        tabla = pedir(f"{base.replace('/site/v2/', '/v2/')}/standings?season={anio}")
        z = {g["name"].split()[-1]: [x["team"]["id"] for x in g["standings"]["entries"]] for g in tabla.get("children", [])}
        if len(z) == 2 and all(len(v) >= 10 for v in z.values()):
            zonas.write_text(json.dumps(z), encoding="utf-8")
    print(f"{anio} {slug}: {len(eventos)} partidos en el calendario, {nuevos} detalles nuevos", flush=True)
    for e in eventos:
        e["_carpeta"] = str(carpeta)
    return eventos


def calendario(liga, anio):
    """El calendario de un año de una liga de ESPN ("arg.1", "arg.copa_lpf"). Los años terminados se bajan una
    sola vez; el año del torneo en curso ya lo bajó bajar(). Con "a_mano", los partidos cargados a mano de ese año."""
    if liga == "a_mano":
        return {"events": [e for a in sorted(A_MANO.glob(f"liga-{anio}-*.json"))
                           for e in eventos_a_mano(a.stem.removeprefix("liga-"))]}
    archivo = archivo_calendario(liga, anio)
    if not archivo.exists() or (anio >= datetime.date.today().year and liga != "arg.1"):
        archivo.parent.mkdir(parents=True, exist_ok=True)
        cal = pedir(f"{ESPN.rsplit('/', 1)[0]}/{liga}/scoreboard?dates={anio}&limit=1000")
        archivo.write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
    return json.loads(archivo.read_text(encoding="utf-8"))


def sumar(anio, fuentes):
    """Puntos, partidos y goles de cada club (id de ESPN) en los partidos terminados de esas fases:
    {id: [pts, pj, g, e, p, gf, gc]}. fuentes: [(liga, patrón del slug de la fase[, año])] (el año, si la fase es
    de otro: la temporada 2019-20 toca 2019 y 2020). Los partidos de PARTIDOS_A_MANO se suman en vez de bajarlos."""
    t = {}
    for liga, patron, *otro in fuentes:
        a = otro[0] if otro else anio
        if (liga, a) in PARTIDOS_A_MANO:
            eventos = [{"season": {"slug": ""}, "status": {"type": {"completed": True}}, "competitions": [{"competitors": [
                {"team": {"id": l}, "score": gl}, {"team": {"id": v}, "score": gv}]}]} for l, v, gl, gv in PARTIDOS_A_MANO[(liga, a)]]
        else:
            eventos = calendario(liga, a).get("events", [])
        for e in eventos:
            if e.get("id") in RESULTADOS_A_MANO:
                lados = sorted(e["competitions"][0]["competitors"], key=lambda c: c["homeAway"] != "home")
                e = {**e, "status": {"type": {"completed": True}}, "competitions": [{"competitors": [
                    {**c, "score": g} for c, g in zip(lados, RESULTADOS_A_MANO[e["id"]])]}]}
            if not re.search(patron, (e.get("season") or {}).get("slug", "")) or not e["status"]["type"].get("completed")                     or e.get("id") in NO_SUMAN:
                continue
            c = e["competitions"][0]["competitors"]
            for a, b in ((c[0], c[1]), (c[1], c[0])):
                ga, gb = int(a["score"]), int(b["score"])
                if e.get("id") in PIERDEN_LOS_DOS and a.get("homeAway") == "home":
                    ga, gb = PIERDEN_LOS_DOS[e["id"]]
                # (partidos a mano con otro resultado para un equipo: Colón-Unión 1999; con un tercer valor, el
                # resultado que cuenta: San Lorenzo-Huracán 1997, perdido 0-0 por los dos)
                otro = (e.get("_a_mano") or {}).get("para_local" if a.get("homeAway") == "home" else "para_visitante")
                if otro:
                    ga, gb = otro[:2]
                f = t.setdefault(a["team"]["id"], [0] * 7)
                r = 2 if ga > gb else 3 if ga == gb else 4
                if otro and len(otro) > 2:
                    r = {"V": 2, "E": 3, "D": 4}[otro[2]]
                f[0] += {2: PUNTOS_VICTORIA.get((e.get("season") or {}).get("slug"), 3), 3: 1, 4: 0}[r]
                f[1] += 1
                f[r] += 1
                f[5] += ga
                f[6] += gb
    for (a, eid, *fase), pts in DESCUENTOS.items():
        if a == anio and eid in t and (not fase or any(f[1] == fase[0] for f in fuentes)):
            t[eid][0] -= pts
    return t


def campeon(liga, anio, patron, club, perdedor=False):
    """El ganador de una final de ESPN (también si se definió por penales), o None si todavía no se jugó.
    club: la función que convierte el equipo de ESPN en nuestro id (y suma el club a la lista).
    perdedor: el que perdió la final (el subcampeón)."""
    for e in calendario(liga, anio).get("events", []):
        if re.search(patron, (e.get("season") or {}).get("slug", "")) and e["status"]["type"].get("completed"):
            lados = e["competitions"][0]["competitors"]
            elegido = [c for c in lados if bool(c.get("winner")) != perdedor]
            if any(c.get("winner") for c in lados) and elegido:
                return club(elegido[0]["team"])
    return None


def repartir_fechas(partidos, cantidad):
    """Le pone a cada partido de la fase regular su número de fecha (fecha_n). ESPN no lo dice, así que se recorren
    los partidos en el orden en que se jugaron (o se van a jugar):
    - Si los dos clubes deben un partido de una fecha ya cerrada, es un partido postergado: va a esa fecha.
    - Si no, va a la fecha en curso, salvo que alguno de los dos ya haya jugado en ella (o que ya esté completa):
      entonces empieza la fecha siguiente. Así se separan también las fechas pegadas (una que termina el lunes y
      otra que empieza el martes).
    Los partidos sin jugar con día a confirmar ESPN los pone todos juntos un domingo: quedan bien igual."""
    por_fecha = max(1, len({c for p in partidos for c in (p["local"], p["visitante"])}) // 2)
    fechas = []   # [{clubes}, ...]; la última es la que está en curso
    for p in sorted(partidos, key=lambda p: p["hora_utc"]):
        par = {p["local"], p["visitante"]}
        debe = [n for n, clubes in enumerate(fechas[:-1]) if not par & clubes]
        if debe:
            n = debe[0]
        elif not fechas or par & fechas[-1] or len(fechas[-1]) >= 2 * por_fecha:
            fechas.append(set())
            n = len(fechas) - 1
        else:
            n = len(fechas) - 1
        fechas[n] |= par
        p["fecha_n"] = n + 1
    if len(fechas) > cantidad:
        reparar(partidos, len(fechas), cantidad)
        fechas = sorted({p["fecha_n"] for p in partidos})
    if len(fechas) != cantidad:
        print(f"  ojo: salieron {len(fechas)} fechas (se esperaban {cantidad})", flush=True)
    return partidos


def reparar(partidos, hay, cantidad):
    """Cuando sobran fechas (postergados que se cruzan: en diciembre de 2024 a Racing le faltaba la fecha 24 y a
    River la 25, y Racing-River no entraba en ninguna), se vuelven a armar entre todas las fechas del final que
    quedaron incompletas, con los partidos sueltos: cada club juega una vez por fecha y cada partido se queda, si se
    puede, en la fecha que ya tenía (o en la más cercana). Se prueba primero el partido con menos fechas posibles."""
    por_fecha = len({c for p in partidos for c in (p["local"], p["visitante"])}) // 2
    tamanio = lambda n: sum(p["fecha_n"] == n for p in partidos)
    sobran = sorted(range(1, hay + 1), key=lambda n: (tamanio(n), -n))[:hay - cantidad]
    quedan = [n for n in range(1, hay + 1) if n not in sobran]
    incompletas = [n for n in quedan if tamanio(n) < por_fecha]
    if not incompletas:
        return
    ventana = [n for n in quedan if n >= min(incompletas)]
    juego = [p for p in partidos if p["fecha_n"] in ventana or p["fecha_n"] in sobran]
    original = {id(p): p["fecha_n"] for p in juego}
    usados = {n: set() for n in ventana}

    def posibles(p):
        return [n for n in ventana if p["local"] not in usados[n] and p["visitante"] not in usados[n]]

    def armar(faltan):
        if not faltan:
            return True
        p = min(faltan, key=lambda q: len(posibles(q)))
        resto = [q for q in faltan if q is not p]
        # primero la fecha que ya tenía; si no, la más cercana
        for n in sorted(posibles(p), key=lambda n: (n != original[id(p)], abs(n - min(original[id(p)], max(ventana))))):
            usados[n] |= {p["local"], p["visitante"]}
            p["fecha_n"] = n
            if armar(resto):
                return True
            usados[n] -= {p["local"], p["visitante"]}
        return False

    if not armar(juego):
        for p in juego:
            p["fecha_n"] = original[id(p)]
        print("  no se pudieron reacomodar los partidos postergados", flush=True)
        return
    # se renumeran las fechas (sin huecos)
    orden = {n: i + 1 for i, n in enumerate(sorted({p["fecha_n"] for p in partidos}))}
    for p in partidos:
        p["fecha_n"] = orden[p["fecha_n"]]


def lider(partidos):
    """El primero de la tabla (puntos, diferencia de gol, goles a favor) si ya se jugaron todos los partidos; si no,
    None. Para los torneos sin playoffs (la Liga 2024)."""
    if not partidos or any(p["gl"] is None for p in partidos):
        return None
    t = {}
    for p in partidos:
        for c, a, b in ((p["local"], p["gl"], p["gv"]), (p["visitante"], p["gv"], p["gl"])):
            f = t.setdefault(c, [0, 0, 0])
            f[0] += 3 if a > b else 1 if a == b else 0
            f[1] += a - b
            f[2] += a
    return max(t, key=lambda c: t[c])


def slug_club(nombre):
    t = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def catalogo():
    """{id de ESPN: id nuestro} y los datos de cada club, de data/equipos.js."""
    t = (RAIZ / "data" / "equipos.js").read_text(encoding="utf-8")
    eq = json.JSONDecoder().raw_decode(t[t.index("equipos = ") + 10:])[0]
    return {e: k for k, v in eq.items() for e in v.get("espn", [])}, eq


def armar(clave):
    cfg = TORNEOS[clave]
    unica = cfg.get("zonas") == "unica"   # todos contra todos: una sola tabla (la Liga 2024)
    etapas = cfg.get("etapas")   # torneos por etapas (la Copa Maradona 2020): las zonas salen del grupo de cada partido
    eventos = [e for a in cfg.get("anios", [cfg["anio"]])
               for e in bajar(a, cfg["slug"], con_zonas="zonas_de" not in cfg and not unica and not etapas and not cfg.get("copa")
                              and cfg.get("zonas") != "grupos",
                              liga=cfg.get("liga", "arg.1"), patron=cfg.get("patron"))]
    carpeta = CACHE / str(cfg["anio"])
    if cfg.get("playoffs_ids"):   # partidos que ESPN mete en la fase regular (2016: la final y el del tercer puesto)
        es_playoff = lambda e: cfg["playoffs_ids"].get(e["id"])
    elif cfg.get("playoffs"):   # finales con nombre propio
        es_playoff = lambda e: next((n for s, n in cfg["playoffs"] if re.search(s, e["season"]["slug"])), None)
    else:
        es_playoff = lambda e: next((n for s, n in PLAYOFFS if re.search(rf"(^|-){s}", e["season"]["slug"])), None)
    etapa_de = lambda e: next((i for i, (_, s, *_) in enumerate(etapas) if re.search(s, e["season"]["slug"])), None)
    if etapas or cfg.get("copa"):   # (sin fase regular, no hay zonas)
        zonas_espn = {}
    elif cfg.get("zonas") == "grupos":
        # la zona de cada club sale del grupo que ESPN le pone a cada partido (2016: "... - GROUP 1"): la de la mayoría
        # de sus partidos (los interzonales van en el grupo de uno de los dos)
        cuenta = {}
        for e in eventos:
            g = ((e["competitions"][0].get("group") or {}).get("name") or "").split()[-1:]
            for c in e["competitions"][0]["competitors"]:
                if g and not es_playoff(e):
                    cuenta.setdefault(c["team"]["id"], {}).setdefault(g[0], 0)
                    cuenta[c["team"]["id"]][g[0]] += 1
        zonas_espn = {}
        for eid, gs in sorted(cuenta.items()):
            zonas_espn.setdefault(max(gs, key=gs.get), []).append(eid)
        zonas_espn = dict(sorted(zonas_espn.items()))
    elif unica:
        # (sin los playoffs: en la Promoción 2012 jugaron equipos de la B Nacional)
        zonas_espn = {"": sorted({c["team"]["id"] for e in eventos if not es_playoff(e)
                                  for c in e["competitions"][0]["competitors"]})}
    else:
        zonas_espn = json.loads((carpeta / f"zonas-{cfg.get('zonas_de', cfg['slug'])}.json").read_text(encoding="utf-8"))
    # control: con las zonas bien puestas, cada club juega 2 partidos contra la otra zona en la fase regular
    zona_de = {i: z for z, ids in zonas_espn.items() for i in ids}
    interzonales = {}
    for e in eventos:
        ids = [c["team"]["id"] for c in e["competitions"][0]["competitors"]]
        if not etapas and not es_playoff(e) and zona_de.get(ids[0]) != zona_de.get(ids[1]):
            for i in ids:
                interzonales[i] = interzonales.get(i, 0) + 1
    raros = {i: n for i, n in interzonales.items() if n > 2}
    if raros:
        print(f"  ojo: clubes con más de 2 partidos contra la otra zona (¿zonas equivocadas?): {raros}", flush=True)
    espn_a_club, eq = catalogo()
    clubes = {}

    def club(t):
        eid = t["id"]
        if eid in CLUBES_NUEVOS:
            cid, nombre = CLUBES_NUEVOS[eid]
        elif eid in espn_a_club:
            cid = espn_a_club[eid]
            nombre = eq[cid]["nombre"]
        else:   # un club que no conocemos: se usa el nombre de ESPN (y se avisa para ponerle uno mejor)
            cid, nombre = slug_club(t["displayName"]), t["displayName"]
            print(f"  club nuevo sin nombre propio: {nombre} (ESPN {eid}); sumarlo a CLUBES_NUEVOS", flush=True)
        nombre = NOMBRES.get(cid, nombre)
        if cid not in clubes:
            escudo = RAIZ / "assets" / "escudos" / f"{cid}.png"
            if not escudo.exists():
                try:
                    req = urllib.request.Request(ESCUDO.format(eid), headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        escudo.write_bytes(r.read())
                except Exception as x:
                    print(f"  no se pudo bajar el escudo de {nombre} ({x})", flush=True)
            clubes[cid] = {"nombre": nombre, "escudo": f"assets/escudos/{cid}.png" if escudo.exists() else None,
                           "colores": eq.get(cid, {}).get("colores") or (["#" + t["color"]] if t.get("color") else None)}
        return cid

    regular, playoffs, desempates = [], {}, []
    for e in sorted(eventos, key=lambda e: e["date"]):
        comp = e["competitions"][0]
        lados = {c["homeAway"]: c for c in comp["competitors"]}
        estado = e["status"]["type"]
        hora = hora_argentina(e["date"])
        p = {
            "espn": e["id"], "hora_utc": e["date"],
            "fecha": hora.strftime("%Y-%m-%d") if comp.get("timeValid", True) else None,
            # ESPN pone "TBD" (y una hora inventada) cuando todavía no se sabe el día
            "hora": hora.strftime("%H:%M") if comp.get("timeValid", e.get("timeValid", True)) else None,
            "a_confirmar": not comp.get("timeValid", True),
            "local": club(lados["home"]["team"]), "visitante": club(lados["away"]["team"]),
            "local_espn": lados["home"]["team"]["id"],
            "gl": int(lados["home"]["score"]) if estado.get("completed") else None,
            "gv": int(lados["away"]["score"]) if estado.get("completed") else None,
            "estadio": (comp.get("venue") or {}).get("fullName"),
            "goles": [],
        }
        if estado.get("name") in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_ABANDONED"):
            p["estado"] = {"STATUS_POSTPONED": "Postergado", "STATUS_CANCELED": "Cancelado",
                           "STATUS_SUSPENDED": "Suspendido", "STATUS_ABANDONED": "Suspendido"}[estado["name"]]
        if estado.get("name") == "STATUS_FINAL_AET":   # (los que se definieron por penales no dicen si hubo alargue)
            p["alargue"] = True
        if lados["home"].get("shootoutScore") is not None:
            p["pen_l"], p["pen_v"] = int(lados["home"]["shootoutScore"]), int(lados["away"]["shootoutScore"])
        if e["id"] in RESULTADOS_A_MANO:
            p["gl"], p["gv"], p["nota"] = RESULTADOS_A_MANO[e["id"]]
            p.pop("estado", None)
            if p["nota"]:
                p["hora"] = None   # (no se jugó)
        if e["id"] in PIERDEN_LOS_DOS:   # (en la tabla, al local se le cuenta otro resultado)
            p["para_local"] = list(PIERDEN_LOS_DOS[e["id"]])
        if e["id"] in PENALES_A_MANO:
            p["pen_l"], p["pen_v"] = PENALES_A_MANO[e["id"]]
        detalle = Path(e.get("_carpeta", carpeta)) / f"{e['id']}.json"
        if detalle.exists():
            completar(p, json.loads(detalle.read_text(encoding="utf-8")))
        p["goles"] = [{**{k: v for k, v in g.items() if v is not None and k not in ("lado", "aid")}, "equipo": g["lado"]}
                      for g in p["goles"]]
        p.pop("formaciones", None)
        if e["id"] in GOLES_CORREGIDOS:
            p["goles"] = GOLES_CORREGIDOS[e["id"]]
        if e["id"] in GOLES_A_MANO:
            p["goles"] = sorted(p["goles"] + GOLES_A_MANO[e["id"]], key=lambda g: g.get("min") or 0)
        if e.get("_a_mano"):   # (sin ESPN: la fecha ya se sabe; los goles, solo con el apellido: jid con el club)
            m = e["_a_mano"]
            del p["espn"]
            p.update({"fecha": m["fecha"], "hora": m.get("hora"), "fecha_n": e["_fecha_n"], "nota": m.get("nota"),
                      "para_local": m.get("para_local"), "para_visitante": m.get("para_visitante"),
                      "goles": [{**g, "jid": f"{p[g['equipo']]}:{g['jugador']}"} for g in m.get("goles", [])]})
        fase = es_playoff(e)
        if cfg.get("desempate") and re.search(cfg["desempate"], e["season"]["slug"]):
            desempates.append(p)
        elif fase:
            playoffs.setdefault(fase, []).append(p)
        else:
            if etapas:
                p["etapa"] = etapa_de(e)
                g = ((comp.get("group") or {}).get("name") or "").replace("Group ", "")
                p["zona"] = g[0] if re.fullmatch(r"[A-Z]\d", g) else g   # "A1" (zona A de la Fase Campeón) -> "A"
            regular.append(p)

    for fase, ps in cfg.get("playoffs_a_mano", {}).items():   # partidos que ESPN no tiene (la Superfinal 2013)
        for p in ps:   # (los clubes, con nuestro id o con el de ESPN, si no jugaron el torneo: la Promoción 2011)
            p = {**p, **{lado: club({"id": p[lado], "displayName": p[lado]}) for lado in ("local", "visitante")
                         if p[lado].isdigit() or p[lado] in CLUBES_NUEVOS}}
            if cfg.get("liga") == "a_mano":   # (goles solo con el apellido: jid con el club, como en la fase regular)
                p["goles"] = [{**g, "jid": f"{p[g['equipo']]}:{g['jugador']}"} for g in p.get("goles", [])]
            playoffs.setdefault(fase, []).append(p)

    if etapas:   # las fechas, por etapa, numeradas desde la primera fecha de cada una
        for i, (_, _, _, primera, cuantas) in enumerate(etapas):
            de_etapa = [p for p in regular if p["etapa"] == i]
            repartir_fechas(de_etapa, cuantas)
            for p in de_etapa:
                p["fecha_n"] += primera - 1
    elif regular and cfg.get("liga") != "a_mano":
        repartir_fechas(regular, cfg["fechas"])
    fechas = {}
    for p in regular:
        fechas.setdefault(p["fecha_n"], []).append(p)
    limpio = lambda p: {k: v for k, v in p.items() if k not in ("hora_utc", "local_espn", "fecha_n", "a_confirmar", "etapa", "zona")
                        and v is not None and v is not False and v != []}
    zonas = {}
    for letra, ids in zonas_espn.items():
        zonas[letra] = [club({"id": i, "displayName": i}) for i in ids]
    datos = {
        "clave": clave, "nombre": cfg["nombre"], "anio": cfg["anio"], "pasan": cfg["pasan"],
        "actualizado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "zonas": zonas,
        "fechas": [{"numero": n, "partidos": [limpio(p) for p in sorted(fechas[n], key=lambda p: p["hora_utc"])]}
                   for n in sorted(fechas)],
        "playoffs": [{"nombre": n, "partidos": [limpio(p) for p in playoffs[n]]}
                     for n in (list(cfg["playoffs_ids"].values()) if cfg.get("playoffs_ids") else [n for _, n in cfg.get("playoffs", PLAYOFFS)])
                     if n in playoffs],
        "clubes": clubes,
    }
    # tabla anual (lo jugado antes en el año) y promedios (las temporadas anteriores), solo de los clubes del torneo
    espn_de = {cid: eid for z in zonas_espn for eid, cid in zip(zonas_espn[z], zonas[z])}   # {id nuestro: id de ESPN}
    if isinstance(cfg.get("anual"), dict):   # la tabla puesta a mano (el Apertura 2002, que ESPN no tiene)
        datos["anual"] = {cid: v for cid, v in cfg["anual"].items() if cid in espn_de}
    elif cfg.get("anual"):
        previo = sumar(cfg["anio"], cfg["anual"])
        datos["anual"] = {cid: previo[eid] for cid, eid in espn_de.items() if eid in previo}
    if cfg.get("promedios"):
        datos["promedios"] = {}
        for anio, fuentes in cfg["promedios"].items():
            if isinstance(fuentes, dict):   # puntos puestos a mano ({club: [pts, pj]}; 2002-03, que ESPN no tiene)
                datos["promedios"][anio] = {cid: v for cid, v in fuentes.items() if cid in espn_de}
                continue
            s = sumar(anio, fuentes)
            datos["promedios"][anio] = {cid: s[eid][:2] for cid, eid in espn_de.items() if eid in s}
        # un club que bajó y volvió a subir cuenta solo desde que volvió (Aldosivi 2018-19: no se le cuenta 2016-17):
        # se le borran las temporadas anteriores a una en la que no estuvo en Primera
        temporadas = list(datos["promedios"])
        for i, anio in enumerate(temporadas):
            for cid in list(datos["promedios"][anio]):
                if any(cid not in datos["promedios"][otra] for otra in temporadas[i + 1:]):
                    del datos["promedios"][anio][cid]
    datos["descensos"] = cfg.get("descensos", False)
    if etapas:
        datos["etapas"] = []
        for i, (nombre, _, pasan, _, _) in enumerate(etapas):
            ps = [p for p in regular if p["etapa"] == i]
            zonas_etapa = {}
            for p in sorted(ps, key=lambda p: p["hora_utc"]):
                for c in (p["local"], p["visitante"]):
                    if c not in zonas_etapa.setdefault(p["zona"], []):
                        zonas_etapa[p["zona"]].append(c)
            datos["etapas"].append({"nombre": nombre, "pasan": pasan, "zonas": dict(sorted(zonas_etapa.items())),
                                    "fechas": sorted({p["fecha_n"] for p in ps})})
    if cfg.get("desempate_a_mano"):   # (un desempate que ESPN no tiene: River-Gimnasia 1999)
        d = cfg["desempate_a_mano"]
        desempates = [{**d, **{lado: club({"id": d[lado], "displayName": d[lado]}) for lado in ("local", "visitante")
                                if d[lado].isdigit() or d[lado] in CLUBES_NUEVOS}}]
    if desempates:
        datos["desempate"] = limpio(desempates[0])
    for k in ("temporada", "descienden", "texto_pasan", "nombre_playoffs", "nombre_anual", "desempate_texto", "goleadores_nota", "promocion", "ventaja", "triangular", "texto_triangular", "ida_y_vuelta", "gol_visitante", "cuadro_desde",
              "campeon_tabla", "anual_texto", "descensos_anulados", "sin_descensos", "nota", "cuadro", "descuentos",
              "descuentos_texto", "promedios_victoria", "puntos_victoria"):
        if cfg.get(k):
            datos[k] = cfg[k]
    if cfg.get("titulo_anual"):
        datos["titulo_anual"] = cfg["titulo_anual"]
    if cfg.get("cupos", {}).get("fijos"):   # (2015: la lista tal cual)
        # (anio_sudamericana: si la Sudamericana es de otro año que la Libertadores; 2007: la Sudamericana 2007 y la
        # Libertadores 2008)
        datos["cupos"] = {"anio": cfg["cupos"]["anio"], "fijos": True, "campeones": [],
                          **{k: cfg["cupos"][k] for k in ("anio_sudamericana", "nombre_sudamericana", "nota") if k in cfg["cupos"]},
                          **{k: [{"titulo": ti, "club": c} for ti, c in cfg["cupos"][k]]
                             for k in ("libertadores", "sudamericana") if k in cfg["cupos"]}}
    elif cfg.get("cupos"):
        cupos = dict(cfg["cupos"])
        # extra: un lugar que no es de la liga (el campeón de la Sudamericana va a la Libertadores por la Conmebol);
        # "tabla": el campeón es el primero de la tabla de ese torneo (la Liga 2023, que se jugó antes en el año);
        # sin liga: el primero de la tabla de este torneo, cuando se jugó todo
        def quien(liga, patron, modo):
            if not liga:
                return lider(regular)
            if modo == "final":   # el ganador de la final de este torneo
                return next((p["local"] if (p["gl"], p.get("pen_l", 0)) > (p["gv"], p.get("pen_v", 0)) else p["visitante"]
                             for p in playoffs.get("Final", []) if p["gl"] is not None), None)
            if modo == "tabla":
                s = sumar(cfg["anio"], [(liga, patron)])
                eid = max(s, key=lambda i: (s[i][0], s[i][5] - s[i][6], s[i][5]))
                return club({"id": eid, "displayName": eid})
            # "perdedor": el lugar fue para el subcampeón (2017: River ganó la Copa Argentina pero ya entraba por la tabla)
            return campeon(liga, cfg["anio"], patron, club, perdedor=modo == "perdedor")
        cupos["campeones"] = [{"titulo": titulo, "club": quien(liga, patron, modo[0] if modo else None),
                               **({"extra": True} if modo and modo[0] == "extra" else {})}
                              for titulo, liga, patron, *modo in cfg["cupos"]["campeones"]]
        # lugares de la Sudamericana que se ganan por un torneo (2021: el subcampeón de la Copa Diego Maradona): le
        # restan lugares a la tabla anual
        # (con solo el título y el club: un lugar puesto a mano, como el del mejor de la Copa de la Superliga 2019)
        cupos["sudamericana_titulos"] = [{"titulo": x[0], "club": x[1] if len(x) == 2 else
                                          campeon(x[1], cfg["anio"], x[2], club, perdedor=x[3] == "perdedor")}
                                         for x in cfg["cupos"].get("sudamericana_titulos", [])]
        datos["cupos"] = cupos
    DATOS.mkdir(parents=True, exist_ok=True)
    # si no cambió nada desde la última vez, queda la hora de antes (así un torneo terminado no cambia cada noche)
    archivo = DATOS / f"{clave}.js"
    if archivo.exists():
        t = archivo.read_text(encoding="utf-8")
        antes = json.JSONDecoder().raw_decode(t[t.index("] = ") + 4:])[0]
        if {**antes, "actualizado": None} == {**json.loads(json.dumps(datos)), "actualizado": None}:
            datos["actualizado"] = antes["actualizado"]
    js = ("/* Generado por tools/actualizar_liga.py — no editar a mano */\n"
          "window.LIGA = window.LIGA || {};\n"
          f"window.LIGA[{json.dumps(clave)}] = {json.dumps(datos, ensure_ascii=False, separators=(',', ':'))};\n")
    (DATOS / f"{clave}.js").write_text(js, encoding="utf-8")
    jugados = sum(p["gl"] is not None for p in regular)
    clubes_regular = {c for p in regular for c in (p["local"], p["visitante"])}
    print(f"{cfg['nombre']}: {len(fechas)} fechas, {jugados} de {len(regular)} partidos jugados; "
          f"playoffs: {sum(len(v) for v in playoffs.values())} partidos", flush=True)
    for n in sorted(fechas):
        cuenta = {}
        for p in fechas[n]:
            for c in (p["local"], p["visitante"]):
                cuenta[c] = cuenta.get(c, 0) + 1
        repetidos = [c for c, k in cuenta.items() if k > 1]
        if len(fechas[n]) != len(clubes_regular) // 2 or repetidos:
            print(f"  fecha {n}: {len(fechas[n])} partidos{'; repetidos: ' + ', '.join(repetidos) if repetidos else ''}")
    return datos


def escribir_indice():
    """El índice de torneos de la liga (para la lista de la página), en orden."""
    indice = [{"clave": c, "nombre": t["nombre"]} for c, t in TORNEOS.items() if (DATOS / f"{c}.js").exists()]
    (DATOS / "indice.js").write_text("/* Generado por tools/actualizar_liga.py — no editar a mano */\n"
                                     f"window.LIGA_INDICE = {json.dumps(indice, ensure_ascii=False)};\n", encoding="utf-8")


def terminado(clave):
    """Si el torneo ya tiene campeón (la final jugada en los datos, o, en los torneos sin playoffs, todos los partidos
    jugados), no hace falta volver a bajarlo cada noche."""
    archivo = DATOS / f"{clave}.js"
    if not archivo.exists():
        return False
    t = archivo.read_text(encoding="utf-8")
    d = json.JSONDecoder().raw_decode(t[t.index("] = ") + 4:])[0]
    if d.get("campeon_tabla"):
        return all("gl" in p for f in d["fechas"] for p in f["partidos"])
    return any(r["nombre"] == "Final" and all("gl" in p for p in r["partidos"]) for r in d["playoffs"])


def main():
    """Sin nada, los torneos que no terminaron; con nombres (o "todos"), esos."""
    pedidos = [a for a in sys.argv[1:] if a in TORNEOS]
    if not pedidos:
        pedidos = list(TORNEOS) if "todos" in sys.argv else [c for c in TORNEOS if not terminado(c)]
    # (los torneos que usan las zonas de otro van después: ese otro baja las zonas)
    for clave in sorted(pedidos, key=lambda c: "zonas_de" in TORNEOS[c]):
        armar(clave)
    escribir_indice()


if __name__ == "__main__":
    main()
