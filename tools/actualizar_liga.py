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
    # 1920: las dos ligas, amateurs las dos (la AFA reconoce a los dos campeones). A mitad de año Lanús y Sportivo Almagro
    # se pasaron de la Asociación Argentina a la Amateurs, y los dos fixtures se rehicieron: RSSSF sigue el original en la
    # primera rueda y, en la segunda, cada día de partidos es una fecha. La de la Asociación Amateurs (marzo de 1920 a
    # enero de 1921; campeón River): 19 equipos a dos ruedas (Lanús y Sportivo Almagro, solo la segunda), con 2 puntos
    # por partido ganado. ESPN no los tiene: van a mano (tools/a_mano; RSSSF, sin goles salvo los de los partidos del
    # título)
    "1920-amateurs": {"nombre": "Campeonato de Primera División 1920 (amateur, Asociación Amateurs)", "anio": 1920,
                      "liga": "a_mano", "slug": "1920-amateurs", "zonas": "unica", "fechas": 45, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Lanús y Sportivo Almagro llegaron de la otra asociación a mitad de año y jugaron solo "
                                     "una rueda. Orden: puntos y, con los mismos puntos, la diferencia de gol (RSSSF pone a los "
                                     "empatados en el mismo puesto). Almagro se llamaba Sportivo Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1920 de la Asociación Amateurs. Cada "
                                     "partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo del Quilmes 0-2 River, el partido en el que River salió campeón "
                                         "(de RSSSF). RSSSF no dice quién fue el goleador del torneo.",
                      "sin_descensos": "No hubo descensos."},
    # La de la Asociación Argentina (marzo de 1920 a enero de 1921; campeón Boca): 13 equipos a dos ruedas, con 2 puntos
    # por partido ganado. Lanús y Sportivo Almagro se fueron y Palermo se desafilió: los partidos que les faltaban se los
    # dieron perdidos ("para_local"/"para_visitante", sin goles; algunos, perdidos para los dos)
    "1920-aaf": {"nombre": "Campeonato de Primera División 1920 (amateur, Asociación Argentina de Football)", "anio": 1920,
                 "liga": "a_mano", "slug": "1920-aaf", "zonas": "unica", "fechas": 44, "pasan": 0, "puntos_victoria": 2,
                 "campeon_tabla": True,
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. Lanús y "
                                "Sportivo Almagro se fueron a la otra asociación a mitad de año, y Palermo se desafilió: los "
                                "partidos que les faltaban se los dieron perdidos. Orden: puntos y, con los mismos puntos, la "
                                "diferencia de gol (RSSSF pone a los empatados en el mismo puesto). Colegiales se llamaba "
                                "Sportivo del Norte. Palermo y Sportivo Palermo eran clubes distintos.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1920 de la Asociación Argentina (amateur). Cada "
                                "partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo del Boca 7-0 Nueva Chicago, el partido que le dio el título a Boca "
                                    "(de RSSSF, con los minutos). RSSSF no dice quién fue el goleador del torneo.",
                 "sin_descensos": "No hubo descensos."},
    # 1921: las dos ligas, amateurs las dos (la AFA reconoce a los dos campeones). La de la Asociación Argentina (abril a
    # diciembre; campeón Huracán): 10 equipos a dos ruedas, con 2 puntos por partido ganado; sin los partidos de Platense,
    # que la asociación anuló (no jugó el mínimo reglamentario). Un suspendido se lo dieron ganado a El Porvenir, con los
    # goles en la tabla. Sportivo del Norte va como Colegiales. ESPN no los tiene: van a mano (tools/a_mano; RSSSF, con
    # los goles de algunos partidos)
    "1921-aaf": {"nombre": "Campeonato de Primera División 1921 (amateur, Asociación Argentina de Football)", "anio": 1921,
                 "liga": "a_mano", "slug": "1921-aaf", "zonas": "unica", "fechas": 26, "pasan": 0, "puntos_victoria": 2,
                 "campeon_tabla": True,
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. Los "
                                "partidos de Platense se anularon porque no jugó el mínimo reglamentario. Orden: puntos y, con "
                                "los mismos puntos, la diferencia de gol (que coincide con el orden de RSSSF). Colegiales se "
                                "llamaba Sportivo del Norte.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1921 de la Asociación Argentina (amateur). Cada "
                                "partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el goleador "
                                    "del torneo fue Guillermo Dannaher (Huracán), con 25 goles.",
                 "sin_descensos": "No hubo descensos."},
    # La de la Asociación Amateurs (abril de 1921 a enero de 1922; campeón Racing): 20 equipos a dos ruedas, con 2 puntos
    # por partido ganado; sin los partidos de General Mitre, que desapareció a mitad de año. El Independiente-Quilmes del
    # 11 de diciembre figura dos veces en RSSSF: va el no jugado, como en su tabla. La tabla de RSSSF cuenta un gol más
    # en un Atlanta-Ferro
    "1921-amateurs": {"nombre": "Campeonato de Primera División 1921 (amateur, Asociación Amateurs)", "anio": 1921,
                      "liga": "a_mano", "slug": "1921-amateurs", "zonas": "unica", "fechas": 47, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Los partidos de General Mitre, que desapareció a mitad de año, se anularon. Orden: "
                                     "puntos y, con los mismos puntos, la diferencia de gol (que coincide con el orden de "
                                     "RSSSF). En la tabla, Atlanta tiene un gol menos en contra y Ferro uno menos a favor que en "
                                     "la de RSSSF, que no coincide con sus propios resultados. Almagro se llamaba Sportivo "
                                     "Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1921 de la Asociación Amateurs. Cada "
                                     "partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el "
                                         "goleador del torneo fue Albérico Zabaleta (Racing), con 30 goles.",
                      "sin_descensos": "No hubo descensos."},
    # 1922: las dos ligas, amateurs las dos (la AFA reconoce a los dos campeones). La de la Asociación Argentina (abril de
    # 1922 a enero de 1923; campeón Huracán): 17 equipos a una rueda, con 2 puntos por partido ganado. Un Del
    # Plata-Progresista suspendido, 1-0, no se terminó porque Progresista no se presentó: en la tabla de RSSSF cuenta el
    # 1-0 ("para_local"). Platense II va como Universal, y Sportivo del Norte, como Colegiales. ESPN no los tiene: van a
    # mano (tools/a_mano; RSSSF, con los goles de algunos partidos)
    "1922-aaf": {"nombre": "Campeonato de Primera División 1922 (amateur, Asociación Argentina de Football)", "anio": 1922,
                 "liga": "a_mano", "slug": "1922-aaf", "zonas": "unica", "fechas": 24, "pasan": 0, "puntos_victoria": 2,
                 "campeon_tabla": True,
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. Orden: "
                                "puntos y, con los mismos puntos, la diferencia de gol (que coincide con el orden de RSSSF). "
                                "Universal se llamaba Platense II; Colegiales, Sportivo del Norte; Dock Sud, Sportivo Dock Sud.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1922 de la Asociación Argentina (amateur). Cada "
                                "partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el goleador "
                                    "del torneo fue José Gaslini (Alvear), con 13 goles.",
                 "sin_descensos": "No hubo descensos."},
    # La de la Asociación Amateurs (abril de 1922 a octubre de 1923; campeón Independiente): 21 equipos a dos ruedas (57
    # fechas, contando las de los partidos atrasados), con 2 puntos por partido ganado. Tres suspendidos se los dieron
    # ganados a uno, con los goles en la tabla. El San Lorenzo-River del 24 de diciembre se terminó en mayo de 1923; RSSSF
    # no trae el resultado, pero en su tabla cuenta un 1-1. Manuel Seoane hizo 51 goles
    "1922-amateurs": {"nombre": "Campeonato de Primera División 1922 (amateur, Asociación Amateurs)", "anio": 1922,
                      "liga": "a_mano", "slug": "1922-amateurs", "zonas": "unica", "fechas": 57, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Era a dos ruedas y terminó en octubre de 1923, con muchos partidos atrasados. Orden: "
                                     "puntos y, con los mismos puntos, la diferencia de gol (que coincide con el orden de "
                                     "RSSSF). Almagro se llamaba Sportivo Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1922 de la Asociación Amateurs. Cada "
                                     "partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el "
                                         "goleador del torneo fue Manuel Seoane (Independiente), con 51 goles.",
                      "sin_descensos": "No hubo descensos."},
    # 1923: las dos ligas, amateurs las dos (la AFA reconoce a los dos campeones). La de la Asociación Amateurs (julio de
    # 1923 a enero de 1924; campeón San Lorenzo): 21 equipos a una rueda, con 2 puntos por partido ganado. Los suspendidos
    # que la asociación le dio ganados a uno van con el resultado del momento y sin goles en la tabla ("para_local"), como
    # en la de RSSSF. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del partido del título)
    "1923-amateurs": {"nombre": "Campeonato de Primera División 1923 (amateur, Asociación Amateurs)", "anio": 1923,
                      "liga": "a_mano", "slug": "1923-amateurs", "zonas": "unica", "fechas": 23, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Orden: puntos y, con los mismos puntos, la diferencia de gol (RSSSF los pone en el "
                                     "mismo puesto). Almagro se llamaba Sportivo Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1923 de la Asociación Amateurs. Cada "
                                     "partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo del Lanús 1-4 San Lorenzo, el partido en el que San Lorenzo salió "
                                         "campeón (de RSSSF, con los minutos). RSSSF no dice quién fue el goleador del torneo.",
                      "sin_descensos": "No hubo descensos."},
    # La de la Asociación Argentina (marzo de 1923 a abril de 1924; campeón Boca): 23 equipos a dos ruedas, pero solo se
    # jugaron unos dos tercios de los partidos. RSSSF no dice a qué fecha pertenece cada partido: cada día es una fecha
    # (40). Boca y Huracán empataron el primer puesto y jugaron cuatro desempates (en "playoffs", sin cuadro): ganó Boca,
    # que va primero en la tabla (también por la diferencia de gol). Platense (de Buenos Aires) va como Universal; Villa
    # Urquiza, como General San Martín, y Sportivo del Norte, como Colegiales. ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, sin goles salvo los del último desempate)
    "1923-aaf": {"nombre": "Campeonato de Primera División 1923 (amateur, Asociación Argentina de Football)", "anio": 1923,
                 "liga": "a_mano", "slug": "1923-aaf", "zonas": "unica", "fechas": 40, "pasan": 2, "puntos_victoria": 2,
                 "campeon_tabla": True,
                 "texto_pasan": "Empatados en el primer puesto (51 puntos): jugaron cuatro desempates por el título, y ganó Boca",
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. Era a dos "
                                "ruedas, pero a fin de año solo se habían jugado unos dos tercios de los partidos, y Boca y "
                                "Huracán acordaron definir el título en desempates. Orden: puntos y, con los mismos puntos, "
                                "la diferencia de gol (RSSSF pone a los empatados en el mismo puesto). Universal se llamaba "
                                "Platense; General San Martín, Villa Urquiza; Colegiales, Sportivo del Norte; Argentino de "
                                "Lomas, Argentino de Banfield; Dock Sud, Sportivo Dock Sud. Palermo y Sportivo Palermo eran "
                                "clubes distintos.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1923 de la Asociación Argentina (amateur), sin "
                                "los desempates. Cada partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo del último desempate (los dos de Garassino, en el alargue). RSSSF no "
                                    "dice quién fue el goleador del torneo.",
                 "nombre_playoffs": "Desempate", "sin_cuadro": True,
                 "playoffs": [(r"^$^", "Desempate por el título")],
                 "playoffs_a_mano": {
                     "Desempate por el título": [
                         {"fecha": "1924-03-16", "local": "boca-juniors", "visitante": "huracan", "gl": 3, "gv": 0,
                          "estadio": "Cancha de Sportivo Barracas"},
                         {"fecha": "1924-03-30", "local": "huracan", "visitante": "boca-juniors", "gl": 2, "gv": 0,
                          "estadio": "Cancha de Sportivo Barracas"},
                         {"fecha": "1924-04-06", "local": "huracan", "visitante": "boca-juniors", "gl": 0, "gv": 0,
                          "estadio": "Cancha de Gimnasia y Esgrima de Buenos Aires",
                          "nota": "Siguió 0-0 después del alargue."},
                         {"fecha": "1924-04-27", "local": "boca-juniors", "visitante": "huracan", "gl": 2, "gv": 0,
                          "alargue": True, "estadio": "Cancha de Sportivo Barracas",
                          "goles": [{"jugador": "Garassino", "equipo": "local"}, {"jugador": "Garassino", "equipo": "local"}],
                          "nota": "Terminó 0-0 y Boca ganó en el alargue, con dos goles de Garassino: salió campeón."},
                     ],
                 },
                 "sin_descensos": "No hubo descensos."},
    # 1924: las dos ligas, la Asociación Argentina de Football y la Asociación Amateurs, amateurs las dos (la AFA reconoce
    # a los dos campeones). La de la Asociación Argentina (abril a diciembre; campeón Boca, invicto): 22 equipos a una
    # rueda, con 2 puntos por partido ganado; cinco partidos no se jugaron. Un suspendido se lo dieron ganado a Nueva
    # Chicago, con los goles en la tabla. Platense II va como Universal; Urquiza, como General San Martín, y Sportivo del
    # Norte, como Colegiales. La tabla de RSSSF no coincide del todo con sus resultados (goles de Sportivo Barracas y
    # Progresista). ESPN no los tiene: van a mano (tools/a_mano; RSSSF, con los goles de algunos partidos)
    "1924-aaf": {"nombre": "Campeonato de Primera División 1924 (amateur, Asociación Argentina de Football)", "anio": 1924,
                 "liga": "a_mano", "slug": "1924-aaf", "zonas": "unica", "fechas": 27, "pasan": 0, "puntos_victoria": 2,
                 "campeon_tabla": True,
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. Cinco "
                                "partidos no se jugaron. Orden: puntos y, con los mismos puntos, la diferencia de gol (que "
                                "coincide con el orden de RSSSF). En la tabla, Sportivo Barracas tiene un gol menos en contra "
                                "y Progresista dos menos a favor que en la de RSSSF, que no coincide con sus propios "
                                "resultados. Universal se llamaba Platense II; General San Martín, Urquiza; Colegiales, "
                                "Sportivo del Norte; Argentino de Lomas, Argentino de Banfield; Dock Sud, Sportivo Dock Sud.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1924 de la Asociación Argentina (amateur). Cada "
                                "partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). RSSSF no dice quién fue "
                                    "el goleador del torneo.",
                 "sin_descensos": "No hubo descensos."},
    # La de la Asociación Amateurs (abril de 1924 a febrero de 1925; campeón San Lorenzo): 24 equipos a una rueda, con 2
    # puntos por partido ganado; a Argentino del Sud le descontaron 2 puntos. Dos suspendidos se los dieron ganados a uno,
    # con los goles en la tabla. Argentino del Sud, Quilmes y Ferro, empatados en el antepenúltimo puesto, jugaron un
    # triangular por el descenso (en "playoffs", sin cuadro): perdió Quilmes, pero la asociación cambió las reglas y no
    # bajó, como Estudiantes de Buenos Aires, el último. La tabla de RSSSF cuenta un gol más en un Atlanta-Ferro
    "1924-amateurs": {"nombre": "Campeonato de Primera División 1924 (amateur, Asociación Amateurs)", "anio": 1924,
                      "liga": "a_mano", "slug": "1924-amateurs", "zonas": "unica", "fechas": 27, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "descuentos": {"argentino-del-sud": 2},
                      "descuentos_texto": "A Argentino del Sud se le descontaron 2 puntos.",
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Orden: puntos y, con los mismos puntos, la diferencia de gol (que coincide con el "
                                     "orden de RSSSF). En la tabla, Atlanta tiene un gol menos a favor y Ferro uno menos en "
                                     "contra que en la de RSSSF, que cuenta como 3-1 su partido de la fecha 6 (2-1). Almagro se "
                                     "llamaba Sportivo Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1924 de la Asociación Amateurs, sin el "
                                     "triangular por el descenso. Cada partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). RSSSF no dice quién "
                                         "fue el goleador del torneo.",
                      "nombre_playoffs": "Triangular por el descenso", "sin_cuadro": True,
                      "playoffs": [(r"^$^", "Triangular por el descenso")],
                      "playoffs_a_mano": {
                          "Triangular por el descenso": [
                              {"fecha": "1925-01-11", "local": "argentino-del-sud", "visitante": "quilmes", "gl": 2, "gv": 1,
                               "estadio": "Cancha de Argentino del Sud"},
                              {"fecha": "1925-01-18", "local": "quilmes", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 0,
                               "estadio": "Cancha de Estudiantes de Bernal"},
                              {"fecha": "1925-01-25", "local": "ferro-carril-oeste", "visitante": "argentino-del-sud", "gl": 1,
                               "gv": 1, "estadio": "Cancha de Liniers",
                               "goles": [{"jugador": "J. Gaslini", "equipo": "local"},
                                         {"jugador": "E. Brameri", "equipo": "visitante"}]},
                              {"fecha": "1925-02-01", "local": "quilmes", "visitante": "argentino-del-sud", "gl": 1, "gv": 1,
                               "estadio": "Quilmes Atlético Club",
                               "goles": [{"jugador": "L. Sandoval", "equipo": "local"},
                                         {"jugador": "J. Bao", "equipo": "visitante"}]},
                              {"fecha": "1925-02-08", "local": "ferro-carril-oeste", "visitante": "quilmes", "gl": 2, "gv": 0,
                               "estadio": "Cancha de Liniers"},
                              {"fecha": "1925-02-15", "local": "argentino-del-sud", "visitante": "ferro-carril-oeste", "gl": 0,
                               "gv": 0, "gana": "argentino-del-sud", "sin_goles": True,
                               "nota": "No se jugó: Ferro no se presentó y perdió el partido."},
                          ],
                      },
                      "sin_descensos": "No hubo descensos. Argentino del Sud, Quilmes y Ferro, empatados en puntos, jugaron "
                                       "un triangular por el descenso (ver la pestaña Triangular por el descenso): Argentino "
                                       "del Sud 6 puntos, Ferro 4 y Quilmes 2. Pero la asociación cambió las reglas y no bajó "
                                       "Quilmes, ni Estudiantes de Buenos Aires, el último de la tabla."},
    # 1925: las dos ligas, la Asociación Argentina de Football y la Asociación Amateurs, amateurs las dos (la AFA reconoce
    # a los dos campeones). La de la Asociación Argentina (abril de 1925 a agosto de 1926; campeón Huracán): 23 equipos a
    # una rueda, con 2 puntos por partido ganado, pero Boca se fue de gira por Europa y jugó solo 7 partidos, y otros
    # quedaron sin jugar. Huracán y Nueva Chicago empataron el primer puesto y jugaron una final (en "playoffs"): 1-1,
    # Nueva Chicago abandonó la cancha a los 83 minutos y no jugó el alargue, y se la dieron a Huracán ("gana"). Un Boca
    # Alumni-Sportivo Barracas suspendido no cuenta en la tabla de RSSSF ("estado"). Platense (después Retiro y Universal)
    # va como Universal, y Urquiza, como General San Martín. ESPN no los tiene: van a mano (tools/a_mano; RSSSF, con los
    # goles de algunos partidos)
    "1925-aaf": {"nombre": "Campeonato de Primera División 1925 (amateur, Asociación Argentina de Football)", "anio": 1925,
                 "liga": "a_mano", "slug": "1925-aaf", "zonas": "unica", "fechas": 34, "pasan": 2, "puntos_victoria": 2,
                 "texto_pasan": "Empatados en el primer puesto (38 puntos): definieron el título en una final",
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. No todos "
                                "jugaron la misma cantidad de partidos: Boca se fue de gira por Europa y jugó solo 7, y otros "
                                "partidos no se jugaron. Orden: puntos y, con los mismos puntos, la diferencia de gol (que "
                                "coincide con el orden de RSSSF). Universal se llamaba Platense (y después Retiro); General "
                                "San Martín, Urquiza; Colegiales, Sportivo del Norte; Argentino de Lomas, Argentino de "
                                "Banfield; Dock Sud, Sportivo Dock Sud.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1925 de la Asociación Argentina (amateur), sin "
                                "la final. Cada partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos; los de la final, con los "
                                    "minutos). Según RSSSF, el goleador del torneo fue Guillermo Stábile (Huracán), con 17 "
                                    "goles.",
                 "nombre_playoffs": "Final (desempate)",
                 "playoffs": [(r"^$^", "Final")],
                 "playoffs_a_mano": {
                     "Final": [
                         {"fecha": "1926-08-22", "local": "huracan", "visitante": "nueva-chicago", "gl": 1, "gv": 1,
                          "gana": "huracan", "estadio": "Cancha de Sportivo Barracas", "arbitro": "L. Celleri",
                          "goles": [{"jugador": "Stábile", "equipo": "local", "min": 65},
                                    {"jugador": "Maure", "equipo": "visitante", "min": 4}],
                          "nota": "Nueva Chicago abandonó la cancha a los 83 minutos y no jugó el alargue: la asociación le dio "
                                  "el partido a Huracán. Dos días después, Nueva Chicago se fue a la Asociación Amateurs."},
                     ],
                 },
                 "sin_descensos": "No hubo descensos."},
    # La de la Asociación Amateurs (abril a diciembre de 1925; campeón Racing, invicto): 25 equipos a una rueda (25 fechas,
    # con uno libre en cada una), con 2 puntos por partido ganado. Dos partidos se los dieron ganados a uno, con los goles
    # en la tabla
    "1925-amateurs": {"nombre": "Campeonato de Primera División 1925 (amateur, Asociación Amateurs)", "anio": 1925,
                      "liga": "a_mano", "slug": "1925-amateurs", "zonas": "unica", "fechas": 25, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Orden: puntos y, con los mismos puntos, la diferencia de gol (que coincide con el "
                                     "orden de RSSSF). Almagro se llamaba Sportivo Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1925 de la Asociación Amateurs. Cada "
                                     "partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el "
                                         "goleador del torneo fue Francisco Bellomo (Estudiantes), con 17 goles.",
                      "sin_descensos": "No hubo descensos."},
    # 1926: de 1919 a 1926 hubo dos ligas, la Asociación Argentina de Football (la oficial) y la Asociación Amateurs
    # Argentina de Football, y la AFA reconoce a los campeones de las dos; las dos eran amateurs. La de la Asociación
    # Argentina (abril de 1926 a enero de 1927; campeón Boca): 18 equipos a una rueda, con 2 puntos por partido ganado; en
    # la fecha 5 se fueron seis equipos a la otra asociación y sus partidos se anularon (las fechas son las del torneo
    # original: quedan 29, algunas con pocos partidos, y los no jugados de la última van repartidos en tres: 31). A General San Martín le descontaron 2 puntos y un partido suyo se
    # lo dieron ganado a Sportsman. Un Argentinos-Alvear suspendido en el entretiempo, 1-0, no se terminó porque Alvear no
    # se presentó: en la tabla de RSSSF cuenta el 1-0 ("para_local"); otro, el Barracas Central-Platense de la Amateurs,
    # cuenta sin goles. Sin descensos: en 1927 las dos ligas se unieron y once clubes de la Asociación Argentina pasaron a
    # la segunda división. ESPN no los tiene: van a mano (tools/a_mano; RSSSF, con los goles de algunos partidos)
    "1926-aaf": {"nombre": "Campeonato de Primera División 1926 (amateur, Asociación Argentina de Football)", "anio": 1926,
                 "liga": "a_mano", "slug": "1926-aaf", "zonas": "unica", "fechas": 31, "pasan": 0, "puntos_victoria": 2,
                 "campeon_tabla": True,
                 "descuentos": {"general-san-martin": 2},
                 "descuentos_texto": "A General San Martín se le descontaron 2 puntos.",
                 "orden_texto": "Campeonato amateur, de la Asociación Argentina de Football: de 1919 a 1926 hubo dos ligas, "
                                "esta y la de la Asociación Amateurs, y la AFA reconoce a los campeones de las dos. En la "
                                "fecha 5 se fueron a la otra asociación All Boys, Colegiales, El Porvenir, Nueva Chicago, "
                                "Sportivo Barracas y Temperley, y sus partidos se anularon. Orden: puntos y, con los mismos "
                                "puntos, la diferencia de gol (que coincide con el orden de RSSSF). Argentino de Lomas se "
                                "llamaba Argentino de Banfield; Dock Sud, Sportivo Dock Sud.",
                 "anual_texto": "La tabla del Campeonato de Primera División 1926 de la Asociación Argentina (amateur). Cada "
                                "partido ganado valía 2 puntos.",
                 "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el goleador "
                                    "del torneo fue Roberto Cherro (Boca), con 19 goles.",
                 "sin_descensos": "No hubo descensos: en 1927 las dos asociaciones se unieron, y Alvear, Argentino de "
                                  "Banfield, Boca Alumni, Del Plata, General San Martín, Palermo, Progresista, Sportivo "
                                  "Balcarce, Sportivo Dock Sud, Sportsman y Universal pasaron a la segunda división."},
    # La de la Asociación Amateurs (abril a diciembre de 1926; campeón Independiente, invicto): 26 equipos a una rueda (25
    # fechas), con 2 puntos por partido ganado. Dos suspendidos se los dieron ganados a uno, con los goles del partido en
    # la tabla; al final, varios equipos no se presentaron (sin goles)
    "1926-amateurs": {"nombre": "Campeonato de Primera División 1926 (amateur, Asociación Amateurs)", "anio": 1926,
                      "liga": "a_mano", "slug": "1926-amateurs", "zonas": "unica", "fechas": 25, "pasan": 0,
                      "puntos_victoria": 2, "campeon_tabla": True,
                      "orden_texto": "Campeonato amateur, de la Asociación Amateurs Argentina de Football: de 1919 a 1926 hubo "
                                     "dos ligas, esta y la de la Asociación Argentina, y la AFA reconoce a los campeones de las "
                                     "dos. Orden: puntos y, con los mismos puntos, la diferencia de gol (que coincide con el "
                                     "orden de RSSSF). Almagro se llamaba Sportivo Almagro.",
                      "anual_texto": "La tabla del Campeonato de Primera División 1926 de la Asociación Amateurs. Cada "
                                     "partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el "
                                         "goleador del torneo fue Manuel Seoane (Independiente), con 30 goles.",
                      "sin_descensos": "No hubo descensos: en 1927 las dos asociaciones se unieron y todos estos equipos "
                                       "siguieron en Primera."},
    # 1927: el campeonato de la Asociación Amateurs Argentina de Football (marzo de 1927 a febrero de 1928; campeón San
    # Lorenzo), el primero después de la unificación de las dos ligas de 1926: 34 equipos a una rueda (33 fechas), con 2
    # puntos por partido ganado. El Banfield 1-2 Talleres se lo dieron ganado a Banfield y a Talleres le descontaron 2
    # puntos; en la tabla de RSSSF cuentan los goles de Talleres y no el de Banfield ("para_local"/"para_visitante"). Otro
    # suspendido se lo dieron ganado a Lanús, y al final varios equipos no se presentaron (sin goles). Defensores de
    # Belgrano y Tigre, empatados en el puesto 30, jugaron un desempate para no quedar entre los cuatro últimos (en
    # "playoffs"; ganó Defensores), pero no bajó nadie: los cuatro últimos eran fundadores de la asociación, que solo
    # bajaban la segunda vez. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, con los goles de algunos partidos, sin
    # minutos)
    "1927-primera": {"nombre": "Campeonato de Primera División 1927 (amateur)", "anio": 1927, "liga": "a_mano",
                     "slug": "1927-primera", "zonas": "unica", "fechas": 33, "pasan": 0, "puntos_victoria": 2,
                     "campeon_tabla": True,
                     "descuentos": {"talleres-remedios-de-escalada": 2},
                     "descuentos_texto": "A Talleres (Remedios de Escalada) se le descontaron 2 puntos, además de perder "
                                         "los del partido con Banfield de la fecha 1, que había ganado.",
                     "orden_texto": "Campeonato amateur: hasta 1930 todo el fútbol argentino era amateur; el profesionalismo "
                                    "empezó en 1931. Fue el primero después de la unificación de las dos ligas que hubo de 1919 "
                                    "a 1926. Orden: puntos y, con los mismos puntos, la diferencia de gol (que coincide con "
                                    "el orden de RSSSF). Almagro se llamaba Sportivo Almagro; Argentino de Lomas, Argentino "
                                    "de Banfield.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1927 (amateur). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el "
                                        "goleador del torneo fue Domingo Tarasconi (Boca), con 35 goles.",
                     "nombre_playoffs": "Desempate", "sin_cuadro": True,
                     "playoffs": [(r"^$^", "Desempate por el puesto 30")],
                     "playoffs_a_mano": {
                         "Desempate por el puesto 30": [
                             {"fecha": "1928-04-05", "local": "defensores-de-belgrano", "visitante": "tigre", "gl": 1, "gv": 1,
                              "estadio": "Cancha de Sportivo Barracas",
                              "goles": [{"jugador": "Caldas", "equipo": "local"}, {"jugador": "Poletti", "equipo": "visitante"}]},
                             {"fecha": "1928-04-08", "local": "defensores-de-belgrano", "visitante": "tigre", "gl": 1, "gv": 0,
                              "estadio": "Cancha de Sportivo Barracas",
                              "goles": [{"jugador": "Caldas", "equipo": "local"}]},
                         ],
                     },
                     "sin_descensos": "No bajó nadie: los cuatro últimos (Tigre, que perdió el desempate con Defensores de "
                                      "Belgrano por el puesto 30, San Isidro, Estudiantes de Buenos Aires y Porteño) eran "
                                      "fundadores de la asociación, que solo bajaban la segunda vez que quedaban entre los "
                                      "cuatro últimos."},
    # 1928: el campeonato de la Asociación Amateurs Argentina de Football (abril de 1928 a julio de 1929; campeón Huracán):
    # 36 equipos a una rueda (35 fechas), con 2 puntos por partido ganado. Un partido suspendido se lo dieron ganado a
    # Tigre, con los goles del partido en la tabla, y en otro no se presentó ninguno de los dos ("para_local"/
    # "para_visitante"); los que se terminaron o se volvieron a jugar van una sola vez, con el resultado final. San Isidro,
    # Vélez y Argentino de Quilmes, empatados en puntos, en el orden de RSSSF ("orden_a_mano"). Bajaron Liberal Argentino y
    # Porteño: los clubes fundadores de la asociación (Argentino del Sud y Defensores de Belgrano) solo bajaban la segunda
    # vez que quedaban entre los cuatro últimos ("descienden_clubes"). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF,
    # con los goles de algunos partidos, sin minutos)
    "1928-primera": {"nombre": "Campeonato de Primera División 1928 (amateur)", "anio": 1928, "liga": "a_mano",
                     "slug": "1928-primera", "zonas": "unica", "fechas": 35, "pasan": 0, "puntos_victoria": 2,
                     "campeon_tabla": True,
                     "orden_a_mano": ["san-isidro", "velez-sarsfield", "argentino-de-quilmes"],
                     "orden_texto": "Campeonato amateur: hasta 1930 todo el fútbol argentino era amateur; el profesionalismo "
                                    "empezó en 1931. Orden: puntos y, con los mismos puntos, la diferencia de gol; San Isidro, "
                                    "Vélez y Argentino de Quilmes, con los mismos puntos, en el orden de RSSSF. Argentino de "
                                    "Lomas se llamaba Argentino de Banfield.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1928 (amateur). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). RSSSF no dice quién "
                                        "fue el goleador del torneo.",
                     "descensos": "tabla", "descienden": 2, "descienden_clubes": ["liberal-argentino", "porteno"],
                     "descienden_texto": "Liberal Argentino y Porteño, de los cuatro últimos; Argentino del Sud y "
                                         "Defensores de Belgrano no bajaron porque, como fundadores de la asociación, solo "
                                         "bajaban la segunda vez que quedaban entre los cuatro últimos"},
    # 1929: el campeonato de la Asociación Amateurs Argentina de Football (julio de 1929 a febrero de 1930; campeón
    # Gimnasia), que se contó como el de 1929 porque el oficial no se jugó: 35 equipos en dos zonas a una rueda (la
    # Impar, de 18, y la Par, de 17; 17 fechas), con 2 puntos por partido ganado. Al final, muchos equipos se retiraron
    # o no se presentaron, y perdían todos los partidos que les faltaban ("para_local"/"para_visitante", sin goles); a
    # los suspendidos que la asociación le dio ganados a uno se les cuentan los goles, como en la tabla de RSSSF. En la
    # Par, Boca y San Lorenzo empataron el primer puesto y lo desempataron en tres partidos ("playoffs"; Boca va primero,
    # "orden_a_mano", como Defensores de Belgrano delante de Sportivo Buenos Aires, el orden de RSSSF). La final, entre los
    # primeros de cada zona, la ganó Gimnasia; el partido por el tercer puesto lo ganó River porque San Lorenzo no se
    # presentó ("gana"). No hubo descensos. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los de la
    # final)
    "1929-primera": {"nombre": "Campeonato de Primera División 1929 (amateur)", "anio": 1929, "liga": "a_mano",
                     "slug": "1929-primera",
                     "zonas_a_mano": {
                         "Zona Impar": ["gimnasia-y-esgrima", "river-plate", "lanus", "racing-club", "almagro",
                                        "talleres-remedios-de-escalada", "san-fernando", "colegiales", "el-porvenir",
                                        "estudiantes-de-la-plata", "tigre", "argentino-del-sud", "banfield", "huracan",
                                        "atlanta", "san-isidro", "estudiantes-buenos-aires", "platense"],
                         "Zona Par": ["boca-juniors", "san-lorenzo", "independiente", "estudiantil-porteno",
                                      "chacarita-juniors", "velez-sarsfield", "argentinos-juniors", "barracas-central",
                                      "sportivo-palermo", "quilmes", "defensores-de-belgrano", "sportivo-buenos-aires",
                                      "excursionistas", "argentino-de-quilmes", "argentino-de-lomas", "ferro-carril-oeste",
                                      "sportivo-barracas"]},
                     "fechas": 17, "pasan": 2, "puntos_victoria": 2,
                     "orden_a_mano": ["boca-juniors", "san-lorenzo", "defensores-de-belgrano", "sportivo-buenos-aires"],
                     "texto_pasan": "Los dos primeros de cada zona: los primeros jugaron la final y los segundos, el partido "
                                    "por el tercer puesto (en la Zona Par, Boca y San Lorenzo empataron el primer puesto y lo "
                                    "desempataron en tres partidos)",
                     "orden_texto": "Campeonato amateur: hasta 1930 todo el fútbol argentino era amateur; el profesionalismo "
                                    "empezó en 1931. Se contó como el campeonato de 1929 porque el oficial no se jugó. Al "
                                    "final muchos equipos se retiraron o no se presentaron, y perdieron todos los partidos que "
                                    "les faltaban. Orden: puntos y, con los mismos puntos, la diferencia de gol; Boca va "
                                    "delante de San Lorenzo por el desempate, y Defensores de Belgrano delante de Sportivo "
                                    "Buenos Aires, como en RSSSF. Argentino de Lomas se llamaba Argentino de Banfield.",
                     "goleadores_nota": "Los goles son solo de la final (de RSSSF, con los minutos).",
                     "nombre_playoffs": "Fase final",
                     "cuadro_desde": "Final",
                     "playoffs": [(r"^$^", n) for n in ("Desempate de la Zona Par", "Tercer puesto", "Final")],
                     "playoffs_a_mano": {
                         "Desempate de la Zona Par": [
                             {"fecha": "1930-01-19", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 2, "gv": 2,
                              "estadio": "Cancha de River Plate"},
                             {"fecha": "1930-01-26", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 2, "gv": 2,
                              "estadio": "Cancha de Racing Club"},
                             {"fecha": "1930-02-02", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 3, "gv": 1,
                              "estadio": "Cancha de River Plate"},
                         ],
                         "Tercer puesto": [
                             {"fecha": "1930-02-09", "local": "river-plate", "visitante": "san-lorenzo", "gl": 0, "gv": 0,
                              "gana": "river-plate", "sin_goles": True, "estadio": "Cancha de Racing Club",
                              "nota": "No se jugó: San Lorenzo no se presentó y perdió el partido."},
                         ],
                         "Final": [
                             {"fecha": "1930-02-09", "local": "boca-juniors", "visitante": "gimnasia-y-esgrima", "gl": 1, "gv": 2,
                              "estadio": "Cancha de River Plate",
                              "goles": [{"jugador": "Di Giano", "equipo": "local", "min": 30, "tipo": "ec"},
                                        {"jugador": "Maleanni", "equipo": "visitante", "min": 62},
                                        {"jugador": "Maleanni", "equipo": "visitante", "min": 70}]},
                         ],
                     },
                     "sin_descensos": "No hubo descensos: en 1930 jugaron los mismos 35 equipos y subió Honor y Patria."},
    # 1930: el último campeonato de la era amateur antes de la división de 1931, de la Asociación Amateurs Argentina de
    # Football (marzo de 1930 a abril de 1931; campeón Boca): 36 equipos a una rueda (35 fechas), con 2 puntos por partido
    # ganado. Varios partidos se suspendieron y quedaron con el resultado del momento; en tres, la asociación le dio los
    # puntos a uno, con los goles del partido en la tabla ("para_local"/"para_visitante"); los que se terminaron o se
    # volvieron a jugar van una sola vez, con el resultado final. Al final, varios equipos no se presentaron
    # ("para_local"/"para_visitante", sin goles). Tres equipos empataron en puntos y en diferencia de gol: en el orden de
    # RSSSF ("orden_a_mano"). Bajaban los dos últimos: Honor y Patria y Argentino del Sud. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, con los goles de algunos partidos, sin minutos)
    "1930-primera": {"nombre": "Campeonato de Primera División 1930 (amateur)", "anio": 1930, "liga": "a_mano",
                     "slug": "1930-primera", "zonas": "unica", "fechas": 35, "pasan": 0, "puntos_victoria": 2,
                     "campeon_tabla": True,
                     "orden_a_mano": ["defensores-de-belgrano", "el-porvenir", "excursionistas"],
                     "orden_texto": "Campeonato amateur: hasta 1930 todo el fútbol argentino era amateur; el profesionalismo "
                                    "empezó en 1931. Orden: puntos y, con los mismos puntos, la diferencia de gol; Defensores "
                                    "de Belgrano, El Porvenir y Excursionistas, con los mismos puntos y la misma diferencia de "
                                    "gol, en el orden de RSSSF. Argentino de Lomas se llamaba Argentino de Banfield.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1930 (amateur). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo de algunos partidos (de RSSSF, sin minutos). Según RSSSF, el "
                                        "goleador del torneo fue Roberto Cherro (Boca), con 37 goles.",
                     "descensos": "tabla", "descienden": 2},
    # 1931 (amateur): el campeonato de la Asociación Amateurs Argentina de Football (desde junio, Asociación Argentina de
    # Football, Amateurs y Profesionales), el que se jugó desde junio, después de que los clubes grandes se fueran a la
    # liga profesional (junio a diciembre; campeón Estudiantil Porteño): 16 equipos a una rueda, con 2 puntos por partido
    # ganado. Almagro y Estudiantil Porteño empataron el primer puesto y jugaron una final (en "playoffs"; ganó
    # Estudiantil Porteño). Sin los partidos de San Isidro, que se fue en julio (anulados). RSSSF no dice a qué fecha
    # pertenece cada partido: se deduce por los días (16 fechas). Bajaba el último: San Fernando. ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo los de la final)
    "1931-amateur": {"nombre": "Campeonato de Primera División 1931 (amateur)", "anio": 1931, "liga": "a_mano",
                     "slug": "1931-amateur", "zonas": "unica", "fechas": 16, "pasan": 2, "puntos_victoria": 2,
                     "texto_pasan": "Empatados en el primer puesto (26 puntos): definieron el título en una final, en la "
                                    "cancha de Sportivo Barracas",
                     "orden_texto": "Campeonato amateur: el de la asociación amateur, que de 1931 a 1934 se jugó al mismo "
                                    "tiempo que el profesional de la Liga Argentina de Football; la AFA reconoce a los "
                                    "campeones de los dos. Es el que se jugó desde junio, después de que los clubes grandes "
                                    "se fueran a la liga profesional. Orden: puntos y, con los mismos puntos, el de RSSSF "
                                    "(que coincide con la diferencia de gol). Las fechas son deducidas (RSSSF da solo los "
                                    "días). Argentino de Lomas se llamaba Argentino de Banfield hasta septiembre.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1931 amateur (las 15 fechas), sin la "
                                    "final. Cada partido ganado valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo de la final (de RSSSF, con los minutos). Según RSSSF, el goleador "
                                        "del torneo fue Justo Ciancia (Almagro), con 14 goles.",
                     "nombre_playoffs": "Final (desempate)",
                     "playoffs": [(r"^$^", "Final")],
                     "playoffs_a_mano": {
                         "Final": [
                             {"fecha": "1931-12-27", "local": "estudiantil-porteno", "visitante": "almagro", "gl": 3, "gv": 1,
                              "estadio": "Cancha de Sportivo Barracas", "arbitro": "Cirilo Garigliano", "publico": 4000,
                              "goles": [{"jugador": "Martínez", "equipo": "local", "min": 25},
                                        {"jugador": "Fernández", "equipo": "visitante", "min": 42},
                                        {"jugador": "Bissio", "equipo": "local", "min": 70},
                                        {"jugador": "Martínez", "equipo": "local", "min": 84}]},
                         ],
                     },
                     "descensos": "tabla", "descienden": 1},
    # 1931: el primer campeonato profesional, de la Liga Argentina de Football, que formaron ese año los clubes grandes al
    # irse de la asociación amateur (mayo de 1931 a enero de 1932; campeón Boca): 18 equipos a dos ruedas (34 fechas),
    # con 2 puntos por partido ganado; la AFA reconoce también al campeón amateur de ese año. Con árbitro y público
    # (entradas vendidas) de cada partido. Dos partidos suspendidos se dieron por ganados en el escritorio y uno lo perdió
    # Platense por no presentarse a terminarlo, sin contar sus goles en la tabla ("para_local"), como en la tabla oficial
    # que da RSSSF; otro se dio por terminado con el resultado del momento. No había descensos. ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo los del Boca-Talleres de la fecha 33)
    "1931-laf": {"nombre": "Campeonato de Primera División 1931 (Liga Argentina de Football)", "anio": 1931, "liga": "a_mano",
                 "slug": "1931-laf", "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                 "orden_texto": "El primer campeonato profesional: el de la Liga Argentina de Football, que formaron ese año "
                                "los clubes grandes al irse de la asociación amateur; ese año hubo también un campeonato "
                                "amateur, y la AFA reconoce a los dos campeones. Orden: puntos y, con los mismos puntos, el "
                                "de RSSSF (que coincide con la diferencia de gol). La tabla es la oficial: sin los goles de "
                                "los partidos dados por ganados en el escritorio.",
                 "goleadores_nota": "Los goles son solo del Boca 4-2 Talleres de la fecha 33, el partido en el que Boca salió "
                                    "campeón (de RSSSF, con los minutos). El goleador del torneo fue Alberto Zozaya "
                                    "(Estudiantes), con 33 goles.",
                 "sin_descensos": "No había descensos."},
    # 1932 (amateur): el campeonato de la Asociación Argentina de Football (Amateurs y Profesionales), la liga amateur
    # (marzo de 1932 a enero de 1933; campeón Sportivo Barracas): 17 equipos a dos ruedas, con 2 puntos por partido
    # ganado. RSSSF no dice a qué fecha pertenece cada partido: se deduce por los días, y los no jugados van donde los dos
    # tenían lugar (quedan 36 fechas). Sportivo Palermo perdió la afiliación y le dieron por perdidos los partidos que le
    # faltaban; al final, varios equipos no se presentaron ("para_local"/"para_visitante", sin goles). Nueva Chicago y
    # Sportivo Buenos Aires jugaron un desempate por el descenso (en "playoffs") que no se terminó: la asociación cambió
    # las reglas y ninguno bajó. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, con los goles de cada partido, sin
    # minutos)
    "1932-amateur": {"nombre": "Campeonato de Primera División 1932 (amateur)", "anio": 1932, "liga": "a_mano",
                     "slug": "1932-amateur", "zonas": "unica", "fechas": 36, "pasan": 0, "puntos_victoria": 2,
                     "campeon_tabla": True,
                     "orden_texto": "Campeonato amateur: el de la Asociación Argentina de Football, que de 1931 a 1934 se "
                                    "jugó al mismo tiempo que el profesional de la Liga Argentina de Football; la AFA "
                                    "reconoce a los campeones de los dos. Orden: puntos y, con los mismos puntos, el de RSSSF "
                                    "(que coincide con la diferencia de gol). Las fechas son deducidas (RSSSF da solo los "
                                    "días). En la tabla, Sportivo Barracas y Estudiantil Porteño tienen un gol de diferencia "
                                    "con la de RSSSF.",
                     "goleadores_nota": "Los goles son de RSSSF (sin los minutos, salvo un partido; algunos nombres van "
                                        "unificados). Faltan los de varios partidos, en los que RSSSF no los trae. RSSSF da "
                                        "como goleadores a Juan Carlos Irurieta (All Boys), con 24, Prudencio Lamazou "
                                        "(Barracas Central), con 22, y Mario Fortunato (Sportivo Barracas), con 21.",
                     "nombre_playoffs": "Desempate por el descenso",
                     "playoffs": [(r"^$^", "Desempate por el descenso")],
                     "playoffs_a_mano": {
                         "Desempate por el descenso": [
                             {"fecha": "1933-01-29", "local": "nueva-chicago", "visitante": "sportivo-buenos-aires", "gl": 2, "gv": 2,
                              "estadio": "Cancha de Sportivo Barracas",
                              "goles": [{"jugador": "Castillo", "equipo": "local"}, {"jugador": "Mercado", "equipo": "local"},
                                        {"jugador": "Benedetti", "equipo": "visitante"}, {"jugador": "López", "equipo": "visitante"}]},
                             {"fecha": "1933-02-04", "local": "sportivo-buenos-aires", "visitante": "nueva-chicago", "gl": 1, "gv": 1,
                              "estadio": "Cancha de Sportivo Barracas",
                              "goles": [{"jugador": "Apolito", "equipo": "local"}, {"jugador": "Sanabria", "equipo": "visitante"}]},
                             {"fecha": "1933-02-18", "local": "nueva-chicago", "visitante": "sportivo-buenos-aires", "gl": 2, "gv": 2,
                              "estadio": "Cancha de Sportivo Barracas",
                              "goles": [{"jugador": "Sanabria", "equipo": "local"}, {"jugador": "Sanabria", "equipo": "local"},
                                        {"jugador": "Fussani", "equipo": "visitante"}, {"jugador": "Fussani", "equipo": "visitante"}],
                              "nota": "Hacía falta un cuarto partido, pero no se jugó: la asociación cambió las reglas y "
                                      "ninguno de los dos bajó."},
                         ],
                     },
                     "cuadro": {"bloques": [("Desempate por el descenso", [["Desempate por el descenso"]])],
                                "nota": "Los tres partidos terminaron empatados."},
                     "sin_descensos": "No hubo descensos por la tabla: Sportivo Palermo, que había perdido la afiliación, "
                                      "quedó afuera, y el desempate entre Nueva Chicago y Sportivo Buenos Aires no se terminó."},
    # 1932: dos campeonatos de Primera, como hasta 1934, y la AFA reconoce a los dos campeones. El profesional, de la Liga
    # Argentina de Football (marzo a noviembre; campeón River): 18 equipos a dos ruedas (34 fechas), con 2 puntos por
    # partido ganado. River e Independiente empataron el primer puesto y jugaron una final en la cancha de San Lorenzo (en
    # "playoffs"; ganó River). Seis partidos se suspendieron y la Liga se los dio ganados a uno ("para_local", sin contar
    # los goles, como RSSSF); otros dos se terminaron otro día. No había descensos. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles salvo los de la final)
    "1932-laf": {"nombre": "Campeonato de Primera División 1932 (Liga Argentina de Football)", "anio": 1932, "liga": "a_mano",
                 "slug": "1932-laf", "zonas": "unica", "fechas": 34, "pasan": 2, "puntos_victoria": 2,
                 "texto_pasan": "Empatados en el primer puesto (50 puntos): definieron el título en una final, en la cancha de "
                                "San Lorenzo",
                 "orden_texto": "Fue el campeonato profesional, de la Liga Argentina de Football; ese año hubo también uno "
                                "amateur, el de la Asociación Argentina de Football, y la AFA reconoce a los dos campeones. "
                                "Orden: puntos y, con los mismos puntos, el de RSSSF (que coincide con la diferencia de gol).",
                 "goleadores_nota": "Los goles son solo de la final (de RSSSF, con los minutos). El goleador del torneo fue "
                                    "Bernabé Ferreyra (River), con 43 goles según RSSSF (44 según Wikipedia).",
                 "nombre_playoffs": "Final (desempate)",
                 "playoffs": [(r"^$^", "Final")],
                 "playoffs_a_mano": {
                     "Final": [
                         {"fecha": "1932-11-20", "local": "river-plate", "visitante": "independiente", "gl": 3, "gv": 0,
                          "estadio": "El Gasómetro",
                          "goles": [{"jugador": "Ferreyra", "equipo": "local", "min": 11},
                                    {"jugador": "Peucelle", "equipo": "local", "min": 22},
                                    {"jugador": "Zatelli", "equipo": "local", "min": 38}]},
                     ],
                 },
                 "sin_descensos": "No había descensos."},
    # 1933 (amateur): el campeonato de la Asociación Argentina de Football (Amateurs y Profesionales), la liga amateur
    # (abril a noviembre; campeón Dock Sud): 20 equipos a una rueda (19 fechas), con 2 puntos por partido ganado. RSSSF no
    # dice a qué fecha pertenece cada partido: se deduce por los días. Cinco partidos no se jugaron y se dieron por
    # perdidos al que no se presentó ("para_local"/"para_visitante", sin goles). ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, con los goles de cada partido, sin minutos)
    "1933-amateur": {"nombre": "Campeonato de Primera División 1933 (amateur)", "anio": 1933, "liga": "a_mano",
                     "slug": "1933-amateur", "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                     "campeon_tabla": True,
                     "orden_texto": "Campeonato amateur: el de la Asociación Argentina de Football, que de 1931 a 1934 se "
                                    "jugó al mismo tiempo que el profesional de la Liga Argentina de Football; la AFA "
                                    "reconoce a los campeones de los dos. Orden: puntos y, con los mismos puntos, el de RSSSF "
                                    "(que coincide con la diferencia de gol). En la tabla, All Boys y Colegiales tienen un gol "
                                    "de diferencia con la de RSSSF: su partido figura 2-1, pero la tabla de RSSSF lo cuenta "
                                    "distinto.",
                     "goleadores_nota": "Los goles son de RSSSF (sin los minutos; algunos nombres van unificados). Faltan los "
                                        "de cinco partidos, en los que RSSSF no los trae completos.",
                     "sin_descensos": "No hubo descensos."},
    # 1933: como en 1934, dos campeonatos de Primera, y la AFA reconoce a los dos campeones. El profesional, de la Liga
    # Argentina de Football (marzo a noviembre; campeón San Lorenzo): 18 equipos a dos ruedas (34 fechas), con 2 puntos
    # por partido ganado. River y Gimnasia empataron en puntos y en diferencia de gol: va River delante, como en RSSSF y
    # Wikipedia ("orden_a_mano"; el cociente de goles). No había descensos: para 1934 la Liga dejó afuera a Quilmes y a
    # Tigre, e hizo jugar fusionados a Lanús con Talleres y a Atlanta con Argentinos. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles salvo el del Chacarita-San Lorenzo de la fecha 34). No había Libertadores
    "1933-laf": {"nombre": "Campeonato de Primera División 1933 (Liga Argentina de Football)", "anio": 1933, "liga": "a_mano",
                 "slug": "1933-laf", "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                 "orden_a_mano": ["river-plate", "gimnasia-y-esgrima"],
                 "orden_texto": "Fue el campeonato profesional, de la Liga Argentina de Football; ese año hubo también uno "
                                "amateur, el de la Asociación Argentina de Football, y la AFA reconoce a los dos campeones. "
                                "Orden: puntos y, con los mismos puntos, la diferencia de gol; River y Gimnasia, con los "
                                "mismos puntos y la misma diferencia de gol, en el orden de RSSSF y Wikipedia (por el cociente "
                                "de goles).",
                 "goleadores_nota": "El gol es solo el del Chacarita 0-1 San Lorenzo de la última fecha, el partido en el que "
                                    "San Lorenzo salió campeón (de RSSSF, con el minuto). El goleador del torneo fue Francisco "
                                    "Varallo (Boca), con 34 goles.",
                 "sin_descensos": "No había descensos. Pero para 1934 la Liga dejó afuera a Quilmes y a Tigre, e hizo jugar "
                                  "fusionados a Lanús con Talleres y a Atlanta con Argentinos (los seis últimos de esta tabla)."},
    # 1934 (amateur): el último campeonato de la Asociación Argentina de Football (Amateurs y Profesionales), la liga
    # amateur que siguió jugándose de 1931 a 1934 junto a la profesional (abril a octubre; campeón Estudiantil Porteño): 23
    # equipos a una rueda (23 fechas, uno libre en cada una), con 2 puntos por partido ganado. La AFA reconoce a su campeón
    # (y al de la profesional). Cuatro partidos no se jugaron y se dieron por perdidos al que no se presentó, y a Ramsar le
    # dieron por perdido un 1-1 con Estudiantes (sin contar los goles, como RSSSF; "para_local"/"para_visitante"). Al
    # unirse las dos ligas en la AFA, estos equipos pasaron a la Segunda y la Tercera División. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, con los goles de cada partido, sin minutos)
    "1934-amateur": {"nombre": "Campeonato de Primera División 1934 (amateur)", "anio": 1934, "liga": "a_mano",
                     "slug": "1934-amateur", "zonas": "unica", "fechas": 23, "pasan": 0, "puntos_victoria": 2,
                     "campeon_tabla": True,
                     "orden_texto": "Campeonato amateur: el de la Asociación Argentina de Football, que de 1931 a 1934 se "
                                    "jugó al mismo tiempo que el profesional de la Liga Argentina de Football; la AFA "
                                    "reconoce a los campeones de los dos. Orden: puntos y, con los mismos puntos, el de RSSSF "
                                    "(que coincide con la diferencia de gol). Argentino de Temperley se llamó Temperley desde "
                                    "1935, según RSSSF.",
                     "goleadores_nota": "Los goles son de RSSSF (sin los minutos; RSSSF escribe algunos nombres de varias "
                                        "formas, y acá van unificados). Faltan los del Nueva Chicago 1-2 Argentino de "
                                        "Temperley (RSSSF trae dos de los tres). Wikipedia da como goleadores a Pedro Maseda (Argentino de Quilmes) y "
                                        "Domingo Tarasconi (General San Martín), con 16 goles.",
                     "sin_descensos": "No hubo descensos: al unirse las dos ligas en la AFA, en noviembre de 1934, estos "
                                      "equipos pasaron a la Segunda y la Tercera División."},
    # 1934: hubo dos campeonatos de Primera, y la AFA reconoce a los dos campeones. El profesional, de la Liga Argentina
    # de Football (marzo a diciembre; campeón Boca): 14 equipos a tres ruedas (39 fechas), con 2 puntos por partido
    # ganado. Lanús y Talleres (Remedios de Escalada) jugaron fusionados ("Unión Talleres-Lanús", club propio, con los dos
    # escudos juntos); Atlanta y Argentinos también, hasta la fecha 25, y después siguió Argentinos solo (va como
    # Argentinos todo el año, como en la tabla de RSSSF). Dos partidos se suspendieron y se dieron por terminados (el
    # Gimnasia-Estudiantes, ganado por Gimnasia en el escritorio: "para_local", con el gol que había hecho Estudiantes).
    # No había descensos. El 3 de noviembre la Liga y la Asociación Argentina (amateur) se unieron en la AFA. ESPN no lo
    # tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del Boca-Platense de la fecha 38). No había Libertadores
    "1934-laf": {"nombre": "Campeonato de Primera División 1934 (Liga Argentina de Football)", "anio": 1934, "liga": "a_mano",
                 "slug": "1934-laf", "zonas": "unica", "fechas": 39, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                 "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que en este torneo coincide con la "
                                "diferencia de gol). Fue el campeonato profesional, de la Liga Argentina de Football: 14 "
                                "equipos a tres ruedas. Lanús y Talleres (Remedios de Escalada) jugaron fusionados, y "
                                "Argentinos jugó fusionado con Atlanta hasta la fecha 25. Ese año hubo también un "
                                "campeonato amateur, el de la Asociación Argentina de Football; la AFA reconoce a los dos "
                                "campeones.",
                 "goleadores_nota": "Los goles son solo del Boca 5-1 Platense de la fecha 38, el partido en el que Boca salió "
                                    "campeón (de RSSSF, con los minutos). El goleador del torneo fue Evaristo Barrera "
                                    "(Racing), con 34 goles.",
                 "sin_descensos": "No había descensos."},
    # 1935: el Campeonato de Primera División 1935 (marzo a diciembre; campeón Boca, bicampeón): 18 equipos a dos ruedas
    # (34 fechas), con 2 puntos por partido ganado; el primero después de la unificación de la liga profesional y la
    # amateur en la AFA (1934). No había descensos (empezaron en 1937). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF,
    # sin goles salvo los del Boca-Tigre de la fecha 33; RSSSF no trae la tabla, controlada con la de Wikipedia). No había
    # Libertadores
    "1935-primera": {"nombre": "Campeonato de Primera División 1935", "anio": 1935, "liga": "a_mano", "slug": "1935-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "goleadores_nota": "Los goles son solo del Boca 3-0 Tigre de la fecha 33, el partido en el que Boca salió "
                                        "campeón (de RSSSF, con los minutos). El goleador del torneo fue Agustín Cosso "
                                        "(Vélez), con 33 goles.",
                     "sin_descensos": "No había descensos: empezaron en 1937."},
    # 1936: la temporada se dividió en dos torneos de 18 equipos a una rueda (17 fechas), con 2 puntos por partido ganado:
    # la Copa de Honor (abril a julio; campeón San Lorenzo) y la Copa Campeonato (agosto a diciembre, los desquites;
    # campeón River). Los dos campeones jugaron la Copa de Oro (ganó River). Desde 2013 la AFA cuenta los tres como
    # títulos de liga. No había descensos (empezaron en 1937). En la Copa de Honor, a Talleres (Remedios de Escalada) lo
    # suspendieron un mes y le dieron por perdidos 4 partidos ("para_local"/"para_visitante", sin goles), y el
    # Independiente-Racing se suspendió y se lo dieron ganado a Independiente. ESPN no los tiene: van a mano (tools/a_mano;
    # RSSSF, sin goles salvo los del Atlanta-San Lorenzo de la Copa de Honor y los de la Copa de Oro). No había Libertadores
    "1936-honor": {"nombre": "Copa de Honor 1936", "anio": 1936, "liga": "a_mano", "slug": "1936-honor",
                   "zonas": "unica", "fechas": 17, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                   "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que en este torneo coincide con la "
                                  "diferencia de gol). La Copa de Honor fue la primera rueda de 1936; la segunda fue la Copa "
                                  "Campeonato, y los dos campeones jugaron después la Copa de Oro. Los tres cuentan como "
                                  "títulos de liga para la AFA (desde 2013).",
                   "goleadores_nota": "Los goles son solo del Atlanta 2-3 San Lorenzo de la fecha 16, el partido en el que San "
                                      "Lorenzo ganó la Copa de Honor (de RSSSF, con los minutos). El goleador fue Alberto "
                                      "Zozaya (Estudiantes), con 16 goles.",
                   "sin_descensos": "No había descensos: empezaron en 1937."},
    "1936-campeonato": {"nombre": "Copa Campeonato 1936", "anio": 1936, "liga": "a_mano", "slug": "1936-campeonato",
                        "zonas": "unica", "fechas": 17, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                        "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide "
                                       "con la diferencia de gol). La Copa Campeonato fue la segunda rueda de 1936 (los "
                                       "desquites de la Copa de Honor).",
                        "anual": [("a_mano", r"^1936-honor$")],
                        "anual_texto": "La tabla del año 1936: suma la Copa de Honor y la Copa Campeonato (con 2 puntos por "
                                       "partido ganado), sin la Copa de Oro.",
                        "goleadores_nota": "De la Copa Campeonato no hay goles cargados (la lista es solo de la Copa de Oro). "
                                           "El goleador fue Evaristo Barrera (Racing), con 19 goles.",
                        "nombre_playoffs": "Copa de Oro",
                        "playoffs": [(r"^$^", "Copa de Oro")],
                        "playoffs_a_mano": {
                            "Copa de Oro": [
                                {"fecha": "1936-12-20", "local": "river-plate", "visitante": "san-lorenzo", "gl": 4, "gv": 2,
                                 "estadio": "La Doble Visera",
                                 "goles": [{"jugador": "Cesarini", "equipo": "local", "min": 39},
                                           {"jugador": "Pantó", "equipo": "visitante", "min": 55},
                                           {"jugador": "Chividini", "equipo": "local", "min": 73, "tipo": "ec"},
                                           {"jugador": "Pedernera", "equipo": "local", "min": 76},
                                           {"jugador": "Cavadini", "equipo": "visitante", "min": 81},
                                           {"jugador": "Cesarini", "equipo": "local", "min": 86}],
                                 "nota": "La Copa de Oro, entre los campeones de la Copa Campeonato (River) y de la Copa de "
                                         "Honor (San Lorenzo): ganó River. El gol de San Lorenzo del minuto 81 fue de Cavadini "
                                         "según RSSSF (de Canteli, según otras fuentes)."},
                            ],
                        },
                        "sin_descensos": "No había descensos: empezaron en 1937."},
    # 1937: el Campeonato de Primera División 1937 (abril a diciembre; campeón River, tricampeón con la Copa Campeonato y
    # la Copa de Oro de 1936): 18 equipos a dos ruedas (34 fechas), con 2 puntos por partido ganado. River y Boca empataron
    # la primera rueda y la desempataron recién en febrero de 1939 (en "playoffs"; no daba un título). Por primera vez en el
    # profesionalismo bajaban los dos últimos de la tabla (no había promedios): Argentinos Juniors y Quilmes. ESPN no lo
    # tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del Argentinos-River de la fecha 32; RSSSF no trae la
    # tabla, controlada con la de Wikipedia). No había Libertadores todavía
    "1937-primera": {"nombre": "Campeonato de Primera División 1937", "anio": 1937, "liga": "a_mano", "slug": "1937-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1937 (las 34 fechas), sin el desempate. Cada "
                                    "partido ganado valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Argentinos 0-6 River de la fecha 32, el partido en el que River "
                                        "salió campeón (de RSSSF, con los minutos). El goleador del torneo fue Arsenio Erico "
                                        "(Independiente), con 47 goles.",
                     "nombre_playoffs": "Desempate",
                     "playoffs": [(r"^$^", "Desempate por la primera rueda")],
                     "playoffs_a_mano": {
                          "Desempate por la primera rueda": [
                              {"fecha": "1939-02-11", "local": "river-plate", "visitante": "boca-juniors", "gl": 5, "gv": 3, "estadio": "El Gasómetro", "goles": [],
                               "nota": "Recién en febrero de 1939. River y Boca habían empatado el primer puesto de la primera rueda: "
                                       "la ganó River (no daba un título de liga)."},
                          ],
                     },
                     "descensos": "tabla", "descienden": 2},
    # 1938: el Campeonato de Primera División 1938 (abril a diciembre; campeón Independiente): 17 equipos a dos ruedas (34
    # fechas, en cada una quedaba uno libre), con 2 puntos por partido ganado. Con los mismos puntos, el orden de Wikipedia:
    # el cociente de goles (Boca delante de Gimnasia, "orden_a_mano"). Bajaban los dos últimos de la tabla (no había
    # promedios): Almagro y Talleres (Remedios de Escalada). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles
    # salvo los del Independiente-Lanús de la fecha 34; RSSSF no trae la tabla, controlada con la de Wikipedia). No había
    # Libertadores todavía
    "1938-primera": {"nombre": "Campeonato de Primera División 1938", "anio": 1938, "liga": "a_mano", "slug": "1938-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["boca-juniors", "gimnasia-y-esgrima", "estudiantes-de-la-plata"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia: el cociente de goles (goles a "
                                    "favor divididos por goles en contra). Así Boca quedó delante de Gimnasia, aunque tenía "
                                    "peor diferencia de gol.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1938 (las 34 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Independiente 8-2 Lanús de la última fecha, el partido en el que "
                                        "Independiente salió campeón (de RSSSF, con los minutos). El goleador del torneo fue "
                                        "Arsenio Erico (Independiente), con 43 goles.",
                     "descensos": "tabla", "descienden": 2},
    # 1939: el Campeonato de Primera División 1939 (marzo a diciembre; campeón Independiente, bicampeón): 18 equipos a dos
    # ruedas (34 fechas), con 2 puntos por partido ganado. Huracán ganó el desempate por la primera rueda (no daba un
    # título). River y Huracán empataron el segundo puesto: el desempate se jugó recién en 1941 (3-3 con alargue) y la
    # revancha nunca se jugó, así que el segundo puesto quedó compartido. Los dos desempates van en "playoffs". El
    # Boca-Ferro de la última fecha se suspendió y se lo dieron ganado a Boca ("para_local", sin contar el gol). Bajaba el
    # último de la tabla (no había promedios): Argentino de Quilmes, sin ningún partido ganado. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles salvo los del Platense-Independiente de la fecha 32). No había Libertadores todavía
    "1939-primera": {"nombre": "Campeonato de Primera División 1939", "anio": 1939, "liga": "a_mano", "slug": "1939-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que en este torneo coincide con la "
                                    "diferencia de gol). River y Huracán, empatados en el segundo puesto, jugaron un "
                                    "desempate que terminó igualado y no se volvió a jugar: el segundo puesto quedó "
                                    "compartido, la única vez en la historia de Primera.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1939 (las 34 fechas), sin los desempates. "
                                    "Cada partido ganado valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Platense 0-2 Independiente de la fecha 32, el partido en el que "
                                        "Independiente salió campeón (de RSSSF, con los minutos). El goleador del torneo fue "
                                        "Arsenio Erico (Independiente), con 40 goles según RSSSF (41 según Wikipedia).",
                     "nombre_playoffs": "Desempates",
                     "playoffs": [(r"^$^", "Desempate por la primera rueda"), (r"^$^", "Desempate por el segundo puesto")],
                     "playoffs_a_mano": {
                          "Desempate por la primera rueda": [
                              {"fecha": "1939-12-10", "local": "huracan", "visitante": "independiente", "gl": 2, "gv": 1, "estadio": "El Gasómetro", "goles": [],
                               "nota": "Para definir el ganador de la primera rueda (no daba un título de liga): ganó Huracán."},
                          ],
                          "Desempate por el segundo puesto": [
                              {"fecha": "1941-11-09", "local": "river-plate", "visitante": "huracan", "gl": 3, "gv": 3, "estadio": "Cancha de Chacarita Juniors",
                               "alargue": True, "goles": [],
                               "nota": "Recién en 1941. Empataron 3-3, con alargue, y la revancha nunca se jugó: el segundo puesto "
                                       "quedó compartido entre River y Huracán."},
                          ],
                     },
                     # (dos desempates sueltos, no un cuadro: cada uno en su parte)
                     "cuadro": {"bloques": [("Desempate por la primera rueda", [["Desempate por la primera rueda"]]),
                                            ("Desempate por el segundo puesto", [["Desempate por el segundo puesto"]])],
                                "nota": "De los desempates hay solo el resultado."},
                     "descensos": "tabla", "descienden": 1},
    # 1940: el Campeonato de Primera División 1940 (abril a diciembre; campeón Boca, el año en que se inauguró la
    # Bombonera): 18 equipos a dos ruedas (34 fechas), con 2 puntos por partido ganado. Por sobornos, la AFA le dio por
    # perdidos a Banfield sus 5 primeros partidos y a Chacarita los de las fechas 22 a 27 ("para_local"/"para_visitante",
    # sin goles; cada uno con su nota); el Vélez-Ferro de la primera fecha también se dio por ganado. Bajaban los dos
    # últimos de la tabla (no había promedios): Vélez y Chacarita. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin
    # goles salvo los del Boca-Independiente de la fecha 32; los partidos, controlados uno por uno con Wikipedia). No había
    # Libertadores todavía
    "1940-primera": {"nombre": "Campeonato de Primera División 1940", "anio": 1940, "liga": "a_mano", "slug": "1940-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol). Por sobornos, la AFA le dio por perdidos a Banfield sus 5 primeros "
                                    "partidos y a Chacarita los de las fechas 22 a 27.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1940 (las 34 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca 5-2 Independiente de la fecha 32, el partido en el que Boca "
                                        "salió campeón (de RSSSF, con los minutos). Los goleadores del torneo fueron Delfín "
                                        "Benítez Cáceres (Racing) e Isidro Lángara (San Lorenzo), con 33 goles.",
                     "descensos": "tabla", "descienden": 2},
    # 1941: el Campeonato de Primera División 1941 (marzo a noviembre; campeón River): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Por un soborno en la fecha 10, a Banfield la AFA lo sancionó por 60 días y le
    # descontó 2 puntos en cada uno de los 8 partidos de ese tiempo (16 en total; cada uno con su nota). Bajaba el último
    # de la tabla (no había promedios): Rosario Central. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo
    # los del Estudiantes-River de la fecha 30). No había Libertadores todavía
    "1941-primera": {"nombre": "Campeonato de Primera División 1941", "anio": 1941, "liga": "a_mano", "slug": "1941-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que en este torneo coincide con la "
                                    "diferencia de gol).",
                     "descuentos": {"banfield": 16},
                     "descuentos_texto": "A Banfield se le descontaron 16 puntos: por un soborno en la fecha 10, la AFA lo "
                                         "sancionó por 60 días, con 2 puntos menos por cada uno de los 8 partidos de ese "
                                         "tiempo. Sin el descuento, hubiese terminado octavo.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1941 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Estudiantes 1-3 River de la última fecha, el partido en el que "
                                        "River salió campeón (de RSSSF, con los minutos). El goleador del torneo fue José "
                                        "Canteli (Newell's), con 30 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1942: el Campeonato de Primera División 1942 (abril a noviembre; campeón River, bicampeón): 16 equipos a dos ruedas
    # (30 fechas), con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Tigre. ESPN no lo
    # tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del Boca-River de la fecha 28; RSSSF no trae la tabla,
    # controlada con la de Wikipedia). No había Libertadores todavía
    "1942-primera": {"nombre": "Campeonato de Primera División 1942", "anio": 1942, "liga": "a_mano", "slug": "1942-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1942 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca 2-2 River de la fecha 28, el partido en el que River salió "
                                        "campeón (de RSSSF, con los minutos). El goleador del torneo fue Rinaldo Martino (San "
                                        "Lorenzo), con 25 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1943: el Campeonato de Primera División 1943 (abril a diciembre; campeón Boca): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Gimnasia. ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo los del Ferro-Boca de la fecha 30; RSSSF no trae la tabla, controlada con
    # la de Wikipedia). No había Libertadores todavía
    "1943-primera": {"nombre": "Campeonato de Primera División 1943", "anio": 1943, "liga": "a_mano", "slug": "1943-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1943 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Ferro 0-2 Boca de la última fecha, el partido en el que Boca "
                                        "salió campeón (de RSSSF, con los minutos). El goleador del torneo fue Luis Arrieta "
                                        "(Lanús), con 23 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1944: el Campeonato de Primera División 1944 (abril a noviembre; campeón Boca): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Banfield. ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo los del Boca-Racing de la fecha 30; RSSSF no trae la tabla, controlada con
    # la de Wikipedia). No había Libertadores todavía
    "1944-primera": {"nombre": "Campeonato de Primera División 1944", "anio": 1944, "liga": "a_mano", "slug": "1944-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1944 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca 3-0 Racing de la última fecha, el partido en el que Boca "
                                        "salió campeón (de RSSSF, con los minutos). El goleador del torneo fue Atilio Mellone "
                                        "(Huracán), con 26 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1945: el Campeonato de Primera División 1945 (abril a diciembre; campeón River): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Gimnasia. Tres partidos se
    # suspendieron y se terminaron otro día (cada uno con su nota). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin
    # goles salvo los del River-Chacarita de la fecha 29; RSSSF no trae la tabla, controlada con la de Wikipedia). No había
    # Libertadores todavía
    "1945-primera": {"nombre": "Campeonato de Primera División 1945", "anio": 1945, "liga": "a_mano", "slug": "1945-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1945 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del River 2-0 Chacarita de la fecha 29, el partido en el que River "
                                        "salió campeón (de RSSSF, con los minutos). El goleador del torneo fue Ángel Labruna "
                                        "(River), con 25 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1946: el Campeonato de Primera División 1946 (abril a diciembre; campeón San Lorenzo): 16 equipos a dos ruedas (30
    # fechas), con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Ferro. Tres partidos se
    # suspendieron y se terminaron otro día (cada uno con su nota). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin
    # goles salvo los del Ferro-San Lorenzo de la fecha 30). No había Libertadores todavía
    "1946-primera": {"nombre": "Campeonato de Primera División 1946", "anio": 1946, "liga": "a_mano", "slug": "1946-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que en este torneo coincide con la "
                                    "diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1946 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Ferro 1-3 San Lorenzo de la fecha 30, el partido en el que San "
                                        "Lorenzo salió campeón (de RSSSF, con los minutos). El goleador del torneo fue Mario "
                                        "Boyé (Boca), con 24 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1947: el Campeonato de Primera División 1947 (abril a noviembre; campeón River, con Di Stéfano): 16 equipos a dos
    # ruedas (30 fechas), con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Atlanta. Cuatro
    # partidos se suspendieron sobre el final y quedó el resultado (cada uno con su nota). ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles salvo los del River-Rosario Central de la fecha 29; RSSSF no trae la tabla, controlada
    # con la de Wikipedia). No había Libertadores todavía
    "1947-primera": {"nombre": "Campeonato de Primera División 1947", "anio": 1947, "liga": "a_mano", "slug": "1947-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1947 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del River 4-0 Rosario Central de la fecha 29, el partido en el que "
                                        "River salió campeón (de RSSSF, con los minutos). El goleador del torneo fue Alfredo "
                                        "Di Stéfano (River), con 27 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1948: el Campeonato de Primera División 1948 (abril a diciembre; campeón Independiente): 16 equipos a dos ruedas (30
    # fechas), con 2 puntos por partido ganado. Hubo una huelga de jugadores y en las últimas fechas los clubes jugaron con
    # juveniles; por eso la AFA anuló los descensos. Racing no se presentó a los dos últimos partidos: se los dieron ganados
    # a Banfield y San Lorenzo ("para_local"/"para_visitante", sin goles) y le descontaron 2 puntos por cada uno. Con los
    # mismos puntos, el orden de RSSSF (el cociente de goles: Tigre delante de Lanús, "orden_a_mano"). ESPN no lo tiene: va
    # a mano (tools/a_mano; RSSSF, sin goles salvo los del Gimnasia-Independiente de la fecha 29). No había Libertadores
    "1948-primera": {"nombre": "Campeonato de Primera División 1948", "anio": 1948, "liga": "a_mano", "slug": "1948-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["tigre", "lanus"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF: el cociente de goles (goles a favor "
                                    "divididos por goles en contra). Así Tigre quedó delante de Lanús, aunque tenía peor "
                                    "diferencia de gol.",
                     "descuentos": {"racing-club": 4},
                     "descuentos_texto": "A Racing se le descontaron 4 puntos, 2 por cada uno de los dos últimos partidos, "
                                         "a los que no se presentó (y que además perdió).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1948 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Gimnasia 1-4 Independiente de la fecha 29, el partido en el que "
                                        "Independiente salió campeón (de RSSSF, con los minutos). El goleador del torneo fue "
                                        "Benjamín Santos (Rosario Central), con 21 goles.",
                     "sin_descensos": "No hubo descensos: hubo una huelga de jugadores (en las últimas fechas los clubes "
                                      "jugaron con juveniles) y la AFA los anuló. Gimnasia, el último, se quedó en Primera."},
    # 1949: el Campeonato de Primera División 1949 (abril a diciembre; campeón Racing): 18 equipos a dos ruedas (34 fechas),
    # con 2 puntos por partido ganado. River y Platense empataron el segundo puesto y jugaron un desempate a ida y vuelta
    # (los dos en la cancha de San Lorenzo; River ganó los dos). Bajaba el último: Huracán y Lanús empataron ese lugar y
    # jugaron cuatro partidos (el tercero, 3-3, lo anuló el Tribunal de Penas; el cuarto, en febrero de 1950, se suspendió
    # con Huracán 3-2 arriba y quedó ese resultado): bajó Lanús. Los dos desempates van en "playoffs", partido por partido,
    # y el orden de esos empatados en "orden_a_mano"; los demás empatados en puntos, como RSSSF (que coincide con la
    # diferencia de gol). Dos partidos se suspendieron y se terminaron otro día (con su nota). ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles). No había Libertadores todavía
    "1949-primera": {"nombre": "Campeonato de Primera División 1949", "anio": 1949, "liga": "a_mano", "slug": "1949-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["river-plate", "platense", "huracan", "lanus"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que coincide con la diferencia de "
                                    "gol), salvo dos empates que se definieron en desempates: River y Platense, por el "
                                    "segundo puesto (quedó segundo River), y Huracán y Lanús, por el descenso (bajó Lanús).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1949 (las 34 fechas), sin los desempates. "
                                    "Cada partido ganado valía 2 puntos.",
                     "goleadores_nota": "De este torneo no hay goles cargados. Los goleadores fueron Juan José Pizzuti "
                                        "(Banfield) y Llamil Simes (Racing), con 26 goles.",
                     "nombre_playoffs": "Desempates",
                     "playoffs": [(r"^$^", "Desempate por el segundo puesto"), (r"^$^", "Desempate por el descenso")],
                     "playoffs_a_mano": {
                          "Desempate por el segundo puesto": [
                              {"fecha": "1949-12-14", "local": "platense", "visitante": "river-plate", "gl": 1, "gv": 2, "estadio": "El Gasómetro", "goles": []},
                              {"fecha": "1949-12-26", "local": "river-plate", "visitante": "platense", "gl": 4, "gv": 0, "estadio": "El Gasómetro", "goles": [],
                               "nota": "River ganó los dos partidos y quedó segundo."},
                          ],
                          "Desempate por el descenso": [
                              {"fecha": "1949-12-18", "local": "huracan", "visitante": "lanus", "gl": 1, "gv": 0, "estadio": "El Gasómetro", "goles": []},
                              {"fecha": "1949-12-24", "local": "lanus", "visitante": "huracan", "gl": 4, "gv": 1, "estadio": "La Doble Visera", "goles": [],
                               "nota": "Ganó un partido cada uno (la diferencia de gol no contaba): hubo que jugar un tercero."},
                              {"fecha": "1950-01-08", "local": "huracan", "visitante": "lanus", "gl": 3, "gv": 3, "estadio": "El Gasómetro", "goles": [],
                               "nota": "Ya en 1950. Partido anulado: con 3-3, sobre el final, el árbitro le anuló un gol a Huracán y los jugadores "
                                       "de Huracán se fueron de la cancha; no se jugó el alargue. El Tribunal de Penas de la AFA, en vez "
                                       "de darle el partido a Lanús, lo anuló y mandó jugarlo de nuevo."},
                              {"fecha": "1950-02-16", "local": "lanus", "visitante": "huracan", "gl": 2, "gv": 3, "estadio": "Monumental", "goles": [],
                               "nota": "Ya en 1950. Se suspendió a los 80 minutos, con Huracán 3-2 arriba: a Lanús le cobraron un penal en contra y "
                                       "sus jugadores se fueron de la cancha. Quedó ese resultado: Huracán se quedó en Primera y Lanús "
                                       "bajó a la Primera B, por primera vez en su historia."},
                          ],
                     },
                     # (dos desempates sueltos, no un cuadro: cada uno en su parte, partido por partido)
                     "cuadro": {"bloques": [("Desempate por el segundo puesto", [["Desempate por el segundo puesto"]]),
                                            ("Desempate por el descenso", [["Desempate por el descenso"]])],
                                "nota": "De los desempates hay solo el resultado."},
                     "descensos": "tabla", "descienden": 1},
    # 1950: el Campeonato de Primera División 1950 (abril a noviembre; campeón Racing): 18 equipos a dos ruedas (34 fechas),
    # con 2 puntos por partido ganado. Bajaban el último (Rosario Central) y el anteúltimo: Huracán y Tigre empataron ese
    # lugar y jugaron un desempate a ida y vuelta (bajó Tigre). Boca e Independiente empataron el segundo puesto y jugaron
    # tres partidos; quedó segundo Boca por el cociente de goles de la tabla con los desempates. Los dos desempates van en
    # "playoffs", partido por partido, y el orden de esos empatados en "orden_a_mano"; los demás empatados en puntos, como
    # RSSSF (que coincide con la diferencia de gol). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los
    # del Banfield-Racing de la fecha 32). No había Libertadores todavía
    "1950-primera": {"nombre": "Campeonato de Primera División 1950", "anio": 1950, "liga": "a_mano", "slug": "1950-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["boca-juniors", "independiente", "huracan", "tigre"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que coincide con la diferencia de "
                                    "gol), salvo dos empates que se definieron en desempates: Boca e Independiente, por el "
                                    "segundo puesto (tres partidos y, como seguían iguales, el cociente de goles de la tabla "
                                    "con los desempates: quedó segundo Boca), y Huracán y Tigre, por el descenso (bajó Tigre).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1950 (las 34 fechas), sin los desempates. "
                                    "Cada partido ganado valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Banfield 3-0 Racing de la fecha 32 (de RSSSF, con los "
                                        "minutos). El goleador del torneo fue Mario Papa (San Lorenzo), con 24 goles.",
                     "nombre_playoffs": "Desempates",
                     "playoffs": [(r"^$^", "Desempate por el segundo puesto"), (r"^$^", "Desempate por el descenso")],
                     "playoffs_a_mano": {
                          "Desempate por el segundo puesto": [
                              {"fecha": "1950-12-03", "local": "boca-juniors", "visitante": "independiente", "gl": 2, "gv": 3, "estadio": "Monumental", "goles": []},
                              {"fecha": "1950-12-08", "local": "independiente", "visitante": "boca-juniors", "gl": 2, "gv": 3, "estadio": "El Cilindro", "goles": []},
                              {"fecha": "1950-12-10", "local": "boca-juniors", "visitante": "independiente", "gl": 3, "gv": 3, "estadio": "El Cilindro", "goles": [],
                               "gana": "boca-juniors",
                               "nota": "Ganó un partido cada uno y empataron el tercero: quedó segundo Boca, por el cociente de goles de la tabla con los desempates (1,24 contra 1,22)."},
                          ],
                          "Desempate por el descenso": [
                              {"fecha": "1950-12-03", "local": "tigre", "visitante": "huracan", "gl": 1, "gv": 3, "estadio": "La Doble Visera", "goles": []},
                              {"fecha": "1950-12-10", "local": "huracan", "visitante": "tigre", "gl": 5, "gv": 1, "estadio": "Monumental", "goles": [],
                               "nota": "Huracán ganó los dos partidos y se quedó en Primera; Tigre bajó a la Primera B."},
                          ],
                     },
                     # (dos desempates sueltos, no un cuadro: cada uno en su parte, partido por partido)
                     "cuadro": {"bloques": [("Desempate por el segundo puesto", [["Desempate por el segundo puesto"]]),
                                            ("Desempate por el descenso", [["Desempate por el descenso"]])],
                                "nota": "De los desempates hay solo el resultado."},
                     "descensos": "tabla", "descienden": 2},
    # 1951: el Campeonato de Primera División 1951 (abril a diciembre; campeón Racing): 17 equipos a dos ruedas (34 fechas,
    # en cada una quedaba uno libre), con 2 puntos por partido ganado. Banfield y Racing terminaron empatados arriba y
    # definieron el título en una final a ida y vuelta en la cancha de San Lorenzo (en "playoffs"; ganó Racing). Bajaban
    # los dos últimos de la tabla (no había promedios): Quilmes y Gimnasia. ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, sin goles; de la final, el gol de RSSSF; la tabla, controlada con la de Wikipedia). No había Libertadores
    "1951-primera": {"nombre": "Campeonato de Primera División 1951", "anio": 1951, "liga": "a_mano", "slug": "1951-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 2, "puntos_victoria": 2,
                     "texto_pasan": "Empatados en el primer puesto (44 puntos): definieron el título en una final a ida y "
                                    "vuelta, en la cancha de San Lorenzo",
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1951 (las 34 fechas; eran 17 equipos y en "
                                    "cada fecha quedaba uno libre), sin la final. Cada partido ganado valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo de la final (de RSSSF, con el minuto). El goleador del torneo fue "
                                        "Santiago Vernazza (River), con 22 goles.",
                     "nombre_playoffs": "Final (desempate)",
                     "playoffs": [(r"^$^", "Final")],
                     "playoffs_a_mano": {
                          "Final": [
                              {"fecha": "1951-12-01", "local": "racing-club", "visitante": "banfield", "gl": 0, "gv": 0, "estadio": "El Gasómetro", "goles": []},
                              {"fecha": "1951-12-05", "local": "banfield", "visitante": "racing-club", "gl": 0, "gv": 1, "estadio": "El Gasómetro", "arbitro": "Cross",
                               "goles": [{"jugador": "Boyé", "equipo": "visitante", "min": 46}]},
                          ],
                     },
                     "ida_y_vuelta": True,
                     "descensos": "tabla", "descienden": 2},
    # 1952: el Campeonato de Primera División 1952 (abril a noviembre; campeón River): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Atlanta. El Newell's-River de la
    # última fecha se suspendió y la AFA se lo dio ganado a River con el 1-0 del momento. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles salvo el del Newell's-River; RSSSF no trae la tabla, controlada con la de
    # Wikipedia). No había Libertadores todavía
    "1952-primera": {"nombre": "Campeonato de Primera División 1952", "anio": 1952, "liga": "a_mano", "slug": "1952-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1952 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Newell's 0-1 River de la última fecha, el partido en el que "
                                        "River salió campeón (de RSSSF, con el minuto). El goleador del torneo fue Eduardo "
                                        "Ricagni (Huracán), con 28 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1953: el Campeonato de Primera División 1953 (abril a noviembre; campeón River): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Con los mismos puntos desempataba el cociente de goles (en este torneo da el mismo
    # orden que la diferencia de gol). Bajaba el último de la tabla (no había promedios): Estudiantes. ESPN no lo tiene: va
    # a mano (tools/a_mano; RSSSF, sin goles salvo los del River-Newell's de la fecha 30). No había Libertadores todavía
    "1953-primera": {"nombre": "Campeonato de Primera División 1953", "anio": 1953, "liga": "a_mano", "slug": "1953-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el cociente de goles (goles a favor divididos "
                                    "por goles en contra) y después los goles a favor; en este torneo da el mismo orden que "
                                    "la diferencia de gol. Así Vélez quedó segundo, delante de Racing, y Newell's se salvó "
                                    "del descenso, que fue para Estudiantes.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1953 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del River 2-1 Newell's de la fecha 30, el partido en el que River "
                                        "salió campeón (de RSSSF, con los minutos). Los goleadores del torneo fueron Juan "
                                        "Benavídez (San Lorenzo) y Juan José Pizzuti (Racing), con 22 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1954: el Campeonato de Primera División 1954 (abril a noviembre; campeón Boca): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Banfield. En las fechas 24 y 26
    # se suspendieron once partidos que se terminaron de jugar días después (cada uno con su nota). ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo el del Boca-Tigre de la fecha 29; RSSSF no trae la tabla, controlada con
    # la de Wikipedia). No había Libertadores todavía
    "1954-primera": {"nombre": "Campeonato de Primera División 1954", "anio": 1954, "liga": "a_mano", "slug": "1954-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de Wikipedia (que en este torneo coincide con "
                                    "la diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1954 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca 1-0 Tigre de la fecha 29, el partido en el que Boca salió "
                                        "campeón (de RSSSF, con el minuto). Los goleadores del torneo fueron Ángel Berni (San "
                                        "Lorenzo), José Borello (Boca) y Norberto Conde (Vélez), con 19 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1955: el Campeonato de Primera División 1955 (abril a diciembre; campeón River): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Platense. Tres partidos de River
    # se suspendieron: el de San Lorenzo de la fecha 12 se terminó de jugar otro día, y los de Estudiantes (fecha 25) y
    # San Lorenzo (fecha 27) la AFA se los dio ganados con el resultado del momento. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles salvo los del Boca-River de la fecha 29). No había Libertadores todavía
    "1955-primera": {"nombre": "Campeonato de Primera División 1955", "anio": 1955, "liga": "a_mano", "slug": "1955-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_texto": "Orden: puntos y, con los mismos puntos, el de RSSSF (que en este torneo coincide con la "
                                    "diferencia de gol).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1955 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca 1-2 River de la fecha 29 (de RSSSF, con los minutos). "
                                        "El goleador del torneo fue Oscar Massei (Rosario Central), con 21 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1956: el Campeonato de Primera División 1956 (abril a diciembre; campeón River): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Bajaba el último de la tabla (no había promedios): Argentinos, Tigre y Chacarita
    # empataron con 22 y se desempató por los partidos entre ellos y contra los cinco primeros ("orden_a_mano", el de
    # RSSSF): bajó Chacarita. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del River-Rosario
    # Central de la fecha 29). No había Libertadores todavía
    "1956-primera": {"nombre": "Campeonato de Primera División 1956", "anio": 1956, "liga": "a_mano", "slug": "1956-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["argentinos-juniors", "tigre", "chacarita-juniors"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, como en RSSSF. Argentinos, Tigre y Chacarita "
                                    "terminaron últimos con 22 puntos: el último puesto, el del descenso, se desempató con "
                                    "los puntos de los partidos entre ellos y contra los cinco primeros de la tabla "
                                    "(Argentinos 10, Tigre 10 y Chacarita 9, que bajó a la Primera B).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1956 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del River 4-0 Rosario Central de la fecha 29, el partido en el que "
                                        "River salió campeón (de RSSSF, con los minutos). Los goleadores del torneo fueron "
                                        "Juan Alberto Castro (Rosario Central) y Ernesto Grillo (Independiente), con 17 goles.",
                     "descensos": "tabla", "descienden": 1},
    # 1957: el Campeonato de Primera División 1957 (mayo a diciembre; campeón River, el tercero seguido): 16 equipos a
    # dos ruedas (30 fechas), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro
    # empatado y contra los tres primeros, y después el cociente de goles ("orden_a_mano", el de RSSSF). Bajaba el peor
    # promedio de puntos por temporada de 1956 y 1957 ("promedios_por_temporada"; RSSSF): Ferro. ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo los del River-Independiente de la fecha 27). No había Libertadores todavía
    "1957-primera": {"nombre": "Campeonato de Primera División 1957", "anio": 1957, "liga": "a_mano", "slug": "1957-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["boca-juniors", "velez-sarsfield", "estudiantes-de-la-plata", "huracan", "newell-s-old-boys",
                                      "independiente", "tigre", "gimnasia-y-esgrima"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los tres primeros de la tabla, y después el cociente de goles (así "
                                    "Boca quedó cuarto, delante de Vélez; Estudiantes delante de Huracán, Newell's delante de "
                                    "Independiente y Tigre delante de Gimnasia).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1957 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del River 2-0 Independiente de la fecha 27, el partido en el que "
                                        "River salió campeón (de RSSSF, con los minutos). El goleador del torneo fue "
                                        "Roberto Zárate (River), con 22 goles.",
                     "promedios_por_temporada": True,
                     "promedios": {"1956": {"river-plate": [43, 1], "racing-club": [39, 1], "boca-juniors": [40, 1], "velez-sarsfield": [37, 1], "san-lorenzo": [29, 1], "lanus": [41, 1], "independiente": [30, 1], "newell-s-old-boys": [26, 1], "rosario-central": [30, 1], "huracan": [23, 1], "estudiantes-de-la-plata": [23, 1], "argentinos-juniors": [22, 1], "gimnasia-y-esgrima": [26, 1], "tigre": [22, 1], "ferro-carril-oeste": [27, 1]}},
                     "descensos": "promedios", "descienden": 1},
    # 1958: el Campeonato de Primera División 1958 (marzo a diciembre, parado durante el Mundial; campeón Racing): 16
    # equipos a dos ruedas (30 fechas), con 2 puntos por partido ganado. El River-Huracán de la fecha 20 no se jugó: se lo
    # dieron ganado a Huracán ("para_local", sin goles) y a River le descontaron 2 puntos. Boca y San Lorenzo empataron el
    # segundo puesto y jugaron un desempate a ida y vuelta en abril de 1959 (en "playoffs"; quedó segundo Boca); los
    # demás empatados en puntos, por los partidos contra el otro empatado y contra los tres primeros ("orden_a_mano", el
    # de RSSSF). Bajaba el peor promedio de puntos por temporada de 1956 a 1958 ("promedios_por_temporada"; RSSSF): Tigre.
    # ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del Lanús-Racing de la fecha 28). No había
    # Libertadores todavía
    "1958-primera": {"nombre": "Campeonato de Primera División 1958", "anio": 1958, "liga": "a_mano", "slug": "1958-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["boca-juniors", "san-lorenzo", "rosario-central", "river-plate", "central-cordoba-rosario",
                                      "huracan", "argentinos-juniors", "lanus"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los tres primeros de la tabla (así Rosario Central quedó delante de "
                                    "River, Central Córdoba delante de Huracán y Argentinos delante de Lanús). Boca y San "
                                    "Lorenzo, empatados en el segundo puesto, jugaron un desempate a ida y vuelta: ganó un "
                                    "partido cada uno y quedó segundo Boca, por el cociente de goles de la tabla.",
                     "descuentos": {"river-plate": 2},
                     "descuentos_texto": "A River se le descontaron 2 puntos (y perdió el partido con Huracán, que no se "
                                         "jugó).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1958 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Lanús 3-3 Racing de la fecha 28, el partido en el que Racing "
                                        "salió campeón (de RSSSF, con los minutos). El goleador del torneo fue José "
                                        "Sanfilippo (San Lorenzo), con 28 goles (29 con el desempate).",
                     "nombre_playoffs": "Desempate",
                     "playoffs": [(r"^$^", "Desempate por el segundo puesto")],
                     "playoffs_a_mano": {
                          "Desempate por el segundo puesto": [
                              {"fecha": "1959-04-23", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 3, "gv": 4, "estadio": "Tomás Adolfo Ducó", "goles": []},
                              {"fecha": "1959-04-26", "local": "san-lorenzo", "visitante": "boca-juniors", "gl": 1, "gv": 3, "estadio": "Tomás Adolfo Ducó", "goles": [],
                               "nota": "Ganó un partido cada uno: quedó segundo Boca, por el cociente de goles de la tabla (70/48, contra 66/47 de San Lorenzo)."},
                          ],
                     },
                     "ida_y_vuelta": True,
                     "promedios_por_temporada": True,
                     "promedios": {"1956": {"river-plate": [43, 1], "racing-club": [39, 1], "boca-juniors": [40, 1], "san-lorenzo": [29, 1], "velez-sarsfield": [37, 1], "independiente": [30, 1], "rosario-central": [30, 1], "lanus": [41, 1], "estudiantes-de-la-plata": [23, 1], "huracan": [23, 1], "argentinos-juniors": [22, 1], "newell-s-old-boys": [26, 1], "gimnasia-y-esgrima": [26, 1], "tigre": [22, 1]},
                                   "1957": {"river-plate": [46, 1], "racing-club": [36, 1], "boca-juniors": [34, 1], "san-lorenzo": [38, 1], "velez-sarsfield": [34, 1], "independiente": [31, 1], "rosario-central": [27, 1], "atlanta": [24, 1], "lanus": [22, 1], "estudiantes-de-la-plata": [33, 1], "huracan": [33, 1], "argentinos-juniors": [28, 1], "newell-s-old-boys": [31, 1], "gimnasia-y-esgrima": [23, 1], "tigre": [23, 1]}},
                     "descensos": "promedios", "descienden": 1},
    # 1959: el Campeonato de Primera División 1959 (mayo a noviembre; campeón San Lorenzo): 16 equipos a dos ruedas (30
    # fechas), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro empatado y
    # contra los primeros ("orden_a_mano", el de RSSSF). Bajaba el peor promedio de puntos por temporada de 1957 a 1959
    # ("promedios_por_temporada"; RSSSF y Wikipedia): Gimnasia y Central Córdoba empataron con 24 y se desempató por los
    # partidos entre ellos y contra los cinco primeros ("promedios_orden"): bajó Central Córdoba. El Newell's-Huracán de
    # la fecha 29 se suspendió y se lo dieron ganado a Huracán ("para_local"). ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, sin goles salvo los del Ferro-San Lorenzo de la fecha 26). A la primera Libertadores (1960) fue el campeón
    "1959-primera": {"nombre": "Campeonato de Primera División 1959", "anio": 1959, "liga": "a_mano", "slug": "1959-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["independiente", "ferro-carril-oeste", "river-plate", "atlanta", "newell-s-old-boys",
                                      "huracan", "boca-juniors", "gimnasia-y-esgrima", "argentinos-juniors"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los primeros de la tabla (así Independiente quedó tercero, delante de "
                                    "Ferro; River, Atlanta y Newell's, en ese orden; Huracán delante de Boca y Gimnasia "
                                    "delante de Argentinos).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1959 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Ferro 3-0 San Lorenzo de la fecha 26, el partido en el que "
                                        "San Lorenzo salió campeón (de RSSSF, con los minutos).",
                     "promedios_por_temporada": True,
                     "promedios": {"1957": {"san-lorenzo": [38, 1], "racing-club": [36, 1], "river-plate": [46, 1], "boca-juniors": [34, 1], "independiente": [31, 1], "velez-sarsfield": [34, 1], "atlanta": [24, 1], "estudiantes-de-la-plata": [33, 1], "huracan": [33, 1], "rosario-central": [27, 1], "newell-s-old-boys": [31, 1], "argentinos-juniors": [28, 1], "lanus": [22, 1], "gimnasia-y-esgrima": [23, 1]},
                                   "1958": {"san-lorenzo": [38, 1], "racing-club": [41, 1], "river-plate": [35, 1], "boca-juniors": [38, 1], "independiente": [33, 1], "velez-sarsfield": [34, 1], "atlanta": [36, 1], "estudiantes-de-la-plata": [31, 1], "huracan": [27, 1], "rosario-central": [35, 1], "newell-s-old-boys": [17, 1], "argentinos-juniors": [25, 1], "lanus": [25, 1], "gimnasia-y-esgrima": [24, 1], "central-cordoba-rosario": [27, 1]}},
                     # (Gimnasia y Central Córdoba, con el mismo promedio: el desempate, por los partidos de la temporada
                     # entre ellos y contra los cinco primeros de la tabla)
                     "promedios_orden": ["gimnasia-y-esgrima", "central-cordoba-rosario"],
                     "promedios_texto": "Gimnasia y Central Córdoba terminaron con el mismo promedio (24,00). Se desempató "
                                        "con los puntos de la temporada en los partidos entre ellos y contra los cinco "
                                        "primeros de la tabla: Gimnasia 9 y Central Córdoba 6, que bajó a la Primera B.",
                     "descensos": "promedios", "descienden": 1,
                     "cupos": {"anio": 1960, "fijos": True, "libertadores": [("Campeón de 1959", "san-lorenzo")]}},
    # 1960: el Campeonato de Primera División 1960 (abril a noviembre; campeón Independiente): 16 equipos a dos ruedas
    # (30 fechas), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro empatado y
    # contra los primeros ("orden_a_mano", el de RSSSF). Bajaba el peor promedio de puntos por temporada de 1958 a 1960
    # ("promedios_por_temporada"; RSSSF y Wikipedia): Newell's. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles
    # salvo el del Atlanta-Independiente de la última fecha). A la Libertadores 1961 fue el campeón
    "1960-primera": {"nombre": "Campeonato de Primera División 1960", "anio": 1960, "liga": "a_mano", "slug": "1960-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["river-plate", "argentinos-juniors", "racing-club", "boca-juniors", "chacarita-juniors",
                                      "huracan"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los primeros de la tabla (así River quedó segundo, delante de "
                                    "Argentinos, Racing delante de Boca y Chacarita delante de Huracán).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1960 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Atlanta 1-0 Independiente de la última fecha (de RSSSF, con "
                                        "el minuto).",
                     # (los puntos de cada temporada; se divide por las temporadas jugadas)
                     "promedios_por_temporada": True,
                     "promedios": {"1958": {"san-lorenzo": [38, 1], "racing-club": [41, 1], "independiente": [33, 1], "river-plate": [35, 1], "boca-juniors": [38, 1], "atlanta": [36, 1], "velez-sarsfield": [34, 1], "argentinos-juniors": [25, 1], "rosario-central": [35, 1], "huracan": [27, 1], "estudiantes-de-la-plata": [31, 1], "gimnasia-y-esgrima": [24, 1], "lanus": [25, 1], "newell-s-old-boys": [17, 1]},
                                   "1959": {"san-lorenzo": [45, 1], "racing-club": [38, 1], "independiente": [33, 1], "river-plate": [32, 1], "boca-juniors": [30, 1], "atlanta": [32, 1], "velez-sarsfield": [26, 1], "argentinos-juniors": [25, 1], "rosario-central": [23, 1], "huracan": [30, 1], "estudiantes-de-la-plata": [28, 1], "ferro-carril-oeste": [33, 1], "gimnasia-y-esgrima": [25, 1], "lanus": [27, 1], "newell-s-old-boys": [32, 1]}},
                     "descensos": "promedios", "descienden": 1,
                     "cupos": {"anio": 1961, "fijos": True, "libertadores": [("Campeón de 1960", "independiente")]}},
    # 1961: el Campeonato de Primera División 1961 (abril a diciembre; campeón Racing): 16 equipos a dos ruedas (30
    # fechas), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro empatado y
    # contra los tres primeros ("orden_a_mano", el de RSSSF). Bajaban los dos peores promedios de puntos por temporada de
    # 1959 a 1961 ("promedios_por_temporada"; RSSSF y Wikipedia): Lanús y Los Andes. ESPN no lo tiene: va a mano
    # (tools/a_mano; Wikipedia, controlada con RSSSF; del Racing-San Lorenzo de la fecha 27, los goles de RSSSF). A la
    # Libertadores 1962 fue el campeón
    "1961-primera": {"nombre": "Campeonato de Primera División 1961", "anio": 1961, "liga": "a_mano", "slug": "1961-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["velez-sarsfield", "chacarita-juniors", "argentinos-juniors", "lanus", "los-andes",
                                      "ferro-carril-oeste"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los tres primeros (así Vélez quedó delante de Chacarita, Argentinos "
                                    "delante de Lanús y Los Andes delante de Ferro).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1961 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Racing-San Lorenzo de la fecha 27, en el que Racing salió "
                                        "campeón (de RSSSF, con los minutos).",
                     # (los puntos de cada temporada; se divide por las temporadas jugadas)
                     "promedios_por_temporada": True,
                     "promedios": {"1959": {"racing-club": [38, 1], "san-lorenzo": [45, 1], "river-plate": [32, 1], "independiente": [33, 1], "boca-juniors": [30, 1], "atlanta": [32, 1], "velez-sarsfield": [26, 1], "argentinos-juniors": [25, 1], "huracan": [30, 1], "gimnasia-y-esgrima": [25, 1], "rosario-central": [23, 1], "estudiantes-de-la-plata": [28, 1], "ferro-carril-oeste": [33, 1], "lanus": [27, 1]},
                                   "1960": {"racing-club": [37, 1], "san-lorenzo": [36, 1], "river-plate": [39, 1], "independiente": [41, 1], "boca-juniors": [37, 1], "atlanta": [27, 1], "velez-sarsfield": [33, 1], "chacarita-juniors": [28, 1], "argentinos-juniors": [39, 1], "huracan": [28, 1], "gimnasia-y-esgrima": [25, 1], "rosario-central": [29, 1], "estudiantes-de-la-plata": [23, 1], "ferro-carril-oeste": [19, 1], "lanus": [21, 1]}},
                     "descensos": "promedios", "descienden": 2,
                     "cupos": {"anio": 1962, "fijos": True, "libertadores": [("Campeón de 1961", "racing-club")]}},
    # 1962: el Campeonato de Primera División 1962 (marzo a diciembre; campeón Boca): 15 equipos a dos ruedas (30 fechas,
    # en cada una quedaba uno libre), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra
    # el otro empatado y contra los tres primeros ("orden_a_mano", el de RSSSF). Bajaban los dos peores promedios de puntos
    # por temporada de 1960 a 1962 ("promedios_por_temporada"; RSSSF y Wikipedia): Ferro y Quilmes. ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles salvo los del Boca-Estudiantes de la última fecha). A la Libertadores 1963 fue el
    # campeón
    "1962-primera": {"nombre": "Campeonato de Primera División 1962", "anio": 1962, "liga": "a_mano", "slug": "1962-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["rosario-central", "chacarita-juniors", "huracan", "atlanta", "san-lorenzo",
                                      "ferro-carril-oeste"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los tres primeros (así Rosario Central quedó delante de Chacarita, "
                                    "Huracán delante de Atlanta y San Lorenzo delante de Ferro).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1962 (las 30 fechas; eran 15 equipos y en "
                                    "cada fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca-Estudiantes de la última fecha (de RSSSF, con los "
                                        "minutos). El goleador fue Luis Artime (River), con 25 goles.",
                     # (los puntos de cada temporada; se divide por las temporadas jugadas)
                     "promedios_por_temporada": True,
                     "promedios": {"1960": {"river-plate": [39, 1], "boca-juniors": [37, 1], "racing-club": [37, 1], "independiente": [41, 1], "san-lorenzo": [36, 1], "atlanta": [27, 1], "gimnasia-y-esgrima": [25, 1], "chacarita-juniors": [28, 1], "argentinos-juniors": [39, 1], "velez-sarsfield": [33, 1], "rosario-central": [29, 1], "huracan": [28, 1], "estudiantes-de-la-plata": [23, 1], "ferro-carril-oeste": [19, 1]},
                                   "1961": {"river-plate": [38, 1], "boca-juniors": [35, 1], "racing-club": [47, 1], "independiente": [33, 1], "san-lorenzo": [40, 1], "atlanta": [37, 1], "gimnasia-y-esgrima": [28, 1], "chacarita-juniors": [31, 1], "argentinos-juniors": [24, 1], "velez-sarsfield": [31, 1], "rosario-central": [23, 1], "huracan": [25, 1], "estudiantes-de-la-plata": [22, 1], "ferro-carril-oeste": [21, 1]}},
                     "descensos": "promedios", "descienden": 2,
                     "cupos": {"anio": 1963, "fijos": True, "libertadores": [("Campeón de 1962", "boca-juniors")]}},
    # 1963: el Campeonato de Primera División 1963 (abril a noviembre; campeón Independiente): 14 equipos a dos ruedas (26
    # fechas), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro empatado y
    # contra los primeros de la tabla ("orden_a_mano", el de RSSSF). Por los promedios bajaba Estudiantes, pero el descenso
    # se anuló. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles salvo los del Independiente 9-1 San Lorenzo de
    # la última fecha). A la Libertadores 1964 fue el campeón
    "1963-primera": {"nombre": "Campeonato de Primera División 1963", "anio": 1963, "liga": "a_mano", "slug": "1963-primera",
                     "zonas": "unica", "fechas": 26, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["racing-club", "boca-juniors", "san-lorenzo", "banfield", "rosario-central",
                                      "argentinos-juniors"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los primeros de la tabla (así Racing quedó delante de Boca, San Lorenzo "
                                    "delante de Banfield y Rosario Central delante de Argentinos).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1963 (las 26 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Independiente 9-1 San Lorenzo de la última fecha (de RSSSF, "
                                        "con los minutos). El goleador fue Luis Artime (River), con 25 goles.",
                     "sin_descensos": "No hubo descensos: por los promedios bajaba Estudiantes, pero la AFA anuló el descenso.",
                     "cupos": {"anio": 1964, "fijos": True, "libertadores": [("Campeón de 1963", "independiente")]}},
    # 1964: el Campeonato de Primera División 1964 (abril a diciembre; campeón Boca): 16 equipos a dos ruedas (30 fechas),
    # con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro empatado y contra los
    # tres primeros ("orden_a_mano", el de RSSSF). Los descensos se anularon. ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, sin goles salvo los del Boca-River de la fecha 29). A la Libertadores 1965 fue el campeón (e Independiente,
    # como campeón de la Libertadores 1964)
    "1964-primera": {"nombre": "Campeonato de Primera División 1964", "anio": 1964, "liga": "a_mano", "slug": "1964-primera",
                     "zonas": "unica", "fechas": 30, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["banfield", "racing-club", "huracan", "ferro-carril-oeste"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los tres primeros (así Banfield quedó delante de Racing y Huracán "
                                    "delante de Ferro).",
                     "anual_texto": "La tabla del Campeonato de Primera División 1964 (las 30 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son solo del Boca-River de la fecha 29 (de RSSSF, con los minutos). El "
                                        "goleador fue Héctor Veira (San Lorenzo), con 17 goles.",
                     "sin_descensos": "No hubo descensos: la AFA los anuló.",
                     "cupos": {"anio": 1965, "fijos": True,
                               "libertadores": [("Campeón de la Copa Libertadores 1964 (lugar aparte)", "independiente"),
                                                ("Campeón de 1964", "boca-juniors")]}},
    # 1965: el Campeonato de Primera División 1965 (abril a diciembre; campeón Boca): 18 equipos a dos ruedas (34 fechas),
    # con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos contra el otro empatado y contra los
    # tres primeros ("orden_a_mano", el de RSSSF, que coincide con esa cuenta). El Independiente-Racing del 13 de mayo se
    # suspendió 2-2 y nunca se completó: va sin resultado ("estado": "Suspendido") y no cuenta. Los descensos se anularon.
    # ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, con los goleadores, solo con el apellido y sin minutos). A la
    # Libertadores 1966 fueron el campeón y el subcampeón
    "1965-primera": {"nombre": "Campeonato de Primera División 1965", "anio": 1965, "liga": "a_mano", "slug": "1965-primera",
                     "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["racing-club", "platense", "banfield", "san-lorenzo", "newell-s-old-boys",
                                      "rosario-central", "lanus", "atlanta"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos contra el otro "
                                    "empatado y contra los tres primeros. Independiente y Racing jugaron un partido menos: el "
                                    "que jugaron entre ellos se suspendió y nunca se terminó.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1965 (las 34 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "Los goles son de RSSSF, solo con el apellido y sin minutos (falta uno de "
                                        "Estudiantes). El goleador fue Juan Carlos Carone (Vélez), con 19 goles.",
                     "sin_descensos": "No hubo descensos: la AFA los anuló por tercer año seguido.",
                     "cupos": {"anio": 1966, "fijos": True,
                               "libertadores": [("Campeón de la Copa Libertadores 1965 (lugar aparte)", "independiente"),
                                                ("Campeón de 1965", "boca-juniors"), ("Subcampeón de 1965", "river-plate")]}},
    # 1966: el Campeonato de Primera División 1966 (marzo a diciembre; campeón Racing): 20 equipos a dos ruedas (38
    # fechas), con 2 puntos por partido ganado. Con los mismos puntos ordenaban los partidos entre los empatados y contra
    # los tres primeros, y después el cociente de goles: el orden de RSSSF va en "orden_a_mano". Los descensos se anularon
    # en la fecha 37. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles). A la Libertadores 1967 fueron el campeón
    # y el subcampeón
    "1966-primera": {"nombre": "Campeonato de Primera División 1966", "anio": 1966, "liga": "a_mano", "slug": "1966-primera",
                     "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                     "orden_a_mano": ["san-lorenzo", "velez-sarsfield", "gimnasia-y-esgrima", "argentinos-juniors", "atlanta",
                                      "newell-s-old-boys", "rosario-central", "banfield", "platense", "ferro-carril-oeste",
                                      "colon"],
                     "orden_texto": "Orden: puntos y, con los mismos puntos, los puntos sacados en los partidos entre los "
                                    "empatados y contra los tres primeros; si seguían igualados, el cociente de goles (goles "
                                    "a favor dividido goles en contra), como Ferro y Colón.",
                     "anual_texto": "La tabla del Campeonato de Primera División 1966 (las 38 fechas). Cada partido ganado "
                                    "valía 2 puntos.",
                     "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Luis Artime (Independiente), "
                                        "con 23 goles.",
                     "sin_descensos": "No hubo descensos: la AFA los anuló en la fecha 37, cuando Colón era el último.",
                     "cupos": {"anio": 1967, "fijos": True,
                               "libertadores": [("Campeón de 1966", "racing-club"), ("Subcampeón de 1966", "river-plate")]}},
    # 1967: el Campeonato Metropolitano 1967 (marzo a agosto; campeón Estudiantes), el primero con este formato: 22
    # equipos por etapas, como el de 1968 (primera fase de 2 zonas de 11 con un interzonal por fecha, semifinales y final
    # a un partido en cancha neutral, Torneo Reclasificatorio con cuatro de la Primera B, en el que bajaron Unión y
    # Deportivo Español y subieron Tigre y Los Andes, y Torneo Promocional con cuatro del interior). ESPN no lo tiene: va a
    # mano (tools/a_mano; RSSSF, sin goles, controlado con Wikipedia; de la final, los goles y el árbitro de RSSSF)
    "1967-metropolitano": {"nombre": "Campeonato Metropolitano 1967", "anio": 1967, "liga": "a_mano", "slug": "1967-metropolitano",
                           "etapas": [("Primera fase", r"primera-fase$", 2, 1, 22,
                                       "Los dos primeros de cada zona pasan a las semifinales; del 3.º al 6.º, al Nacional; el "
                                       "7.º y el 8.º juegan el Torneo Promocional, y los tres últimos, el Torneo "
                                       "Reclasificatorio. En cada fecha, el que quedaba libre en su zona jugaba un interzonal, "
                                       "que suma en su zona"),
                                      ("Torneo Reclasificatorio", r"reclasificatorio$", 6, 23, 18,
                                       "Los seis primeros juegan en Primera en 1968 (Tigre y Los Andes, de la Primera B, "
                                       "suben; Almagro y Defensores de Belgrano siguen en la B)"),
                                      ("Torneo Promocional", r"promocional$", 1, 41, 14,
                                       "Campeón del Torneo Promocional (lo jugaron, mientras se jugaba el Nacional, el 7.º y "
                                       "el 8.º de cada zona con cuatro equipos del interior; no definía ascensos ni descensos)")],
                           "fechas": 54, "pasan": 0, "puntos_victoria": 2, "desempate_goles": "gf",
                           "nota": "Cada partido ganado valía 2 puntos y, con los mismos puntos, desempataban los goles a favor. "
                                   "Fue el primer Metropolitano: en la primera fase había 2 zonas de 11 a dos ruedas; los dos "
                                   "primeros de cada zona jugaban las semifinales y la final, a un partido en cancha neutral; "
                                   "del 3.º al 6.º pasaban al Nacional; el 7.º y el 8.º jugaban el Torneo Promocional, y los "
                                   "tres últimos, el Torneo Reclasificatorio con cuatro de la Primera B, en el que bajaron "
                                   "Unión y Deportivo Español.",
                           "descensos": "etapa",
                           "descienden_etapa": {"Torneo Reclasificatorio": ["union", "deportivo-espanol"]},
                           "goleadores_nota": "Los goles son solo de la final (de RSSSF, con los minutos): del resto del torneo "
                                              "no están. El goleador fue Bernardo Acosta (Lanús), con 18 goles.",
                           "nombre_playoffs": "Fase final",
                           "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                           "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1967-08-03T19:00Z", "fecha": "1967-08-03", "local": "estudiantes-de-la-plata", "visitante": "platense", "gl": 4, "gv": 3, "estadio": "Estadio La Bombonera"},
                               {"hora_utc": "1967-08-04T19:00Z", "fecha": "1967-08-04", "local": "racing-club", "visitante": "independiente", "gl": 2, "gv": 0, "estadio": "Estadio El Cilindro"},
                           ],
                           "Final": [
                               {"hora_utc": "1967-08-06T19:00Z", "fecha": "1967-08-06", "local": "estudiantes-de-la-plata", "visitante": "racing-club", "gl": 3, "gv": 0, "estadio": "Estadio El Gasómetro", "arbitro": "Guillermo Nimo", "goles": [{"jugador": "Madero", "equipo": "local", "min": 52}, {"jugador": "Verón", "equipo": "local", "min": 69}, {"jugador": "Ribaudo", "equipo": "local", "min": 72}]},
                           ],
                           }},
    # El Campeonato Nacional 1967 (septiembre a diciembre; campeón Independiente): 16 equipos (12 del Metropolitano y 4
    # del Torneo Regional) a una rueda, con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano;
    # Wikipedia, controlada con RSSSF; del Independiente-Racing de la última fecha, los goles de RSSSF). A la Libertadores
    # 1968 fueron el campeón y el subcampeón (y Racing, como campeón de la Libertadores 1967)
    "1967-nacional": {"nombre": "Campeonato Nacional 1967", "anio": 1967, "liga": "a_mano", "slug": "1967-nacional",
                      "zonas": "unica", "fechas": 15, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "desempate_goles": "gf",
                      "anual_texto": "La tabla del Campeonato Nacional 1967 (15 fechas, a una rueda). Cada partido ganado "
                                     "valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo del Independiente-Racing de la última fecha (de RSSSF, con los "
                                         "minutos). El goleador del torneo fue Luis Artime (Independiente), con 11 goles.",
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "cupos": {"anio": 1968, "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 1967 (lugar aparte)", "racing-club"),
                                                 ("Campeón del Nacional 1967", "independiente"),
                                                 ("Subcampeón del Nacional 1967", "estudiantes-de-la-plata")]}},
    # 1968:el Campeonato Metropolitano 1968 (marzo a agosto; campeón San Lorenzo, invicto): 22 equipos por etapas
    # ("etapas"; en tools/a_mano, cada fecha dice su etapa y cada partido su zona): la primera fase, 2 zonas de 11 a dos
    # ruedas (22 fechas, con un interzonal por fecha), con 2 puntos por partido ganado y, con los mismos puntos, los goles
    # a favor como desempate ("desempate_goles": "gf"). Los dos primeros de cada zona jugaban las semifinales y la final, a
    # un partido en cancha neutral; del 3.º al 6.º pasaban al Nacional; el 7.º y el 8.º jugaban el Torneo Promocional (con
    # cuatro del interior, mientras se jugaba el Nacional: no definía nada), y los tres últimos, el Torneo Reclasificatorio
    # con cuatro de la Primera B (los seis primeros jugaban en Primera en 1969: bajaron Ferro y Tigre y subieron Unión y
    # Morón, "descienden_etapa"). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles; de la final, los goles y
    # el árbitro de RSSSF)
    "1968-metropolitano": {"nombre": "Campeonato Metropolitano 1968", "anio": 1968, "liga": "a_mano", "slug": "1968-metropolitano",
                           "etapas": [("Primera fase", r"primera-fase$", 2, 1, 22,
                                       "Los dos primeros de cada zona pasan a las semifinales; del 3.º al 6.º, al Nacional; el "
                                       "7.º y el 8.º juegan el Torneo Promocional, y los tres últimos, el Torneo "
                                       "Reclasificatorio. En cada fecha, el que quedaba libre en su zona jugaba un interzonal, "
                                       "que suma en su zona"),
                                      ("Torneo Reclasificatorio", r"reclasificatorio$", 6, 23, 18,
                                       "Los seis primeros juegan en Primera en 1969 (Unión y Deportivo Morón, de la Primera B, "
                                       "suben; Nueva Chicago y Almagro siguen en la B)"),
                                      ("Torneo Promocional", r"promocional$", 1, 41, 14,
                                       "Campeón del Torneo Promocional (lo jugaron, mientras se jugaba el Nacional, el 7.º y "
                                       "el 8.º de cada zona con cuatro equipos del interior; no definía ascensos ni descensos)")],
                           "fechas": 54, "pasan": 0, "puntos_victoria": 2, "desempate_goles": "gf",
                           "nota": "Cada partido ganado valía 2 puntos y, con los mismos puntos, desempataban los goles a favor. "
                                   "En la primera fase había 2 zonas de 11 a dos ruedas: los dos primeros de cada zona jugaban "
                                   "las semifinales y la final, a un partido en cancha neutral; del 3.º al 6.º pasaban al "
                                   "Nacional; el 7.º y el 8.º jugaban el Torneo Promocional, y los tres últimos, el Torneo "
                                   "Reclasificatorio con cuatro de la Primera B, en el que bajaron Ferro y Tigre.",
                           "descensos": "etapa",
                           "descienden_etapa": {"Torneo Reclasificatorio": ["ferro-carril-oeste", "tigre"]},
                           "goleadores_nota": "Los goles son solo de la final (de RSSSF, con los minutos): del resto del torneo "
                                              "no están. Los goleadores fueron Alfredo Obberti (Los Andes) y Rodolfo Fischer "
                                              "(San Lorenzo), con 13 goles.",
                           "nombre_playoffs": "Fase final",
                           "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                           "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1968-07-31T19:00Z", "fecha": "1968-07-31", "local": "san-lorenzo", "visitante": "river-plate", "gl": 3, "gv": 1, "estadio": "Estadio El Cilindro"},
                               {"hora_utc": "1968-08-01T19:00Z", "fecha": "1968-08-01", "local": "velez-sarsfield", "visitante": "estudiantes-de-la-plata", "gl": 0, "gv": 1, "estadio": "Estadio El Cilindro"},
                           ],
                           "Final": [
                               {"hora_utc": "1968-08-04T19:00Z", "fecha": "1968-08-04", "local": "san-lorenzo", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 1, "estadio": "Estadio Monumental", "arbitro": "Miguel Ángel Francisco Comesaña", "alargue": True, "goles": [{"jugador": "Verón", "equipo": "visitante", "min": 47}, {"jugador": "Veglio", "equipo": "local", "min": 67}, {"jugador": "Fischer", "equipo": "local", "min": 100}]},
                           ],
                           }},
    # El Campeonato Nacional 1968 (septiembre a diciembre; campeón Vélez): 16 equipos (12 del Metropolitano y 4 del
    # Torneo Regional) a una rueda, con 2 puntos por partido ganado. Vélez, River y Racing empataron el primer puesto y
    # jugaron un triangular en cancha de San Lorenzo ("triangular"); Vélez y River empataron también ahí y fue campeón
    # Vélez por tener más goles a favor (en el triangular y en la fase regular). ESPN no lo tiene: va a mano
    # (tools/a_mano; Wikipedia, controlada con RSSSF; del triangular, los goles y los árbitros de Wikipedia)
    "1968-nacional": {"nombre": "Campeonato Nacional 1968", "anio": 1968, "liga": "a_mano", "slug": "1968-nacional",
                      "zonas": "unica", "fechas": 15, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "desempate_goles": "gf", "triangular": True, "nombre_playoffs": "Triangular final",
                      "playoffs": [(r"^$^", "Triangular final")],
                      "playoffs_a_mano": {
                           "Triangular final": [
                               {"hora_utc": "1968-12-19T19:00Z", "fecha": "1968-12-19", "local": "river-plate", "visitante": "racing-club", "gl": 2, "gv": 0, "estadio": "Estadio El Gasómetro", "arbitro": "Aurelio Domingo Bossolino", "goles": [{"jugador": "Dominichi", "equipo": "local", "min": 43}, {"jugador": "Más", "equipo": "local", "min": 68}]},
                               {"hora_utc": "1968-12-22T19:00Z", "fecha": "1968-12-22", "local": "river-plate", "visitante": "velez-sarsfield", "gl": 1, "gv": 1, "estadio": "Estadio El Gasómetro", "arbitro": "Guillermo Nimo", "goles": [{"jugador": "Luna", "equipo": "visitante", "min": 11}, {"jugador": "Onega", "equipo": "local", "min": 35}]},
                               {"hora_utc": "1968-12-29T19:00Z", "fecha": "1968-12-29", "local": "velez-sarsfield", "visitante": "racing-club", "gl": 4, "gv": 2, "estadio": "Estadio El Gasómetro", "arbitro": "Jorge Aníbal Álvarez", "goles": [{"jugador": "Moreyra", "equipo": "local", "min": 3}, {"jugador": "Maschio", "equipo": "visitante", "min": 23}, {"jugador": "Wehbe", "equipo": "local", "min": 55}, {"jugador": "Wehbe", "equipo": "local", "min": 81}, {"jugador": "Martinoli", "equipo": "visitante", "min": 88}, {"jugador": "Wehbe", "equipo": "local", "min": 89, "tipo": "pen"}]},
                           ],
                      },
                      "texto_triangular": "Vélez, River y Racing terminaron empatados en el primer puesto, con 22 puntos, y "
                                          "jugaron un triangular a un partido, todos contra todos, en cancha de San Lorenzo. "
                                          "Vélez y River sumaron 3 puntos: Vélez salió campeón por tener más goles a favor "
                                          "(también en la fase regular, 39 contra 35).",
                      "anual_texto": "La tabla del Campeonato Nacional 1968 (15 fechas, a una rueda; sin el triangular). "
                                     "Cada partido ganado valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo del triangular final (de Wikipedia, con los minutos). El "
                                         "goleador del torneo fue Omar Wehbe (Vélez), con 13 goles.",
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "cupos": {"anio": 1969, "fijos": True,
                                "libertadores": [("Campeón del Nacional 1968", "velez-sarsfield"),
                                                 ("Subcampeón del Nacional 1968", "river-plate")],
                                "nota": "Los dos se clasificaron a la Copa Libertadores 1969, pero no la jugaron: los clubes "
                                        "argentinos renunciaron a esa edición."}},
    # 1969:el Campeonato Metropolitano 1969 (febrero a julio; campeón Chacarita): 22 equipos por etapas ("etapas"; en
    # tools/a_mano, cada fecha dice su etapa y cada partido su zona): la primera fase, 2 zonas de 11 a dos ruedas (22
    # fechas; en cada una, el que quedaba libre en su zona jugaba un interzonal, sin zona en el archivo), con 2 puntos por
    # partido ganado y, con los mismos puntos, los goles a favor como desempate ("desempate_goles": "gf"). Los dos primeros
    # de cada zona jugaban las semifinales y la final, a un partido en cancha neutral (Boca-River terminó 0-0 con alargue y
    # pasó River por tener más goles a favor en la primera fase: "gana"). Del 3.º al 6.º pasaban al Nacional; el 7.º y el
    # 8.º jugaban el Petit Torneo (por eliminación directa: el ganador, Unión, pasaba al Nacional), y los tres últimos, con
    # los otros tres del Petit, el Torneo Reclasificatorio (a dos ruedas; los dos últimos jugaban una segunda etapa con dos
    # de la Primera B: bajó Morón, "descienden_etapa"). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles; de la
    # final, los goles y el árbitro de RSSSF)
    "1969-metropolitano": {"nombre": "Campeonato Metropolitano 1969", "anio": 1969, "liga": "a_mano", "slug": "1969-metropolitano",
                           "etapas": [("Primera fase", r"primera-fase$", 2, 1, 22,
                                       "Los dos primeros de cada zona pasan a las semifinales; del 3.º al 6.º, al Nacional; el "
                                       "7.º y el 8.º juegan el Petit Torneo, y los tres últimos, el Torneo Reclasificatorio. En "
                                       "cada fecha, el que quedaba libre en su zona jugaba un interzonal, que suma en su zona"),
                                      ("Petit Torneo", r"petit$", 1, 23, 2,
                                       "Se jugó por eliminación directa (semifinales y final): el ganador pasa al Nacional y los "
                                       "otros tres juegan el Torneo Reclasificatorio"),
                                      ("Torneo Reclasificatorio", r"reclasificatorio$", 7, 25, 18,
                                       "Los siete primeros se quedan en Primera; los dos últimos juegan la segunda etapa con dos "
                                       "de la Primera B"),
                                      ("Segunda etapa del Reclasificatorio", r"segunda-etapa$", 1, 43, 3,
                                       "Se queda en Primera (Ferro y San Telmo, de la Primera B, siguen en la B)")],
                           "fechas": 45, "pasan": 0, "puntos_victoria": 2, "desempate_goles": "gf",
                           "nota": "Cada partido ganado valía 2 puntos y, con los mismos puntos, desempataban los goles a favor. "
                                   "En la primera fase había 2 zonas de 11 a dos ruedas: los dos primeros de cada zona jugaban "
                                   "las semifinales y la final, a un partido en cancha neutral; del 3.º al 6.º pasaban al "
                                   "Nacional, y los demás jugaban el Petit Torneo y el Torneo Reclasificatorio, en el que bajó "
                                   "Deportivo Morón. Como no subió nadie, en 1970 fueron 21 equipos.",
                           "descensos": "etapa",
                           "descienden_etapa": {"Segunda etapa del Reclasificatorio": ["deportivo-moron"]},
                           "goleadores_nota": "Los goles son solo de la final (de RSSSF, con los minutos): del resto del torneo "
                                              "no están. El goleador fue Walter Machado da Silva (Racing), con 14 goles.",
                           "nombre_playoffs": "Fase final",
                           "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                           "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1969-07-02T19:00Z", "fecha": "1969-07-02", "local": "chacarita-juniors", "visitante": "racing-club", "gl": 1, "gv": 0, "estadio": "Estadio La Bombonera"},
                               {"hora_utc": "1969-07-03T19:00Z", "fecha": "1969-07-03", "local": "boca-juniors", "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "Estadio El Cilindro", "alargue": True, "gana": "river-plate", "nota": "Pasó River por haber hecho más goles en la primera fase (35; Boca, 34)"},
                           ],
                           "Final": [
                               {"hora_utc": "1969-07-06T19:00Z", "fecha": "1969-07-06", "local": "chacarita-juniors", "visitante": "river-plate", "gl": 4, "gv": 1, "estadio": "Estadio El Cilindro", "arbitro": "Roberto Barreiro", "goles": [{"jugador": "Neumann", "equipo": "local", "min": 12}, {"jugador": "Trebucq", "equipo": "visitante", "min": 18}, {"jugador": "Neumann", "equipo": "local", "min": 37}, {"jugador": "Marcos", "equipo": "local", "min": 47}, {"jugador": "Frassoldati", "equipo": "local", "min": 56}]},
                           ],
                           }},
    # El Campeonato Nacional 1969 (septiembre a diciembre; campeón Boca): 18 equipos (13 del Metropolitano y 5 del Torneo
    # Regional) a una rueda, con 2 puntos por partido ganado; a Unión le descontaron 2 puntos. River y San Lorenzo
    # empataron el segundo puesto, que daba un lugar en la Libertadores 1970: jugaron un desempate a ida y vuelta (en
    # "playoffs"), y River va segundo en la tabla ("orden_a_mano"). ESPN no lo tiene: va a mano (tools/a_mano; Wikipedia,
    # controlada con RSSSF; del River-Boca de la última fecha, los goles de RSSSF; del desempate, los goles y los árbitros
    # de Wikipedia)
    "1969-nacional": {"nombre": "Campeonato Nacional 1969", "anio": 1969, "liga": "a_mano", "slug": "1969-nacional",
                      "zonas": "unica", "fechas": 17, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "desempate_goles": "gf", "orden_a_mano": ["river-plate", "san-lorenzo"],
                      "descuentos": {"union": 2},
                      "descuentos_texto": "A Unión se le descontaron 2 puntos. River y San Lorenzo terminaron empatados en "
                                          "el segundo puesto: lo definieron en un desempate a ida y vuelta (ganó River).",
                      "anual_texto": "La tabla del Campeonato Nacional 1969 (17 fechas, a una rueda). Cada partido ganado "
                                     "valía 2 puntos.",
                      "goleadores_nota": "Los goles son solo del River-Boca de la última fecha (de RSSSF) y del desempate "
                                         "(de Wikipedia). Los goleadores del torneo fueron Carlos Bulla (Platense) y Rodolfo "
                                         "Fischer (San Lorenzo), con 14 goles.",
                      "nombre_playoffs": "Desempate",
                      "playoffs": [(r"^$^", "Desempate por el segundo puesto")],
                      "playoffs_a_mano": {
                           "Desempate por el segundo puesto": [
                               {"hora_utc": "1969-12-17T19:00Z", "fecha": "1969-12-17", "local": "san-lorenzo", "visitante": "river-plate", "gl": 0, "gv": 1, "estadio": "Estadio José Amalfitani", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Marchetti", "equipo": "visitante", "min": 24}]},
                               {"hora_utc": "1969-12-21T19:00Z", "fecha": "1969-12-21", "local": "river-plate", "visitante": "san-lorenzo", "gl": 3, "gv": 2, "estadio": "Estadio El Cilindro", "arbitro": "Oscar Antonio Veiró", "goles": [{"jugador": "P. González", "equipo": "visitante", "min": 10}, {"jugador": "Montivero", "equipo": "local", "min": 31}, {"jugador": "Más", "equipo": "local", "min": 44, "tipo": "pen"}, {"jugador": "Más", "equipo": "local", "min": 78}, {"jugador": "Rosl", "equipo": "visitante", "min": 82}]},
                           ],
                      },
                      "ida_y_vuelta": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "cupos": {"anio": 1970, "fijos": True,
                                "libertadores": [("Campeón del Nacional 1969", "boca-juniors"),
                                                 ("Subcampeón del Nacional 1969 (ganó el desempate con San Lorenzo)",
                                                  "river-plate")]}},
    # 1970:el Campeonato Metropolitano 1970 (marzo a julio; campeón Independiente): 21 equipos a una rueda (21 fechas, en
    # cada una quedaba uno libre), con 2 puntos por partido ganado; con los mismos puntos desempataban los goles a favor
    # y después los goles en contra ("desempate_goles": "gf"). Después, por etapas ("etapas"; en tools/a_mano, cada fecha
    # dice su etapa): los doce primeros pasaban al Nacional; del 13.º al 16.º jugaban el Petit Torneo (los dos primeros
    # pasaban al Nacional) y los cinco últimos, con los dos últimos del Petit, el Torneo Reclasificatorio (a dos ruedas;
    # bajaban los dos últimos, Unión y Lanús, y el 4.º y el 5.º jugaban el Torneo de Promoción con dos de la Primera B:
    # subió Ferro y bajó Quilmes); los que bajaron, en "descienden_etapa". ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, sin goles)
    "1970-metropolitano": {"nombre": "Campeonato Metropolitano 1970", "anio": 1970, "liga": "a_mano", "slug": "1970-metropolitano",
                           "etapas": [("Campeonato Metropolitano", r"metropolitano$", 12, 1, 21,
                                       "Campeón: el primero. Los doce primeros pasan al Nacional; del 13.º al 16.º juegan el "
                                       "Petit Torneo, y los cinco últimos, el Torneo Reclasificatorio"),
                                      ("Petit Torneo", r"petit$", 2, 22, 3,
                                       "Los dos primeros pasan al Nacional; los otros dos, al Torneo Reclasificatorio"),
                                      ("Torneo Reclasificatorio", r"reclasificatorio$", 3, 25, 14,
                                       "Los tres primeros se quedan en Primera; el 4.º y el 5.º juegan el Torneo de Promoción"),
                                      ("Torneo de Promoción", r"promocion$", 2, 39, 3,
                                       "Los dos primeros juegan en Primera en 1971 (Ferro, de la Primera B, sube)")],
                           "fechas": 41, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Campeonato Metropolitano",
                           "desempate_goles": "gf",
                           "nota": "Cada partido ganado valía 2 puntos y, con los mismos puntos, desempataban los goles a favor "
                                   "y después los goles en contra. Eran 21 equipos a una rueda. Los doce primeros jugaron el "
                                   "Nacional; los otros, el Petit Torneo y el Torneo Reclasificatorio, y el 4.º y el 5.º del "
                                   "Reclasificatorio, el Torneo de Promoción con Ferro y Almirante Brown, de la Primera B.",
                           "descensos": "etapa",
                           "descienden_etapa": {"Torneo Reclasificatorio": ["union", "lanus"], "Torneo de Promoción": ["quilmes"]},
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Oscar Más (River), con 16 "
                                              "goles."},
    # El Campeonato Nacional 1970 (septiembre a diciembre; campeón Boca): 20 equipos en 2 zonas de 10 a dos ruedas
    # ("zonas_a_mano"), con dos fechas de interzonales (la 4 y la 14), con 2 puntos por partido ganado y el mismo
    # desempate del Metropolitano; a Platense le descontaron 2 puntos. Los dos primeros de cada zona jugaban las
    # semifinales y la final, a un partido en cancha neutral. ESPN no lo tiene: va a mano (tools/a_mano; Wikipedia,
    # controlada con RSSSF; de la fase final, también los goles y los árbitros). A la Libertadores 1971 fueron el campeón
    # y el subcampeón
    "1970-nacional": {"nombre": "Campeonato Nacional 1970", "anio": 1970, "liga": "a_mano", "slug": "1970-nacional",
                      "zonas_a_mano": {"A": ["chacarita-juniors", "gimnasia-y-esgrima", "river-plate", "san-lorenzo", "gimnasia-mendoza", "racing-club", "newell-s-old-boys", "talleres", "san-martin-tucuman", "platense"],
                                       "B": ["rosario-central", "boca-juniors", "velez-sarsfield", "independiente", "estudiantes-de-la-plata", "banfield", "atlanta", "kimberley", "gimnasia-jujuy", "san-martin-san-juan"]},
                      "fechas": 20, "pasan": 2, "puntos_victoria": 2, "desempate_goles": "gf",
                      "texto_pasan": "Pasan a las semifinales (los dos primeros de cada zona). Las fechas 4 y 14 fueron de "
                                     "interzonales",
                      "descuentos": {"platense": 2},
                      "descuentos_texto": "A Platense se le descontaron 2 puntos.",
                      "goleadores_nota": "Los goles son solo de las semifinales y la final (de Wikipedia, con los minutos). El "
                                         "goleador del torneo fue Carlos Bianchi (Vélez), con 18 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1970-12-19T19:00Z", "fecha": "1970-12-19", "local": "rosario-central", "visitante": "gimnasia-y-esgrima", "gl": 3, "gv": 0, "estadio": "Estadio Coloso del Parque", "arbitro": "Roberto Goicoechea", "goles": [{"jugador": "Landucci", "equipo": "local", "min": 52}, {"jugador": "Bustos", "equipo": "local", "min": 70}, {"jugador": "Poy", "equipo": "local", "min": 77}]},
                               {"hora_utc": "1970-12-20T19:00Z", "fecha": "1970-12-20", "local": "chacarita-juniors", "visitante": "boca-juniors", "gl": 0, "gv": 2, "estadio": "Estadio El Cilindro", "arbitro": "Humberto Orestes Dellacasa", "goles": [{"jugador": "Coch", "equipo": "visitante", "min": 5}, {"jugador": "Coch", "equipo": "visitante", "min": 72}]},
                           ],
                           "Final": [
                               {"hora_utc": "1970-12-23T19:00Z", "fecha": "1970-12-23", "local": "boca-juniors", "visitante": "rosario-central", "gl": 2, "gv": 1, "estadio": "Estadio Monumental", "arbitro": "Ángel Coerezza", "alargue": True, "goles": [{"jugador": "Rojas", "equipo": "local", "min": 80}, {"jugador": "Coch", "equipo": "local", "min": 108}, {"jugador": "Landucci", "equipo": "visitante", "min": 41}]},
                           ],
                      },
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "anual_texto": "La tabla de las dos zonas del Campeonato Nacional 1970 (los 20 equipos, con los "
                                     "interzonales). Cada partido ganado valía 2 puntos.",
                      "cupos": {"anio": 1971, "fijos": True,
                                "libertadores": [("Campeón del Nacional 1970", "boca-juniors"),
                                                 ("Subcampeón del Nacional 1970", "rosario-central")]}},
    # 1971: el Campeonato Metropolitano 1971 (marzo a septiembre; campeón Independiente): 19 equipos a dos ruedas (38
    # fechas, en cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano;
    # RSSSF, con los goleadores, solo con el apellido y sin minutos). Sin promedios: bajaban los dos últimos de la tabla
    # ("descensos": "tabla"): Los Andes y Platense. A la Libertadores 1972 fueron el campeón del Nacional (Rosario Central)
    # e Independiente, que le ganó al subcampeón del Nacional (San Lorenzo) el partido por el segundo lugar
    "1971-metropolitano": {"nombre": "Campeonato Metropolitano 1971", "anio": 1971, "liga": "a_mano", "slug": "1971-metropolitano",
                           "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1971 (las 38 fechas; eran 19 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "Los goles son de RSSSF, solo con el apellido (falta uno). El goleador fue Carlos "
                                              "Bianchi (Vélez), con 36 goles.",
                           "descensos": "tabla", "descienden": 2,
                           "cupos": {"anio": 1972, "fijos": True,
                                     "libertadores": [("Campeón del Nacional 1971", "rosario-central"),
                                                      ("Ganador del partido entre el campeón del Metropolitano y el subcampeón "
                                                       "del Nacional", "independiente")],
                                     "nota": "Independiente, campeón del Metropolitano, le ganó a San Lorenzo, subcampeón del "
                                             "Nacional, el partido por el segundo lugar: 1-0 en cancha de Boca (29 de "
                                             "diciembre)."}},
    # El Campeonato Nacional 1971 (octubre a diciembre; campeón Rosario Central): 28 equipos en 2 zonas de 14 a una rueda
    # ("zonas_a_mano"), con una fecha de interzonales (la 11), con 2 puntos por partido ganado; a Huracán de Ingeniero White
    # le descontaron 2 puntos. Los dos primeros de cada zona jugaban las semifinales (el primero de una zona con el segundo
    # de la otra) y la final, a un partido en cancha neutral. ESPN no lo tiene: va a mano (tools/a_mano; resultados, días y
    # estadios de Wikipedia, goles de RSSSF; de la fase final, los goles con los minutos y los árbitros de Wikipedia)
    "1971-nacional": {"nombre": "Campeonato Nacional 1971", "anio": 1971, "liga": "a_mano", "slug": "1971-nacional",
                      "zonas_a_mano": {"A": ["independiente", "newell-s-old-boys", "belgrano", "river-plate", "argentinos-juniors", "ferro-carril-oeste", "banfield", "kimberley", "san-martin-mendoza", "gimnasia-y-esgrima", "huracan", "juventud-antoniana", "don-orione", "huracan-comodoro-rivadavia"],
                                       "B": ["rosario-central", "san-lorenzo", "boca-juniors", "gimnasia-mendoza", "atlanta", "velez-sarsfield", "estudiantes-de-la-plata", "racing-club", "chacarita-juniors", "colon", "san-martin-tucuman", "guarani-antonio-franco", "central-cordoba", "huracan-ingeniero-white"]},
                      "fechas": 14, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a las semifinales (los dos primeros de cada zona). La fecha 11 fue de interzonales",
                      "descuentos": {"huracan-ingeniero-white": 2},
                      "descuentos_texto": "A Huracán de Ingeniero White se le descontaron 2 puntos.",
                      "goleadores_nota": "Los goles de la fase de zonas son de RSSSF, solo con el apellido y sin minutos "
                                         "(faltan tres); los de la fase final, de Wikipedia, con los minutos. Los goleadores "
                                         "del torneo fueron José Luñiz (Juventud Antoniana) y Alfredo Obberti (Newell's), "
                                         "con 10 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1971-12-18T19:00Z", "fecha": "1971-12-18", "local": "independiente", "visitante": "san-lorenzo", "gl": 2, "gv": 2, "estadio": "Estadio Monumental", "arbitro": "Humberto Orestes Dellacasa", "alargue": True, "pen_l": 6, "pen_v": 7, "goles": [{"jugador": "Semenewicz", "equipo": "local", "min": 9}, {"jugador": "Maglioni", "equipo": "local", "min": 37}, {"jugador": "Ayala", "equipo": "visitante", "min": 60}, {"jugador": "Fischer", "equipo": "visitante", "min": 90}]},
                               {"hora_utc": "1971-12-19T19:00Z", "fecha": "1971-12-19", "local": "rosario-central", "visitante": "newell-s-old-boys", "gl": 1, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Poy", "equipo": "local", "min": 54}]},
                           ],
                           "Final": [
                               {"hora_utc": "1971-12-22T19:00Z", "fecha": "1971-12-22", "local": "rosario-central", "visitante": "san-lorenzo", "gl": 2, "gv": 1, "estadio": "Estadio Coloso del Parque", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Gramajo", "equipo": "local", "min": 17}, {"jugador": "Colman", "equipo": "local", "min": 23}, {"jugador": "Scotta", "equipo": "visitante", "min": 5}]},
                           ],
                      },
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1972: el Campeonato Metropolitano 1972 (febrero a octubre; campeón San Lorenzo): 18 equipos a dos ruedas (34 fechas),
    # con 2 puntos por partido ganado; a Banfield le descontaron 21 puntos. Después, los seis últimos jugaron el Torneo
    # Reclasificatorio (a una rueda, en cancha neutral), cuyos puntos se sumaban a los del Metropolitano ("etapa_suma"):
    # bajaban los dos últimos de la suma, Lanús y Banfield. Va por etapas (en tools/a_mano, cada fecha dice su etapa).
    # ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles). A la Libertadores 1973 fueron los campeones del
    # Metropolitano y del Nacional (San Lorenzo, los dos) y River, subcampeón del Nacional
    "1972-metropolitano": {"nombre": "Campeonato Metropolitano 1972", "anio": 1972, "liga": "a_mano", "slug": "1972-metropolitano",
                           "etapas": [("Campeonato Metropolitano", r"metropolitano$", 0, 1, 34,
                                       "Campeón: el primero. Los seis últimos jugaron el Torneo Reclasificatorio"),
                                      ("Torneo Reclasificatorio", r"reclasificatorio$", 0, 35, 5,
                                       "A una rueda, en cancha neutral")],
                           "fechas": 39, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Campeonato Metropolitano",
                           "nota": "Cada partido ganado valía 2 puntos. Eran 18 equipos a dos ruedas; los seis últimos jugaron "
                                   "después el Torneo Reclasificatorio, cuyos puntos se sumaban a los del Metropolitano: "
                                   "bajaban los dos últimos de esa suma.",
                           "descuentos": {"banfield": 21},
                           "descuentos_texto": "A Banfield se le descontaron 21 puntos: lo suspendieron cuatro meses desde el 16 "
                                               "de marzo, que eran 36 puntos, pero como solo sumó 21, se le perdonaron los otros "
                                               "15.",
                           "descensos": "etapa", "descienden": 2, "etapa_suma": "Torneo Reclasificatorio",
                           "texto_suma": "Los puntos del Metropolitano (con el descuento a Banfield) más los del Torneo "
                                         "Reclasificatorio.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Miguel Brindisi "
                                              "(Huracán), con 21 goles."},
    # El Campeonato Nacional 1972 (octubre a diciembre; campeón San Lorenzo): 26 equipos en 2 zonas de 13 a una rueda
    # ("zonas_a_mano"; 13 fechas: en cada una, el que quedaba libre jugaba un interzonal), con 2 puntos por partido ganado.
    # Pasaba el primero de cada zona, y el segundo solo si quedaba a tres puntos o menos (River sí, Colón no): River jugó
    # la semifinal con Boca y San Lorenzo pasó directo a la final, a un partido en cancha neutral. ESPN no lo tiene: va a
    # mano (tools/a_mano; Wikipedia, controlada con RSSSF; de la semifinal y la final, también los goles y los árbitros)
    "1972-nacional": {"nombre": "Campeonato Nacional 1972", "anio": 1972, "liga": "a_mano", "slug": "1972-nacional",
                      "zonas_a_mano": {"A": ["san-lorenzo", "river-plate", "velez-sarsfield", "san-martin-mendoza", "atlanta", "rosario-central", "independiente", "san-lorenzo-mdp", "lanus", "gimnasia-y-esgrima", "san-martin-tucuman", "bartolome-mitre", "independiente-trelew"],
                                       "B": ["boca-juniors", "colon", "argentinos-juniors", "huracan", "racing-club", "belgrano", "banfield", "ferro-carril-oeste", "sportivo-desamparados", "chacarita-juniors", "gimnasia-mendoza", "estudiantes-de-la-plata", "newell-s-old-boys"]},
                      "fechas": 13, "pasan": 1, "puntos_victoria": 2,
                      "texto_pasan": "Pasa a la fase final el primero de cada zona, y el segundo solo si quedaba a tres puntos "
                                     "o menos: pasó River (a uno de San Lorenzo), que jugó la semifinal con Boca, y San "
                                     "Lorenzo fue directo a la final. En cada fecha, el que quedaba libre jugaba un interzonal",
                      "goleadores_nota": "Los goles son solo de la semifinal y la final (de Wikipedia, con los minutos; RSSSF "
                                         "pone el de Figueroa a los 102). El goleador del torneo fue Carlos Morete (River), "
                                         "con 14 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                      "cuadro_desde": "Final",
                      "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1972-12-13T19:00Z", "fecha": "1972-12-13", "local": "boca-juniors", "visitante": "river-plate", "gl": 2, "gv": 3, "estadio": "Estadio José Amalfitani", "arbitro": "Humberto Orestes Dellacasa", "goles": [{"jugador": "Rogel", "equipo": "local", "min": 30}, {"jugador": "Curioni", "equipo": "local", "min": 74}, {"jugador": "Mastrángelo", "equipo": "visitante", "min": 32}, {"jugador": "Mouzo", "equipo": "visitante", "min": 45, "tipo": "ec"}, {"jugador": "Morete", "equipo": "visitante", "min": 54}]},
                           ],
                           "Final": [
                               {"hora_utc": "1972-12-17T19:00Z", "fecha": "1972-12-17", "local": "san-lorenzo", "visitante": "river-plate", "gl": 1, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Roberto Goicoechea", "alargue": True, "goles": [{"jugador": "Figueroa", "equipo": "local", "min": 100}]},
                           ],
                      },
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "anual_texto": "La tabla de las dos zonas del Campeonato Nacional 1972 (los 26 equipos, con los "
                                     "interzonales). Cada partido ganado valía 2 puntos.",
                      "cupos": {"anio": 1973, "fijos": True,
                                "libertadores": [("Campeón del Metropolitano y del Nacional 1972", "san-lorenzo"),
                                                 ("Subcampeón del Nacional 1972", "river-plate")]}},
    # 1973: el Campeonato Metropolitano 1973 (marzo a septiembre; campeón Huracán): 17 equipos a dos ruedas (34 fechas,
    # en cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano;
    # resultados de RSSSF, días y estadios de Wikipedia; sin goles). No hubo descensos. A la Libertadores 1974 fueron los
    # campeones del Metropolitano y del Nacional
    "1973-metropolitano": {"nombre": "Campeonato Metropolitano 1973", "anio": 1973, "liga": "a_mano", "slug": "1973-metropolitano",
                           "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1973 (las 34 fechas; eran 17 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "No están los goles de este torneo. Los goleadores fueron Hugo Curioni (Boca), "
                                              "Oscar Más (River) e Ignacio Peña (Estudiantes), con 17 goles.",
                           "sin_descensos": "No hubo descensos: la AFA los anuló.",
                           "cupos": {"anio": 1974, "fijos": True,
                                     "libertadores": [("Campeón del Metropolitano 1973", "huracan"),
                                                      ("Campeón del Nacional 1973", "rosario-central")]}},
    # El Campeonato Nacional 1973 (octubre a diciembre; campeón Rosario Central): 30 equipos por etapas ("etapas"; en
    # tools/a_mano, cada fecha dice su etapa y cada partido su zona): la fase de zonas, 2 zonas de 15 a una rueda (15
    # fechas; en cada una, el que quedaba libre jugaba un interzonal, sin zona en el archivo), y el cuadrangular final, los
    # dos primeros de cada zona a una rueda en cancha neutral (el primero fue el campeón, "campeon_etapa"). Con 2 puntos por
    # partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; Wikipedia, controlada con RSSSF). No había descensos
    "1973-nacional": {"nombre": "Campeonato Nacional 1973", "anio": 1973, "liga": "a_mano", "slug": "1973-nacional",
                      "etapas": [("Fase de zonas", r"zonas$", 2, 1, 15,
                                  "Los dos primeros de cada zona pasan al cuadrangular final. En cada fecha, el que quedaba "
                                  "libre en su zona jugaba un interzonal, que suma en su zona"),
                                 ("Cuadrangular final", r"cuadrangular$", 0, 16, 3, "Campeón: el primero")],
                      "fechas": 18, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Cuadrangular final",
                      "nota": "Cada partido ganado valía 2 puntos. En la fase de zonas había 2 zonas de 15 a una rueda; los "
                              "dos primeros de cada zona jugaban el cuadrangular final, a una rueda y en cancha neutral, y el "
                              "primero fue el campeón.",
                      "goleadores_nota": "Solo están los goles del partido en que Rosario Central salió campeón (San Lorenzo 1, "
                                         "Rosario Central 1). El goleador del torneo fue Juan Gómez Voglino (Atlanta), con 18 "
                                         "goles.",
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1974: el Campeonato Metropolitano 1974 (febrero a junio; campeón Newell's): 18 equipos por etapas ("etapas"; en
    # tools/a_mano, cada fecha dice su etapa y cada partido su zona): la primera fase, 2 zonas de 9 a dos ruedas (18
    # fechas; en cada una, el que quedaba libre jugaba un interzonal, sin zona en el archivo); Boca y Ferro empataron el
    # segundo puesto de la zona B y jugaron un desempate ("desempate_a_mano"); y el cuadrangular final, los dos primeros
    # de cada zona a una rueda en cancha neutral (el primero fue el campeón, "campeon_etapa"). Con 2 puntos por partido
    # ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles). No hubo descensos
    "1974-metropolitano": {"nombre": "Campeonato Metropolitano 1974", "anio": 1974, "liga": "a_mano", "slug": "1974-metropolitano",
                           "etapas": [("Primera fase", r"primera-fase$", 2, 1, 18,
                                       "Los dos primeros de cada zona pasan al cuadrangular final. En cada fecha, el que "
                                       "quedaba libre en su zona jugaba un interzonal, que suma en su zona"),
                                      ("Cuadrangular final", r"cuadrangular$", 0, 19, 3, "Campeón: el primero")],
                           "fechas": 21, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Cuadrangular final",
                           "nota": "Cada partido ganado valía 2 puntos. En la primera fase había 2 zonas de 9 a dos ruedas: "
                                   "los dos primeros de cada zona jugaban el cuadrangular final, a una rueda y en cancha "
                                   "neutral, y el primero fue el campeón.",
                           "desempate_a_mano": {"fecha": "1974-05-22", "local": "ferro-carril-oeste", "visitante": "boca-juniors",
                                                "gl": 0, "gv": 2, "estadio": "Cancha de Vélez Sarsfield"},
                           "desempate_texto": "Boca y Ferro terminaron empatados en puntos en el segundo puesto de la zona B: "
                                              "lo definieron en un partido, en cancha de Vélez, y pasó Boca al cuadrangular "
                                              "final.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo (solo los de Rosario Central-Newell's, "
                                              "el del título). El goleador fue Carlos Morete (River), con 18 goles.",
                           "sin_descensos": "No hubo descensos: la AFA los anuló."},
    # El Campeonato Nacional 1974 (julio a diciembre; campeón San Lorenzo): 36 equipos por etapas: la fase de zonas, 4
    # zonas de 9 a dos ruedas (18 fechas; en cada una, el que quedaba libre jugaba un interzonal), y el octogonal final, los
    # dos primeros de cada zona a una rueda (el primero fue el campeón). Con 2 puntos por partido ganado. Después, el
    # Reducido por los dos lugares en la Libertadores 1975 (Newell's, San Lorenzo y Rosario Central, el subcampeón de los
    # dos torneos), a una rueda: va como "triangular" (con "pasan_triangular", los dos que fueron). ESPN no lo tiene: va a
    # mano (tools/a_mano; resultados de RSSSF, días y estadios de Wikipedia; del Reducido, los goles y los árbitros de
    # Wikipedia). No había descensos
    "1974-nacional": {"nombre": "Campeonato Nacional 1974", "anio": 1974, "liga": "a_mano", "slug": "1974-nacional",
                      "etapas": [("Fase de zonas", r"zonas$", 2, 1, 18,
                                  "Los dos primeros de cada zona pasan al octogonal final. En cada fecha, el que quedaba "
                                  "libre en su zona jugaba un interzonal, que suma en su zona"),
                                 ("Octogonal final", r"octogonal$", 0, 19, 7, "Campeón: el primero")],
                      "fechas": 25, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Octogonal final",
                      "nota": "Cada partido ganado valía 2 puntos. En la fase de zonas había 4 zonas de 9 a dos ruedas; los "
                              "dos primeros de cada zona jugaban el octogonal final, a una rueda, y el primero fue el "
                              "campeón.",
                      "goleadores_nota": "Solo están los goles del partido en que San Lorenzo salió campeón (Ferro 2, San "
                                         "Lorenzo 3) y los del Reducido. El goleador del torneo fue Mario Kempes "
                                         "(Rosario Central), con 25 goles.",
                      "nombre_playoffs": "Reducido por la Libertadores",
                      "playoffs": [(r"^$^", "Reducido por la Libertadores")],
                      "triangular": True, "pasan_triangular": 2,
                      "texto_triangular": "Los campeones del Metropolitano (Newell's) y del Nacional (San Lorenzo) y Rosario "
                                          "Central, subcampeón de los dos, jugaron por los dos lugares en la Copa Libertadores "
                                          "1975, a una rueda: fueron Rosario Central y Newell's.",
                      "playoffs_a_mano": {
                           "Reducido por la Libertadores": [
                               {"hora_utc": "1974-12-26T19:00Z", "fecha": "1974-12-26", "local": "san-lorenzo", "visitante": "rosario-central", "gl": 0, "gv": 1, "estadio": "Estadio El Cilindro", "arbitro": "Roberto Osvaldo Barreiro", "goles": [{"jugador": "Zavagno", "equipo": "visitante", "min": 76}]},
                               {"hora_utc": "1974-12-28T19:00Z", "fecha": "1974-12-28", "local": "newell-s-old-boys", "visitante": "san-lorenzo", "gl": 2, "gv": 0, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Raúl Loureiro", "goles": [{"jugador": "Zanabria", "equipo": "local", "min": 28}, {"jugador": "Zanabria", "equipo": "local", "min": 64, "tipo": "pen"}]},
                               {"hora_utc": "1974-12-30T19:00Z", "fecha": "1974-12-30", "local": "rosario-central", "visitante": "newell-s-old-boys", "gl": 2, "gv": 0, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Luis Pestarino", "goles": [{"jugador": "Kempes", "equipo": "local", "min": 28}, {"jugador": "Cabral", "equipo": "local", "min": 80}]},
                           ],
                      },
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1975: el Campeonato Metropolitano 1975 (febrero a agosto; campeón River): 20 equipos a dos ruedas (38 fechas), con
    # 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles). No hubo descensos: la AFA
    # los anuló por tercera temporada seguida. A la Libertadores 1976 fueron los campeones del Metropolitano y del Nacional
    "1975-metropolitano": {"nombre": "Campeonato Metropolitano 1975", "anio": 1975, "liga": "a_mano", "slug": "1975-metropolitano",
                           "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1975 (las 38 fechas). Cada partido ganado "
                                          "valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Héctor Scotta (San "
                                              "Lorenzo), con 32 goles.",
                           "sin_descensos": "No hubo descensos: la AFA los anuló por tercera temporada seguida.",
                           "cupos": {"anio": 1976, "fijos": True,
                                     "libertadores": [("Campeón del Metropolitano y del Nacional 1975", "river-plate"),
                                                      ("Ganador del desempate de los subcampeones", "estudiantes-de-la-plata")],
                                     "nota": "River ganó los dos torneos del año: el otro lugar lo jugaron los subcampeones, "
                                             "Huracán (del Metropolitano) y Estudiantes (del Nacional), a un partido en cancha "
                                             "de Racing (25 de enero de 1976): 3-2 para Estudiantes."}},
    # El Campeonato Nacional 1975 (septiembre a diciembre; campeón River): 32 equipos por etapas ("etapas"; en tools/a_mano,
    # cada fecha dice su etapa y cada partido su zona): la fase de zonas, 4 zonas de 8 a dos ruedas con dos fechas de
    # interzonales (la 1 y la 9; sin zona en el archivo), y el torneo final, los dos primeros de cada zona a una rueda (el
    # primero fue el campeón, "campeon_etapa"). Con 2 puntos por partido ganado; a Banfield le descontaron 2 puntos. ESPN no
    # lo tiene: va a mano (tools/a_mano; resultados de RSSSF, días y estadios de Wikipedia). No había descensos
    "1975-nacional": {"nombre": "Campeonato Nacional 1975", "anio": 1975, "liga": "a_mano", "slug": "1975-nacional",
                      "etapas": [("Fase de zonas", r"zonas$", 2, 1, 16,
                                  "Los dos primeros de cada zona pasan al torneo final. Las fechas 1 y 9 fueron de "
                                  "interzonales, que suman en la zona de cada club"),
                                 ("Torneo final", r"octogonal$", 0, 17, 7, "Campeón: el primero")],
                      "fechas": 23, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Torneo final",
                      "nota": "Cada partido ganado valía 2 puntos. En la fase de zonas había 4 zonas de 8 a dos ruedas, con "
                              "dos fechas de interzonales; los dos primeros de cada zona jugaban el torneo final, a una "
                              "rueda, y el primero fue el campeón.",
                      "descuentos": {"banfield": 2},
                      "descuentos_texto": "A Banfield se le descontaron 2 puntos.",
                      "goleadores_nota": "Solo están los goles del partido en que River salió campeón (Rosario Central 1, "
                                         "River 2). El goleador del torneo fue Héctor Scotta (San Lorenzo), con 28 goles.",
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1976: el Campeonato Metropolitano 1976 (febrero a agosto; campeón Boca): 22 equipos por etapas ("etapas"; en
    # tools/a_mano, cada fecha o cada partido dice su etapa, y cada partido su zona): la primera fase, 2 zonas de 11 a dos
    # ruedas (22 fechas; en cada una, el que quedaba libre jugaba un interzonal, sin zona en el archivo); los seis primeros
    # de cada zona jugaban el Torneo Campeonato (a una rueda; el primero era el campeón, "campeon_etapa") y los otros, el
    # Torneo por el descenso (a una rueda, en las mismas fechas; bajaba el último, "descensos": "etapa": San Telmo). Con 2
    # puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, con los goleadores, solo con el apellido
    # y sin minutos)
    "1976-metropolitano": {"nombre": "Campeonato Metropolitano 1976", "anio": 1976, "liga": "a_mano", "slug": "1976-metropolitano",
                           "etapas": [("Primera fase", r"primera-fase$", 6, 1, 22,
                                       "Los seis primeros de cada zona pasan al Torneo Campeonato; los otros, al Torneo por el "
                                       "descenso. En cada fecha, el que quedaba libre en su zona jugaba un interzonal, que "
                                       "suma en su zona"),
                                      ("Torneo Campeonato", r"campeonato$", 0, 23, 11, "Campeón: el primero"),
                                      ("Torneo por el descenso", r"descenso$", 0, 23, 9,
                                       "A una rueda, en las mismas fechas que el Torneo Campeonato")],
                           "fechas": 33, "pasan": 0, "puntos_victoria": 2, "campeon_etapa": "Torneo Campeonato",
                           "nota": "Cada partido ganado valía 2 puntos. En la primera fase había 2 zonas de 11 a dos ruedas: "
                                   "los seis primeros de cada zona jugaban el Torneo Campeonato, a una rueda, y el primero fue "
                                   "el campeón; los otros diez, el Torneo por el descenso, también a una rueda, en el que bajaba "
                                   "el último.",
                           "descensos": "etapa", "descienden": 1,
                           "goleadores_nota": "Los goles son de RSSSF, solo con el apellido. El goleador fue Mario Kempes "
                                              "(Rosario Central), con 21 goles."},
    # El Campeonato Nacional 1976 (septiembre a diciembre; campeón Boca): 34 equipos (los del Metropolitano, menos el que
    # bajó, y los del interior) en 4 zonas ("zonas_a_mano"): la A y la B de 8, a dos ruedas, con dos fechas de
    # interzonales entre ellas (la 3 y la 11), y la C y la D de 9, a dos ruedas (en cada fecha, el que quedaba libre jugaba
    # un interzonal con el de la otra). Con 2 puntos por partido ganado; los dos primeros de cada zona jugaban la fase
    # final, a un partido; antes, Boca-Quilmes y Talleres-Newell's desempataron el primer puesto de sus zonas. ESPN no lo
    # tiene: va a mano (tools/a_mano; resultados y goles de RSSSF, días y estadios de Wikipedia; de la fase final, los
    # goles con los minutos y los árbitros de Wikipedia). Como Boca ganó los dos torneos, el segundo lugar en la
    # Libertadores 1977 lo jugaron los dos subcampeones, River y Huracán
    "1976-nacional": {"nombre": "Campeonato Nacional 1976", "anio": 1976, "liga": "a_mano", "slug": "1976-nacional",
                      "zonas_a_mano": {"A": ["boca-juniors", "quilmes", "independiente", "atletico-tucuman", "gimnasia-jujuy", "gimnasia-y-esgrima", "chacarita-juniors", "temperley"],
                                       "B": ["river-plate", "banfield", "estudiantes-de-la-plata", "racing-club", "atlanta", "ledesma", "san-martin-tucuman", "san-telmo"],
                                       "C": ["huracan", "union", "rosario-central", "san-martin-mendoza", "aldosivi", "velez-sarsfield", "platense", "sportivo-patria", "all-boys"],
                                       "D": ["talleres", "newell-s-old-boys", "ferro-carril-oeste", "argentinos-juniors", "huracan-comodoro-rivadavia", "central-norte", "colon", "san-lorenzo", "san-lorenzo-mdp"]},
                      "fechas": 18, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona). Las zonas A y B jugaron entre "
                                     "ellas dos fechas de interzonales; en la C y la D, el que quedaba libre en cada fecha "
                                     "jugaba un interzonal",
                      "goleadores_nota": "Los goles de la fase de zonas son de RSSSF, solo con el apellido y sin minutos; los "
                                         "de la fase final, de Wikipedia, con los minutos. Los goleadores del torneo fueron "
                                         "Norberto Eresuma (San Lorenzo de Mar del Plata), Luis Ludueña (Talleres) y Víctor "
                                         "Marchetti (Unión), con 12 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Desempates por el primer puesto", "Cuartos de final", "Semifinales", "Final")],
                      "cuadro_desde": "Cuartos de final",
                      "playoffs_a_mano": {
                           "Desempates por el primer puesto": [
                               {"hora_utc": "1976-12-14T19:00Z", "fecha": "1976-12-14", "local": "boca-juniors", "visitante": "quilmes", "gl": 2, "gv": 1, "estadio": "Estadio El Cilindro", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Alves", "equipo": "local", "min": 13}, {"jugador": "Ovide", "equipo": "local", "min": 39}, {"jugador": "Gramajo", "equipo": "visitante", "min": 20}]},
                               {"hora_utc": "1976-12-14T19:00Z", "fecha": "1976-12-14", "local": "talleres", "visitante": "newell-s-old-boys", "gl": 3, "gv": 1, "estadio": "Estadio Boutique de Barrio Jardín", "arbitro": "Sergio García", "alargue": True, "goles": [{"jugador": "Alderete", "equipo": "local", "min": 39}, {"jugador": "Alderete", "equipo": "local", "min": 98}, {"jugador": "Cherini", "equipo": "local", "min": 105}, {"jugador": "Irigoyen", "equipo": "visitante", "min": 24}]},
                           ],
                           "Cuartos de final": [
                               {"hora_utc": "1976-12-16T19:00Z", "fecha": "1976-12-16", "local": "boca-juniors", "visitante": "banfield", "gl": 2, "gv": 1, "estadio": "Estadio El Cilindro", "arbitro": "Alberto Ducatelli", "goles": [{"jugador": "Felman", "equipo": "local", "min": 3, "tipo": "pen"}, {"jugador": "Taverna", "equipo": "local", "min": 63}, {"jugador": "Sacconi", "equipo": "visitante", "min": 33}]},
                               {"hora_utc": "1976-12-16T19:00Z", "fecha": "1976-12-16", "local": "huracan", "visitante": "newell-s-old-boys", "gl": 2, "gv": 0, "estadio": "Estadio La Bombonera", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Saldaño", "equipo": "local", "min": 11}, {"jugador": "Houseman", "equipo": "local", "min": 75, "tipo": "pen"}]},
                               {"hora_utc": "1976-12-16T19:00Z", "fecha": "1976-12-16", "local": "river-plate", "visitante": "quilmes", "gl": 2, "gv": 1, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Ángel Coerezza", "goles": [{"jugador": "Más", "equipo": "local", "min": 28}, {"jugador": "Más", "equipo": "local", "min": 36}, {"jugador": "Kaliszuk", "equipo": "visitante", "min": 44}]},
                               {"hora_utc": "1976-12-16T19:00Z", "fecha": "1976-12-16", "local": "talleres", "visitante": "union", "gl": 4, "gv": 0, "estadio": "Estadio Juan Domingo Perón", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Regenhardt", "equipo": "local", "min": 3, "tipo": "ec"}, {"jugador": "Alderete", "equipo": "local", "min": 23}, {"jugador": "Bocanelli", "equipo": "local", "min": 63}, {"jugador": "Bravo", "equipo": "local", "min": 83}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1976-12-19T19:00Z", "fecha": "1976-12-19", "local": "boca-juniors", "visitante": "huracan", "gl": 1, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Roberto Osvaldo Barreiro", "goles": [{"jugador": "Mastrángelo", "equipo": "local", "min": 11}]},
                               {"hora_utc": "1976-12-19T19:00Z", "fecha": "1976-12-19", "local": "river-plate", "visitante": "talleres", "gl": 1, "gv": 0, "estadio": "Estadio La Bombonera", "arbitro": "Luis Pestarino", "goles": [{"jugador": "Passarella", "equipo": "local", "min": 17}]},
                           ],
                           "Final": [
                               {"hora_utc": "1976-12-22T19:00Z", "fecha": "1976-12-22", "local": "boca-juniors", "visitante": "river-plate", "gl": 1, "gv": 0, "estadio": "Estadio El Cilindro", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Suñé", "equipo": "local", "min": 72}]},
                           ],
                      },
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "anual_texto": "La tabla de la fase de zonas del Campeonato Nacional 1976 (los 34 equipos, con los "
                                     "interzonales). Cada partido ganado valía 2 puntos.",
                      "cupos": {"anio": 1977, "fijos": True,
                                "libertadores": [("Campeón del Metropolitano y del Nacional 1976", "boca-juniors"),
                                                 ("Ganador del desempate de los subcampeones", "river-plate")],
                                "nota": "Boca ganó los dos torneos del año: el otro lugar lo jugaron los subcampeones, Huracán "
                                        "(del Metropolitano) y River (del Nacional), a un partido en cancha de Boca (29 de "
                                        "diciembre): 4-1 para River."}},
    # 1977: el Campeonato Metropolitano 1977 (febrero a noviembre; campeón River): 23 equipos a dos ruedas (46 fechas, en
    # cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, con
    # los goleadores, solo con el apellido y sin minutos). Sin promedios: bajaban los tres últimos de la tabla
    # ("descensos": "tabla"); Platense y Lanús empataron en el anteúltimo lugar de los que se salvaban y jugaron un
    # desempate (0-0, penales para Platense: bajó Lanús, con Temperley y Ferro). A la Libertadores 1978 fueron los campeones
    # del Metropolitano y del Nacional
    "1977-metropolitano": {"nombre": "Campeonato Metropolitano 1977", "anio": 1977, "liga": "a_mano", "slug": "1977-metropolitano",
                           "zonas": "unica", "fechas": 46, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1977 (las 46 fechas; eran 23 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "Los goles son de RSSSF, solo con el apellido (faltan tres). El goleador fue "
                                              "Carlos Álvarez (Argentinos), con 27 goles.",
                           "descensos": "tabla", "descienden": 3,
                           "desempate_a_mano": {"fecha": "1977-11-16", "local": "platense", "visitante": "lanus", "gl": 0, "gv": 0,
                                                "pen_l": 8, "pen_v": 7, "estadio": "Cancha de San Lorenzo"},
                           "desempate_texto": "Platense y Lanús terminaron empatados en puntos arriba de Temperley y Ferro, "
                                              "en el último lugar del descenso: lo definieron en un partido, en cancha de San "
                                              "Lorenzo (0-0 y penales para Platense), y bajó Lanús.",
                           "cupos": {"anio": 1978, "fijos": True,
                                     "libertadores": [("Campeón del Metropolitano 1977", "river-plate"),
                                                      ("Campeón del Nacional 1977", "independiente")],
                                     "nota": "Boca también jugó la Libertadores 1978, como campeón de la de 1977."}},
    # El Campeonato Nacional 1977 (noviembre de 1977 a enero de 1978; campeón Independiente): 32 equipos (los del
    # Metropolitano, menos los que bajaron, y los del interior) en 4 zonas de 8 a dos ruedas ("zonas_a_mano"), sin
    # interzonales, con 2 puntos por partido ganado; el primero de cada zona jugaba las semifinales, a ida y vuelta (con el
    # global igualado, gol de visitante y después alargue y penales). Independiente salió campeón por el gol de visitante.
    # ESPN no lo tiene: va a mano (tools/a_mano; resultados y goles de RSSSF, días y estadios de Wikipedia; de la fase
    # final, los goles con los minutos y los árbitros de Wikipedia)
    "1977-nacional": {"nombre": "Campeonato Nacional 1977", "anio": 1977, "liga": "a_mano", "slug": "1977-nacional",
                      "zonas_a_mano": {"A": ["newell-s-old-boys", "san-lorenzo", "independiente-rivadavia", "gimnasia-y-esgrima", "san-martin-tucuman", "estudiantes-buenos-aires", "banfield", "circulo-deportivo"],
                                       "B": ["estudiantes-de-la-plata", "boca-juniors", "rosario-central", "los-andes-san-juan", "quilmes", "cipolletti", "chacarita-juniors", "central-norte"],
                                       "C": ["talleres", "racing-club", "river-plate", "velez-sarsfield", "platense", "sarmiento-resistencia", "colon", "gimnasia-jujuy"],
                                       "D": ["independiente", "belgrano", "huracan", "atlanta", "argentinos-juniors", "union", "ledesma", "all-boys"]},
                      "fechas": 14, "pasan": 1, "puntos_victoria": 2,
                      "texto_pasan": "Pasa a las semifinales (el primero de cada zona)",
                      "goleadores_nota": "Los goles de la fase de zonas son de RSSSF, solo con el apellido y sin minutos; los "
                                         "de la fase final, de Wikipedia, con los minutos. El goleador del torneo fue "
                                         "Alfredo Letanú (Estudiantes), con 13 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1978-01-14T19:00Z", "fecha": "1978-01-14", "local": "talleres", "visitante": "newell-s-old-boys", "gl": 1, "gv": 1, "estadio": "Estadio Boutique de Barrio Jardín", "arbitro": "Roberto Osvaldo Barreiro", "goles": [{"jugador": "Cherini", "equipo": "local", "min": 69, "tipo": "pen"}, {"jugador": "Roux Larrosa", "equipo": "visitante", "min": 10}]},
                               {"hora_utc": "1978-01-18T19:00Z", "fecha": "1978-01-18", "local": "newell-s-old-boys", "visitante": "talleres", "gl": 0, "gv": 1, "estadio": "Estadio Coloso del Parque", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Bravo", "equipo": "visitante", "min": 85}]},
                               {"hora_utc": "1978-01-14T19:00Z", "fecha": "1978-01-14", "local": "estudiantes-de-la-plata", "visitante": "independiente", "gl": 1, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Ángel Coerezza", "goles": [{"jugador": "C. López", "equipo": "local", "min": 60}, {"jugador": "Outes", "equipo": "visitante", "min": 16}]},
                               {"hora_utc": "1978-01-18T19:00Z", "fecha": "1978-01-18", "local": "independiente", "visitante": "estudiantes-de-la-plata", "gl": 3, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Jorge Eduardo Romero", "alargue": True, "goles": [{"jugador": "O. Pérez", "equipo": "local", "min": 16}, {"jugador": "Trossero", "equipo": "local", "min": 92, "tipo": "pen"}, {"jugador": "Bochini", "equipo": "local", "min": 115}, {"jugador": "Onnis", "equipo": "visitante", "min": 71}]},
                           ],
                           "Final": [
                               {"hora_utc": "1978-01-21T19:00Z", "fecha": "1978-01-21", "local": "independiente", "visitante": "talleres", "gl": 1, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Ángel Coerezza", "goles": [{"jugador": "Trossero", "equipo": "local", "min": 58, "tipo": "pen"}, {"jugador": "Cherini", "equipo": "visitante", "min": 65, "tipo": "pen"}]},
                               {"hora_utc": "1978-01-25T19:00Z", "fecha": "1978-01-25", "local": "talleres", "visitante": "independiente", "gl": 2, "gv": 2, "estadio": "Estadio Boutique de Barrio Jardín", "arbitro": "Roberto Osvaldo Barreiro", "goles": [{"jugador": "Cherini", "equipo": "local", "min": 60, "tipo": "pen"}, {"jugador": "Bocanelli", "equipo": "local", "min": 74}, {"jugador": "Outes", "equipo": "visitante", "min": 29}, {"jugador": "Bochini", "equipo": "visitante", "min": 83}]},
                           ],
                      },
                      "ida_y_vuelta": True, "gol_visitante": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1978: el Campeonato Metropolitano 1978 (marzo a octubre; campeón Quilmes): 21 equipos a dos ruedas (42 fechas, en
    # cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin
    # goles). Sin promedios: bajaban los dos últimos de la tabla ("descensos": "tabla"): Banfield y Estudiantes de Buenos
    # Aires. A la Libertadores 1979 fueron los campeones del Metropolitano y del Nacional
    "1978-metropolitano": {"nombre": "Campeonato Metropolitano 1978", "anio": 1978, "liga": "a_mano", "slug": "1978-metropolitano",
                           "zonas": "unica", "fechas": 42, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1978 (las 42 fechas; eran 21 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. Los goleadores fueron Luis Andreuchi "
                                              "(Quilmes) y Diego Maradona (Argentinos), con 21 goles.",
                           "descensos": "tabla", "descienden": 2,
                           "cupos": {"anio": 1979, "fijos": True,
                                     "libertadores": [("Campeón del Metropolitano 1978", "quilmes"),
                                                      ("Campeón del Nacional 1978", "independiente")]}},
    # El Campeonato Nacional 1978 (noviembre de 1978 a enero de 1979; campeón Independiente): 32 equipos (los del
    # Metropolitano, menos los que bajaron, más Ferro, el campeón de la Primera B, y los del interior) en 4 zonas de 8 a
    # dos ruedas ("zonas_a_mano"), sin interzonales, con 2 puntos por partido ganado; los dos primeros de cada zona
    # jugaban la fase final, a ida y vuelta (con el global igualado, gol de visitante y después alargue y penales). Tres
    # partidos se dieron por ganados en el escritorio ("para_local"). ESPN no lo tiene: va a mano (tools/a_mano;
    # resultados de RSSSF, días y estadios de Wikipedia; de la fase final, también los goles y los árbitros de Wikipedia)
    "1978-nacional": {"nombre": "Campeonato Nacional 1978", "anio": 1978, "liga": "a_mano", "slug": "1978-nacional",
                      "zonas_a_mano": {"A": ["talleres", "racing-club", "newell-s-old-boys", "ledesma", "ferro-carril-oeste", "estudiantes-de-la-plata", "all-boys", "juventud-antoniana"],
                                       "B": ["union", "huracan", "atletico-tucuman", "boca-juniors", "patronato", "chacarita-juniors", "gimnasia-mendoza", "platense"],
                                       "C": ["independiente", "velez-sarsfield", "gimnasia-y-esgrima", "racing-cordoba", "deportivo-roca", "rosario-central", "argentinos-juniors", "altos-hornos-zapla"],
                                       "D": ["river-plate", "colon", "san-martin-mendoza", "atlanta", "san-martin-tucuman", "quilmes", "alvarado", "san-lorenzo"]},
                      "fechas": 14, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona)",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de la fase de "
                                         "zonas no están. El goleador del torneo fue José Rinaldi (Talleres), con 16 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Cuartos de final": [
                               {"hora_utc": "1978-12-23T19:00Z", "fecha": "1978-12-23", "local": "huracan", "visitante": "talleres", "gl": 2, "gv": 1, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Abel Gnecco", "goles": [{"jugador": "J. Sanabria", "equipo": "local", "min": 65}, {"jugador": "D. Sanabria", "equipo": "local", "min": 80}, {"jugador": "Cheves", "equipo": "visitante", "min": 55, "tipo": "ec"}]},
                               {"hora_utc": "1978-12-27T19:00Z", "fecha": "1978-12-27", "local": "talleres", "visitante": "huracan", "gl": 3, "gv": 0, "estadio": "Estadio Córdoba", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Ludueña", "equipo": "local", "min": 46}, {"jugador": "Reinaldi", "equipo": "local", "min": 53}, {"jugador": "Reinaldi", "equipo": "local", "min": 68}]},
                               {"hora_utc": "1978-12-23T19:00Z", "fecha": "1978-12-23", "local": "colon", "visitante": "independiente", "gl": 2, "gv": 2, "estadio": "Estadio Brigadier General Estanislao López", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Mazo", "equipo": "local", "min": 44}, {"jugador": "Di Meola", "equipo": "local", "min": 81}, {"jugador": "Barberón", "equipo": "visitante", "min": 73}, {"jugador": "Larrosa", "equipo": "visitante", "min": 80}]},
                               {"hora_utc": "1978-12-27T19:00Z", "fecha": "1978-12-27", "local": "independiente", "visitante": "colon", "gl": 2, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Bochini", "equipo": "local", "min": 37}, {"jugador": "Alzamendi", "equipo": "local", "min": 79}]},
                               {"hora_utc": "1978-12-23T19:00Z", "fecha": "1978-12-23", "local": "river-plate", "visitante": "velez-sarsfield", "gl": 2, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Miguel Francisco Comesaña", "goles": [{"jugador": "Ártico", "equipo": "local", "min": 17, "tipo": "ec"}, {"jugador": "Luque", "equipo": "local", "min": 77}]},
                               {"hora_utc": "1978-12-27T19:00Z", "fecha": "1978-12-27", "local": "velez-sarsfield", "visitante": "river-plate", "gl": 2, "gv": 1, "estadio": "Estadio José Amalfitani", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Roldán", "equipo": "local", "min": 7, "tipo": "pen"}, {"jugador": "Jiménez", "equipo": "local", "min": 84}, {"jugador": "J. J. López", "equipo": "visitante", "min": 30}]},
                               {"hora_utc": "1978-12-23T19:00Z", "fecha": "1978-12-23", "local": "racing-club", "visitante": "union", "gl": 1, "gv": 2, "estadio": "Estadio El Cilindro", "arbitro": "Roberto Osvaldo Barreiro", "goles": [{"jugador": "R. Díaz", "equipo": "local", "min": 50}, {"jugador": "Escobar", "equipo": "visitante", "min": 32, "tipo": "ec"}, {"jugador": "Ribeca", "equipo": "visitante", "min": 80}]},
                               {"hora_utc": "1978-12-27T19:00Z", "fecha": "1978-12-27", "local": "union", "visitante": "racing-club", "gl": 1, "gv": 0, "estadio": "Estadio Club Atlético Unión", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Pitarch", "equipo": "local", "min": 34}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1978-12-30T19:00Z", "fecha": "1978-12-30", "local": "independiente", "visitante": "talleres", "gl": 2, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Miguel Francisco Comesaña", "goles": [{"jugador": "Bochini", "equipo": "local", "min": 35}, {"jugador": "Bochini", "equipo": "local", "min": 42}, {"jugador": "Cabrera", "equipo": "visitante", "min": 69}]},
                               {"hora_utc": "1979-01-03T19:00Z", "fecha": "1979-01-03", "local": "talleres", "visitante": "independiente", "gl": 1, "gv": 2, "estadio": "Estadio Córdoba", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Reinaldi", "equipo": "local", "min": 7}, {"jugador": "Trossero", "equipo": "visitante", "min": 18}, {"jugador": "Outes", "equipo": "visitante", "min": 68}]},
                               {"hora_utc": "1978-12-30T19:00Z", "fecha": "1978-12-30", "local": "union", "visitante": "river-plate", "gl": 0, "gv": 1, "estadio": "Estadio Club Atlético Unión", "arbitro": "Alberto Ducatelli", "goles": [{"jugador": "Luque", "equipo": "visitante", "min": 67}]},
                               {"hora_utc": "1979-01-03T19:00Z", "fecha": "1979-01-03", "local": "river-plate", "visitante": "union", "gl": 1, "gv": 1, "estadio": "Estadio Monumental", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Alonso", "equipo": "local", "min": 67}, {"jugador": "Bottaniz", "equipo": "visitante", "min": 36, "tipo": "pen"}]},
                           ],
                           "Final": [
                               {"hora_utc": "1979-01-07T19:00Z", "fecha": "1979-01-07", "local": "river-plate", "visitante": "independiente", "gl": 0, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Arturo Ithurralde"},
                               {"hora_utc": "1979-01-10T19:00Z", "fecha": "1979-01-10", "local": "independiente", "visitante": "river-plate", "gl": 2, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Bochini", "equipo": "local", "min": 19}, {"jugador": "Bochini", "equipo": "local", "min": 56}]},
                           ],
                      },
                      "ida_y_vuelta": True, "gol_visitante": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1979: el Campeonato Metropolitano 1979 (marzo a agosto; campeón River): 20 equipos por etapas ("etapas"; en
    # tools/a_mano, cada fecha dice su etapa y cada partido su zona): la primera fase, 2 zonas de 10 a dos ruedas (18
    # fechas; pasaban los dos primeros a las semifinales: Vélez y Argentinos empataron el segundo puesto de la zona A y
    # jugaron un desempate, "desempate_a_mano"), y el Torneo por el descenso (los dos últimos de cada zona, a dos ruedas;
    # bajaban los tres últimos, "descensos": "etapa": Gimnasia, Chacarita y Atlanta). Con 2 puntos por partido ganado.
    # Semifinales y final a ida y vuelta. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles; de la final, los
    # goles y los árbitros de Wikipedia)
    "1979-metropolitano": {"nombre": "Campeonato Metropolitano 1979", "anio": 1979, "liga": "a_mano", "slug": "1979-metropolitano",
                           "etapas": [("Primera fase", r"primera-fase$", 2, 1, 18,
                                       "Los dos primeros de cada zona pasan a las semifinales; los dos últimos juegan el "
                                       "Torneo por el descenso"),
                                      ("Torneo por el descenso", r"descenso$", 1, 19, 6,
                                       "Se queda en Primera")],
                           "fechas": 24, "pasan": 0, "puntos_victoria": 2,
                           "nota": "Cada partido ganado valía 2 puntos. En la primera fase había 2 zonas de 10 a dos ruedas: "
                                   "los dos primeros de cada zona pasaban a las semifinales, a ida y vuelta (el primero de una "
                                   "zona con el segundo de la otra), y los dos últimos jugaban el Torneo por el descenso, en el "
                                   "que bajaban tres de los cuatro.",
                           "desempate_a_mano": {"fecha": "1979-07-22", "local": "velez-sarsfield", "visitante": "argentinos-juniors",
                                                "gl": 4, "gv": 0, "estadio": "Cancha de Ferro Carril Oeste"},
                           "desempate_texto": "Vélez y Argentinos terminaron empatados en puntos en el segundo puesto de la "
                                              "zona A: lo definieron en un partido, en cancha de Ferro, y pasó Vélez a las "
                                              "semifinales.",
                           "descensos": "etapa", "descienden": 3,
                           "goleadores_nota": "Los goles son solo de la final (de Wikipedia, con los minutos): del resto del "
                                              "torneo no están. Los goleadores fueron Sergio Fortunato (Estudiantes) y Diego "
                                              "Maradona (Argentinos), con 14 goles.",
                           "nombre_playoffs": "Fase final",
                           "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final")],
                           "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1979-07-29T19:00Z", "fecha": "1979-07-29", "local": "river-plate", "visitante": "independiente", "gl": 4, "gv": 3, "estadio": "Estadio Monumental"},
                               {"hora_utc": "1979-08-05T19:00Z", "fecha": "1979-08-05", "local": "independiente", "visitante": "river-plate", "gl": 1, "gv": 2, "estadio": "Estadio La Doble Visera"},
                               {"hora_utc": "1979-07-29T19:00Z", "fecha": "1979-07-29", "local": "rosario-central", "visitante": "velez-sarsfield", "gl": 0, "gv": 1, "estadio": "Estadio Gigante de Arroyito"},
                               {"hora_utc": "1979-08-05T19:00Z", "fecha": "1979-08-05", "local": "velez-sarsfield", "visitante": "rosario-central", "gl": 0, "gv": 0, "estadio": "Estadio José Amalfitani"},
                           ],
                           "Final": [
                               {"hora_utc": "1979-08-12T19:00Z", "fecha": "1979-08-12", "local": "velez-sarsfield", "visitante": "river-plate", "gl": 0, "gv": 2, "estadio": "Estadio José Amalfitani", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Galletti", "equipo": "visitante", "min": 52}, {"jugador": "González", "equipo": "visitante", "min": 65}]},
                               {"hora_utc": "1979-08-19T19:00Z", "fecha": "1979-08-19", "local": "river-plate", "visitante": "velez-sarsfield", "gl": 5, "gv": 1, "estadio": "Estadio Monumental", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Alonso", "equipo": "local", "min": 13}, {"jugador": "Commisso", "equipo": "local", "min": 41}, {"jugador": "Luque", "equipo": "local", "min": 55}, {"jugador": "González", "equipo": "local", "min": 57}, {"jugador": "Jorge", "equipo": "visitante", "min": 87}, {"jugador": "González", "equipo": "local", "min": 89}]},
                           ],
                           },
                           "ida_y_vuelta": True},
    # El Campeonato Nacional 1979 (septiembre a diciembre; campeón River): 28 equipos (los del Metropolitano, menos los
    # que bajaron, y los del interior) en 4 zonas de 7 a dos ruedas ("zonas_a_mano"); en cada fecha, el que quedaba libre
    # jugaba un interzonal (la A con la C y la B con la D). Con 2 puntos por partido ganado; los dos primeros de cada zona
    # jugaban la fase final, a ida y vuelta (con el global igualado, gol de visitante y después alargue y penales). ESPN
    # no lo tiene: va a mano (tools/a_mano; resultados de RSSSF, días y estadios de Wikipedia; de la fase final, también
    # los goles y los árbitros de Wikipedia). Como River ganó los dos torneos, el segundo lugar en la Libertadores 1980 lo
    # jugaron los dos subcampeones, Vélez y Unión
    "1979-nacional": {"nombre": "Campeonato Nacional 1979", "anio": 1979, "liga": "a_mano", "slug": "1979-nacional",
                      "zonas_a_mano": {"A": ["velez-sarsfield", "union", "ferro-carril-oeste", "san-martin-tucuman", "independiente", "juventud-pringles", "ledesma"],
                                       "B": ["talleres", "river-plate", "huracan", "newell-s-old-boys", "quilmes", "kimberley", "gimnasia-y-tiro"],
                                       "C": ["racing-club", "atletico-tucuman", "argentinos-juniors", "colon", "all-boys", "independiente-rivadavia", "altos-hornos-zapla"],
                                       "D": ["instituto", "rosario-central", "boca-juniors", "san-lorenzo", "estudiantes-de-la-plata", "chaco-for-ever", "cipolletti"]},
                      "fechas": 14, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona). En cada fecha, el que quedaba "
                                     "libre jugaba un interzonal (la zona A con la C y la B con la D)",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de la fase de "
                                         "zonas no están. El goleador del torneo fue Diego Maradona (Argentinos), con 12 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Cuartos de final": [
                               {"hora_utc": "1979-12-05T19:00Z", "fecha": "1979-12-05", "local": "racing-club", "visitante": "rosario-central", "gl": 1, "gv": 3, "estadio": "Estadio El Cilindro", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Barbas", "equipo": "local", "min": 90}, {"jugador": "Bauza", "equipo": "visitante", "min": 20}, {"jugador": "Bauza", "equipo": "visitante", "min": 40}, {"jugador": "Trama", "equipo": "visitante", "min": 50}]},
                               {"hora_utc": "1979-12-09T19:00Z", "fecha": "1979-12-09", "local": "rosario-central", "visitante": "racing-club", "gl": 3, "gv": 0, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Orte", "equipo": "local", "min": 22}, {"jugador": "Trama", "equipo": "local", "min": 61}, {"jugador": "Orte", "equipo": "local", "min": 85}]},
                               {"hora_utc": "1979-12-05T19:00Z", "fecha": "1979-12-05", "local": "velez-sarsfield", "visitante": "river-plate", "gl": 1, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Alberto Ducatelli", "goles": [{"jugador": "Larraquy", "equipo": "local", "min": 55}]},
                               {"hora_utc": "1979-12-09T19:00Z", "fecha": "1979-12-09", "local": "river-plate", "visitante": "velez-sarsfield", "gl": 1, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Teodoro Nitti", "alargue": True, "pen_l": 4, "pen_v": 3, "goles": [{"jugador": "J. J. López", "equipo": "local", "min": 85}]},
                               {"hora_utc": "1979-12-05T19:00Z", "fecha": "1979-12-05", "local": "union", "visitante": "talleres", "gl": 3, "gv": 0, "estadio": "Estadio Club Atlético Unión", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Paz", "equipo": "local", "min": 22}, {"jugador": "Pitarch", "equipo": "local", "min": 49, "tipo": "pen"}, {"jugador": "Ribeca", "equipo": "local", "min": 75}]},
                               {"hora_utc": "1979-12-09T19:00Z", "fecha": "1979-12-09", "local": "talleres", "visitante": "union", "gl": 2, "gv": 0, "estadio": "Estadio Córdoba", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Bravo", "equipo": "local", "min": 31}, {"jugador": "Bravo", "equipo": "local", "min": 39}]},
                               {"hora_utc": "1979-12-05T19:00Z", "fecha": "1979-12-05", "local": "instituto", "visitante": "atletico-tucuman", "gl": 3, "gv": 2, "estadio": "Estadio Córdoba", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Olmedo", "equipo": "local", "min": 15}, {"jugador": "Palavecino", "equipo": "local", "min": 64}, {"jugador": "Palavecino", "equipo": "local", "min": 90}, {"jugador": "Nicolás Gómez", "equipo": "visitante", "min": 7}, {"jugador": "Nicolás Gómez", "equipo": "visitante", "min": 21}]},
                               {"hora_utc": "1979-12-09T19:00Z", "fecha": "1979-12-09", "local": "atletico-tucuman", "visitante": "instituto", "gl": 3, "gv": 0, "estadio": "Estadio Monumental José Fierro", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Palomba", "equipo": "local", "min": 36}, {"jugador": "Néstor Gómez", "equipo": "local", "min": 73}, {"jugador": "Barrientos", "equipo": "local", "min": 74}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1979-12-12T19:00Z", "fecha": "1979-12-12", "local": "river-plate", "visitante": "rosario-central", "gl": 4, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Carrasco", "equipo": "local", "min": 36}, {"jugador": "Passarella", "equipo": "local", "min": 52, "tipo": "pen"}, {"jugador": "Díaz", "equipo": "local", "min": 74}, {"jugador": "Carrasco", "equipo": "local", "min": 75}]},
                               {"hora_utc": "1979-12-16T19:00Z", "fecha": "1979-12-16", "local": "rosario-central", "visitante": "river-plate", "gl": 1, "gv": 3, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Orte", "equipo": "local", "min": 47}, {"jugador": "Luque", "equipo": "visitante", "min": 22}, {"jugador": "Díaz", "equipo": "visitante", "min": 53}, {"jugador": "Saporiti", "equipo": "visitante", "min": 61}]},
                               {"hora_utc": "1979-12-12T19:00Z", "fecha": "1979-12-12", "local": "atletico-tucuman", "visitante": "union", "gl": 0, "gv": 2, "estadio": "Estadio Monumental José Fierro", "arbitro": "Alberto Ducatelli", "goles": [{"jugador": "Alí", "equipo": "visitante", "min": 23}, {"jugador": "Pitarch", "equipo": "visitante", "min": 84}]},
                               {"hora_utc": "1979-12-16T19:00Z", "fecha": "1979-12-16", "local": "union", "visitante": "atletico-tucuman", "gl": 2, "gv": 0, "estadio": "Estadio Club Atlético Unión", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Paz", "equipo": "local", "min": 19}, {"jugador": "Mazzoni", "equipo": "local", "min": 85}]},
                           ],
                           "Final": [
                               {"hora_utc": "1979-12-19T19:00Z", "fecha": "1979-12-19", "local": "union", "visitante": "river-plate", "gl": 1, "gv": 1, "estadio": "Estadio Club Atlético Unión", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Mazzoni", "equipo": "local", "min": 78}, {"jugador": "Alonso", "equipo": "visitante", "min": 88}]},
                               {"hora_utc": "1979-12-23T19:00Z", "fecha": "1979-12-23", "local": "river-plate", "visitante": "union", "gl": 0, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Jorge Eduardo Romero"},
                           ],
                      },
                      "ida_y_vuelta": True, "gol_visitante": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano.",
                      "anual_texto": "La tabla de la fase de zonas del Campeonato Nacional 1979 (los 28 equipos, con los "
                                     "interzonales). Cada partido ganado valía 2 puntos.",
                      "cupos": {"anio": 1980, "fijos": True,
                                "libertadores": [("Campeón del Metropolitano y del Nacional 1979", "river-plate"),
                                                 ("Ganador del desempate de los subcampeones", "velez-sarsfield")],
                                "nota": "River ganó los dos torneos del año: el otro lugar lo jugaron los subcampeones, Vélez "
                                        "(del Metropolitano) y Unión (del Nacional), a ida y vuelta: 0-0 en Santa Fe (27 de "
                                        "diciembre) y 3-0 para Vélez en Liniers (30 de diciembre)."}},
    # 1980: el Campeonato Metropolitano 1980 (febrero a agosto; campeón River): 19 equipos a dos ruedas (38 fechas, en
    # cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin
    # goles). Sin promedios: bajaban los tres últimos de la tabla ("descensos": "tabla"): Quilmes, All Boys y Tigre. A la
    # Libertadores 1981 fueron los campeones del Metropolitano y del Nacional
    "1980-metropolitano": {"nombre": "Campeonato Metropolitano 1980", "anio": 1980, "liga": "a_mano", "slug": "1980-metropolitano",
                           "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1980 (las 38 fechas; eran 19 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Diego Maradona "
                                              "(Argentinos), con 25 goles.",
                           "descensos": "tabla", "descienden": 3,
                           "cupos": {"anio": 1981, "fijos": True,
                                     "libertadores": [("Campeón del Metropolitano 1980", "river-plate"),
                                                      ("Campeón del Nacional 1980", "rosario-central")]}},
    # El Campeonato Nacional 1980 (septiembre a diciembre; campeón Rosario Central): 28 equipos (los del Metropolitano y
    # los del interior) en 4 zonas de 7 a dos ruedas ("zonas_a_mano"); en cada fecha, el que quedaba libre jugaba un
    # interzonal (la A con la C y la B con la D). Con 2 puntos por partido ganado; los dos primeros de cada zona jugaban
    # la fase final, a ida y vuelta (con el global igualado, gol de visitante). ESPN no lo tiene: va a mano (tools/a_mano;
    # resultados de RSSSF, días y estadios de Wikipedia; de la fase final, también los goles y los árbitros de Wikipedia)
    "1980-nacional": {"nombre": "Campeonato Nacional 1980", "anio": 1980, "liga": "a_mano", "slug": "1980-nacional",
                      "zonas_a_mano": {"A": ["rosario-central", "racing-cordoba", "estudiantes-de-la-plata", "velez-sarsfield",
                                             "gimnasia-jujuy", "racing-club", "atletico-tucuman"],
                                       "B": ["argentinos-juniors", "union", "talleres", "huracan", "boca-juniors",
                                             "san-martin-mendoza", "san-lorenzo-mdp"],
                                       "C": ["newell-s-old-boys", "independiente", "ferro-carril-oeste", "atletico-concepcion",
                                             "quilmes", "central-norte", "chaco-for-ever"],
                                       "D": ["instituto", "river-plate", "platense", "san-lorenzo", "colon", "cipolletti",
                                             "independiente-rivadavia"]},
                      "fechas": 14, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona). En cada fecha, el que quedaba "
                                     "libre jugaba un interzonal (la zona A con la C y la B con la D)",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de la fase de "
                                         "zonas no están. El goleador del torneo fue Diego Maradona (Argentinos), con 18 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Cuartos de final": [
                               {"hora_utc": "1980-11-30T19:00Z", "fecha": "1980-11-30", "local": "instituto", "visitante": "independiente", "gl": 2, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Palavecino", "equipo": "local", "min": 51}, {"jugador": "R. Rodríguez", "equipo": "local", "min": 82}, {"jugador": "Alzamendi", "equipo": "visitante", "min": 83}]},
                               {"hora_utc": "1980-12-03T19:00Z", "fecha": "1980-12-03", "local": "independiente", "visitante": "instituto", "gl": 5, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Brailovsky", "equipo": "local", "min": 2}, {"jugador": "Alzamendi", "equipo": "local", "min": 13}, {"jugador": "Alzamendi", "equipo": "local", "min": 21}, {"jugador": "Mazo", "equipo": "local", "min": 28}, {"jugador": "Mazo", "equipo": "local", "min": 54}, {"jugador": "M. Rodríguez", "equipo": "visitante", "min": 87}]},
                               {"hora_utc": "1980-11-30T19:00Z", "fecha": "1980-11-30", "local": "argentinos-juniors", "visitante": "racing-cordoba", "gl": 1, "gv": 1, "estadio": "Cancha de Vélez Sarsfield", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Magallanes", "equipo": "local", "min": 27}, {"jugador": "Coloccini", "equipo": "visitante", "min": 72}]},
                               {"hora_utc": "1980-12-03T19:00Z", "fecha": "1980-12-03", "local": "racing-cordoba", "visitante": "argentinos-juniors", "gl": 3, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Ballejo", "equipo": "local", "min": 11}, {"jugador": "Gasparini", "equipo": "local", "min": 31}, {"jugador": "Ballejo", "equipo": "local", "min": 57}, {"jugador": "Vidal", "equipo": "visitante", "min": 18}]},
                               {"hora_utc": "1980-11-30T19:00Z", "fecha": "1980-11-30", "local": "river-plate", "visitante": "newell-s-old-boys", "gl": 3, "gv": 2, "estadio": "Estadio Monumental", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Alonso", "equipo": "local", "min": 32}, {"jugador": "Gordon", "equipo": "local", "min": 55}, {"jugador": "Gordon", "equipo": "local", "min": 88}, {"jugador": "Santamaría", "equipo": "visitante", "min": 15, "tipo": "pen"}, {"jugador": "Yazalde", "equipo": "visitante", "min": 41}]},
                               {"hora_utc": "1980-12-03T19:00Z", "fecha": "1980-12-03", "local": "newell-s-old-boys", "visitante": "river-plate", "gl": 6, "gv": 2, "estadio": "Estadio Coloso del Parque", "arbitro": "Alberto Ducatelli", "goles": [{"jugador": "Bulleri", "equipo": "local", "min": 22}, {"jugador": "Talavera", "equipo": "local", "min": 33}, {"jugador": "Santamaría", "equipo": "local", "min": 38}, {"jugador": "Yazalde", "equipo": "local", "min": 63}, {"jugador": "Pérez", "equipo": "local", "min": 66}, {"jugador": "Acosta", "equipo": "local", "min": 74}, {"jugador": "Gordon", "equipo": "visitante", "min": 1}, {"jugador": "Alonso", "equipo": "visitante", "min": 8}]},
                               {"hora_utc": "1980-11-30T19:00Z", "fecha": "1980-11-30", "local": "rosario-central", "visitante": "union", "gl": 2, "gv": 0, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Bauza", "equipo": "local", "min": 80, "tipo": "pen"}, {"jugador": "Agonil", "equipo": "local", "min": 87}]},
                               {"hora_utc": "1980-12-03T19:00Z", "fecha": "1980-12-03", "local": "union", "visitante": "rosario-central", "gl": 2, "gv": 1, "estadio": "Estadio Club Atlético Unión", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Alí", "equipo": "local", "min": 14}, {"jugador": "Mendoza", "equipo": "local", "min": 83}, {"jugador": "Bauza", "equipo": "visitante", "min": 45, "tipo": "pen"}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1980-12-07T19:00Z", "fecha": "1980-12-07", "local": "racing-cordoba", "visitante": "independiente", "gl": 4, "gv": 0, "estadio": "Estadio Córdoba", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Amuchástegui", "equipo": "local", "min": 21}, {"jugador": "Amuchástegui", "equipo": "local", "min": 25}, {"jugador": "Ballejo", "equipo": "local", "min": 37}, {"jugador": "Aramayo", "equipo": "local", "min": 65}]},
                               {"hora_utc": "1980-12-14T19:00Z", "fecha": "1980-12-14", "local": "independiente", "visitante": "racing-cordoba", "gl": 5, "gv": 3, "estadio": "Estadio La Doble Visera", "arbitro": "Alberto Ducatelli", "goles": [{"jugador": "Mazo", "equipo": "local", "min": 10, "tipo": "pen"}, {"jugador": "Alzamendi", "equipo": "local", "min": 36}, {"jugador": "Alzamendi", "equipo": "local", "min": 64}, {"jugador": "Alzamendi", "equipo": "local", "min": 67}, {"jugador": "Brailovsky", "equipo": "local", "min": 86}, {"jugador": "Ballejo", "equipo": "visitante", "min": 6}, {"jugador": "Ballejo", "equipo": "visitante", "min": 40}, {"jugador": "Ballejo", "equipo": "visitante", "min": 85}]},
                               {"hora_utc": "1980-12-07T19:00Z", "fecha": "1980-12-07", "local": "rosario-central", "visitante": "newell-s-old-boys", "gl": 3, "gv": 0, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Ghielmetti", "equipo": "local", "min": 33}, {"jugador": "Gaitán", "equipo": "local", "min": 39}, {"jugador": "Marchetti", "equipo": "local", "min": 71}]},
                               {"hora_utc": "1980-12-14T19:00Z", "fecha": "1980-12-14", "local": "newell-s-old-boys", "visitante": "rosario-central", "gl": 1, "gv": 0, "estadio": "Estadio Coloso del Parque", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Santamaría", "equipo": "local", "min": 39}]},
                           ],
                           "Final": [
                               {"hora_utc": "1980-12-17T19:00Z", "fecha": "1980-12-17", "local": "rosario-central", "visitante": "racing-cordoba", "gl": 5, "gv": 1, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Bauza", "equipo": "local", "min": 7, "tipo": "pen"}, {"jugador": "Palma", "equipo": "local", "min": 42}, {"jugador": "Marchetti", "equipo": "local", "min": 65}, {"jugador": "Agonil", "equipo": "local", "min": 72}, {"jugador": "Trama", "equipo": "local", "min": 77}, {"jugador": "Oyola", "equipo": "visitante", "min": 55}]},
                               {"hora_utc": "1980-12-21T19:00Z", "fecha": "1980-12-21", "local": "racing-cordoba", "visitante": "rosario-central", "gl": 2, "gv": 0, "estadio": "Estadio Córdoba", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Oyola", "equipo": "local", "min": 8}, {"jugador": "Gasparini", "equipo": "local", "min": 82}]},
                           ],
                      },
                      "ida_y_vuelta": True, "gol_visitante": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1981: el Campeonato Metropolitano 1981 (febrero a agosto; campeón Boca): 18 equipos a dos ruedas (34 fechas), con
    # 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles). Sin promedios: bajaban
    # los dos últimos de la tabla ("descensos": "tabla"): San Lorenzo y Colón. Talleres-Argentinos (2-2) se lo dieron
    # ganado a Argentinos por doping. A la Libertadores 1982 fueron los campeones del Metropolitano y del Nacional
    "1981-metropolitano": {"nombre": "Campeonato Metropolitano 1981", "anio": 1981, "liga": "a_mano", "slug": "1981-metropolitano",
                           "zonas": "unica", "fechas": 34, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1981 (las 34 fechas). Cada partido ganado "
                                          "valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Raúl Chaparro "
                                              "(Instituto), con 20 goles.",
                           "descensos": "tabla", "descienden": 2,
                           "cupos": {"anio": 1982, "fijos": True,
                                     "libertadores": [("Campeón del Metropolitano 1981", "boca-juniors"),
                                                      ("Campeón del Nacional 1981", "river-plate")]}},
    # El Campeonato Nacional 1981 (septiembre a diciembre; campeón River): 28 equipos (los del Metropolitano y los del
    # interior) en 4 zonas de 7 a dos ruedas ("zonas_a_mano"); en cada fecha, el que quedaba libre jugaba un interzonal
    # (la A con la C y la B con la D). Con 2 puntos por partido ganado; los dos primeros de cada zona jugaban la fase
    # final, a ida y vuelta (con el global igualado, gol de visitante). A Racing de Córdoba le descontaron 4 puntos (2 por
    # cada uno de los dos partidos que jugó estando suspendido). ESPN no lo tiene: va a mano (tools/a_mano; resultados de
    # RSSSF, días y estadios de Wikipedia; de la fase final, también los goles y los árbitros de Wikipedia)
    "1981-nacional": {"nombre": "Campeonato Nacional 1981", "anio": 1981, "liga": "a_mano", "slug": "1981-nacional",
                      "zonas_a_mano": {"A": ["rosario-central", "gimnasia-jujuy", "argentinos-juniors", "huracan", "belgrano",
                                             "gimnasia-mendoza", "racing-club"],
                                       "B": ["ferro-carril-oeste", "river-plate", "loma-negra", "talleres",
                                             "guarani-antonio-franco", "san-martin-tucuman", "sarmiento"],
                                       "C": ["independiente", "velez-sarsfield", "racing-cordoba", "newell-s-old-boys",
                                             "platense", "gimnasia-y-tiro", "huracan-san-rafael"],
                                       "D": ["boca-juniors", "instituto", "estudiantes-de-la-plata", "san-lorenzo",
                                             "atletico-tucuman", "union", "san-lorenzo-mdp"]},
                      "fechas": 14, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona). En cada fecha, el que quedaba "
                                     "libre jugaba un interzonal (la zona A con la C y la B con la D)",
                      "descuentos": {"racing-cordoba": 4},
                      "descuentos_texto": "A Racing de Córdoba se le descontaron 4 puntos: jugó dos partidos estando suspendido "
                                          "(2 puntos menos por cada uno).",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de la fase de "
                                         "zonas no están. El goleador del torneo fue Carlos Bianchi (Vélez), con 15 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Cuartos de final": [
                               {"hora_utc": "1981-12-02T19:00Z", "fecha": "1981-12-02", "local": "ferro-carril-oeste", "visitante": "gimnasia-jujuy", "gl": 1, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Crocco", "equipo": "local", "min": 5}]},
                               {"hora_utc": "1981-12-06T19:00Z", "fecha": "1981-12-06", "local": "gimnasia-jujuy", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 1, "estadio": "Estadio 23 de Agosto", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Arregui", "equipo": "visitante", "min": 77}]},
                               {"hora_utc": "1981-12-02T19:00Z", "fecha": "1981-12-02", "local": "boca-juniors", "visitante": "velez-sarsfield", "gl": 2, "gv": 1, "estadio": "Estadio La Bombonera", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Ruggeri", "equipo": "local", "min": 87}, {"jugador": "Perotti", "equipo": "local", "min": 89}, {"jugador": "Bujedo", "equipo": "visitante", "min": 85}]},
                               {"hora_utc": "1981-12-06T19:00Z", "fecha": "1981-12-06", "local": "velez-sarsfield", "visitante": "boca-juniors", "gl": 3, "gv": 1, "estadio": "Estadio José Amalfitani", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Bianchi", "equipo": "local", "min": 5}, {"jugador": "Roldán", "equipo": "local", "min": 37}, {"jugador": "Comas", "equipo": "local", "min": 53}, {"jugador": "Ruggeri", "equipo": "visitante", "min": 87}]},
                               {"hora_utc": "1981-12-02T19:00Z", "fecha": "1981-12-02", "local": "rosario-central", "visitante": "river-plate", "gl": 1, "gv": 2, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Iglesias", "equipo": "local", "min": 58}, {"jugador": "Passarella", "equipo": "visitante", "min": 33}, {"jugador": "Vieta", "equipo": "visitante", "min": 90}]},
                               {"hora_utc": "1981-12-06T19:00Z", "fecha": "1981-12-06", "local": "river-plate", "visitante": "rosario-central", "gl": 0, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Claudio Aquiles Busca"},
                               {"hora_utc": "1981-12-02T19:00Z", "fecha": "1981-12-02", "local": "instituto", "visitante": "independiente", "gl": 1, "gv": 2, "estadio": "Estadio Córdoba", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Mastrosimone", "equipo": "local", "min": 20}, {"jugador": "Alzamendi", "equipo": "visitante", "min": 6}, {"jugador": "Trossero", "equipo": "visitante", "min": 47, "tipo": "pen"}]},
                               {"hora_utc": "1981-12-06T19:00Z", "fecha": "1981-12-06", "local": "independiente", "visitante": "instituto", "gl": 0, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Jorge Eduardo Romero"},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1981-12-09T19:00Z", "fecha": "1981-12-09", "local": "velez-sarsfield", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 2, "estadio": "Estadio José Amalfitani", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Bianchi", "equipo": "local", "min": 63, "tipo": "pen"}, {"jugador": "Arregui", "equipo": "visitante", "min": 8}, {"jugador": "Cañete", "equipo": "visitante", "min": 87}]},
                               {"hora_utc": "1981-12-13T19:00Z", "fecha": "1981-12-13", "local": "ferro-carril-oeste", "visitante": "velez-sarsfield", "gl": 1, "gv": 1, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Arregui", "equipo": "local", "min": 87}, {"jugador": "Bianchi", "equipo": "visitante", "min": 84}]},
                               {"hora_utc": "1981-12-09T19:00Z", "fecha": "1981-12-09", "local": "independiente", "visitante": "river-plate", "gl": 1, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Alzamendi", "equipo": "local", "min": 39}, {"jugador": "Passarella", "equipo": "visitante", "min": 26}]},
                               {"hora_utc": "1981-12-13T19:00Z", "fecha": "1981-12-13", "local": "river-plate", "visitante": "independiente", "gl": 0, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Claudio Aquiles Busca"},
                           ],
                           "Final": [
                               {"hora_utc": "1981-12-16T19:00Z", "fecha": "1981-12-16", "local": "river-plate", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Olarticoechea", "equipo": "local", "min": 71}]},
                               {"hora_utc": "1981-12-20T19:00Z", "fecha": "1981-12-20", "local": "ferro-carril-oeste", "visitante": "river-plate", "gl": 0, "gv": 1, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Kempes", "equipo": "visitante", "min": 58}]},
                           ],
                      },
                      "ida_y_vuelta": True, "gol_visitante": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # 1982: el Campeonato Nacional 1982 (febrero a junio; campeón Ferro): 32 equipos (los del Metropolitano y los del
    # interior) en 4 zonas de 8 a dos ruedas ("zonas_a_mano"), más dos fechas de interzonales (la 5 y la 13: la A con la C
    # y la B con la D), con 2 puntos por partido ganado; los dos primeros de cada zona jugaban la fase final, a ida y
    # vuelta. ESPN no lo tiene: va a mano (tools/a_mano; resultados de RSSSF, días y estadios de Wikipedia; de la fase
    # final, también los goles y los árbitros de Wikipedia). No había descensos (salían del Metropolitano)
    "1982-nacional": {"nombre": "Campeonato Nacional 1982", "anio": 1982, "liga": "a_mano", "slug": "1982-nacional",
                      "zonas_a_mano": {"A": ["quilmes", "independiente-rivadavia", "newell-s-old-boys", "instituto",
                                             "sarmiento", "river-plate", "gimnasia-jujuy", "nueva-chicago"],
                                       "B": ["ferro-carril-oeste", "union", "independiente", "argentinos-juniors",
                                             "atletico-concepcion", "san-lorenzo-mdp", "estudiantes-santiago", "union-san-vicente"],
                                       "C": ["estudiantes-de-la-plata", "talleres", "rosario-central", "boca-juniors",
                                             "gimnasia-mendoza", "central-norte", "huracan", "mariano-moreno"],
                                       "D": ["racing-cordoba", "san-martin-tucuman", "velez-sarsfield", "racing-club",
                                             "platense", "guarani-antonio-franco", "deportivo-roca", "renato-cesarini"]},
                      "fechas": 16, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona). Las fechas 5 y 13 fueron de "
                                     "interzonales (la zona A con la C y la B con la D)",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de la fase de "
                                         "zonas no están. El goleador del torneo fue Miguel Ángel Juárez (Ferro), con 22 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Cuartos de final": [
                               {"hora_utc": "1982-05-23T19:00Z", "fecha": "1982-05-23", "local": "talleres", "visitante": "racing-cordoba", "gl": 1, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Oviedo", "equipo": "local", "min": 66}, {"jugador": "Oyola", "equipo": "visitante", "min": 60}]},
                               {"hora_utc": "1982-05-30T19:00Z", "fecha": "1982-05-30", "local": "racing-cordoba", "visitante": "talleres", "gl": 1, "gv": 3, "estadio": "Estadio Córdoba", "arbitro": "Claudio Aquiles Busca", "alargue": True, "goles": [{"jugador": "Noriega", "equipo": "local", "min": 64}, {"jugador": "Morete", "equipo": "visitante", "min": 8}, {"jugador": "González", "equipo": "visitante", "min": 109}, {"jugador": "González", "equipo": "visitante", "min": 120}]},
                               {"hora_utc": "1982-05-23T19:00Z", "fecha": "1982-05-23", "local": "independiente-rivadavia", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 1, "estadio": "Malvinas Argentinas", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Juárez", "equipo": "visitante", "min": 59}]},
                               {"hora_utc": "1982-05-30T19:00Z", "fecha": "1982-05-30", "local": "ferro-carril-oeste", "visitante": "independiente-rivadavia", "gl": 0, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Abel Gnecco"},
                               {"hora_utc": "1982-05-23T19:00Z", "fecha": "1982-05-23", "local": "estudiantes-de-la-plata", "visitante": "san-martin-tucuman", "gl": 3, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Trama", "equipo": "local", "min": 51}, {"jugador": "Gottardi", "equipo": "local", "min": 62}, {"jugador": "Brown", "equipo": "local", "min": 74, "tipo": "pen"}, {"jugador": "Roldán", "equipo": "visitante", "min": 87, "tipo": "pen"}]},
                               {"hora_utc": "1982-05-30T19:00Z", "fecha": "1982-05-30", "local": "san-martin-tucuman", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 2, "estadio": "Estadio La Ciudadela", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Roldán", "equipo": "local", "min": 75, "tipo": "pen"}, {"jugador": "Ignacio", "equipo": "local", "min": 87}, {"jugador": "Gottardi", "equipo": "visitante", "min": 59}, {"jugador": "Gottardi", "equipo": "visitante", "min": 88}]},
                               {"hora_utc": "1982-05-23T19:00Z", "fecha": "1982-05-23", "local": "union", "visitante": "quilmes", "gl": 1, "gv": 1, "estadio": "Estadio Club Atlético Unión", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Mendoza", "equipo": "local", "min": 51, "tipo": "pen"}, {"jugador": "Acevedo", "equipo": "visitante", "min": 37}]},
                               {"hora_utc": "1982-05-30T19:00Z", "fecha": "1982-05-30", "local": "quilmes", "visitante": "union", "gl": 1, "gv": 1, "estadio": "Estadio Quilmes Atlético Club", "arbitro": "Jorge Eduardo Romero", "alargue": True, "pen_l": 4, "pen_v": 3, "goles": [{"jugador": "Converti", "equipo": "local", "min": 66}, {"jugador": "Centurión", "equipo": "visitante", "min": 55}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1982-06-06T19:00Z", "fecha": "1982-06-06", "local": "ferro-carril-oeste", "visitante": "talleres", "gl": 4, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Cañete", "equipo": "local", "min": 10}, {"jugador": "Cúper", "equipo": "local", "min": 25}, {"jugador": "Juárez", "equipo": "local", "min": 67}, {"jugador": "Juárez", "equipo": "local", "min": 76}]},
                               {"hora_utc": "1982-06-13T19:00Z", "fecha": "1982-06-13", "local": "talleres", "visitante": "ferro-carril-oeste", "gl": 4, "gv": 4, "estadio": "Estadio Córdoba", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Morete", "equipo": "local", "min": 7}, {"jugador": "Morete", "equipo": "local", "min": 26}, {"jugador": "J. J. López", "equipo": "local", "min": 54}, {"jugador": "Reinaldi", "equipo": "local", "min": 90}, {"jugador": "Juárez", "equipo": "visitante", "min": 12}, {"jugador": "Juárez", "equipo": "visitante", "min": 29}, {"jugador": "Juárez", "equipo": "visitante", "min": 36}, {"jugador": "Pavón", "equipo": "visitante", "min": 61, "tipo": "ec"}]},
                               {"hora_utc": "1982-06-06T19:00Z", "fecha": "1982-06-06", "local": "quilmes", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 0, "estadio": "Estadio Quilmes Atlético Club", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Acevedo", "equipo": "local", "min": 61}, {"jugador": "Acevedo", "equipo": "local", "min": 83}]},
                               {"hora_utc": "1982-06-13T19:00Z", "fecha": "1982-06-13", "local": "estudiantes-de-la-plata", "visitante": "quilmes", "gl": 0, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Milozzi", "equipo": "visitante", "min": 15, "tipo": "pen"}]},
                           ],
                           "Final": [
                               {"hora_utc": "1982-06-20T19:00Z", "fecha": "1982-06-20", "local": "quilmes", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 0, "estadio": "Estadio Quilmes Atlético Club", "arbitro": "Jorge Eduardo Romero"},
                               {"hora_utc": "1982-06-27T19:00Z", "fecha": "1982-06-27", "local": "ferro-carril-oeste", "visitante": "quilmes", "gl": 2, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Juárez", "equipo": "local", "min": 25}, {"jugador": "Rocchia", "equipo": "local", "min": 54}]},
                           ],
                      },
                      "ida_y_vuelta": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # El Campeonato Metropolitano 1982 (julio de 1982 a febrero de 1983; campeón Estudiantes): 19 equipos a dos ruedas
    # (38 fechas, en cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles: Wikipedia todavía no tiene los partidos). Sin promedios: bajaban los dos últimos de
    # la tabla ("descensos": "tabla"); Unión y Quilmes empataron en el anteúltimo lugar y jugaron un desempate (bajó
    # Quilmes; Sarmiento, el último). A la Libertadores 1983 fueron los campeones del Nacional y del Metropolitano
    "1982-metropolitano": {"nombre": "Campeonato Metropolitano 1982", "anio": 1982, "liga": "a_mano", "slug": "1982-metropolitano",
                           "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1982 (las 38 fechas; eran 19 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Carlos Morete "
                                              "(Independiente), con 20 goles.",
                           "descensos": "tabla", "descienden": 2,
                           "desempate_a_mano": {"fecha": "1983-02-20", "local": "union", "visitante": "quilmes", "gl": 1, "gv": 0,
                                                "estadio": "Cancha de Sarmiento (Junín)", "arbitro": "Teodoro Nitti",
                                                "goles": [{"jugador": "Capocetti", "equipo": "local", "min": 56, "tipo": "pen"}]},
                           "desempate_texto": "Unión y Quilmes terminaron empatados en puntos en el anteúltimo lugar, arriba de "
                                              "Sarmiento (que bajó por ser el último): lo definieron en un partido, en cancha de "
                                              "Sarmiento, en Junín, y bajó Quilmes.",
                           "cupos": {"anio": 1983, "fijos": True,
                                     "libertadores": [("Campeón del Nacional 1982", "ferro-carril-oeste"),
                                                      ("Campeón del Metropolitano 1982", "estudiantes-de-la-plata")]}},
    # 1983: el Campeonato Nacional 1983 (marzo a junio; campeón Estudiantes): 32 equipos (los del Metropolitano y los
    # del interior) por etapas ("etapas"; en tools/a_mano, cada fecha dice su etapa y cada partido su zona): la primera
    # fase, 8 zonas de 4 a dos ruedas (pasaban los tres primeros), y la segunda, 8 zonas de 3 a dos ruedas, en las que
    # el que quedaba libre en cada fecha jugaba un interzonal con uno de la zona de al lado (A con B, C con D...; sin
    # zona en el archivo); pasaban los dos primeros. Con 2 puntos por partido ganado. Después, la fase final, a ida y
    # vuelta. ESPN no lo tiene: va a mano (tools/a_mano; resultados de RSSSF, días y estadios de Wikipedia; de la fase
    # final, también los goles y los árbitros de Wikipedia). No había descensos (salían del Metropolitano)
    "1983-nacional": {"nombre": "Campeonato Nacional 1983", "anio": 1983, "liga": "a_mano", "slug": "1983-nacional",
                      # etapas: (nombre, patrón de la fase, cuántos pasan por zona, primera fecha, cuántas fechas, texto)
                      "etapas": [("Primera fase", r"primera-fase$", 3, 1, 6,
                                  "Los tres primeros de cada zona pasan a la segunda fase"),
                                 ("Segunda fase", r"segunda-fase$", 2, 7, 6,
                                  "Los dos primeros de cada zona pasan a la fase final. El que quedaba libre en cada "
                                  "fecha jugaba un partido interzonal (A con B, C con D, E con F y G con H), que suma en "
                                  "su zona")],
                      "fechas": 12, "pasan": 0, "puntos_victoria": 2,
                      "nota": "Cada partido ganado valía 2 puntos. En la primera fase había 8 zonas de 4 y pasaban los tres "
                              "primeros; en la segunda, 8 zonas de 3, y pasaban los dos primeros a la fase final, a ida y "
                              "vuelta (con el global igualado, alargue y penales).",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de las fases de "
                                         "zonas no están. El goleador del torneo fue Mario Husillos (Loma Negra), con 11 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Octavos de final", "Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Octavos de final": [
                               {"hora_utc": "1983-05-15T19:00Z", "fecha": "1983-05-15", "local": "union", "visitante": "independiente", "gl": 1, "gv": 0, "estadio": "Estadio Club Atlético Unión", "arbitro": "Julio Gumersindo Barraza", "goles": [{"jugador": "Zavagno", "equipo": "local", "min": 28}]},
                               {"hora_utc": "1983-05-18T19:00Z", "fecha": "1983-05-18", "local": "independiente", "visitante": "union", "gl": 1, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Raúl Marsiglia", "alargue": True, "pen_l": 6, "pen_v": 5, "goles": [{"jugador": "Burruchaga", "equipo": "local", "min": 62}]},
                               {"hora_utc": "1983-05-15T19:00Z", "fecha": "1983-05-15", "local": "talleres", "visitante": "racing-cordoba", "gl": 2, "gv": 2, "estadio": "Estadio Córdoba", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Oviedo", "equipo": "local", "min": 32, "tipo": "pen"}, {"jugador": "Bevilacqua", "equipo": "local", "min": 49}, {"jugador": "Gasparini", "equipo": "visitante", "min": 28}, {"jugador": "Amuchástegui", "equipo": "visitante", "min": 52}]},
                               {"hora_utc": "1983-05-18T19:00Z", "fecha": "1983-05-18", "local": "racing-cordoba", "visitante": "talleres", "gl": 0, "gv": 0, "estadio": "Estadio Córdoba", "arbitro": "Teodoro Nitti", "alargue": True, "pen_l": 5, "pen_v": 3},
                               {"hora_utc": "1983-05-16T19:00Z", "fecha": "1983-05-16", "local": "boca-juniors", "visitante": "argentinos-juniors", "gl": 1, "gv": 1, "estadio": "Estadio La Bombonera", "arbitro": "Claudio Aquiles Busca", "goles": [{"jugador": "Domínguez", "equipo": "local", "min": 31}, {"jugador": "Landucci", "equipo": "visitante", "min": 50}]},
                               {"hora_utc": "1983-05-19T19:00Z", "fecha": "1983-05-19", "local": "argentinos-juniors", "visitante": "boca-juniors", "gl": 3, "gv": 2, "estadio": "Cancha de River Plate", "arbitro": "Juan Carlos Demaro", "alargue": True, "goles": [{"jugador": "Espíndola", "equipo": "local", "min": 81, "tipo": "pen"}, {"jugador": "Espíndola", "equipo": "local", "min": 87}, {"jugador": "Videla", "equipo": "local", "min": 107}, {"jugador": "Gareca", "equipo": "visitante", "min": 28}, {"jugador": "Domínguez", "equipo": "visitante", "min": 80}]},
                               {"hora_utc": "1983-05-16T19:00Z", "fecha": "1983-05-16", "local": "river-plate", "visitante": "velez-sarsfield", "gl": 1, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Chaparro", "equipo": "local", "min": 78}]},
                               {"hora_utc": "1983-05-19T19:00Z", "fecha": "1983-05-19", "local": "velez-sarsfield", "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Juan Carlos Loustau"},
                               {"hora_utc": "1983-05-16T19:00Z", "fecha": "1983-05-16", "local": "temperley", "visitante": "platense", "gl": 2, "gv": 1, "estadio": "Cancha de Banfield", "arbitro": "Jorge Vigliano", "goles": [{"jugador": "Scotta", "equipo": "local", "min": 15}, {"jugador": "Dabrowski", "equipo": "local", "min": 89}, {"jugador": "López Turitich", "equipo": "visitante", "min": 66}]},
                               {"hora_utc": "1983-05-19T19:00Z", "fecha": "1983-05-19", "local": "platense", "visitante": "temperley", "gl": 0, "gv": 0, "estadio": "Estadio Ciudad de Vicente López", "arbitro": "Pedro Luis Feola"},
                               {"hora_utc": "1983-05-14T19:00Z", "fecha": "1983-05-14", "local": "newell-s-old-boys", "visitante": "rosario-central", "gl": 0, "gv": 0, "estadio": "Estadio Coloso del Parque", "arbitro": "Teodoro Nitti"},
                               {"hora_utc": "1983-05-19T19:00Z", "fecha": "1983-05-19", "local": "rosario-central", "visitante": "newell-s-old-boys", "gl": 2, "gv": 0, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Campagna", "equipo": "local", "min": 71}, {"jugador": "Scalise", "equipo": "local", "min": 86}]},
                               {"hora_utc": "1983-05-15T19:00Z", "fecha": "1983-05-15", "local": "loma-negra", "visitante": "racing-club", "gl": 2, "gv": 1, "estadio": "Cancha de Racing de Olavarría", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Husillos", "equipo": "local", "min": 75, "tipo": "pen"}, {"jugador": "Varales", "equipo": "local", "min": 89}, {"jugador": "Rizzi", "equipo": "visitante", "min": 72}]},
                               {"hora_utc": "1983-05-19T19:00Z", "fecha": "1983-05-19", "local": "racing-club", "visitante": "loma-negra", "gl": 4, "gv": 0, "estadio": "Cancha de Huracán", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Leroyer", "equipo": "local", "min": 1}, {"jugador": "Rizzi", "equipo": "local", "min": 33, "tipo": "pen"}, {"jugador": "Rizzi", "equipo": "local", "min": 51, "tipo": "pen"}, {"jugador": "Gizzi", "equipo": "local", "min": 66}]},
                               {"hora_utc": "1983-05-16T19:00Z", "fecha": "1983-05-16", "local": "estudiantes-de-la-plata", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 0, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Alberto Florentino Clerc", "goles": [{"jugador": "Trobbiani", "equipo": "local", "min": 59}]},
                               {"hora_utc": "1983-05-19T19:00Z", "fecha": "1983-05-19", "local": "ferro-carril-oeste", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 2, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Francisco Lamolina", "goles": [{"jugador": "Arregui", "equipo": "local", "min": 11}, {"jugador": "Márcico", "equipo": "local", "min": 77}, {"jugador": "Sabella", "equipo": "visitante", "min": 58}, {"jugador": "Brown", "equipo": "visitante", "min": 83}]},
                           ],
                           "Cuartos de final": [
                               {"hora_utc": "1983-05-21T19:00Z", "fecha": "1983-05-21", "local": "racing-cordoba", "visitante": "independiente", "gl": 1, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Maldonado", "equipo": "local", "min": 35}, {"jugador": "Marangoni", "equipo": "visitante", "min": 87}]},
                               {"hora_utc": "1983-05-25T19:00Z", "fecha": "1983-05-25", "local": "independiente", "visitante": "racing-cordoba", "gl": 1, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Abel Gnecco", "alargue": True, "pen_l": 4, "pen_v": 2, "goles": [{"jugador": "Burruchaga", "equipo": "local", "min": 60, "tipo": "pen"}, {"jugador": "Gasparini", "equipo": "visitante", "min": 54, "tipo": "pen"}]},
                               {"hora_utc": "1983-05-22T19:00Z", "fecha": "1983-05-22", "local": "river-plate", "visitante": "argentinos-juniors", "gl": 0, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Teodoro Nitti"},
                               {"hora_utc": "1983-05-25T19:00Z", "fecha": "1983-05-25", "local": "argentinos-juniors", "visitante": "river-plate", "gl": 1, "gv": 0, "estadio": "Cancha de Vélez Sarsfield", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Videla", "equipo": "local", "min": 79}]},
                               {"hora_utc": "1983-05-22T19:00Z", "fecha": "1983-05-22", "local": "rosario-central", "visitante": "temperley", "gl": 0, "gv": 1, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Aldape", "equipo": "visitante", "min": 48}]},
                               {"hora_utc": "1983-05-25T19:00Z", "fecha": "1983-05-25", "local": "temperley", "visitante": "rosario-central", "gl": 1, "gv": 1, "estadio": "Cancha de Banfield", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Finarolli", "equipo": "local", "min": 22}, {"jugador": "Iglesias", "equipo": "visitante", "min": 1}]},
                               {"hora_utc": "1983-05-22T19:00Z", "fecha": "1983-05-22", "local": "estudiantes-de-la-plata", "visitante": "racing-club", "gl": 3, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Trama", "equipo": "local", "min": 1}, {"jugador": "Gottardi", "equipo": "local", "min": 26}, {"jugador": "Gottardi", "equipo": "local", "min": 43}, {"jugador": "Gizzi", "equipo": "visitante", "min": 65}]},
                               {"hora_utc": "1983-05-25T19:00Z", "fecha": "1983-05-25", "local": "racing-club", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 1, "estadio": "Cancha de Huracán", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Brown", "equipo": "local", "min": 47, "tipo": "ec"}, {"jugador": "Leiva", "equipo": "local", "min": 58}, {"jugador": "Gottardi", "equipo": "visitante", "min": 22}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1983-05-29T19:00Z", "fecha": "1983-05-29", "local": "argentinos-juniors", "visitante": "independiente", "gl": 2, "gv": 1, "estadio": "Cancha de Vélez Sarsfield", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Pasculli", "equipo": "local", "min": 10}, {"jugador": "Batista", "equipo": "local", "min": 57}, {"jugador": "Percudani", "equipo": "visitante", "min": 69}]},
                               {"hora_utc": "1983-06-01T19:00Z", "fecha": "1983-06-01", "local": "independiente", "visitante": "argentinos-juniors", "gl": 2, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Burruchaga", "equipo": "local", "min": 24}, {"jugador": "Morete", "equipo": "local", "min": 72}]},
                               {"hora_utc": "1983-05-29T19:00Z", "fecha": "1983-05-29", "local": "estudiantes-de-la-plata", "visitante": "temperley", "gl": 1, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Agüero", "equipo": "local", "min": 23}, {"jugador": "Aldape", "equipo": "visitante", "min": 52}]},
                               {"hora_utc": "1983-06-01T19:00Z", "fecha": "1983-06-01", "local": "temperley", "visitante": "estudiantes-de-la-plata", "gl": 1, "gv": 3, "estadio": "Cancha de Banfield", "arbitro": "Abel Gnecco", "alargue": True, "goles": [{"jugador": "Dabrowski", "equipo": "local", "min": 81}, {"jugador": "Brown", "equipo": "visitante", "min": 53}, {"jugador": "Gottardi", "equipo": "visitante", "min": 97}, {"jugador": "Trobbiani", "equipo": "visitante", "min": 104}]},
                           ],
                           "Final": [
                               {"hora_utc": "1983-06-04T19:00Z", "fecha": "1983-06-04", "local": "estudiantes-de-la-plata", "visitante": "independiente", "gl": 2, "gv": 0, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Gottardi", "equipo": "local", "min": 35}, {"jugador": "Trama", "equipo": "local", "min": 83}]},
                               {"hora_utc": "1983-06-10T19:00Z", "fecha": "1983-06-10", "local": "independiente", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Giusti", "equipo": "local", "min": 14}, {"jugador": "Trossero", "equipo": "local", "min": 71}, {"jugador": "Trama", "equipo": "visitante", "min": 44}]},
                           ],
                      },
                      "ida_y_vuelta": True,
                      "sin_descensos": "En el Nacional no había descensos: se definían en el Metropolitano."},
    # El Campeonato Metropolitano 1983 (junio a diciembre; campeón Independiente): 19 equipos a dos ruedas (38 fechas,
    # en cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF,
    # sin goles; días y estadios de Wikipedia). Volvieron los promedios, por temporada (1982 y 1983; Wikipedia): bajaron
    # los dos peores, Racing Club y Nueva Chicago. A la Libertadores 1984 fueron los campeones del Nacional y del
    # Metropolitano
    "1983-metropolitano": {"nombre": "Campeonato Metropolitano 1983", "anio": 1983, "liga": "a_mano", "slug": "1983-metropolitano",
                           "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1983 (las 38 fechas; eran 19 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Víctor Ramos "
                                              "(Newell's), con 30 goles.",
                           # (los puntos de cada temporada; se divide por las temporadas jugadas)
                           "promedios_por_temporada": True,
                           "promedios": {"1982": {"independiente": [52, 1], "estudiantes-de-la-plata": [54, 1],
                                                  "velez-sarsfield": [42, 1], "boca-juniors": [48, 1], "ferro-carril-oeste": [37, 1],
                                                  "newell-s-old-boys": [44, 1], "huracan": [41, 1], "instituto": [33, 1],
                                                  "rosario-central": [37, 1], "racing-cordoba": [39, 1], "talleres": [33, 1],
                                                  "union": [27, 1], "argentinos-juniors": [28, 1], "river-plate": [34, 1],
                                                  "platense": [28, 1], "nueva-chicago": [28, 1], "racing-club": [28, 1]}},
                           "descensos": "promedios", "descienden": 2,
                           "cupos": {"anio": 1984, "fijos": True,
                                     "libertadores": [("Campeón del Nacional 1983", "estudiantes-de-la-plata"),
                                                      ("Campeón del Metropolitano 1983", "independiente")]}},
    # 1984: el Campeonato Nacional 1984 (febrero a mayo; campeón Ferro): 32 equipos (los del Metropolitano y los del
    # interior) en 8 zonas de 4 a dos ruedas ("zonas_a_mano"), con 2 puntos por partido ganado; los dos primeros de cada
    # zona jugaban la fase final, a ida y vuelta. A Chacarita le descontaron 6 puntos. ESPN no lo tiene: va a mano
    # (tools/a_mano; resultados de RSSSF, estadios de Wikipedia; de la fase final, también los goles y los árbitros de
    # Wikipedia). No había descensos (salían del Metropolitano)
    "1984-nacional": {"nombre": "Campeonato Nacional 1984", "anio": 1984, "liga": "a_mano", "slug": "1984-nacional",
                      "zonas_a_mano": {"A": ["newell-s-old-boys", "talleres", "boca-juniors", "ferro-general-pico"],
                                       "B": ["san-lorenzo", "gimnasia-mendoza", "union-general-pinedo", "temperley"],
                                       "C": ["belgrano", "rosario-central", "velez-sarsfield", "central-norte"],
                                       "D": ["river-plate", "huracan", "estudiantes-rio-cuarto", "atletico-uruguay"],
                                       "E": ["ferro-carril-oeste", "instituto", "platense", "altos-hornos-zapla"],
                                       "F": ["independiente", "atletico-tucuman", "chacarita-juniors", "kimberley"],
                                       "G": ["argentinos-juniors", "racing-cordoba", "union", "ledesma"],
                                       "H": ["estudiantes-de-la-plata", "olimpo", "atlanta", "union-san-vicente"]},
                      "fechas": 6, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la fase final (los dos primeros de cada zona)",
                      "descuentos": {"chacarita-juniors": 6},
                      "descuentos_texto": "A Chacarita se le descontaron 6 puntos (por incidentes en la final del Reducido de "
                                          "la Primera B 1983).",
                      "goleadores_nota": "Los goles son solo de la fase final (de Wikipedia, con los minutos): de la fase de "
                                         "zonas no están. El goleador del torneo fue Pedro Pasculli (Argentinos), con 9 goles.",
                      "nombre_playoffs": "Fase final",
                      "playoffs": [(r"^$^", n) for n in ("Octavos de final", "Cuartos de final", "Semifinales", "Final")],
                      "playoffs_a_mano": {
                           "Octavos de final": [
                               {"hora_utc": "1984-04-03T19:00Z", "fecha": "1984-04-03", "local": "4", "visitante": "9785", "gl": 2, "gv": 0, "estadio": "Estadio Córdoba", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Guerini", "equipo": "local", "min": 6}, {"jugador": "Mazo", "equipo": "local", "min": 21, "tipo": "pen"}]},
                               {"hora_utc": "1984-04-04T19:00Z", "fecha": "1984-04-04", "local": "rco", "visitante": "san-lorenzo", "gl": 1, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Juan Carlos Demaro", "goles": [{"jugador": "Oyola", "equipo": "local", "min": 55}, {"jugador": "Perazzo", "equipo": "visitante", "min": 13}]},
                               {"hora_utc": "1984-04-04T19:00Z", "fecha": "1984-04-04", "local": "estudiantes-de-la-plata", "visitante": "talleres", "gl": 0, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi", "arbitro": "Raúl Marsiglia", "goles": [{"jugador": "Hoyos", "equipo": "visitante", "min": 82, "tipo": "pen"}]},
                               {"hora_utc": "1984-04-04T19:00Z", "fecha": "1984-04-04", "local": "rosario-central", "visitante": "independiente", "gl": 1, "gv": 1, "estadio": "Estadio Gigante de Arroyito", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Killer", "equipo": "local", "min": 87}, {"jugador": "Merlini", "equipo": "visitante", "min": 90}]},
                               {"hora_utc": "1984-04-04T19:00Z", "fecha": "1984-04-04", "local": "2975", "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "Estadio Juan Domingo Perón", "arbitro": "Juan Carlos Loustau"},
                               {"hora_utc": "1984-04-04T19:00Z", "fecha": "1984-04-04", "local": "ferro-carril-oeste", "visitante": "huracan", "gl": 1, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Francisco Lamolina", "goles": [{"jugador": "Marchesini", "equipo": "local", "min": 73}]},
                               {"hora_utc": "1984-04-04T19:00Z", "fecha": "1984-04-04", "local": "2636", "visitante": "newell-s-old-boys", "gl": 0, "gv": 0, "estadio": "Estadio Roberto Nicolás Carminatti", "arbitro": "Abel Gnecco"},
                               {"hora_utc": "1984-04-05T19:00Z", "fecha": "1984-04-05", "local": "argentinos-juniors", "visitante": "11972", "gl": 3, "gv": 2, "estadio": "Cancha de Ferro Carril Oeste", "arbitro": "Mario Luis Gallina", "goles": [{"jugador": "Pasculli", "equipo": "local", "min": 19}, {"jugador": "Pasculli", "equipo": "local", "min": 40}, {"jugador": "Lemme", "equipo": "local", "min": 32}, {"jugador": "Funes", "equipo": "visitante", "min": 8, "tipo": "pen"}, {"jugador": "Zolorza", "equipo": "visitante", "min": 56}]},
                               {"hora_utc": "1984-04-10T19:00Z", "fecha": "1984-04-10", "local": "talleres", "visitante": "estudiantes-de-la-plata", "gl": 1, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Juárez", "equipo": "local", "min": 32}, {"jugador": "Vieta", "equipo": "visitante", "min": 35}]},
                               {"hora_utc": "1984-04-11T19:00Z", "fecha": "1984-04-11", "local": "san-lorenzo", "visitante": "rco", "gl": 3, "gv": 1, "estadio": "Cancha de Atlanta", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Perazzo", "equipo": "local", "min": 24}, {"jugador": "Navarro", "equipo": "local", "min": 32}, {"jugador": "Rinaldi", "equipo": "local", "min": 49}, {"jugador": "Gasparini", "equipo": "visitante", "min": 64}]},
                               {"hora_utc": "1984-04-11T19:00Z", "fecha": "1984-04-11", "local": "11972", "visitante": "argentinos-juniors", "gl": 1, "gv": 2, "estadio": "Malvinas Argentinas", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "O. Olguín", "equipo": "local", "min": 64}, {"jugador": "Pasculli", "equipo": "visitante", "min": 65}, {"jugador": "Pasculli", "equipo": "visitante", "min": 82}]},
                               {"hora_utc": "1984-04-11T19:00Z", "fecha": "1984-04-11", "local": "independiente", "visitante": "rosario-central", "gl": 1, "gv": 0, "estadio": "Estadio La Doble Visera", "arbitro": "Juan Carlos Demaro", "goles": [{"jugador": "Trossero", "equipo": "local", "min": 79}]},
                               {"hora_utc": "1984-04-11T19:00Z", "fecha": "1984-04-11", "local": "river-plate", "visitante": "2975", "gl": 2, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Francescoli", "equipo": "local", "min": 87}, {"jugador": "Francescoli", "equipo": "local", "min": 89, "tipo": "pen"}]},
                               {"hora_utc": "1984-04-11T19:00Z", "fecha": "1984-04-11", "local": "huracan", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 0, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Julio Gumersindo Barraza", "alargue": True, "pen_l": 6, "pen_v": 7, "goles": [{"jugador": "Sánchez", "equipo": "local", "min": 22}]},
                               {"hora_utc": "1984-04-11T19:00Z", "fecha": "1984-04-11", "local": "newell-s-old-boys", "visitante": "2636", "gl": 1, "gv": 1, "estadio": "Estadio Coloso del Parque", "arbitro": "Francisco Lamolina", "alargue": True, "pen_l": 7, "pen_v": 6, "goles": [{"jugador": "Martino", "equipo": "local", "min": 47}, {"jugador": "Palacio Corrales", "equipo": "visitante", "min": 40}]},
                               {"hora_utc": "1984-04-07T19:00Z", "fecha": "1984-04-07", "local": "9785", "visitante": "4", "gl": 0, "gv": 0, "estadio": "Cancha de Central Córdoba (Santiago del Estero)", "arbitro": "Abel Gnecco", "nota": "Se suspendió a los 19 minutos del segundo tiempo (0-0); lo que faltaba se jugó el 14 de abril, en cancha de Central Córdoba (Santiago del Estero)"},
                           ],
                           "Cuartos de final": [
                               {"hora_utc": "1984-04-18T19:00Z", "fecha": "1984-04-18", "local": "4", "visitante": "river-plate", "gl": 0, "gv": 4, "estadio": "Estadio Córdoba", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Teglia", "equipo": "visitante", "min": 4}, {"jugador": "Teglia", "equipo": "visitante", "min": 45}, {"jugador": "Bica", "equipo": "visitante", "min": 13}, {"jugador": "Alfaro", "equipo": "visitante", "min": 70}]},
                               {"hora_utc": "1984-04-18T19:00Z", "fecha": "1984-04-18", "local": "argentinos-juniors", "visitante": "talleres", "gl": 2, "gv": 1, "estadio": "Cancha de Ferro Carril Oeste", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Batista", "equipo": "local", "min": 37}, {"jugador": "Pasculli", "equipo": "local", "min": 76}, {"jugador": "Hoyos", "equipo": "visitante", "min": 81}]},
                               {"hora_utc": "1984-04-18T19:00Z", "fecha": "1984-04-18", "local": "newell-s-old-boys", "visitante": "san-lorenzo", "gl": 2, "gv": 2, "estadio": "Estadio Coloso del Parque", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Ciraolo", "equipo": "local", "min": 10}, {"jugador": "Almirón", "equipo": "local", "min": 77}, {"jugador": "Higuaín", "equipo": "visitante", "min": 31}, {"jugador": "Perazzo", "equipo": "visitante", "min": 53}]},
                               {"hora_utc": "1984-04-26T19:00Z", "fecha": "1984-04-26", "local": "ferro-carril-oeste", "visitante": "independiente", "gl": 1, "gv": 1, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Márcico", "equipo": "local", "min": 52}, {"jugador": "Sánchez", "equipo": "visitante", "min": 33}]},
                               {"hora_utc": "1984-04-25T19:00Z", "fecha": "1984-04-25", "local": "river-plate", "visitante": "4", "gl": 0, "gv": 2, "estadio": "Estadio Monumental", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Scatolaro", "equipo": "visitante", "min": 39}, {"jugador": "Blasón", "equipo": "visitante", "min": 89, "tipo": "pen"}]},
                               {"hora_utc": "1984-04-25T19:00Z", "fecha": "1984-04-25", "local": "talleres", "visitante": "argentinos-juniors", "gl": 4, "gv": 2, "estadio": "Estadio Córdoba", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Hoyos", "equipo": "local", "min": 4}, {"jugador": "Tedini", "equipo": "local", "min": 33}, {"jugador": "Bevilacqua", "equipo": "local", "min": 51}, {"jugador": "Beccérica", "equipo": "local", "min": 84}, {"jugador": "Ereros", "equipo": "visitante", "min": 46}, {"jugador": "Videla", "equipo": "visitante", "min": 65}]},
                               {"hora_utc": "1984-04-25T19:00Z", "fecha": "1984-04-25", "local": "san-lorenzo", "visitante": "newell-s-old-boys", "gl": 2, "gv": 1, "estadio": "Cancha de Atlanta", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Perazzo", "equipo": "local", "min": 44}, {"jugador": "Luna", "equipo": "local", "min": 71}, {"jugador": "Viglione", "equipo": "visitante", "min": 79}]},
                               {"hora_utc": "1984-05-02T19:00Z", "fecha": "1984-05-02", "local": "independiente", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 1, "estadio": "Estadio La Doble Visera", "arbitro": "Juan Antonio Bava", "alargue": True, "goles": [{"jugador": "Arregui", "equipo": "visitante", "min": 104}]},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1984-05-02T19:00Z", "fecha": "1984-05-02", "local": "san-lorenzo", "visitante": "river-plate", "gl": 1, "gv": 2, "estadio": "Cancha de Vélez Sarsfield", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Quinteros", "equipo": "local", "min": 35}, {"jugador": "Francescoli", "equipo": "visitante", "min": 67}, {"jugador": "Alonso", "equipo": "visitante", "min": 82}]},
                               {"hora_utc": "1984-05-09T19:00Z", "fecha": "1984-05-09", "local": "ferro-carril-oeste", "visitante": "talleres", "gl": 1, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Noremberg", "equipo": "local", "min": 54}]},
                               {"hora_utc": "1984-05-09T19:00Z", "fecha": "1984-05-09", "local": "river-plate", "visitante": "san-lorenzo", "gl": 2, "gv": 1, "estadio": "Estadio Monumental", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Villalba", "equipo": "local", "min": 7}, {"jugador": "Alonso", "equipo": "local", "min": 25}, {"jugador": "Biaín", "equipo": "visitante", "min": 51}]},
                               {"hora_utc": "1984-05-16T19:00Z", "fecha": "1984-05-16", "local": "talleres", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 1, "estadio": "Estadio Córdoba", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Tedini", "equipo": "local", "min": 7}, {"jugador": "Noremberg", "equipo": "visitante", "min": 56}]},
                           ],
                           "Final": [
                               {"hora_utc": "1984-05-24T19:00Z", "fecha": "1984-05-24", "local": "river-plate", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 3, "estadio": "Estadio Monumental", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Cañete", "equipo": "visitante", "min": 3}, {"jugador": "Noremberg", "equipo": "visitante", "min": 20}, {"jugador": "Márcico", "equipo": "visitante", "min": 36, "tipo": "pen"}]},
                               {"hora_utc": "1984-05-30T19:00Z", "fecha": "1984-05-30", "local": "ferro-carril-oeste", "visitante": "river-plate", "gl": 1, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Teodoro Nitti", "nota": "Se suspendió a los 25 minutos del segundo tiempo y quedó el resultado", "goles": [{"jugador": "Cañete", "equipo": "local", "min": 2}]},
                           ],
                      },
                      "ida_y_vuelta": True},
    # El Campeonato Metropolitano 1984 (abril a diciembre; campeón Argentinos): 19 equipos a dos ruedas (38 fechas, en
    # cada una quedaba uno libre), con 2 puntos por partido ganado. ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin
    # goles; estadios de Wikipedia). Los promedios eran por temporada (1982, 1983 y 1984; RSSSF): bajaron los dos peores,
    # Rosario Central y Atlanta. A la Libertadores 1985 fueron los campeones del Nacional y del Metropolitano
    "1984-metropolitano": {"nombre": "Campeonato Metropolitano 1984", "anio": 1984, "liga": "a_mano", "slug": "1984-metropolitano",
                           "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                           "anual_texto": "La tabla del Campeonato Metropolitano 1984 (las 38 fechas; eran 19 equipos y en cada "
                                          "fecha uno quedaba libre). Cada partido ganado valía 2 puntos.",
                           "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Enzo Francescoli "
                                              "(River), con 24 goles.",
                           # (los puntos de cada temporada; se divide por las temporadas jugadas)
                           "promedios_por_temporada": True,
                           "promedios": {"1982": {"estudiantes-de-la-plata": [54, 1], "ferro-carril-oeste": [37, 1],
                                                  "independiente": [52, 1], "velez-sarsfield": [42, 1], "newell-s-old-boys": [44, 1],
                                                  "argentinos-juniors": [28, 1], "boca-juniors": [48, 1], "racing-cordoba": [39, 1],
                                                  "river-plate": [34, 1], "instituto": [33, 1], "huracan": [41, 1], "talleres": [33, 1],
                                                  "platense": [28, 1], "union": [27, 1], "rosario-central": [37, 1]},
                                         "1983": {"estudiantes-de-la-plata": [38, 1], "ferro-carril-oeste": [46, 1],
                                                  "independiente": [48, 1], "velez-sarsfield": [44, 1], "san-lorenzo": [47, 1],
                                                  "newell-s-old-boys": [35, 1], "argentinos-juniors": [36, 1], "boca-juniors": [37, 1],
                                                  "racing-cordoba": [27, 1], "river-plate": [29, 1], "instituto": [35, 1],
                                                  "huracan": [32, 1], "talleres": [33, 1], "temperley": [33, 1], "platense": [34, 1],
                                                  "union": [38, 1], "rosario-central": [30, 1]}},
                           "descensos": "promedios", "descienden": 2,
                           "cupos": {"anio": 1985, "fijos": True,
                                     "libertadores": [("Campeón del Nacional 1984", "ferro-carril-oeste"),
                                                      ("Campeón del Metropolitano 1984", "argentinos-juniors")]}},
    # 1985: el Campeonato Nacional 1985 (febrero a septiembre; campeón Argentinos), el último Nacional: 32 equipos (los
    # del Metropolitano y los del interior) en 8 zonas de 4 a dos ruedas ("zonas_a_mano"), con 2 puntos por partido
    # ganado; los dos primeros de cada zona pasaban a la rueda de ganadores y los otros dos a la de perdedores, adonde
    # caían también los que perdían en la de ganadores (doble eliminación). La final la jugaron el ganador de cada rueda:
    # ganó Vélez, que venía de la de perdedores, y como Argentinos no había perdido todavía se jugó otra, que ganó
    # Argentinos. ESPN no lo tiene: va a mano (tools/a_mano; resultados de RSSSF, estadios de Wikipedia; de la doble
    # eliminación, también los goles y los árbitros de Wikipedia). No había descensos (salían del Metropolitano)
    "1985-nacional": {"nombre": "Campeonato Nacional 1985", "anio": 1985, "liga": "a_mano", "slug": "1985-nacional",
                      "zonas_a_mano": {"A": ["estudiantes-de-la-plata", "santamarina", "racing-cordoba", "platense"],
                                       "B": ["boca-juniors", "estudiantes-rio-cuarto", "temperley", "altos-hornos-zapla"],
                                       "C": ["talleres", "independiente", "guarani-antonio-franco", "huracan"],
                                       "D": ["river-plate", "union", "gimnasia-y-esgrima", "cipolletti"],
                                       "E": ["newell-s-old-boys", "san-lorenzo", "huracan-las-heras", "circulo-deportivo"],
                                       "F": ["argentinos-juniors", "chacarita-juniors", "central-norte", "belgrano"],
                                       "G": ["san-martin-tucuman", "velez-sarsfield", "argentino-firmat", "juventud-alianza"],
                                       "H": ["ferro-carril-oeste", "deportivo-espanol", "instituto", "juventud-antoniana"]},
                      "fechas": 6, "pasan": 2, "puntos_victoria": 2,
                      "texto_pasan": "Pasan a la rueda de ganadores (los dos primeros de cada zona; los otros dos van a la de "
                                     "perdedores)",
                      "goleadores_nota": "Los goles son solo de la doble eliminación (de Wikipedia, con los minutos): de la "
                                         "fase de zonas no están. El goleador del torneo fue Jorge Comas (Vélez), con 12 goles.",
                      "nombre_playoffs": "Doble eliminación",
                      "playoffs": [(r"^$^", n) for n in (
                          "Ganadores: octavos de final", "Ganadores: cuartos de final", "Ganadores: semifinales",
                          "Ganadores: final", "Perdedores: primera fase", "Perdedores: segunda fase",
                          "Perdedores: tercera fase", "Perdedores: cuarta fase", "Perdedores: quinta fase",
                          "Perdedores: sexta fase", "Perdedores: final", "Final (primer partido)", "Final")],
                      "playoffs_a_mano": {
                           "Ganadores: octavos de final": [
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "boca-juniors", "visitante": "velez-sarsfield", "gl": 3, "gv": 2, "estadio": "Estadio Monumental", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Dykstra", "equipo": "local", "min": 34}, {"jugador": "Graciani", "equipo": "local", "min": 39}, {"jugador": "Tapia", "equipo": "local", "min": 55}, {"jugador": "Gabrich", "equipo": "visitante", "min": 65}, {"jugador": "Comas", "equipo": "visitante", "min": 78, "tipo": "pen"}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "deportivo-espanol", "visitante": "river-plate", "gl": 2, "gv": 1, "estadio": "Estadio Club Atlético Atlanta", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Vázquez", "equipo": "local", "min": 57}, {"jugador": "D'Angelo", "equipo": "local", "min": 78}, {"jugador": "Amuchástegui", "equipo": "visitante", "min": 29}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "ferro-carril-oeste", "visitante": "union", "gl": 1, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Fantaguzzi", "equipo": "local", "min": 49}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "independiente", "visitante": "rsa", "gl": 3, "gv": 1, "estadio": "Estadio La Doble Visera (Avellaneda)", "arbitro": "Francisco Lamolina", "goles": [{"jugador": "Percudani", "equipo": "local", "min": 33}, {"jugador": "Percudani", "equipo": "local", "min": 85}, {"jugador": "Reinoso", "equipo": "local", "min": 71}, {"jugador": "Gauna", "equipo": "visitante", "min": 9}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "newell-s-old-boys", "visitante": "chacarita-juniors", "gl": 0, "gv": 0, "estadio": "Estadio Coloso del Parque (Rosario)", "arbitro": "Teodoro Nitti"},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "san-lorenzo", "visitante": "argentinos-juniors", "gl": 2, "gv": 2, "estadio": "Estadio José Amalfitani", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Insúa", "equipo": "local", "min": 73, "tipo": "pen"}, {"jugador": "Espíndola", "equipo": "local", "min": 88}, {"jugador": "Olguín", "equipo": "visitante", "min": 23, "tipo": "pen"}, {"jugador": "Ereros", "equipo": "visitante", "min": 76}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "san-martin-tucuman", "visitante": "19685", "gl": 4, "gv": 2, "estadio": "Estadio La Ciudadela (San Miguel de Tucumán)", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Gutiérrez", "equipo": "local", "min": 2}, {"jugador": "Gutiérrez", "equipo": "local", "min": 68}, {"jugador": "Román", "equipo": "local", "min": 23}, {"jugador": "Robles", "equipo": "local", "min": 60}, {"jugador": "Coleoni", "equipo": "visitante", "min": 4, "tipo": "pen"}, {"jugador": "Coleoni", "equipo": "visitante", "min": 54}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "talleres", "visitante": "estudiantes-de-la-plata", "gl": 1, "gv": 1, "estadio": "Estadio Ciudad de Córdoba", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Pochettino", "equipo": "local", "min": 68}, {"jugador": "Trobbiani", "equipo": "visitante", "min": 15}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "argentinos-juniors", "visitante": "san-lorenzo", "gl": 1, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Ereros", "equipo": "local", "min": 86}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "chacarita-juniors", "visitante": "newell-s-old-boys", "gl": 1, "gv": 2, "estadio": "Estadio El Coliseo de Mitre y Puccini (Campana)", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Theiler", "equipo": "local", "min": 3, "tipo": "ec"}, {"jugador": "Almirón", "equipo": "visitante", "min": 18}, {"jugador": "Paolorossi", "equipo": "visitante", "min": 71}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "19685", "visitante": "san-martin-tucuman", "gl": 0, "gv": 0, "estadio": "Estadio Ciudad de Río Cuarto", "arbitro": "Juan Carlos Demaro"},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "estudiantes-de-la-plata", "visitante": "talleres", "gl": 3, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi (La Plata)", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Iglesias", "equipo": "local", "min": 22}, {"jugador": "Gugnali", "equipo": "local", "min": 64}, {"jugador": "Herrera", "equipo": "local", "min": 75}, {"jugador": "Muggione", "equipo": "visitante", "min": 81}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "rsa", "visitante": "independiente", "gl": 2, "gv": 3, "estadio": "Estadio Municipal General San Martín (Tandil)", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Portugal", "equipo": "local", "min": 41}, {"jugador": "Puggioni", "equipo": "local", "min": 85}, {"jugador": "Clara", "equipo": "visitante", "min": 37}, {"jugador": "Percudani", "equipo": "visitante", "min": 55}, {"jugador": "Bochini", "equipo": "visitante", "min": 56}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "river-plate", "visitante": "deportivo-espanol", "gl": 5, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Francisco Lamolina", "goles": [{"jugador": "Alonso", "equipo": "local", "min": 35, "tipo": "pen"}, {"jugador": "Amuchástegui", "equipo": "local", "min": 38}, {"jugador": "Amuchástegui", "equipo": "local", "min": 73}, {"jugador": "Gareca", "equipo": "local", "min": 50}, {"jugador": "Villazán", "equipo": "local", "min": 76}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "union", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 2, "estadio": "Estadio Club Atlético Unión (Santa Fe)", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Alí", "equipo": "local", "min": 47}, {"jugador": "Márcico", "equipo": "visitante", "min": 8}, {"jugador": "González", "equipo": "visitante", "min": 17}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "velez-sarsfield", "visitante": "boca-juniors", "gl": 2, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Gabrich", "equipo": "local", "min": 12}, {"jugador": "Comas", "equipo": "local", "min": 82}]},
                           ],
                           "Ganadores: cuartos de final": [
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "ferro-carril-oeste", "visitante": "independiente", "gl": 3, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Márcico", "equipo": "local", "min": 9}, {"jugador": "Márcico", "equipo": "local", "min": 64}, {"jugador": "Fantaguzzi", "equipo": "local", "min": 43}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "newell-s-old-boys", "visitante": "velez-sarsfield", "gl": 1, "gv": 2, "estadio": "Estadio Eva Perón (Junín)", "arbitro": "Arturo Ithurralde", "alargue": True, "goles": [{"jugador": "Almirón", "equipo": "local", "min": 75}, {"jugador": "Comas", "equipo": "visitante", "min": 12}, {"jugador": "Cuciuffo", "equipo": "visitante", "min": 119}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "river-plate", "visitante": "estudiantes-de-la-plata", "gl": 2, "gv": 0, "estadio": "Estadio La Doble Visera (Avellaneda)", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Gareca", "equipo": "local", "min": 84, "tipo": "pen"}, {"jugador": "Gareca", "equipo": "local", "min": 87}]},
                               {"hora_utc": "1985-03-30T19:00Z", "fecha": "1985-03-30", "local": "san-martin-tucuman", "visitante": "argentinos-juniors", "gl": 0, "gv": 2, "estadio": "Estadio Ciudad de Córdoba", "arbitro": "Jorge Eduardo Romero", "goles": [{"jugador": "Castro", "equipo": "visitante", "min": 42}, {"jugador": "Ereros", "equipo": "visitante", "min": 89}]},
                           ],
                           "Ganadores: semifinales": [
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "ferro-carril-oeste", "visitante": "argentinos-juniors", "gl": 0, "gv": 3, "estadio": "Estadio José Amalfitani", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Batista", "equipo": "visitante", "min": 19}, {"jugador": "Pasculli", "equipo": "visitante", "min": 83}, {"jugador": "Ereros", "equipo": "visitante", "min": 88}]},
                               {"hora_utc": "1985-04-16T19:00Z", "fecha": "1985-04-16", "local": "velez-sarsfield", "visitante": "river-plate", "gl": 3, "gv": 0, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Comas", "equipo": "local", "min": 28}, {"jugador": "Comas", "equipo": "local", "min": 35}, {"jugador": "Comas", "equipo": "local", "min": 75}]},
                           ],
                           "Ganadores: final": [
                               {"hora_utc": "1985-07-09T19:00Z", "fecha": "1985-07-09", "local": "argentinos-juniors", "visitante": "velez-sarsfield", "gl": 2, "gv": 0, "estadio": "Estadio La Bombonera", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Videla", "equipo": "local", "min": 14}, {"jugador": "Batista", "equipo": "local", "min": 79}]},
                               {"hora_utc": "1985-07-17T19:00Z", "fecha": "1985-07-17", "local": "velez-sarsfield", "visitante": "argentinos-juniors", "gl": 2, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Juan Carlos Loustau", "alargue": True, "pen_l": 2, "pen_v": 4, "goles": [{"jugador": "Comas", "equipo": "local", "min": 10}, {"jugador": "Meza", "equipo": "local", "min": 63}]},
                           ],
                           "Perdedores: primera fase": [
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "ahz", "visitante": "afi", "gl": 2, "gv": 0, "estadio": "Estadio Centro Siderúrgico (Palpalá)", "arbitro": "Juan Carlos Demaro", "goles": [{"jugador": "Borneman", "equipo": "local", "min": 74}, {"jugador": "Borneman", "equipo": "local", "min": 77}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "cip", "visitante": "instituto", "gl": 0, "gv": 0, "estadio": "Estadio La Visera de Cemento (Cipolletti)", "arbitro": "Aníbal Hay"},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "4", "visitante": "hlh", "gl": 2, "gv": 1, "estadio": "Estadio Club Atlético Belgrano (Córdoba)", "arbitro": "Julio Gumersindo Barraza", "goles": [{"jugador": "Blasón", "equipo": "local", "min": 7}, {"jugador": "Gáspari", "equipo": "local", "min": 69}, {"jugador": "Moyano", "equipo": "visitante", "min": 9}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "cno", "visitante": "cde", "gl": 0, "gv": 0, "estadio": "Estadio Doctor Luis Güemes (Salta)", "arbitro": "Francisco Cardillo"},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "gimnasia-y-esgrima", "visitante": "jan", "gl": 3, "gv": 0, "estadio": "Estadio Del Bosque (La Plata)", "arbitro": "Carlos Ramón Coradina", "goles": [{"jugador": "Carrió", "equipo": "local", "min": 13}, {"jugador": "Vargas", "equipo": "local", "min": 27}, {"jugador": "Toledo", "equipo": "local", "min": 87}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "gaf", "visitante": "platense", "gl": 0, "gv": 0, "estadio": "Estadio Clemente Fernández de Oliveira (Posadas)", "arbitro": "Juan Carlos Crespi"},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "huracan", "visitante": "rco", "gl": 2, "gv": 1, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Raúl Marsiglia", "goles": [{"jugador": "García", "equipo": "local", "min": 41}, {"jugador": "Morresi", "equipo": "local", "min": 54, "tipo": "pen"}, {"jugador": "Noriega", "equipo": "visitante", "min": 90}]},
                               {"hora_utc": "1985-03-20T19:00Z", "fecha": "1985-03-20", "local": "jal", "visitante": "10162", "gl": 4, "gv": 3, "estadio": "Estadio San Martín de San Juan", "arbitro": "Mario Luis Gallina", "goles": [{"jugador": "Torletti", "equipo": "local", "min": 45}, {"jugador": "Rodríguez", "equipo": "local", "min": 52}, {"jugador": "Giuliani", "equipo": "local", "min": 56}, {"jugador": "Ceballos", "equipo": "local", "min": 90}, {"jugador": "Custodio Mendes", "equipo": "visitante", "min": 14}, {"jugador": "Erbín", "equipo": "visitante", "min": 66}, {"jugador": "Ballejo", "equipo": "visitante", "min": 68}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "afi", "visitante": "ahz", "gl": 2, "gv": 1, "estadio": "Estadio Félix Oriola (Firmat)", "arbitro": "Raúl Marsiglia", "goles": [{"jugador": "Infantino", "equipo": "local", "min": 8}, {"jugador": "Meubry", "equipo": "local", "min": 31}, {"jugador": "Bacas", "equipo": "visitante", "min": 44}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "cde", "visitante": "cno", "gl": 2, "gv": 3, "estadio": "Estadio General San Martín (Mar del Plata)", "arbitro": "Carlos Ramón Coradina", "goles": [{"jugador": "A. Rodríguez", "equipo": "local", "min": 74}, {"jugador": "Vera", "equipo": "local", "min": 87, "tipo": "pen"}, {"jugador": "Macaione", "equipo": "visitante", "min": 35}, {"jugador": "Maladot", "equipo": "visitante", "min": 68}, {"jugador": "Viera", "equipo": "visitante", "min": 69}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "hlh", "visitante": "4", "gl": 3, "gv": 1, "estadio": "Estadio Malvinas Argentinas (Mendoza)", "arbitro": "Aníbal Hay", "goles": [{"jugador": "Bachino", "equipo": "local", "min": 22}, {"jugador": "Blanco", "equipo": "local", "min": 50}, {"jugador": "Moyano", "equipo": "local", "min": 61}, {"jugador": "Villagra", "equipo": "visitante", "min": 90}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "instituto", "visitante": "cip", "gl": 3, "gv": 1, "estadio": "Estadio Juan Domingo Perón (Córdoba)", "arbitro": "Mario Luis Gallina", "goles": [{"jugador": "M. A. Rodríguez", "equipo": "local", "min": 1}, {"jugador": "R. Rodríguez", "equipo": "local", "min": 51, "tipo": "pen"}, {"jugador": "Beltrán", "equipo": "local", "min": 85}, {"jugador": "Giner", "equipo": "visitante", "min": 75}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "jan", "visitante": "gimnasia-y-esgrima", "gl": 1, "gv": 0, "estadio": "Estadio Fray Honorato Pistoia (Salta)", "arbitro": "Juan Carlos Biscay", "goles": [{"jugador": "Garnica", "equipo": "local", "min": 55}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "platense", "visitante": "gaf", "gl": 1, "gv": 0, "estadio": "Estadio Ciudad de Vicente López (Florida)", "arbitro": "Julio Gumersindo Barraza", "goles": [{"jugador": "Bufarini", "equipo": "local", "min": 63}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "rco", "visitante": "huracan", "gl": 1, "gv": 1, "estadio": "Estadio Miguel Sancho (Córdoba)", "arbitro": "Francisco Cardillo", "alargue": True, "goles": [{"jugador": "Ferreyra", "equipo": "local", "min": 10}, {"jugador": "Candedo", "equipo": "visitante", "min": 115}]},
                               {"hora_utc": "1985-03-24T19:00Z", "fecha": "1985-03-24", "local": "10162", "visitante": "jal", "gl": 4, "gv": 1, "estadio": "Estadio Alfredo Beranger (Turdera)", "arbitro": "Juan Carlos Crespi", "alargue": True, "goles": [{"jugador": "Ballejo", "equipo": "local", "min": 18}, {"jugador": "Moris", "equipo": "local", "min": 54, "tipo": "pen"}, {"jugador": "Moris", "equipo": "local", "min": 120, "tipo": "pen"}, {"jugador": "Valente", "equipo": "local", "min": 119}, {"jugador": "Rodríguez", "equipo": "visitante", "min": 27}]},
                           ],
                           "Perdedores: segunda fase": [
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "boca-juniors", "visitante": "ahz", "gl": 3, "gv": 1, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Olarticoechea", "equipo": "local", "min": 37}, {"jugador": "Graciani", "equipo": "local", "min": 60}, {"jugador": "Dykstra", "equipo": "local", "min": 67}, {"jugador": "Borneman", "equipo": "visitante", "min": 83}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "chacarita-juniors", "visitante": "huracan", "gl": 0, "gv": 0, "estadio": "Estadio Club Atlético Atlanta", "arbitro": "Mario Luis Gallina", "alargue": True, "pen_l": 4, "pen_v": 3},
                               {"hora_utc": "1985-03-30T19:00Z", "fecha": "1985-03-30", "local": "deportivo-espanol", "visitante": "gimnasia-y-esgrima", "gl": 2, "gv": 0, "estadio": "Estadio La Doble Visera (Avellaneda)", "arbitro": "Aníbal Hay", "goles": [{"jugador": "Moreno", "equipo": "local", "min": 11}, {"jugador": "Nigretti", "equipo": "local", "min": 79}]},
                               {"hora_utc": "1985-03-30T19:00Z", "fecha": "1985-03-30", "local": "19685", "visitante": "10162", "gl": 0, "gv": 1, "estadio": "Estadio El Coloso del Barrio Talleres (General Pico)", "arbitro": "Carlos Ramón Coradina", "goles": [{"jugador": "Finarolli", "equipo": "visitante", "min": 62}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "rsa", "visitante": "cno", "gl": 1, "gv": 1, "estadio": "Estadio Fray Honorato Pistoia (Salta)", "arbitro": "Juan Carlos Crespi", "alargue": True, "pen_l": 2, "pen_v": 4, "goles": [{"jugador": "Maladot", "equipo": "visitante", "min": 63}, {"jugador": "Portugal", "equipo": "local", "min": 30}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "san-lorenzo", "visitante": "hlh", "gl": 3, "gv": 3, "estadio": "Estadio Ciudad de Río Cuarto", "arbitro": "Teodoro Nitti", "alargue": True, "pen_l": 3, "pen_v": 2, "goles": [{"jugador": "Bachino", "equipo": "visitante", "min": 72}, {"jugador": "Guirado", "equipo": "visitante", "min": 105}, {"jugador": "Próstamo", "equipo": "visitante", "min": 108}, {"jugador": "Espíndola", "equipo": "local", "min": 84}, {"jugador": "Perazzo", "equipo": "local", "min": 91}, {"jugador": "Perazzo", "equipo": "local", "min": 100}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "talleres", "visitante": "instituto", "gl": 0, "gv": 4, "estadio": "Estadio Ciudad de Córdoba", "arbitro": "Abel Gnecco", "goles": [{"jugador": "Rosas", "equipo": "visitante", "min": 31}, {"jugador": "Dertycia", "equipo": "visitante", "min": 59}, {"jugador": "Dertycia", "equipo": "visitante", "min": 87}, {"jugador": "Mattei", "equipo": "visitante", "min": 73}]},
                               {"hora_utc": "1985-03-31T19:00Z", "fecha": "1985-03-31", "local": "union", "visitante": "platense", "gl": 3, "gv": 0, "estadio": "Estadio 12 de Octubre (San Nicolás de los Arroyos)", "arbitro": "Juan Carlos Demaro", "goles": [{"jugador": "Comas", "equipo": "local", "min": 13}, {"jugador": "Comas", "equipo": "local", "min": 84}, {"jugador": "Alí", "equipo": "local", "min": 17}]},
                           ],
                           "Perdedores: tercera fase": [
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "cno", "visitante": "union", "gl": 0, "gv": 0, "estadio": "Estadio Emilio Fabrizzi (Palpalá)", "arbitro": "Francisco Cardillo", "alargue": True, "pen_l": 1, "pen_v": 3},
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "chacarita-juniors", "visitante": "san-lorenzo", "gl": 2, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Francisco Lamolina", "alargue": True, "goles": [{"jugador": "Olarán", "equipo": "local", "min": 115}, {"jugador": "Gasparini", "equipo": "local", "min": 117}]},
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "estudiantes-de-la-plata", "visitante": "deportivo-espanol", "gl": 1, "gv": 1, "estadio": "Estadio Jorge Luis Hirschi (La Plata)", "arbitro": "Raúl Marsiglia", "alargue": True, "pen_l": 6, "pen_v": 5, "goles": [{"jugador": "Trama", "equipo": "local", "min": 6}, {"jugador": "J. L. Rodríguez", "equipo": "visitante", "min": 54}]},
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "independiente", "visitante": "boca-juniors", "gl": 1, "gv": 0, "estadio": "Estadio La Doble Visera (Avellaneda)", "arbitro": "Teodoro Nitti", "nota": "Se suspendió a los 40 minutos del segundo tiempo y quedó el resultado", "goles": [{"jugador": "Barberón", "equipo": "local", "min": 31}]},
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "newell-s-old-boys", "visitante": "10162", "gl": 2, "gv": 1, "estadio": "Estadio Coloso del Parque (Rosario)", "arbitro": "Jorge Vigliano", "goles": [{"jugador": "Almirón", "equipo": "local", "min": 8, "tipo": "pen"}, {"jugador": "Cozzoni", "equipo": "local", "min": 66}, {"jugador": "Finarolli", "equipo": "visitante", "min": 3}]},
                               {"hora_utc": "1985-04-07T19:00Z", "fecha": "1985-04-07", "local": "san-martin-tucuman", "visitante": "instituto", "gl": 0, "gv": 0, "estadio": "Estadio La Ciudadela (San Miguel de Tucumán)", "arbitro": "Ricardo Calabria", "alargue": True, "pen_l": 4, "pen_v": 1},
                           ],
                           "Perdedores: cuarta fase": [
                               {"hora_utc": "1985-07-10T19:00Z", "fecha": "1985-07-10", "local": "chacarita-juniors", "visitante": "newell-s-old-boys", "gl": 0, "gv": 1, "estadio": "Estadio Gigante de Arroyito (Rosario)", "arbitro": "Juan Carlos Loustau", "goles": [{"jugador": "Dezotti", "equipo": "visitante", "min": 14}]},
                               {"hora_utc": "1985-07-10T19:00Z", "fecha": "1985-07-10", "local": "estudiantes-de-la-plata", "visitante": "san-martin-tucuman", "gl": 1, "gv": 0, "estadio": "Estadio Ciudad de Córdoba", "arbitro": "Arturo Ithurralde", "goles": [{"jugador": "Trama", "equipo": "local", "min": 73}]},
                               {"hora_utc": "1985-07-10T19:00Z", "fecha": "1985-07-10", "local": "river-plate", "visitante": "union", "gl": 1, "gv": 0, "estadio": "Estadio Monumental", "arbitro": "Carlos Alfonso Espósito", "goles": [{"jugador": "Amuchástegui", "equipo": "local", "min": 60}]},
                               {"hora_utc": "1985-07-10T19:00Z", "fecha": "1985-07-10", "local": "ferro-carril-oeste", "visitante": "independiente", "gl": 0, "gv": 0, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Abel Gnecco", "alargue": True, "pen_l": 2, "pen_v": 4},
                           ],
                           "Perdedores: quinta fase": [
                               {"hora_utc": "1985-07-24T19:00Z", "fecha": "1985-07-24", "local": "independiente", "visitante": "newell-s-old-boys", "gl": 0, "gv": 2, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Ricardo Calabria", "goles": [{"jugador": "Almirón", "equipo": "visitante", "min": 47}, {"jugador": "Dezotti", "equipo": "visitante", "min": 83}]},
                               {"hora_utc": "1985-07-17T19:00Z", "fecha": "1985-07-17", "local": "river-plate", "visitante": "estudiantes-de-la-plata", "gl": 4, "gv": 1, "estadio": "Estadio Ferro Carril Oeste", "arbitro": "Teodoro Nitti", "goles": [{"jugador": "Francescoli", "equipo": "local", "min": 23, "tipo": "pen"}, {"jugador": "Alfaro", "equipo": "local", "min": 50}, {"jugador": "Amuchástegui", "equipo": "local", "min": 60}, {"jugador": "Amuchástegui", "equipo": "local", "min": 77}, {"jugador": "Ponce", "equipo": "visitante", "min": 67, "tipo": "pen"}]},
                           ],
                           "Perdedores: sexta fase": [
                               {"hora_utc": "1985-07-31T19:00Z", "fecha": "1985-07-31", "local": "river-plate", "visitante": "newell-s-old-boys", "gl": 2, "gv": 0, "estadio": "Estadio José Amalfitani", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Francescoli", "equipo": "local", "min": 24, "tipo": "pen"}, {"jugador": "Amuchástegui", "equipo": "local", "min": 71}]},
                           ],
                           "Perdedores: final": [
                               {"hora_utc": "1985-08-07T19:00Z", "fecha": "1985-08-07", "local": "velez-sarsfield", "visitante": "river-plate", "gl": 2, "gv": 1, "estadio": "Estadio Tomás Adolfo Ducó", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Larraquy", "equipo": "local", "min": 63}, {"jugador": "Comas", "equipo": "local", "min": 85}, {"jugador": "Francescoli", "equipo": "visitante", "min": 54}]},
                           ],
                           "Final (primer partido)": [
                               {"hora_utc": "1985-08-28T19:00Z", "fecha": "1985-08-28", "local": "argentinos-juniors", "visitante": "velez-sarsfield", "gl": 1, "gv": 1, "estadio": "Estadio Monumental", "arbitro": "Ricardo Calabria", "alargue": True, "pen_l": 3, "pen_v": 4, "goles": [{"jugador": "Borghi", "equipo": "local", "min": 39}, {"jugador": "Larraquy", "equipo": "visitante", "min": 79}]},
                           ],
                           "Final": [
                               {"hora_utc": "1985-09-04T19:00Z", "fecha": "1985-09-04", "local": "velez-sarsfield", "visitante": "argentinos-juniors", "gl": 1, "gv": 2, "estadio": "Estadio Monumental", "arbitro": "Juan Antonio Bava", "goles": [{"jugador": "Comas", "equipo": "local", "min": 58}, {"jugador": "Castro", "equipo": "visitante", "min": 50}, {"jugador": "Batista", "equipo": "visitante", "min": 80}]},
                           ],
                      },
                      "ida_y_vuelta": True,
                      "cuadro": {"bloques": [("Rueda de ganadores: los dos primeros de cada zona. El que perdía pasaba a la "
                                              "rueda de perdedores",
                                              [["Ganadores: octavos de final"], ["Ganadores: cuartos de final"],
                                               ["Ganadores: semifinales"], ["Ganadores: final"]]),
                                             ("Rueda de perdedores: los otros dos de cada zona y, en cada fase, los que "
                                              "iban perdiendo en la rueda de ganadores. El que perdía quedaba afuera",
                                              [["Perdedores: primera fase"], ["Perdedores: segunda fase"],
                                               ["Perdedores: tercera fase"], ["Perdedores: cuarta fase"],
                                               ["Perdedores: quinta fase"], ["Perdedores: sexta fase"],
                                               ["Perdedores: final"]]),
                                             ("Final: el ganador de cada rueda. Ganó Vélez, que venía de la rueda de "
                                              "perdedores; como Argentinos no había perdido todavía, se jugó otra final",
                                              [["Final (primer partido)"], ["Final"]])],
                                 "nota": "En el Nacional no había descensos (salían de los promedios del Metropolitano). "
                                         "Argentinos ya iba a la Libertadores 1986 como campeón de la de 1985, así que "
                                         "Vélez, el subcampeón, fue a la Liguilla Pre-Libertadores 1985-86."}},
    # 1986: el Campeonato 1985-86 (julio de 1985 a abril de 1986; campeón River), el primero de agosto a mayo como en
    # Europa: 19 equipos a dos ruedas (38 fechas, en cada una quedaba uno libre), con 2 puntos por partido ganado; va
    # con el año en que terminó ("1986-temporada"). ESPN no lo tiene: va a mano (tools/a_mano; RSSSF, sin goles ni
    # estadios). Los promedios eran por temporada (los puntos de 1983, 1984 y 1985-86 divididos por las temporadas
    # jugadas: "promedios_por_temporada"; RSSSF y Wikipedia). Bajó Chacarita (el peor promedio) y el anteúltimo, Huracán,
    # jugó el Octogonal con siete de la Primera B: lo perdió con Deportivo Italiano y también bajó (RSSSF, sin goles).
    # El segundo lugar en la Libertadores 1986 lo jugaron en una Liguilla Pre-Libertadores con cinco del campeonato,
    # Vélez (subcampeón del Nacional 1985) y seis del Torneo del Interior (RSSSF, con los goles; estadios de Wikipedia;
    # ganó Boca). Argentinos fue a la Libertadores como campeón de la de 1985
    "1986-temporada": {"nombre": "Campeonato 1985-86", "anio": 1986, "liga": "a_mano", "slug": "1986-temporada",
                       "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2,
                       "campeon_tabla": True, "temporada": "1985-86",
                       "anual_texto": "La tabla del Campeonato 1985-86 (las 38 fechas; eran 19 equipos y en cada fecha uno "
                                      "quedaba libre). Cada partido ganado valía 2 puntos.",
                       "goleadores_nota": "RSSSF no tiene los goles del campeonato: la lista es solo de la Liguilla. El "
                                          "goleador del campeonato fue Enzo Francescoli (River), con 25 goles.",
                       "nombre_playoffs": "Liguilla y Octogonal",
                       "playoffs": [(r"^$^", n) for n in (
                           "Liguilla: octavos de final", "Liguilla: cuartos de final", "Liguilla: semifinales",
                           "Liguilla: final", "Octogonal: cuartos de final", "Octogonal: semifinales", "Octogonal: final",
                           "Octogonal: desempate")],
                       "playoffs_a_mano": {
                           "Liguilla: octavos de final": [
                               {"hora_utc": "1986-04-27T19:00Z", "fecha": "1986-04-27", "local": "acc", "visitante": "boca-juniors", "gl": 1, "gv": 2, "goles": [{"jugador": "González", "equipo": "local"}, {"jugador": "Graciani", "equipo": "visitante"}, {"jugador": "Higuaín", "equipo": "visitante"}], "estadio": "El Coloso del Ruca Quimey"},
                               {"hora_utc": "1986-04-27T19:00Z", "fecha": "1986-04-27", "local": "cfc", "visitante": "velez-sarsfield", "gl": 0, "gv": 3, "goles": [{"jugador": "Hernández", "equipo": "visitante"}, {"jugador": "Vanemerak", "equipo": "visitante"}, {"jugador": "Bianchi", "equipo": "visitante"}], "estadio": "Stewart Shipton"},
                               {"hora_utc": "1986-04-27T19:00Z", "fecha": "1986-04-27", "local": "ferro-carril-oeste", "visitante": "gue", "gl": 2, "gv": 1, "goles": [{"jugador": "E.González", "equipo": "local"}, {"jugador": "E.González", "equipo": "local"}, {"jugador": "Paz", "equipo": "visitante"}], "estadio": "Arquitecto Ricardo Etcheverri"},
                               {"hora_utc": "1986-04-27T19:00Z", "fecha": "1986-04-27", "local": "san-lorenzo", "visitante": "gaf", "gl": 4, "gv": 1, "goles": [{"jugador": "Perazzo", "equipo": "local"}, {"jugador": "Insúa", "equipo": "local"}, {"jugador": "Giovagnoli", "equipo": "local"}, {"jugador": "Ortega Sánchez", "equipo": "local"}, {"jugador": "Ferreyra", "equipo": "visitante"}], "estadio": "Cancha de Boca Juniors"},
                               {"hora_utc": "1986-05-04T19:00Z", "fecha": "1986-05-04", "local": "boca-juniors", "visitante": "acc", "gl": 2, "gv": 1, "goles": [{"jugador": "Krasouski", "equipo": "local"}, {"jugador": "Stafuza", "equipo": "local"}, {"jugador": "E.Sánchez", "equipo": "visitante"}], "estadio": "La Bombonera"},
                               {"hora_utc": "1986-05-04T19:00Z", "fecha": "1986-05-04", "local": "gaf", "visitante": "san-lorenzo", "gl": 0, "gv": 3, "goles": [{"jugador": "Ortega Sánchez", "equipo": "visitante"}, {"jugador": "Madelón", "equipo": "visitante"}, {"jugador": "Bica", "equipo": "visitante"}], "estadio": "Guaraní Antonio Franco"},
                               {"hora_utc": "1986-05-04T19:00Z", "fecha": "1986-05-04", "local": "gue", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 2, "goles": [{"jugador": "J.Pérez", "equipo": "local"}, {"jugador": "E.González", "equipo": "visitante"}, {"jugador": "Artime", "equipo": "visitante"}], "estadio": "Cancha de Mitre (Santiago del Estero)"},
                               {"hora_utc": "1986-05-04T19:00Z", "fecha": "1986-05-04", "local": "velez-sarsfield", "visitante": "cfc", "gl": 2, "gv": 1, "goles": [{"jugador": "Gutierrez", "equipo": "local"}, {"jugador": "Hernández", "equipo": "local"}, {"jugador": "Uribio", "equipo": "visitante"}], "estadio": "José Amalfitani"},
                           ],
                           "Liguilla: cuartos de final": [
                               {"hora_utc": "1986-05-11T19:00Z", "fecha": "1986-05-11", "local": "4", "visitante": "newell-s-old-boys", "gl": 1, "gv": 3, "goles": [{"jugador": "Scatolaro", "equipo": "local"}, {"jugador": "Llop", "equipo": "visitante"}, {"jugador": "Sen", "equipo": "visitante"}, {"jugador": "Cozzoni", "equipo": "visitante"}], "estadio": "Gigante de Alberdi"},
                               {"hora_utc": "1986-05-11T19:00Z", "fecha": "1986-05-11", "local": "boca-juniors", "visitante": "2636", "gl": 1, "gv": 1, "goles": [{"jugador": "Passucci", "equipo": "local"}, {"jugador": "Schmidt", "equipo": "visitante"}], "estadio": "La Bombonera"},
                               {"hora_utc": "1986-05-11T19:00Z", "fecha": "1986-05-11", "local": "deportivo-espanol", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 0, "estadio": "España"},
                               {"hora_utc": "1986-05-11T19:00Z", "fecha": "1986-05-11", "local": "velez-sarsfield", "visitante": "san-lorenzo", "gl": 1, "gv": 1, "goles": [{"jugador": "Hernández", "equipo": "local"}, {"jugador": "Alul", "equipo": "visitante"}], "estadio": "José Amalfitani"},
                               {"hora_utc": "1986-05-18T19:00Z", "fecha": "1986-05-18", "local": "ferro-carril-oeste", "visitante": "deportivo-espanol", "gl": 4, "gv": 1, "goles": [{"jugador": "E.González", "equipo": "local"}, {"jugador": "E.González", "equipo": "local"}, {"jugador": "Artime", "equipo": "local"}, {"jugador": "Cuper", "equipo": "local"}, {"jugador": "Rodriguez", "equipo": "visitante"}], "alargue": True, "estadio": "Arquitecto Ricardo Etcheverri"},
                               {"hora_utc": "1986-05-18T19:00Z", "fecha": "1986-05-18", "local": "newell-s-old-boys", "visitante": "4", "gl": 2, "gv": 1, "goles": [{"jugador": "Dezotti", "equipo": "local"}, {"jugador": "Cozzoni", "equipo": "local"}, {"jugador": "Celiz", "equipo": "visitante"}], "estadio": "El Coloso del Parque"},
                               {"hora_utc": "1986-05-18T19:00Z", "fecha": "1986-05-18", "local": "2636", "visitante": "boca-juniors", "gl": 2, "gv": 3, "goles": [{"jugador": "Di Pietri", "equipo": "local"}, {"jugador": "Stach", "equipo": "local"}, {"jugador": "Torres", "equipo": "visitante"}, {"jugador": "Torres", "equipo": "visitante"}, {"jugador": "Rinaldi", "equipo": "visitante"}], "alargue": True, "estadio": "Roberto N. Carminatti"},
                               {"hora_utc": "1986-05-18T19:00Z", "fecha": "1986-05-18", "local": "san-lorenzo", "visitante": "velez-sarsfield", "gl": 0, "gv": 0, "pen_l": 4, "pen_v": 3, "alargue": True, "estadio": "Cancha de Boca Juniors"},
                           ],
                           "Liguilla: semifinales": [
                               {"hora_utc": "1986-05-25T19:00Z", "fecha": "1986-05-25", "local": "newell-s-old-boys", "visitante": "ferro-carril-oeste", "gl": 1, "gv": 0, "goles": [{"jugador": "Cozzoni", "equipo": "local"}], "estadio": "El Coloso del Parque"},
                               {"hora_utc": "1986-05-25T19:00Z", "fecha": "1986-05-25", "local": "san-lorenzo", "visitante": "boca-juniors", "gl": 1, "gv": 2, "goles": [{"jugador": "Perazzo", "equipo": "local"}, {"jugador": "Graciani", "equipo": "visitante"}, {"jugador": "Passucci", "equipo": "visitante"}], "estadio": "Cancha de River Plate"},
                               {"hora_utc": "1986-05-29T19:00Z", "fecha": "1986-05-29", "local": "ferro-carril-oeste", "visitante": "newell-s-old-boys", "gl": 1, "gv": 1, "goles": [{"jugador": "Fantaguzzi", "equipo": "local"}, {"jugador": "Dezotti", "equipo": "visitante"}], "estadio": "Arquitecto Ricardo Etcheverri"},
                               {"hora_utc": "1986-06-01T19:00Z", "fecha": "1986-06-01", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 0, "gv": 0, "estadio": "La Bombonera"},
                           ],
                           "Liguilla: final": [
                               {"hora_utc": "1986-06-08T19:00Z", "fecha": "1986-06-08", "local": "boca-juniors", "visitante": "newell-s-old-boys", "gl": 0, "gv": 2, "goles": [{"jugador": "Martino", "equipo": "visitante"}, {"jugador": "Martino", "equipo": "visitante"}], "estadio": "La Bombonera"},
                               {"hora_utc": "1986-06-15T19:00Z", "fecha": "1986-06-15", "local": "newell-s-old-boys", "visitante": "boca-juniors", "gl": 1, "gv": 4, "goles": [{"jugador": "Sialle", "equipo": "local"}, {"jugador": "Graciani", "equipo": "visitante"}, {"jugador": "Graciani", "equipo": "visitante"}, {"jugador": "Torres", "equipo": "visitante"}, {"jugador": "Torres", "equipo": "visitante"}], "estadio": "El Coloso del Parque"},
                           ],
                           "Octogonal: cuartos de final": [
                               {"hora_utc": "1986-06-04T19:00Z", "fecha": "1986-06-04", "local": "huracan", "visitante": "12", "gl": 2, "gv": 0, "estadio": "Cancha de Ferro Carril Oeste"},
                               {"hora_utc": "1986-06-04T19:00Z", "fecha": "1986-06-04", "local": "lan", "visitante": "dar", "gl": 1, "gv": 0, "estadio": "Cancha de Independiente"},
                               {"hora_utc": "1986-06-04T19:00Z", "fecha": "1986-06-04", "local": "235", "visitante": "8950", "gl": 2, "gv": 0, "estadio": "Cancha de Atlanta"},
                               {"hora_utc": "1986-06-04T19:00Z", "fecha": "1986-06-04", "local": "dit", "visitante": "7767", "gl": 2, "gv": 0, "estadio": "Cancha de River Plate"},
                               {"hora_utc": "1986-06-07T19:00Z", "fecha": "1986-06-07", "local": "12", "visitante": "huracan", "gl": 2, "gv": 3, "estadio": "Cancha de River Plate"},
                               {"hora_utc": "1986-06-07T19:00Z", "fecha": "1986-06-07", "local": "dar", "visitante": "lan", "gl": 2, "gv": 2, "alargue": True, "estadio": "Cancha de Atlanta"},
                               {"hora_utc": "1986-06-07T19:00Z", "fecha": "1986-06-07", "local": "8950", "visitante": "235", "gl": 2, "gv": 2, "estadio": "Cancha de Independiente"},
                               {"hora_utc": "1986-06-07T19:00Z", "fecha": "1986-06-07", "local": "7767", "visitante": "dit", "gl": 1, "gv": 2, "estadio": "Cancha de Ferro Carril Oeste"},
                           ],
                           "Octogonal: semifinales": [
                               {"hora_utc": "1986-06-11T19:00Z", "fecha": "1986-06-11", "local": "huracan", "visitante": "lan", "gl": 1, "gv": 0, "estadio": "Cancha de Vélez Sarsfield"},
                               {"hora_utc": "1986-06-11T19:00Z", "fecha": "1986-06-11", "local": "dit", "visitante": "235", "gl": 1, "gv": 1, "estadio": "Cancha de Ferro Carril Oeste"},
                               {"hora_utc": "1986-06-14T19:00Z", "fecha": "1986-06-14", "local": "lan", "visitante": "huracan", "gl": 1, "gv": 3, "estadio": "Cancha de Independiente"},
                               {"hora_utc": "1986-06-14T19:00Z", "fecha": "1986-06-14", "local": "235", "visitante": "dit", "gl": 0, "gv": 0, "pen_l": 3, "pen_v": 4, "estadio": "Cancha de Vélez Sarsfield"},
                           ],
                           "Octogonal: final": [
                               {"hora_utc": "1986-06-18T19:00Z", "fecha": "1986-06-18", "local": "dit", "visitante": "huracan", "gl": 1, "gv": 0, "estadio": "Cancha de Ferro Carril Oeste"},
                               {"hora_utc": "1986-06-21T19:00Z", "fecha": "1986-06-21", "local": "huracan", "visitante": "dit", "gl": 2, "gv": 1, "estadio": "Cancha de Vélez Sarsfield"},
                           ],
                           "Octogonal: desempate": [
                               {"hora_utc": "1986-06-24T19:00Z", "fecha": "1986-06-24", "local": "dit", "visitante": "huracan", "gl": 2, "gv": 2, "pen_l": 4, "pen_v": 2, "estadio": "Cancha de Vélez Sarsfield"},
                           ],
                       },
                       "ida_y_vuelta": True,
                       "cuadro": {"bloques": [("Liguilla Pre-Libertadores: por el segundo lugar en la Libertadores 1986. La "
                                               "jugaron cinco del campeonato (del 2.º al 7.º, menos Argentinos, que ya iba "
                                               "como campeón de la Libertadores 1985), Vélez (subcampeón del Nacional 1985) "
                                               "y seis del Torneo del Interior",
                                               [["Liguilla: octavos de final"], ["Liguilla: cuartos de final"],
                                                ["Liguilla: semifinales"], ["Liguilla: final"]]),
                                              ("Octogonal Reclasificatorio: Huracán (el anteúltimo de los promedios) y "
                                               "siete de la Primera B, por un lugar en la Primera División",
                                               [["Octogonal: cuartos de final"], ["Octogonal: semifinales"],
                                                ["Octogonal: final"], ["Octogonal: desempate"]])],
                                  "nota": "De la Liguilla hay solo los goleadores, sin los minutos; del Octogonal, solo el "
                                          "resultado. Deportivo Italiano ganó el Octogonal: subió, y Huracán bajó."},
                       # (los puntos de cada temporada; se divide por las temporadas jugadas)
                       "promedios_por_temporada": True,
                       "promedios": {"1983": {"ferro-carril-oeste": [46, 1], "argentinos-juniors": [36, 1], "river-plate": [29, 1],
                                              "san-lorenzo": [47, 1], "velez-sarsfield": [44, 1], "newell-s-old-boys": [35, 1],
                                              "independiente": [48, 1], "estudiantes-de-la-plata": [38, 1], "boca-juniors": [37, 1],
                                              "talleres": [33, 1], "instituto": [35, 1], "union": [38, 1], "racing-cordoba": [27, 1],
                                              "platense": [34, 1], "temperley": [33, 1], "huracan": [32, 1]},
                                     "1984": {"ferro-carril-oeste": [50, 1], "argentinos-juniors": [51, 1], "river-plate": [43, 1],
                                              "san-lorenzo": [37, 1], "velez-sarsfield": [42, 1], "newell-s-old-boys": [38, 1],
                                              "independiente": [31, 1], "estudiantes-de-la-plata": [48, 1], "boca-juniors": [30, 1],
                                              "talleres": [34, 1], "instituto": [33, 1], "union": [30, 1], "racing-cordoba": [43, 1],
                                              "platense": [33, 1], "temperley": [31, 1], "huracan": [27, 1],
                                              "chacarita-juniors": [34, 1]}},
                       "descensos": "promedios", "descienden": 1, "promocion": 1,
                       "texto_promocion": "Octogonal Reclasificatorio con siete de la Primera B: Huracán lo perdió y también bajó",
                       "cupos": {"anio": 1986, "fijos": True,
                                 "libertadores": [("Campeón del Campeonato 1985-86", "river-plate"),
                                                  ("Ganador de la Liguilla Pre-Libertadores", "boca-juniors"),
                                                  ("Campeón de la Libertadores 1985", "argentinos-juniors")]}},
    # 1987: el Campeonato 1986-87 (julio de 1986 a mayo de 1987; campeón Rosario Central), a dos ruedas (38 fechas), con
    # 2 puntos por partido ganado; va con el año en que terminó ("1987-temporada"). ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles ni estadios). River-Temperley se lo dieron ganado a Temperley (doping) y
    # Estudiantes-Ferro cuenta como empate (así está en las tablas finales; ver "fuente"). Promedios de 1984 y 1985-86
    # (36 fechas cada uno; Wikipedia). Bajó Deportivo Italiano (el peor promedio) y, empatados en el promedio, Platense y
    # Temperley jugaron un desempate: bajó Temperley. El segundo lugar en la Libertadores 1987 lo jugaron en una Liguilla
    # Pre-Libertadores (RSSSF, sin goles; estadios de Wikipedia; ganó Independiente); River fue como campeón de la
    # Libertadores 1986
    "1987-temporada": {"nombre": "Campeonato 1986-87", "anio": 1987, "liga": "a_mano", "slug": "1987-temporada",
                       "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2,
                       "campeon_tabla": True, "temporada": "1986-87",
                       "anual_texto": "La tabla del Campeonato 1986-87 (las 38 fechas). Cada partido ganado valía 2 puntos.",
                       "goleadores_nota": "RSSSF no tiene los goles del campeonato ni de la Liguilla. El goleador del "
                                          "campeonato fue Omar Palma (Rosario Central), con 20 goles.",
                       "nombre_playoffs": "Liguilla Pre-Libertadores",
                       "playoffs": [(r"^$^", n) for n in ("Cuartos de final", "Semifinales", "Final de la Liguilla")],
                       "playoffs_a_mano": {
                           "Cuartos de final": [
                               {"hora_utc": "1987-05-10T19:00Z", "fecha": "1987-05-10", "local": "235", "visitante": "independiente", "gl": 1, "gv": 0, "estadio": "Cancha de Huracán"},
                               {"hora_utc": "1987-05-10T19:00Z", "fecha": "1987-05-10", "local": "4", "visitante": "newell-s-old-boys", "gl": 0, "gv": 0, "estadio": "Gigante de Alberdi"},
                               {"hora_utc": "1987-05-10T19:00Z", "fecha": "1987-05-10", "local": "dar", "visitante": "boca-juniors", "gl": 2, "gv": 4, "estadio": "Cancha de Vélez Sarsfield"},
                               {"hora_utc": "1987-05-10T19:00Z", "fecha": "1987-05-10", "local": "racing-club", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 0, "estadio": "El Cilindro"},
                               {"hora_utc": "1987-05-17T19:00Z", "fecha": "1987-05-17", "local": "boca-juniors", "visitante": "dar", "gl": 2, "gv": 2, "estadio": "La Bombonera"},
                               {"hora_utc": "1987-05-17T19:00Z", "fecha": "1987-05-17", "local": "ferro-carril-oeste", "visitante": "racing-club", "gl": 2, "gv": 1, "estadio": "Arquitecto Ricardo Etcheverri", "alargue": True},
                               {"hora_utc": "1987-05-17T19:00Z", "fecha": "1987-05-17", "local": "independiente", "visitante": "235", "gl": 2, "gv": 0, "estadio": "La Doble Visera"},
                               {"hora_utc": "1987-05-17T19:00Z", "fecha": "1987-05-17", "local": "newell-s-old-boys", "visitante": "4", "gl": 2, "gv": 0, "estadio": "El Coloso del Parque"},
                           ],
                           "Semifinales": [
                               {"hora_utc": "1987-05-24T19:00Z", "fecha": "1987-05-24", "local": "ferro-carril-oeste", "visitante": "independiente", "gl": 0, "gv": 1, "estadio": "Arquitecto Ricardo Etcheverri"},
                               {"hora_utc": "1987-05-24T19:00Z", "fecha": "1987-05-24", "local": "newell-s-old-boys", "visitante": "boca-juniors", "gl": 0, "gv": 1, "estadio": "El Coloso del Parque"},
                               {"hora_utc": "1987-05-31T19:00Z", "fecha": "1987-05-31", "local": "boca-juniors", "visitante": "newell-s-old-boys", "gl": 5, "gv": 2, "estadio": "La Bombonera"},
                               {"hora_utc": "1987-05-31T19:00Z", "fecha": "1987-05-31", "local": "independiente", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 0, "estadio": "La Doble Visera"},
                           ],
                           "Final de la Liguilla": [
                               {"hora_utc": "1987-06-07T19:00Z", "fecha": "1987-06-07", "local": "independiente", "visitante": "boca-juniors", "gl": 2, "gv": 2, "estadio": "La Doble Visera"},
                               {"hora_utc": "1987-06-14T19:00Z", "fecha": "1987-06-14", "local": "boca-juniors", "visitante": "independiente", "gl": 1, "gv": 2, "estadio": "La Bombonera"},
                           ],
                       },
                       "ida_y_vuelta": True,
                       "cuadro": {"bloques": [("Liguilla Pre-Libertadores: por el segundo lugar en la Libertadores 1987",
                                               [["Cuartos de final"], ["Semifinales"], ["Final de la Liguilla"]])],
                                  "nota": "La jugaron los que siguieron a Rosario Central en la tabla (del 2.º al 6.º) y "
                                          "tres del Nacional B: Deportivo Armenio (el campeón), Banfield y Belgrano. De los "
                                          "partidos hay solo el resultado."},
                       # (con 2 puntos por partido ganado; 1984 y 1985-86, de 36 fechas)
                       "promedios": {"1984": {"river-plate": [43, 36], "ferro-carril-oeste": [50, 36], "newell-s-old-boys": [38, 36],
                                              "argentinos-juniors": [51, 36], "san-lorenzo": [37, 36], "boca-juniors": [30, 36],
                                              "velez-sarsfield": [42, 36], "independiente": [31, 36],
                                              "estudiantes-de-la-plata": [48, 36], "instituto": [33, 36], "talleres": [34, 36],
                                              "racing-cordoba": [43, 36], "union": [30, 36], "platense": [33, 36],
                                              "temperley": [31, 36]},
                                     "1985-86": {"river-plate": [56, 36], "ferro-carril-oeste": [40, 36],
                                                 "newell-s-old-boys": [46, 36], "argentinos-juniors": [44, 36],
                                                 "san-lorenzo": [40, 36], "deportivo-espanol": [46, 36], "boca-juniors": [41, 36],
                                                 "velez-sarsfield": [34, 36], "independiente": [36, 36],
                                                 "estudiantes-de-la-plata": [27, 36], "instituto": [35, 36], "talleres": [37, 36],
                                                 "gimnasia-y-esgrima": [36, 36], "racing-cordoba": [26, 36], "union": [31, 36],
                                                 "platense": [27, 36], "temperley": [29, 36]}},
                       "descensos": "promedios", "descienden": 2,
                       "desempate_a_mano": {"fecha": "1987-05-06", "local": "platense", "visitante": "temperley",
                                            "gl": 2, "gv": 0, "estadio": "Cancha de Huracán"},
                       "desempate_texto": "Platense y Temperley terminaron empatados en los promedios, arriba de Deportivo "
                                          "Italiano (que bajó por ser el último): lo definieron en un partido, en cancha de "
                                          "Huracán, y bajó Temperley. RSSSF no tiene los goles.",
                       "cupos": {"anio": 1987, "fijos": True,
                                 "libertadores": [("Campeón del Campeonato 1986-87", "rosario-central"),
                                                  ("Ganador de la Liguilla Pre-Libertadores", "independiente"),
                                                  ("Campeón de la Libertadores 1986", "river-plate")]}},
    # 1988: el Campeonato 1987-88 (agosto de 1987 a junio de 1988; campeón Newell's), a dos ruedas (38 fechas), con 2
    # puntos por partido ganado; va con el año en que terminó ("1988-temporada"). ESPN no lo tiene: va a mano
    # (tools/a_mano; RSSSF, sin goles ni estadios). A Instituto le descontaron 2 puntos y perdió en el escritorio el
    # partido con San Lorenzo. Promedios de 1985-86 (36 fechas) y 1986-87 (Wikipedia). Bajó Banfield (el peor promedio)
    # y, empatados en el promedio, Unión y Racing de Córdoba jugaron un desempate: bajó Unión. El segundo lugar en la
    # Libertadores 1988 lo jugaron en una Liguilla Pre-Libertadores (RSSSF, sin goles; estadios de Wikipedia; ganó San
    # Lorenzo); los demás jugaron la Liguilla Clasificación, que daba un lugar en la Pre-Libertadores siguiente (Platense)
    "1988-temporada": {"nombre": "Campeonato 1987-88", "anio": 1988, "liga": "a_mano", "slug": "1988-temporada",
                       "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2,
                       "campeon_tabla": True, "temporada": "1987-88",
                       "anual_texto": "La tabla del Campeonato 1987-88 (las 38 fechas). Cada partido ganado valía 2 puntos.",
                       "goleadores_nota": "RSSSF no tiene los goles del campeonato ni de las liguillas. El goleador del "
                                          "campeonato fue José Luis Rodríguez (Deportivo Español), con 18 goles.",
                       "descuentos": {"instituto": 2},
                       "descuentos_texto": "A Instituto se le descontaron 2 puntos.",
                       "nombre_playoffs": "Liguillas",
                       "playoffs": [(r"^$^", n) for n in (
                           "Pre-Libertadores: cuartos de final", "Pre-Libertadores: semifinales", "Pre-Libertadores: final",
                           "Clasificación: octavos de final", "Clasificación: cuartos de final", "Clasificación: semifinales",
                           "Clasificación: final", "Clasificación: desempate")],
                       # (pasa: el que pasó con el global igualado)
                       "playoffs_a_mano": {
                           "Pre-Libertadores: cuartos de final": [
                               {"hora_utc": "1988-06-08T19:00Z", "fecha": "1988-06-08", "local": "argentinos-juniors", "visitante": "racing-club", "gl": 1, "gv": 1, "estadio": "Cancha de Ferro Carril Oeste"},
                               {"hora_utc": "1988-06-08T19:00Z", "fecha": "1988-06-08", "local": "dma", "visitante": "san-lorenzo", "gl": 1, "gv": 1, "estadio": "Cancha de Huracán (Corrientes)"},
                               {"hora_utc": "1988-06-08T19:00Z", "fecha": "1988-06-08", "local": "rosario-central", "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "El Gigante de Arroyito"},
                               {"hora_utc": "1988-06-08T19:00Z", "fecha": "1988-06-08", "local": "velez-sarsfield", "visitante": "gimnasia-y-esgrima", "gl": 3, "gv": 0, "estadio": "José Amalfitani"},
                               {"hora_utc": "1988-06-11T19:00Z", "fecha": "1988-06-11", "local": "racing-club", "visitante": "argentinos-juniors", "gl": 3, "gv": 1, "estadio": "El Cilindro"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "gimnasia-y-esgrima", "visitante": "velez-sarsfield", "gl": 1, "gv": 1, "estadio": "Del Bosque"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "river-plate", "visitante": "rosario-central", "gl": 1, "gv": 0, "estadio": "Monumental"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "san-lorenzo", "visitante": "dma", "gl": 1, "gv": 1, "estadio": "Cancha de Huracán", "pasa": "san-lorenzo", "nota": "Global 2-2: pasó San Lorenzo, el subcampeón, por ser de Primera (Mandiyú era el campeón del Nacional B)"},
                           ],
                           "Pre-Libertadores: semifinales": [
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "river-plate", "visitante": "racing-club", "gl": 3, "gv": 3, "estadio": "Monumental"},
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "velez-sarsfield", "visitante": "san-lorenzo", "gl": 0, "gv": 1, "estadio": "José Amalfitani"},
                               {"hora_utc": "1988-06-19T19:00Z", "fecha": "1988-06-19", "local": "san-lorenzo", "visitante": "velez-sarsfield", "gl": 0, "gv": 0, "estadio": "Cancha de Ferro Carril Oeste"},
                               {"hora_utc": "1988-06-20T19:00Z", "fecha": "1988-06-20", "local": "racing-club", "visitante": "river-plate", "gl": 1, "gv": 0, "estadio": "El Cilindro"},
                           ],
                           "Pre-Libertadores: final": [
                               {"hora_utc": "1988-06-23T19:00Z", "fecha": "1988-06-23", "local": "racing-club", "visitante": "san-lorenzo", "gl": 0, "gv": 2, "estadio": "El Cilindro"},
                               {"hora_utc": "1988-06-26T19:00Z", "fecha": "1988-06-26", "local": "san-lorenzo", "visitante": "racing-club", "gl": 0, "gv": 1, "estadio": "Cancha de Vélez Sarsfield"},
                           ],
                           "Clasificación: octavos de final": [
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "boca-juniors", "visitante": "instituto", "gl": 4, "gv": 2, "estadio": "La Bombonera"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "deportivo-armenio", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 0, "estadio": "Cancha de Platense"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "independiente", "visitante": "estudiantes-de-la-plata", "gl": 1, "gv": 2, "estadio": "La Doble Visera"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "racing-cordoba", "visitante": "platense", "gl": 1, "gv": 1, "estadio": "Miguel Sancho"},
                               {"hora_utc": "1988-06-12T19:00Z", "fecha": "1988-06-12", "local": "talleres", "visitante": "deportivo-espanol", "gl": 1, "gv": 0, "estadio": "Estadio Córdoba"},
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "deportivo-espanol", "visitante": "talleres", "gl": 2, "gv": 0, "estadio": "Cancha de Huracán"},
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "estudiantes-de-la-plata", "visitante": "independiente", "gl": 1, "gv": 2, "estadio": "Jorge Luis Hirschi", "pasa": "independiente", "nota": "Global 3-3: pasó Independiente por haber terminado mejor en el campeonato (11.º; Estudiantes, 16.º)"},
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "ferro-carril-oeste", "visitante": "deportivo-armenio", "gl": 1, "gv": 1, "estadio": "Arquitecto Ricardo Etcheverri", "pasa": "deportivo-armenio", "nota": "Global 1-1: pasó Deportivo Armenio por haber terminado mejor en el campeonato (13.º; Ferro, 14.º)"},
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "instituto", "visitante": "boca-juniors", "gl": 2, "gv": 3, "estadio": "Estadio Córdoba"},
                               {"hora_utc": "1988-06-15T19:00Z", "fecha": "1988-06-15", "local": "platense", "visitante": "racing-cordoba", "gl": 2, "gv": 0, "estadio": "Ciudad de Vicente López"},
                           ],
                           "Clasificación: cuartos de final": [
                               {"hora_utc": "1988-06-19T19:00Z", "fecha": "1988-06-19", "local": "boca-juniors", "visitante": "independiente", "gl": 2, "gv": 0, "estadio": "La Bombonera"},
                               {"hora_utc": "1988-06-19T19:00Z", "fecha": "1988-06-19", "local": "platense", "visitante": "deportivo-armenio", "gl": 1, "gv": 1, "estadio": "Ciudad de Vicente López"},
                               {"hora_utc": "1988-06-22T19:00Z", "fecha": "1988-06-22", "local": "independiente", "visitante": "boca-juniors", "gl": 2, "gv": 3, "estadio": "La Doble Visera"},
                               {"hora_utc": "1988-06-22T19:00Z", "fecha": "1988-06-22", "local": "deportivo-armenio", "visitante": "platense", "gl": 0, "gv": 0, "estadio": "Cancha de Platense", "pasa": "platense", "nota": "Global 1-1: pasó Platense por haber terminado mejor en el campeonato (10.º; Deportivo Armenio, 13.º)"},
                           ],
                           "Clasificación: semifinales": [
                               {"hora_utc": "1988-06-26T19:00Z", "fecha": "1988-06-26", "local": "deportivo-espanol", "visitante": "boca-juniors", "gl": 0, "gv": 4, "estadio": "España"},
                               {"hora_utc": "1988-06-29T19:00Z", "fecha": "1988-06-29", "local": "boca-juniors", "visitante": "deportivo-espanol", "gl": 1, "gv": 1, "estadio": "La Bombonera"},
                           ],
                           "Clasificación: final": [
                               {"hora_utc": "1988-07-03T19:00Z", "fecha": "1988-07-03", "local": "boca-juniors", "visitante": "platense", "gl": 0, "gv": 0, "estadio": "La Bombonera"},
                               {"hora_utc": "1988-07-07T19:00Z", "fecha": "1988-07-07", "local": "platense", "visitante": "boca-juniors", "gl": 1, "gv": 1, "estadio": "Estadio Ciudad de Vicente López"},
                           ],
                           "Clasificación: desempate": [
                               {"hora_utc": "1988-07-10T19:00Z", "fecha": "1988-07-10", "local": "boca-juniors", "visitante": "platense", "gl": 1, "gv": 2, "estadio": "Cancha de Ferro Carril Oeste"},
                           ],
                       },
                       "ida_y_vuelta": True,
                       "cuadro": {"bloques": [("Liguilla Pre-Libertadores: por el segundo lugar en la Libertadores 1988. La "
                                               "jugaron los que siguieron a Newell's en la tabla (del 2.º al 8.º) y "
                                               "Deportivo Mandiyú (campeón del Nacional B)",
                                               [["Pre-Libertadores: cuartos de final"], ["Pre-Libertadores: semifinales"],
                                                ["Pre-Libertadores: final"]]),
                                              ("Liguilla Clasificación: los demás (menos los que bajaron), por un lugar en "
                                               "la Liguilla Pre-Libertadores siguiente",
                                               [["Clasificación: octavos de final"], ["Clasificación: cuartos de final"],
                                                ["Clasificación: semifinales"], ["Clasificación: final"],
                                                ["Clasificación: desempate"]])],
                                  "nota": "Con el global igualado pasaba el que había hecho más diferencia de gol y, si "
                                          "no, el que había terminado mejor en el campeonato. De los partidos hay solo el "
                                          "resultado."},
                       # (con 2 puntos por partido ganado; 1985-86, de 36 fechas)
                       "promedios": {"1985-86": {"newell-s-old-boys": [46, 36], "river-plate": [56, 36], "san-lorenzo": [40, 36],
                                                 "boca-juniors": [41, 36], "deportivo-espanol": [46, 36], "independiente": [36, 36],
                                                 "ferro-carril-oeste": [40, 36], "gimnasia-y-esgrima": [36, 36],
                                                 "velez-sarsfield": [34, 36], "argentinos-juniors": [44, 36], "instituto": [35, 36],
                                                 "talleres": [37, 36], "estudiantes-de-la-plata": [27, 36], "platense": [27, 36],
                                                 "racing-cordoba": [26, 36], "union": [31, 36]},
                                     "1986-87": {"newell-s-old-boys": [48, 38], "river-plate": [39, 38], "racing-club": [44, 38],
                                                 "san-lorenzo": [44, 38], "rosario-central": [49, 38], "boca-juniors": [46, 38],
                                                 "deportivo-espanol": [36, 38], "independiente": [47, 38],
                                                 "ferro-carril-oeste": [44, 38], "gimnasia-y-esgrima": [37, 38],
                                                 "velez-sarsfield": [41, 38], "argentinos-juniors": [28, 38], "instituto": [41, 38],
                                                 "talleres": [38, 38], "estudiantes-de-la-plata": [37, 38], "platense": [27, 38],
                                                 "racing-cordoba": [33, 38], "union": [31, 38]}},
                       "descensos": "promedios", "descienden": 2,
                       "desempate_a_mano": {"fecha": "1988-06-08", "local": "union", "visitante": "racing-cordoba",
                                            "gl": 1, "gv": 1, "alargue": True, "pen_l": 4, "pen_v": 5, "estadio": "La Bombonera"},
                       "desempate_texto": "Unión y Racing de Córdoba terminaron empatados en los promedios, arriba de "
                                          "Banfield (que bajó por ser el último): lo definieron en un partido, en cancha de "
                                          "Boca, y bajó Unión (perdió por penales).",
                       "cupos": {"anio": 1988, "fijos": True,
                                 "libertadores": [("Campeón del Campeonato 1987-88", "newell-s-old-boys"),
                                                  ("Ganador de la Liguilla Pre-Libertadores", "san-lorenzo")]}},
    # 1989: el Campeonato 1988-89 (septiembre de 1988 a mayo de 1989; campeón Independiente), a dos ruedas (38 fechas),
    # con una regla propia: 3 puntos por partido ganado, 1 por el empate y, después de cada empate, penales que le daban
    # un punto más al ganador ("punto_penales"); va con el año en que terminó ("1989-temporada"). ESPN no lo tiene: va
    # a mano (tools/a_mano; RSSSF, sin goles ni estadios; dos penales corregidos, ver "fuente"). A Racing, Newell's,
    # Rosario Central y San Martín de Tucumán les descontaron 2 puntos; Newell's-Rosario lo perdieron los dos y
    # Racing-Boca lo perdió Racing. Promedios de 1986-87 y 1987-88 (RSSSF): para los promedios, 2 puntos por partido
    # ganado y sin el punto de los penales ("promedios_victoria", con los descuentos). Bajaron los dos peores promedios
    # (San Martín de Tucumán y Deportivo Armenio). El segundo lugar en la Libertadores 1990 lo jugaron en una Liguilla
    # Pre-Libertadores con doble eliminación (RSSSF, con los goles; estadios de Wikipedia; ganó River)
    "1989-temporada": {"nombre": "Campeonato 1988-89", "anio": 1989, "liga": "a_mano", "slug": "1989-temporada",
                       "zonas": "unica", "fechas": 38, "pasan": 0, "punto_penales": True,
                       "campeon_tabla": True, "temporada": "1988-89",
                       "anual_texto": "La tabla del Campeonato 1988-89 (las 38 fechas). Cada partido ganado valía 3 puntos "
                                      "y el empate 1, más 1 para el que ganaba los penales después del empate.",
                       "goleadores_nota": "RSSSF no tiene los goles del campeonato: la lista es solo de la Liguilla. Los "
                                          "goleadores del campeonato fueron Oscar Dertycia (Argentinos) y Néstor Gorosito "
                                          "(San Lorenzo), con 20 goles.",
                       "descuentos": {"racing-club": 2, "newell-s-old-boys": 2, "rosario-central": 2, "san-martin-tucuman": 2},
                       "descuentos_texto": "A Racing, a Newell's, a Rosario Central y a San Martín de Tucumán se les "
                                           "descontaron 2 puntos.",
                       "nombre_playoffs": "Liguilla Pre-Libertadores",
                       "playoffs": [(r"^$^", n) for n in (
                           "Octogonal: cuartos de final", "Octogonal: semifinales", "Octogonal: final",
                           "Clasificación: primera fase", "Clasificación: segunda fase", "Clasificación: tercera fase",
                           "Clasificación: cuarta fase", "Clasificación: quinta fase", "Clasificación: final",
                           "Clasificación: desempate", "Final por la Libertadores 1990")],
                       # (pasa: el que pasó con el global igualado, por haber terminado mejor en el campeonato)
                       "playoffs_a_mano": {
                           "Octogonal: cuartos de final": [
                               {"hora_utc": "1989-06-03T19:00Z", "fecha": "1989-06-03", "local": "cfe", "visitante": "boca-juniors", "gl": 0, "gv": 1, "estadio": "Juan Alberto García", "goles": [{"jugador": "Stafuza", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-04T19:00Z", "fecha": "1989-06-04", "local": "argentinos-juniors", "visitante": "river-plate", "gl": 2, "gv": 0, "estadio": "José Amalfitani", "goles": [{"jugador": "Dertycia", "equipo": "local"}, {"jugador": "Ereros", "equipo": "local"}]},
                               {"hora_utc": "1989-06-04T19:00Z", "fecha": "1989-06-04", "local": "platense", "visitante": "deportivo-espanol", "gl": 0, "gv": 0, "estadio": "Ciudad de Vicente López"},
                               {"hora_utc": "1989-06-04T19:00Z", "fecha": "1989-06-04", "local": "talleres", "visitante": "san-lorenzo", "gl": 0, "gv": 2, "estadio": "La Boutique", "goles": [{"jugador": "Ahmed", "equipo": "visitante"}, {"jugador": "Ferreyra", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "boca-juniors", "visitante": "cfe", "gl": 2, "gv": 1, "estadio": "La Bombonera", "goles": [{"jugador": "Latorre", "equipo": "local"}, {"jugador": "Latorre", "equipo": "local"}, {"jugador": "Fernández", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "deportivo-espanol", "visitante": "platense", "gl": 1, "gv": 3, "estadio": "España", "goles": [{"jugador": "Correa", "equipo": "local"}, {"jugador": "De Vicente", "equipo": "visitante"}, {"jugador": "Espina", "equipo": "visitante"}, {"jugador": "Spontón", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "river-plate", "visitante": "argentinos-juniors", "gl": 1, "gv": 0, "estadio": "Monumental", "goles": [{"jugador": "Centurión", "equipo": "local"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "san-lorenzo", "visitante": "talleres", "gl": 1, "gv": 1, "estadio": "Tomás Adolfo Ducó", "goles": [{"jugador": "Zacarías", "equipo": "local"}, {"jugador": "Cañete", "equipo": "visitante"}]},
                           ],
                           "Octogonal: semifinales": [
                               {"hora_utc": "1989-06-11T19:00Z", "fecha": "1989-06-11", "local": "boca-juniors", "visitante": "platense", "gl": 1, "gv": 1, "estadio": "La Bombonera", "goles": [{"jugador": "Graciani", "equipo": "local"}, {"jugador": "Boldrini", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-11T19:00Z", "fecha": "1989-06-11", "local": "san-lorenzo", "visitante": "argentinos-juniors", "gl": 1, "gv": 0, "estadio": "Tomás Adolfo Ducó", "goles": [{"jugador": "Gorosito", "equipo": "local"}]},
                               {"hora_utc": "1989-06-14T19:00Z", "fecha": "1989-06-14", "local": "argentinos-juniors", "visitante": "san-lorenzo", "gl": 1, "gv": 3, "estadio": "Arquitecto Ricardo Etcheverri", "goles": [{"jugador": "Cáceres", "equipo": "local"}, {"jugador": "Gorosito", "equipo": "visitante"}, {"jugador": "Acosta", "equipo": "visitante"}, {"jugador": "Acosta", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-14T19:00Z", "fecha": "1989-06-14", "local": "platense", "visitante": "boca-juniors", "gl": 1, "gv": 1, "estadio": "José Amalfitani", "goles": [{"jugador": "De Vicente", "equipo": "local"}, {"jugador": "Latorre", "equipo": "visitante"}], "pasa": "boca-juniors", "nota": "Global 2-2: pasó Boca por haber terminado mejor en el campeonato (2.º; Platense, 15.º)"},
                           ],
                           "Octogonal: final": [
                               {"hora_utc": "1989-06-16T19:00Z", "fecha": "1989-06-16", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 1, "gv": 1, "estadio": "La Bombonera", "goles": [{"jugador": "Graciani", "equipo": "local"}, {"jugador": "Gorosito", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-22T19:00Z", "fecha": "1989-06-22", "local": "san-lorenzo", "visitante": "boca-juniors", "gl": 4, "gv": 0, "estadio": "Tomás Adolfo Ducó", "goles": [{"jugador": "Gorosito", "equipo": "local"}, {"jugador": "Acosta", "equipo": "local"}, {"jugador": "Acosta", "equipo": "local"}, {"jugador": "Siviski", "equipo": "local"}]},
                           ],
                           "Clasificación: primera fase": [
                               {"hora_utc": "1989-06-03T19:00Z", "fecha": "1989-06-03", "local": "racing-cordoba", "visitante": "gimnasia-y-esgrima", "gl": 0, "gv": 0, "estadio": "Miguel Sancho"},
                               {"hora_utc": "1989-06-04T19:00Z", "fecha": "1989-06-04", "local": "deportivo-mandiyu", "visitante": "velez-sarsfield", "gl": 1, "gv": 1, "estadio": "Huracán Corrientes", "goles": [{"jugador": "Blanchart", "equipo": "local"}, {"jugador": "Simeone", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-04T19:00Z", "fecha": "1989-06-04", "local": "estudiantes-de-la-plata", "visitante": "instituto", "gl": 0, "gv": 0, "estadio": "Jorge Luis Hirschi"},
                               {"hora_utc": "1989-06-04T19:00Z", "fecha": "1989-06-04", "local": "racing-club", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 1, "estadio": "El Cilindro", "goles": [{"jugador": "Agonil", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-11T19:00Z", "fecha": "1989-06-11", "local": "rosario-central", "visitante": "newell-s-old-boys", "gl": 1, "gv": 1, "estadio": "José Amalfitani", "goles": [{"jugador": "Escudero", "equipo": "local"}, {"jugador": "Martino", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "ferro-carril-oeste", "visitante": "racing-club", "gl": 0, "gv": 0, "estadio": "Arquitecto Ricardo Etcheverri"},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "gimnasia-y-esgrima", "visitante": "racing-cordoba", "gl": 2, "gv": 0, "estadio": "Del Bosque", "goles": [{"jugador": "Airez", "equipo": "local"}, {"jugador": "Güendulain", "equipo": "local"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "instituto", "visitante": "estudiantes-de-la-plata", "gl": 1, "gv": 0, "estadio": "Juan Domingo Perón", "goles": [{"jugador": "Giovagnoli", "equipo": "local"}]},
                               {"hora_utc": "1989-06-07T19:00Z", "fecha": "1989-06-07", "local": "velez-sarsfield", "visitante": "deportivo-mandiyu", "gl": 0, "gv": 3, "estadio": "José Amalfitani", "goles": [{"jugador": "Blanchart", "equipo": "visitante"}, {"jugador": "Blanchart", "equipo": "visitante"}, {"jugador": "Leani", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-13T19:00Z", "fecha": "1989-06-13", "local": "newell-s-old-boys", "visitante": "rosario-central", "gl": 5, "gv": 3, "estadio": "Arquitecto Ricardo Etcheverri", "goles": [{"jugador": "Taffarel", "equipo": "local"}, {"jugador": "Taffarel", "equipo": "local"}, {"jugador": "Batistuta", "equipo": "local"}, {"jugador": "Batistuta", "equipo": "local"}, {"jugador": "Ramos", "equipo": "local"}, {"jugador": "Llop", "equipo": "visitante", "tipo": "ec"}, {"jugador": "Pizzi", "equipo": "visitante"}, {"jugador": "Bauza", "equipo": "visitante"}]},
                           ],
                           "Clasificación: segunda fase": [
                               {"hora_utc": "1989-06-11T19:00Z", "fecha": "1989-06-11", "local": "cfe", "visitante": "river-plate", "gl": 1, "gv": 5, "estadio": "Juan Alberto García", "goles": [{"jugador": "Sosa", "equipo": "local"}, {"jugador": "Batista", "equipo": "visitante"}, {"jugador": "Bevilaqua", "equipo": "visitante"}, {"jugador": "Borrelli", "equipo": "visitante"}, {"jugador": "Borrelli", "equipo": "visitante"}, {"jugador": "Beltramo", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-11T19:00Z", "fecha": "1989-06-11", "local": "ferro-carril-oeste", "visitante": "gimnasia-y-esgrima", "gl": 1, "gv": 4, "estadio": "Arquitecto Ricardo Etcheverri", "goles": [{"jugador": "Marchesini", "equipo": "local"}, {"jugador": "Airez", "equipo": "visitante"}, {"jugador": "Airez", "equipo": "visitante"}, {"jugador": "Gambier", "equipo": "visitante"}, {"jugador": "Gambier", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-11T19:00Z", "fecha": "1989-06-11", "local": "talleres", "visitante": "instituto", "gl": 2, "gv": 1, "estadio": "La Boutique", "goles": [{"jugador": "Pochettino", "equipo": "local"}, {"jugador": "Commiso", "equipo": "local"}, {"jugador": "Giovagnoli", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-18T19:00Z", "fecha": "1989-06-18", "local": "deportivo-mandiyu", "visitante": "newell-s-old-boys", "gl": 2, "gv": 1, "estadio": "Huracán Corrientes", "goles": [{"jugador": "Attadía", "equipo": "local"}, {"jugador": "L.Ramos", "equipo": "local"}, {"jugador": "Batistuta", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-14T19:00Z", "fecha": "1989-06-14", "local": "gimnasia-y-esgrima", "visitante": "ferro-carril-oeste", "gl": 0, "gv": 1, "estadio": "Del Bosque", "goles": [{"jugador": "Marchesini", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-14T19:00Z", "fecha": "1989-06-14", "local": "instituto", "visitante": "talleres", "gl": 1, "gv": 3, "estadio": "Juan Domingo Perón", "goles": [{"jugador": "Cozzoni", "equipo": "local"}, {"jugador": "Cañete", "equipo": "visitante"}, {"jugador": "Cañete", "equipo": "visitante"}, {"jugador": "Pochettino", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-14T19:00Z", "fecha": "1989-06-14", "local": "river-plate", "visitante": "cfe", "gl": 1, "gv": 1, "estadio": "Monumental", "goles": [{"jugador": "Zamora", "equipo": "local"}, {"jugador": "Di Marco", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-21T19:00Z", "fecha": "1989-06-21", "local": "newell-s-old-boys", "visitante": "deportivo-mandiyu", "gl": 2, "gv": 1, "estadio": "El Coloso del Parque", "goles": [{"jugador": "V.Ramos", "equipo": "local"}, {"jugador": "V.Ramos", "equipo": "local"}, {"jugador": "Leani", "equipo": "visitante"}], "pasa": "newell-s-old-boys", "nota": "Global 3-3: pasó Newell's por haber terminado mejor en el campeonato (12.º; Mandiyú, 14.º)"},
                           ],
                           "Clasificación: tercera fase": [
                               {"hora_utc": "1989-06-18T19:00Z", "fecha": "1989-06-18", "local": "deportivo-espanol", "visitante": "platense", "gl": 0, "gv": 0, "estadio": "España"},
                               {"hora_utc": "1989-06-18T19:00Z", "fecha": "1989-06-18", "local": "gimnasia-y-esgrima", "visitante": "argentinos-juniors", "gl": 1, "gv": 1, "estadio": "Del Bosque", "goles": [{"jugador": "Airez", "equipo": "local"}, {"jugador": "Dertycia", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-25T19:00Z", "fecha": "1989-06-25", "local": "newell-s-old-boys", "visitante": "talleres", "gl": 0, "gv": 0, "estadio": "Coloso del Parque"},
                               {"hora_utc": "1989-06-22T19:00Z", "fecha": "1989-06-22", "local": "argentinos-juniors", "visitante": "gimnasia-y-esgrima", "gl": 4, "gv": 1, "estadio": "Arquitecto Ricardo Etcheverri", "goles": [{"jugador": "Trapasso", "equipo": "local"}, {"jugador": "Rudman", "equipo": "local"}, {"jugador": "Castillo", "equipo": "local"}, {"jugador": "Castillo", "equipo": "local"}, {"jugador": "Güendulain", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-22T19:00Z", "fecha": "1989-06-22", "local": "platense", "visitante": "deportivo-espanol", "gl": 1, "gv": 4, "estadio": "Ciudad de Vicente López", "goles": [{"jugador": "Boldrini", "equipo": "local"}, {"jugador": "Gaona", "equipo": "visitante"}, {"jugador": "González", "equipo": "visitante"}, {"jugador": "González", "equipo": "visitante"}, {"jugador": "Ortega", "equipo": "visitante"}]},
                               {"hora_utc": "1989-06-28T19:00Z", "fecha": "1989-06-28", "local": "talleres", "visitante": "newell-s-old-boys", "gl": 0, "gv": 1, "estadio": "Miguel Sancho", "goles": [{"jugador": "Taffarel", "equipo": "visitante"}]},
                           ],
                           "Clasificación: cuarta fase": [
                               {"hora_utc": "1989-07-02T19:00Z", "fecha": "1989-07-02", "local": "argentinos-juniors", "visitante": "river-plate", "gl": 0, "gv": 1, "estadio": "José Amalfitani", "goles": [{"jugador": "Centurión", "equipo": "visitante"}]},
                               {"hora_utc": "1989-07-02T19:00Z", "fecha": "1989-07-02", "local": "newell-s-old-boys", "visitante": "deportivo-espanol", "gl": 0, "gv": 1, "estadio": "Coloso del Parque", "goles": [{"jugador": "Caviglia", "equipo": "visitante"}]},
                               {"hora_utc": "1989-07-05T19:00Z", "fecha": "1989-07-05", "local": "deportivo-espanol", "visitante": "newell-s-old-boys", "gl": 0, "gv": 0, "estadio": "España"},
                               {"hora_utc": "1989-07-05T19:00Z", "fecha": "1989-07-05", "local": "river-plate", "visitante": "argentinos-juniors", "gl": 4, "gv": 0, "estadio": "Monumental", "goles": [{"jugador": "Passarella", "equipo": "local"}, {"jugador": "Centurión", "equipo": "local"}, {"jugador": "Centurión", "equipo": "local"}, {"jugador": "Zamora", "equipo": "local"}]},
                           ],
                           "Clasificación: quinta fase": [
                               {"hora_utc": "1989-07-12T19:00Z", "fecha": "1989-07-12", "local": "river-plate", "visitante": "deportivo-espanol", "gl": 1, "gv": 0, "estadio": "Monumental", "goles": [{"jugador": "Gordillo", "equipo": "local"}]},
                               {"hora_utc": "1989-07-16T19:00Z", "fecha": "1989-07-16", "local": "deportivo-espanol", "visitante": "river-plate", "gl": 0, "gv": 1, "estadio": "José Amalfitani", "goles": [{"jugador": "Zamora", "equipo": "visitante"}]},
                           ],
                           "Clasificación: final": [
                               {"hora_utc": "1989-07-19T19:00Z", "fecha": "1989-07-19", "local": "river-plate", "visitante": "boca-juniors", "gl": 0, "gv": 0, "estadio": "Monumental"},
                               {"hora_utc": "1989-07-24T19:00Z", "fecha": "1989-07-24", "local": "boca-juniors", "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "La Bombonera"},
                           ],
                           "Clasificación: desempate": [
                               {"hora_utc": "1989-07-27T19:00Z", "fecha": "1989-07-27", "local": "boca-juniors", "visitante": "river-plate", "gl": 1, "gv": 2, "estadio": "José Amalfitani", "goles": [{"jugador": "Marangoni", "equipo": "local"}, {"jugador": "Serrizuela", "equipo": "visitante"}, {"jugador": "Centurión", "equipo": "visitante"}]},
                           ],
                           "Final por la Libertadores 1990": [
                               {"hora_utc": "1989-09-27T19:00Z", "fecha": "1989-09-27", "local": "san-lorenzo", "visitante": "river-plate", "gl": 0, "gv": 1, "estadio": "Tomás Adolfo Ducó", "goles": [{"jugador": "Batistuta", "equipo": "visitante"}]},
                               {"hora_utc": "1989-10-31T19:00Z", "fecha": "1989-10-31", "local": "river-plate", "visitante": "san-lorenzo", "gl": 0, "gv": 0, "estadio": "Monumental"},
                           ],
                       },
                       "ida_y_vuelta": True,
                       "cuadro": {"bloques": [("Torneo Octogonal (la rueda de ganadores): los seis primeros, Chaco For "
                                               "Ever (campeón del Nacional B) y Platense (ganador del Clasificación "
                                               "1987-88). El que perdía pasaba al Clasificación",
                                               [["Octogonal: cuartos de final"], ["Octogonal: semifinales"],
                                                ["Octogonal: final"]]),
                                              ("Torneo Clasificación (la rueda de perdedores): los otros doce del "
                                               "campeonato y los que perdían en el Octogonal",
                                               [["Clasificación: primera fase"], ["Clasificación: segunda fase"],
                                                ["Clasificación: tercera fase"], ["Clasificación: cuarta fase"],
                                                ["Clasificación: quinta fase"], ["Clasificación: final"],
                                                ["Clasificación: desempate"]]),
                                              ("Por el segundo lugar en la Libertadores 1990: el ganador del Octogonal "
                                               "contra el del Clasificación", [["Final por la Libertadores 1990"]])],
                                  "nota": "Con el global igualado pasaba el que había hecho más diferencia de gol y, si "
                                          "no, el que había terminado mejor en el campeonato. De los partidos hay solo "
                                          "los goleadores, sin los minutos."},
                       "promedios_victoria": 2,
                       # (con 2 puntos por partido ganado)
                       "promedios": {"1986-87": {"independiente": [47, 38], "newell-s-old-boys": [48, 38], "san-lorenzo": [44, 38],
                                                 "racing-club": [44, 38], "boca-juniors": [46, 38], "river-plate": [39, 38],
                                                 "rosario-central": [49, 38], "deportivo-espanol": [36, 38],
                                                 "gimnasia-y-esgrima": [37, 38], "velez-sarsfield": [41, 38],
                                                 "estudiantes-de-la-plata": [37, 38], "argentinos-juniors": [28, 38],
                                                 "talleres": [38, 38], "ferro-carril-oeste": [44, 38], "platense": [27, 38],
                                                 "instituto": [41, 38], "racing-cordoba": [33, 38]},
                                     "1987-88": {"independiente": [37, 38], "newell-s-old-boys": [55, 38], "san-lorenzo": [49, 38],
                                                 "racing-club": [48, 38], "boca-juniors": [35, 38], "river-plate": [46, 38],
                                                 "rosario-central": [40, 38], "deportivo-espanol": [40, 38],
                                                 "gimnasia-y-esgrima": [43, 38], "velez-sarsfield": [41, 38],
                                                 "estudiantes-de-la-plata": [32, 38], "argentinos-juniors": [40, 38],
                                                 "talleres": [27, 38], "ferro-carril-oeste": [33, 38], "platense": [38, 38],
                                                 "instituto": [33, 38], "racing-cordoba": [31, 38], "deportivo-armenio": [34, 38]}},
                       "descensos": "promedios", "descienden": 2,
                       "cupos": {"anio": 1990, "fijos": True,
                                 "libertadores": [("Campeón del Campeonato 1988-89", "independiente"),
                                                  ("Ganador de la Liguilla Pre-Libertadores", "river-plate")],
                                 "nota": "Los dos lugares en la Libertadores 1989 salieron de la primera rueda (el Torneo "
                                         "Apertura 1988-89): Racing y Boca, los dos primeros de esas 19 fechas."}},
    # 1990: el Campeonato 1989-90 (agosto de 1989 a mayo de 1990; campeón River) fue el último de una sola tabla, a
    # dos ruedas (38 fechas), con 2 puntos por partido ganado; va con el año en que terminó ("1990-temporada"). ESPN no
    # lo tiene: va a mano (tools/a_mano; RSSSF, sin goles; Wikipedia, solo las fechas 1 a 8, con día y estadio). A
    # Talleres, Rosario Central y Newell's les descontaron 2 puntos, y Rosario-Newell's lo perdieron los dos. Promedios de
    # 1987-88 y 1988-89 (RSSSF y Wikipedia; 1988-89 sin el punto extra de los penales). Bajó Instituto (el último) y,
    # empatados en el promedio, Chaco For Ever y Racing de Córdoba jugaron un desempate: bajó Racing. El segundo lugar en
    # la Libertadores 1991 lo jugaron en una Liguilla Pre-Libertadores (RSSSF y Wikipedia; ganó Boca)
    "1990-temporada": {"nombre": "Campeonato 1989-90", "anio": 1990, "liga": "a_mano", "slug": "1990-temporada",
                       "zonas": "unica", "fechas": 38, "pasan": 0, "puntos_victoria": 2,
                       "campeon_tabla": True, "temporada": "1989-90",
                       "anual_texto": "La tabla del Campeonato 1989-90 (las 38 fechas). Cada partido ganado valía 2 puntos.",
                       "goleadores_nota": "RSSSF no tiene los goles del campeonato: la lista es solo de la Liguilla. El "
                                          "goleador del campeonato fue Ariel Cozzoni (Newell's), con 23 goles.",
                       "descuentos": {"talleres": 2, "rosario-central": 2, "newell-s-old-boys": 2},
                       "descuentos_texto": "A Talleres, a Rosario Central y a Newell's se les descontaron 2 puntos.",
                       "nombre_playoffs": "Liguilla Pre-Libertadores",
                       "playoffs": [(r"^$^", n) for n in ("Semifinales", "Final de la Liguilla")],
                       "playoffs_a_mano": {
                           "Semifinales": [
                               {"hora_utc": "1990-05-27T19:00Z", "fecha": "1990-05-27", "local": "boca-juniors", "visitante": "deportivo-espanol", "gl": 1, "gv": 0, "estadio": "La Bombonera", "goles": [{"jugador": "Abramovich", "equipo": "local"}]},
                               {"hora_utc": "1990-05-27T19:00Z", "fecha": "1990-05-27", "local": "independiente", "visitante": "rosario-central", "gl": 1, "gv": 1, "estadio": "La Doble Visera", "goles": [{"jugador": "Alfaro Moreno", "equipo": "local"}, {"jugador": "Pizzi", "equipo": "visitante"}]},
                               {"hora_utc": "1990-05-30T19:00Z", "fecha": "1990-05-30", "local": "rosario-central", "visitante": "independiente", "gl": 1, "gv": 3, "estadio": "Gigante de Arroyito", "alargue": True, "goles": [{"jugador": "Pizzi", "equipo": "local"}, {"jugador": "Alfaro Moreno", "equipo": "visitante"}, {"jugador": "Alfaro Moreno", "equipo": "visitante"}, {"jugador": "Villarreal", "equipo": "visitante"}]},
                               {"hora_utc": "1990-05-31T19:00Z", "fecha": "1990-05-31", "local": "deportivo-espanol", "visitante": "boca-juniors", "gl": 1, "gv": 1, "estadio": "Cancha de Vélez Sarsfield", "goles": [{"jugador": "Parodi", "equipo": "local"}, {"jugador": "Graciani", "equipo": "visitante"}]},
                           ],
                           "Final de la Liguilla": [
                               {"hora_utc": "1990-06-03T19:00Z", "fecha": "1990-06-03", "local": "boca-juniors", "visitante": "independiente", "gl": 1, "gv": 0, "goles": [{"jugador": "Pico", "equipo": "local"}]},
                               {"hora_utc": "1990-06-06T19:00Z", "fecha": "1990-06-06", "local": "independiente", "visitante": "boca-juniors", "gl": 0, "gv": 1, "goles": [{"jugador": "Latorre", "equipo": "visitante"}]},
                           ],
                       },
                       "ida_y_vuelta": True,
                       "cuadro": {"bloques": [("Liguilla Pre-Libertadores: por el segundo lugar en la Libertadores 1991",
                                               [["Semifinales"], ["Final de la Liguilla"]])],
                                  "nota": "La jugaron Independiente (el mejor de la primera rueda), Boca y Rosario Central "
                                          "(los que siguieron a River en la tabla) y Deportivo Español. De los partidos hay "
                                          "solo los goleadores, sin los minutos."},
                       # (con 2 puntos por partido ganado)
                       "promedios": {"1987-88": {"river-plate": [46, 38], "independiente": [37, 38], "boca-juniors": [35, 38],
                                                 "racing-club": [48, 38], "san-lorenzo": [49, 38],
                                                 "newell-s-old-boys": [55, 38], "argentinos-juniors": [40, 38],
                                                 "gimnasia-y-esgrima": [43, 38], "deportivo-espanol": [40, 38],
                                                 "rosario-central": [40, 38], "velez-sarsfield": [41, 38],
                                                 "estudiantes-de-la-plata": [32, 38], "platense": [38, 38], "talleres": [27, 38],
                                                 "ferro-carril-oeste": [33, 38], "racing-cordoba": [31, 38], "instituto": [33, 38]},
                                     "1988-89": {"river-plate": [45, 38], "independiente": [55, 38], "boca-juniors": [49, 38],
                                                 "racing-club": [40, 38], "san-lorenzo": [42, 38],
                                                 "newell-s-old-boys": [33, 38], "argentinos-juniors": [42, 38],
                                                 "gimnasia-y-esgrima": [36, 38], "deportivo-espanol": [46, 38],
                                                 "rosario-central": [34, 38], "velez-sarsfield": [33, 38],
                                                 "estudiantes-de-la-plata": [42, 38], "platense": [33, 38], "talleres": [44, 38],
                                                 "deportivo-mandiyu": [33, 38], "ferro-carril-oeste": [30, 38],
                                                 "racing-cordoba": [33, 38], "instituto": [23, 38]}},
                       "descensos": "promedios", "descienden": 2,
                       "desempate_a_mano": {"fecha": "1990-05-25", "local": "chaco-for-ever", "visitante": "racing-cordoba",
                                            "gl": 5, "gv": 0, "estadio": "La Bombonera",
                                            "goles": [{"jugador": "Ortolá", "equipo": "local"},
                                                      {"jugador": "Scatolaro", "equipo": "local"},
                                                      {"jugador": "Scatolaro", "equipo": "local"},
                                                      {"jugador": "Salaberry", "equipo": "local"}]},
                       "desempate_texto": "Chaco For Ever y Racing de Córdoba terminaron empatados en los promedios, arriba "
                                          "de Instituto (que bajó por ser el último): lo definieron en un partido, en cancha "
                                          "de Boca, y bajó Racing. RSSSF tiene solo cuatro de los cinco goles de Chaco.",
                       "cupos": {"anio": 1991, "fijos": True,
                                 "libertadores": [("Campeón del Campeonato 1989-90", "river-plate"),
                                                  ("Ganador de la Liguilla Pre-Libertadores", "boca-juniors")]}},
    # El Torneo Apertura 1990 (agosto-diciembre; campeón Newell's) abría la temporada 1990-91, que se jugó en dos
    # torneos con una final entre los campeones (ver el Clausura 1991). Boca y San Lorenzo perdieron los dos el
    # partido entre ellos. Los goles, de RSSSF (sin minutos)
    "1990-apertura": {"nombre": "Torneo Apertura 1990", "anio": 1990, "liga": "a_mano", "slug": "1990-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "goleadores_nota": "Goles de RSSSF, sin minutos.",
                      "sin_descensos": "En el Torneo Apertura 1990 no hubo descensos: se definieron al terminar la "
                                       "temporada 1990-91, con el Torneo Clausura 1991. El campeón de la temporada salió de "
                                       "una final entre Newell's y Boca, el campeón del Clausura."},
    # 1991: dos torneos de 20 equipos a una rueda, con 2 puntos por partido ganado; ESPN no los tiene: van a mano
    # (tools/a_mano; RSSSF; Wikipedia no tiene los partidos del Clausura ni estadios ni días del Apertura). El Torneo
    # Clausura 1991 (febrero-junio; campeón Boca, invicto) cerraba la temporada 1990-91, que era un solo campeonato: su
    # campeón salió de una final entre los ganadores del Apertura 1990 (Newell's) y del Clausura (Boca), y ganó Newell's
    # por penales. El segundo lugar en la Libertadores 1992 lo jugaron en una Liguilla Pre-Libertadores (RSSSF y
    # Wikipedia; ganó San Lorenzo). Su "tabla anual" es la de la temporada, con el Apertura 1990 (cargado a mano; Boca y
    # San Lorenzo perdieron los dos el partido entre ellos). Promedios de 1988-89 y 1989-90, de RSSSF. Bajaron los dos
    # últimos (Chaco For Ever y Lanús). Los goles del Clausura, de RSSSF (sin minutos)
    "1991-clausura": {"nombre": "Torneo Clausura 1991", "anio": 1991, "liga": "a_mano", "slug": "1991-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                      "campeon_tabla": True, "temporada": "1990-91", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "Goles de RSSSF, sin minutos; la lista suma los de la final por el campeonato y "
                                         "los de la Liguilla.",
                      "nombre_playoffs": "Final y Liguilla",
                      "playoffs": [(r"^$^", n) for n in ("Final por el campeonato", "Cuartos de final", "Semifinales",
                                                         "Final de la Liguilla")],
                      "playoffs_a_mano": {
                          "Final por el campeonato": [
                              {"hora_utc": "1991-07-06T19:00Z", "fecha": "1991-07-06", "local": "newell-s-old-boys", "visitante": "boca-juniors", "gl": 1, "gv": 0, "estadio": "Gigante de Arroyito (Rosario Central)", "goles": [{"jugador": "Berizzo", "equipo": "local"}]},
                              {"hora_utc": "1991-07-09T19:00Z", "fecha": "1991-07-09", "local": "boca-juniors", "visitante": "newell-s-old-boys", "gl": 1, "gv": 0, "estadio": "La Bombonera", "pen_l": 1, "pen_v": 3, "goles": [{"jugador": "Reinoso", "equipo": "local"}]},
                          ],
                          "Cuartos de final": [
                              {"hora_utc": "1991-07-13T19:00Z", "fecha": "1991-07-13", "local": "river-plate", "visitante": "deportivo-mandiyu", "gl": 2, "gv": 0, "goles": [{"jugador": "Berti", "equipo": "local"}, {"jugador": "Castro", "equipo": "local"}]},
                              {"hora_utc": "1991-07-13T19:00Z", "fecha": "1991-07-13", "local": "independiente", "visitante": "san-lorenzo", "gl": 1, "gv": 1, "goles": [{"jugador": "Artime", "equipo": "local"}, {"jugador": "Ferreyra", "equipo": "visitante"}]},
                              {"hora_utc": "1991-07-14T19:00Z", "fecha": "1991-07-14", "local": "velez-sarsfield", "visitante": "racing-club", "gl": 3, "gv": 0, "goles": [{"jugador": "Acosta", "equipo": "local"}, {"jugador": "Acosta", "equipo": "local"}, {"jugador": "E.González", "equipo": "local"}]},
                              {"hora_utc": "1991-07-14T19:00Z", "fecha": "1991-07-14", "local": "boca-juniors", "visitante": "argentinos-juniors", "gl": 0, "gv": 1, "goles": [{"jugador": "Fernández", "equipo": "visitante"}]},
                              {"hora_utc": "1991-07-20T19:00Z", "fecha": "1991-07-20", "local": "argentinos-juniors", "visitante": "boca-juniors", "gl": 0, "gv": 2, "estadio": "Cancha de Vélez Sarsfield", "goles": [{"jugador": "Gaona", "equipo": "visitante"}, {"jugador": "Soñora", "equipo": "visitante"}]},
                              {"hora_utc": "1991-07-21T19:00Z", "fecha": "1991-07-21", "local": "deportivo-mandiyu", "visitante": "river-plate", "gl": 0, "gv": 2, "estadio": "Cancha de Huracán Corrientes", "goles": [{"jugador": "Silvani", "equipo": "visitante"}, {"jugador": "Vega", "equipo": "visitante", "tipo": "ec"}]},
                              {"hora_utc": "1991-07-21T19:00Z", "fecha": "1991-07-21", "local": "racing-club", "visitante": "velez-sarsfield", "gl": 5, "gv": 1, "alargue": True, "goles": [{"jugador": "Alfonso", "equipo": "local"}, {"jugador": "Paz", "equipo": "local"}, {"jugador": "Ortega Sánchez", "equipo": "local"}, {"jugador": "Fleita", "equipo": "local"}, {"jugador": "Borelli", "equipo": "local"}, {"jugador": "Acuña", "equipo": "visitante"}]},
                              {"hora_utc": "1991-07-21T19:00Z", "fecha": "1991-07-21", "local": "san-lorenzo", "visitante": "independiente", "gl": 2, "gv": 1, "estadio": "Cancha de Vélez Sarsfield", "goles": [{"jugador": "Zandoná", "equipo": "local"}, {"jugador": "Bustos", "equipo": "local"}, {"jugador": "Artime", "equipo": "visitante"}]},
                          ],
                          "Semifinales": [
                              {"hora_utc": "1991-07-28T19:00Z", "fecha": "1991-07-28", "local": "river-plate", "visitante": "san-lorenzo", "gl": 0, "gv": 0},
                              {"hora_utc": "1991-07-28T19:00Z", "fecha": "1991-07-28", "local": "boca-juniors", "visitante": "racing-club", "gl": 1, "gv": 1, "goles": [{"jugador": "Gaona", "equipo": "local"}, {"jugador": "Ortega Sánchez", "equipo": "visitante"}]},
                              {"hora_utc": "1991-08-04T19:00Z", "fecha": "1991-08-04", "local": "san-lorenzo", "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "Cancha de Huracán", "pen_l": 4, "pen_v": 1},
                              {"hora_utc": "1991-08-04T19:00Z", "fecha": "1991-08-04", "local": "racing-club", "visitante": "boca-juniors", "gl": 0, "gv": 0, "pen_l": 2, "pen_v": 4},
                          ],
                          "Final de la Liguilla": [
                              {"hora_utc": "1991-08-08T19:00Z", "fecha": "1991-08-08", "local": "san-lorenzo", "visitante": "boca-juniors", "gl": 1, "gv": 0, "estadio": "Cancha de Vélez Sarsfield", "goles": [{"jugador": "Carrizo", "equipo": "local"}]},
                              {"hora_utc": "1991-08-11T19:00Z", "fecha": "1991-08-11", "local": "boca-juniors", "visitante": "san-lorenzo", "gl": 0, "gv": 1, "goles": [{"jugador": "Rossi", "equipo": "visitante"}]},
                          ],
                      },
                      "ida_y_vuelta": True,
                      "cuadro": {"bloques": [("Final por el campeonato 1990-91: Newell's (campeón del Apertura 1990) y "
                                              "Boca (campeón del Clausura 1991)", [["Final por el campeonato"]]),
                                             ("Liguilla Pre-Libertadores: por el segundo lugar en la Libertadores 1992",
                                              [["Cuartos de final"], ["Semifinales"], ["Final de la Liguilla"]])],
                                 "nota": "Newell's ganó la final por penales y fue el campeón de la temporada 1990-91. "
                                         "A la Liguilla fueron el que perdió la final y los que siguieron en las tablas "
                                         "del Apertura y del Clausura. De los partidos hay solo los goleadores, sin los "
                                         "minutos."},
                      "anual": [("a_mano", r"^1990-apertura$", 1990)],
                      "anual_texto": "La tabla de la temporada 1990-91: suma el Torneo Apertura 1990 (Boca y San Lorenzo perdieron los dos el partido entre "
                                     "ellos, suspendido por la muerte de un hincha) y el Torneo Clausura 1991. Cada partido "
                                     "ganado valía 2 puntos. El campeón salió de la final entre los dos campeones.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1988-89": {"boca-juniors": [49, 38], "river-plate": [45, 38], "independiente": [55, 38],
                                                "san-lorenzo": [42, 38], "racing-club": [42, 38], "velez-sarsfield": [33, 38],
                                                "newell-s-old-boys": [35, 38], "rosario-central": [36, 38],
                                                "argentinos-juniors": [42, 38], "estudiantes-de-la-plata": [42, 38],
                                                "talleres": [44, 38], "gimnasia-y-esgrima": [36, 38],
                                                "ferro-carril-oeste": [30, 38], "deportivo-mandiyu": [33, 38],
                                                "deportivo-espanol": [46, 38], "platense": [33, 38]},
                                    "1989-90": {"boca-juniors": [43, 38], "river-plate": [53, 38], "independiente": [46, 38],
                                                "san-lorenzo": [35, 38], "racing-club": [39, 38], "velez-sarsfield": [42, 38],
                                                "newell-s-old-boys": [36, 38], "rosario-central": [43, 38],
                                                "argentinos-juniors": [38, 38], "estudiantes-de-la-plata": [34, 38],
                                                "talleres": [36, 38], "gimnasia-y-esgrima": [39, 38],
                                                "ferro-carril-oeste": [39, 38], "deportivo-mandiyu": [36, 38],
                                                "deportivo-espanol": [31, 38], "platense": [36, 38], "union": [36, 38],
                                                "chaco-for-ever": [32, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1992, "fijos": True,
                                "libertadores": [("Campeón de la temporada 1990-91 (ganó la final)", "newell-s-old-boys"),
                                                 ("Ganador de la Liguilla Pre-Libertadores", "san-lorenzo")],
                                "nota": "La Copa Conmebol empezó en 1992: sus lugares salieron de la temporada 1991-92."}},
    # El Torneo Apertura 1991 (agosto-diciembre; campeón River) abría la temporada 1991-92
    "1991-apertura": {"nombre": "Torneo Apertura 1991", "anio": 1991, "liga": "a_mano", "slug": "1991-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Ramón Díaz (River), "
                                         "con 14 goles.",
                      "anual": [("a_mano", r"^1991-clausura$")],
                      "anual_texto": "La tabla del año 1991: suma el Torneo Clausura 1991 y el Torneo Apertura 1991 (con 2 "
                                     "puntos por partido ganado). No daba lugares en las copas.",
                      "sin_descensos": "En el Torneo Apertura 1991 no hubo descensos: se definieron al terminar la "
                                       "temporada 1991-92, con el Torneo Clausura 1992."},
    # 1992: dos torneos de 20 equipos a una rueda, con 2 puntos por partido ganado; ESPN no los tiene: van a mano
    # (tools/a_mano; RSSSF, sin goles; Wikipedia no tiene estadios ni días). El Torneo Clausura 1992 (febrero-julio;
    # campeón Newell's) cerraba la temporada 1991-92: su "tabla anual" es la de la temporada, con el Apertura 1991
    # (cargado a mano). A Quilmes le descontaron 2 puntos (también en la tabla del año 1992, por DESCUENTOS). Promedios de
    # 1989-90 y 1990-91, de RSSSF. Bajaron los dos últimos (Unión y Quilmes). Los lugares en las copas salieron de la
    # Liguilla Pre-Libertadores (RSSSF): los dos campeones (River y Newell's) jugaron una final a tres partidos; ocho
    # equipos de la temporada jugaron un Octogonal, y el ganador (Vélez) jugó con el campeón que perdió la final (Newell's)
    # por el segundo lugar en la Libertadores 1993. A la Copa Conmebol 1992, los del Octogonal (Boca no quiso jugarla)
    "1992-clausura": {"nombre": "Torneo Clausura 1992", "anio": 1992, "liga": "a_mano", "slug": "1992-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                      "campeon_tabla": True, "temporada": "1991-92", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles del torneo: la lista es solo de la Liguilla "
                                         "Pre-Libertadores. Los goleadores del torneo fueron Diego Latorre (Boca) y Darío "
                                         "Scotto (Platense), con 9 goles.",
                      "descuentos": {"quilmes": 2},
                      "descuentos_texto": "A Quilmes se le descontaron 2 puntos.",
                      "nombre_playoffs": "Liguilla Pre-Libertadores",
                      "playoffs": [(r"^$^", n) for n in ("Final de campeones", "Cuartos de final", "Semifinales",
                                                         "Final del Octogonal", "Por el segundo lugar en la Libertadores")],
                      "playoffs_a_mano": {
                          "Final de campeones": [
                              {"hora_utc": "1992-07-12T18:00Z", "fecha": "1992-07-12", "local": "newell-s-old-boys",
                               "visitante": "river-plate", "gl": 0, "gv": 0, "estadio": "Cancha de Rosario Central"},
                              {"hora_utc": "1992-07-19T18:00Z", "fecha": "1992-07-19", "local": "river-plate",
                               "visitante": "newell-s-old-boys", "gl": 1, "gv": 0,
                               "goles": [{"jugador": "Medina Bello", "equipo": "local"}]},
                              {"hora_utc": "1992-07-26T18:00Z", "fecha": "1992-07-26", "local": "river-plate",
                               "visitante": "newell-s-old-boys", "gl": 3, "gv": 2, "estadio": "Cancha de Córdoba",
                               "goles": [{"jugador": "Medina Bello", "equipo": "local"}, {"jugador": "Medina Bello", "equipo": "local"},
                                         {"jugador": "R. Díaz", "equipo": "local"}, {"jugador": "Martino", "equipo": "visitante"},
                                         {"jugador": "Lunari", "equipo": "visitante"}]}],
                          "Cuartos de final": [
                              {"hora_utc": "1992-07-10T23:00Z", "fecha": "1992-07-10", "local": "deportivo-espanol",
                               "visitante": "racing-club", "gl": 1, "gv": 0, "estadio": "Cancha de Huracán",
                               "goles": [{"jugador": "Rodríguez", "equipo": "local"}]},
                              {"hora_utc": "1992-07-12T17:00Z", "fecha": "1992-07-12", "local": "boca-juniors",
                               "visitante": "san-lorenzo", "gl": 2, "gv": 0, "alargue": True, "estadio": "Cancha de Huracán",
                               "goles": [{"jugador": "Latorre", "equipo": "local"}, {"jugador": "Latorre", "equipo": "local"}]},
                              {"hora_utc": "1992-07-12T18:00Z", "fecha": "1992-07-12", "local": "platense",
                               "visitante": "gimnasia-y-esgrima", "gl": 0, "gv": 1, "estadio": "Cancha de Independiente",
                               "goles": [{"jugador": "Barros Schelotto", "equipo": "visitante"}]},
                              {"hora_utc": "1992-07-12T19:00Z", "fecha": "1992-07-12", "local": "velez-sarsfield",
                               "visitante": "huracan", "gl": 1, "gv": 0, "estadio": "Cancha de Ferro Carril Oeste",
                               "goles": [{"jugador": "Rinaldi", "tipo": "ec", "equipo": "local"}]}],
                          "Semifinales": [
                              {"hora_utc": "1992-07-18T18:00Z", "fecha": "1992-07-18", "local": "boca-juniors",
                               "visitante": "gimnasia-y-esgrima", "gl": 0, "gv": 1, "estadio": "Cancha de Vélez Sarsfield",
                               "goles": [{"jugador": "Guerra", "equipo": "visitante"}]},
                              {"hora_utc": "1992-07-19T18:00Z", "fecha": "1992-07-19", "local": "velez-sarsfield",
                               "visitante": "deportivo-espanol", "gl": 1, "gv": 1, "pen_l": 4, "pen_v": 2,
                               "estadio": "Cancha de Ferro Carril Oeste",
                               "goles": [{"jugador": "Ortega Sánchez", "equipo": "local"},
                                         {"jugador": "Rodríguez", "equipo": "visitante"}]}],
                          "Final del Octogonal": [
                              {"hora_utc": "1992-07-26T20:00Z", "fecha": "1992-07-26", "local": "velez-sarsfield",
                               "visitante": "gimnasia-y-esgrima", "gl": 3, "gv": 0, "estadio": "Cancha de River",
                               "goles": [{"jugador": "Mancuso", "equipo": "local"}, {"jugador": "Flores", "equipo": "local"},
                                         {"jugador": "Flores", "equipo": "local"}]}],
                          "Por el segundo lugar en la Libertadores": [
                              {"hora_utc": "1992-08-02T18:00Z", "fecha": "1992-08-02", "local": "newell-s-old-boys",
                               "visitante": "velez-sarsfield", "gl": 1, "gv": 0, "estadio": "Cancha de Rosario Central",
                               "goles": [{"jugador": "Saldaña", "equipo": "local"}]}]},
                      "cuadro": {"bloques": [("Final de campeones (a tres partidos: ganó River, que ganó dos)",
                                              [["Final de campeones"]]),
                                             ("Octogonal: ocho equipos de la temporada, por la Copa Conmebol y por un "
                                              "lugar en la final por la Libertadores",
                                              [["Cuartos de final"], ["Semifinales"], ["Final del Octogonal"]]),
                                             ("Por el segundo lugar en la Libertadores: el campeón que perdió la final "
                                              "contra el ganador del Octogonal", [["Por el segundo lugar en la Libertadores"]])],
                                 "nota": "La Liguilla Pre-Libertadores repartió los lugares de la Argentina en las copas. "
                                         "De los partidos hay solo los goleadores, sin los minutos."},
                      "anual": [("a_mano", r"^1991-apertura$", 1991)],
                      "anual_texto": "La tabla de la temporada 1991-92: suma el Torneo Apertura 1991 y el Torneo "
                                     "Clausura 1992. Cada partido ganado valía 2 "
                                     "puntos. Los lugares en las copas no salieron de esta tabla sino de la Liguilla "
                                     "Pre-Libertadores.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1989-90": {"river-plate": [53, 38], "boca-juniors": [43, 38], "velez-sarsfield": [42, 38],
                                                "newell-s-old-boys": [36, 38], "independiente": [46, 38],
                                                "racing-club": [39, 38], "rosario-central": [43, 38],
                                                "ferro-carril-oeste": [39, 38], "san-lorenzo": [35, 38],
                                                "gimnasia-y-esgrima": [39, 38], "platense": [36, 38],
                                                "argentinos-juniors": [38, 38], "deportivo-mandiyu": [36, 38],
                                                "deportivo-espanol": [31, 38], "estudiantes-de-la-plata": [34, 38],
                                                "talleres": [36, 38], "union": [36, 38]},
                                    "1990-91": {"river-plate": [45, 38], "boca-juniors": [51, 38], "velez-sarsfield": [45, 38],
                                                "newell-s-old-boys": [48, 38], "independiente": [40, 38],
                                                "racing-club": [40, 38], "huracan": [40, 38], "rosario-central": [39, 38],
                                                "ferro-carril-oeste": [38, 38], "san-lorenzo": [45, 38],
                                                "gimnasia-y-esgrima": [33, 38], "platense": [35, 38],
                                                "argentinos-juniors": [36, 38], "deportivo-mandiyu": [38, 38],
                                                "deportivo-espanol": [28, 38], "estudiantes-de-la-plata": [39, 38],
                                                "talleres": [29, 38], "union": [31, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1993, "anio_sudamericana": 1992, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 1991 (ganó la final de campeones)", "river-plate"),
                                                 ("Campeón del Torneo Clausura 1992 (le ganó al del Octogonal)",
                                                  "newell-s-old-boys")],
                                "sudamericana": [("Ganador del Octogonal", "velez-sarsfield"),
                                                 ("Finalista del Octogonal", "gimnasia-y-esgrima"),
                                                 ("Semifinalista del Octogonal (en lugar de Boca, que no quiso jugarla)",
                                                  "deportivo-espanol")],
                                "nota": "Los lugares salieron de la Liguilla Pre-Libertadores (ver esa pestaña)."}},
    # El Torneo Apertura 1992 (agosto-diciembre, con un partido terminado en abril de 1993; campeón Boca) abría la
    # temporada 1992-93. A River y a San Martín de Tucumán les descontaron 2 puntos (en la temporada 1992-93 del Clausura
    # 1993, por DESCUENTOS)
    "1992-apertura": {"nombre": "Torneo Apertura 1992", "anio": 1992, "liga": "a_mano", "slug": "1992-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Alberto Acosta "
                                         "(San Lorenzo), con 12 goles.",
                      "descuentos": {"river-plate": 2, "san-martin-tucuman": 2},
                      "descuentos_texto": "A River y a San Martín de Tucumán se les descontaron 2 puntos.",
                      "anual": [("a_mano", r"^1992-clausura$")],
                      "anual_texto": "La tabla del año 1992: suma el Torneo Clausura 1992 (a Quilmes le descontaron 2 "
                                     "puntos) y el Torneo Apertura 1992 (con 2 puntos por partido ganado). No daba lugares "
                                     "en las copas.",
                      "sin_descensos": "En el Torneo Apertura 1992 no hubo descensos: se definieron al terminar la "
                                       "temporada 1992-93, con el Torneo Clausura 1993."},
    # 1993: dos torneos de 20 equipos a una rueda, con 2 puntos por partido ganado; ESPN no los tiene: van a mano
    # (tools/a_mano; RSSSF, sin goles; Wikipedia no tiene estadios ni días). El Torneo Clausura 1993 (febrero-junio;
    # campeón Vélez) cerraba la temporada 1992-93: su "tabla anual" es la de la temporada, con el Apertura 1992 (cargado
    # a mano; a River y San Martín de Tucumán, 2 puntos menos por DESCUENTOS). A Rosario Central le descontaron 2 puntos (también en la
    # tabla del año 1993, por DESCUENTOS); cuatro partidos se definieron en el escritorio (ver las notas). Promedios de
    # 1990-91 y 1991-92, de RSSSF. Bajaron los dos últimos (Talleres y San Martín de Tucumán). A la Copa Conmebol 1993,
    # los tres mejores de la temporada que no iban a otra copa (Wikipedia)
    "1993-clausura": {"nombre": "Torneo Clausura 1993", "anio": 1993, "liga": "a_mano", "slug": "1993-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                      "campeon_tabla": True, "temporada": "1992-93", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Rubén Da Silva "
                                         "(River), con 13 goles.",
                      "descuentos": {"rosario-central": 2},
                      "descuentos_texto": "A Rosario Central se le descontaron 2 puntos.",
                      "anual": [("a_mano", r"^1992-apertura$", 1992)],
                      "anual_texto": "La tabla de la temporada 1992-93: suma el Torneo Apertura 1992 ("
                                     "a River y a San Martín de Tucumán les descontaron 2 puntos) y el Torneo Clausura 1993. Cada partido ganado valía 2 puntos.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1990-91": {"boca-juniors": [51, 38], "river-plate": [45, 38], "velez-sarsfield": [45, 38],
                                                "san-lorenzo": [45, 38], "independiente": [40, 38],
                                                "newell-s-old-boys": [48, 38], "huracan": [40, 38], "racing-club": [40, 38],
                                                "deportivo-espanol": [28, 38], "ferro-carril-oeste": [38, 38],
                                                "rosario-central": [39, 38], "deportivo-mandiyu": [38, 38],
                                                "gimnasia-y-esgrima": [33, 38], "estudiantes-de-la-plata": [39, 38],
                                                "platense": [35, 38], "argentinos-juniors": [36, 38], "talleres": [29, 38]},
                                    "1991-92": {"boca-juniors": [50, 38], "river-plate": [55, 38], "velez-sarsfield": [48, 38],
                                                "san-lorenzo": [34, 38], "independiente": [36, 38],
                                                "newell-s-old-boys": [44, 38], "huracan": [38, 38], "racing-club": [39, 38],
                                                "deportivo-espanol": [45, 38], "ferro-carril-oeste": [37, 38],
                                                "rosario-central": [34, 38], "belgrano": [35, 38], "deportivo-mandiyu": [33, 38],
                                                "gimnasia-y-esgrima": [41, 38], "estudiantes-de-la-plata": [29, 38],
                                                "platense": [42, 38], "argentinos-juniors": [35, 38], "talleres": [37, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1994, "anio_sudamericana": 1993, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón del Torneo Apertura 1992", "boca-juniors"),
                                                 ("Campeón del Torneo Clausura 1993", "velez-sarsfield")],
                                "sudamericana": [("Tabla de la temporada 1992-93", "san-lorenzo"),
                                                 ("Tabla de la temporada 1992-93", "huracan"),
                                                 ("Tabla de la temporada 1992-93", "deportivo-espanol")],
                                "nota": "A la Supercopa 1993 fueron invitados River, Boca, Racing, Independiente, "
                                        "Estudiantes y Argentinos; por eso no podían jugar la Copa Conmebol."}},
    # El Torneo Apertura 1993 (septiembre de 1993 a marzo de 1994; campeón River) abría la temporada 1993-94
    "1993-apertura": {"nombre": "Torneo Apertura 1993", "anio": 1993, "liga": "a_mano", "slug": "1993-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Sergio Martínez "
                                         "(Boca), con 12 goles.",
                      "anual": [("a_mano", r"^1993-clausura$")],
                      "anual_texto": "La tabla del año 1993: suma el Torneo Clausura 1993 (a Rosario Central le "
                                     "descontaron 2 puntos) y el Torneo Apertura 1993 (con 2 puntos por partido ganado). "
                                     "No daba lugares en las copas: salían de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 1993 no hubo descensos: se definieron al terminar la "
                                       "temporada 1993-94, con el Torneo Clausura 1994."},
    # 1994: dos torneos de 20 equipos a una rueda, con 2 puntos por partido ganado ("puntos_victoria" y
    # PUNTOS_VICTORIA); ESPN no los tiene: van a mano (tools/a_mano; RSSSF, sin goles; Wikipedia no tiene estadios ni
    # días). El Torneo Clausura 1994 (marzo-agosto; campeón Independiente) cerraba la temporada 1993-94: su "tabla
    # anual" es la de la temporada, con el Apertura 1993 (cargado a mano). Promedios de 1991-92 y 1992-93, de RSSSF.
    # Bajaron los dos últimos (Estudiantes y Gimnasia y Tiro). Vélez fue a la Libertadores 1995 como campeón de la de
    # 1994. A la Copa Conmebol 1994, los tres mejores de la temporada que no iban a otra copa (Wikipedia)
    "1994-clausura": {"nombre": "Torneo Clausura 1994", "anio": 1994, "liga": "a_mano", "slug": "1994-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                      "campeon_tabla": True, "temporada": "1993-94", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. Los goleadores fueron Hernán Crespo "
                                         "(River) y Marcelo Espina (Platense), con 11 goles.",
                      "anual": [("a_mano", r"^1993-apertura$", 1993)],
                      "anual_texto": "La tabla de la temporada 1993-94: suma el Torneo Apertura 1993 y el Torneo "
                                     "Clausura 1994. Cada partido ganado valía 2 puntos.",
                      # (con 2 puntos por partido ganado)
                      "promedios": {"1991-92": {"river-plate": [55, 38], "boca-juniors": [50, 38], "velez-sarsfield": [48, 38],
                                                "independiente": [36, 38], "huracan": [38, 38], "san-lorenzo": [34, 38],
                                                "deportivo-espanol": [45, 38], "racing-club": [39, 38],
                                                "gimnasia-y-esgrima": [41, 38], "rosario-central": [34, 38],
                                                "ferro-carril-oeste": [37, 38], "belgrano": [35, 38], "platense": [42, 38],
                                                "newell-s-old-boys": [44, 38], "argentinos-juniors": [35, 38],
                                                "deportivo-mandiyu": [33, 38], "estudiantes-de-la-plata": [29, 38]},
                                    "1992-93": {"river-plate": [46, 38], "boca-juniors": [48, 38], "velez-sarsfield": [48, 38],
                                                "independiente": [41, 38], "huracan": [43, 38], "san-lorenzo": [45, 38],
                                                "deportivo-espanol": [41, 38], "lanus": [37, 38], "racing-club": [36, 38],
                                                "gimnasia-y-esgrima": [34, 38], "rosario-central": [39, 38],
                                                "ferro-carril-oeste": [38, 38], "belgrano": [38, 38], "platense": [28, 38],
                                                "newell-s-old-boys": [25, 38], "argentinos-juniors": [33, 38],
                                                "deportivo-mandiyu": [37, 38], "estudiantes-de-la-plata": [38, 38]}},
                      "descensos": "promedios", "descienden": 2,
                      "cupos": {"anio": 1995, "anio_sudamericana": 1994, "nombre_sudamericana": "Copa Conmebol", "fijos": True,
                                "libertadores": [("Campeón de la Copa Libertadores 1994 (lugar aparte)", "velez-sarsfield"),
                                                 ("Campeón del Torneo Apertura 1993", "river-plate"),
                                                 ("Campeón del Torneo Clausura 1994", "independiente")],
                                "sudamericana": [("Tabla de la temporada 1993-94", "san-lorenzo"),
                                                 ("Tabla de la temporada 1993-94", "huracan"),
                                                 ("Tabla de la temporada 1993-94", "lanus")],
                                "nota": "A la Supercopa 1994 fueron invitados Vélez, River, Boca, Racing, Independiente, "
                                        "Estudiantes y Argentinos; por eso no podían jugar la Copa Conmebol."}},
    # El Torneo Apertura 1994 (septiembre-diciembre; campeón River) abría la temporada 1994-95. A Talleres le
    # descontaron 2 puntos (RSSSF y Wikipedia no dicen por qué); en la temporada 1994-95 del Clausura 1995, por DESCUENTOS
    "1994-apertura": {"nombre": "Torneo Apertura 1994", "anio": 1994, "liga": "a_mano", "slug": "1994-apertura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2, "campeon_tabla": True,
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue Enzo Francescoli "
                                         "(River), con 12 goles.",
                      "descuentos": {"talleres": 2},
                      "descuentos_texto": "A Talleres se le descontaron 2 puntos.",
                      "anual": [("a_mano", r"^1994-clausura$")],
                      "anual_texto": "La tabla del año 1994: suma el Torneo Clausura 1994 y el Torneo Apertura 1994 (con 2 "
                                     "puntos por partido ganado). No daba lugares en las copas: salían de la temporada.",
                      "sin_descensos": "En el Torneo Apertura 1994 no hubo descensos: se definieron al terminar la "
                                       "temporada 1994-95, con el Torneo Clausura 1995."},
    # 1995: dos torneos de 20 equipos a una rueda; ESPN no los tiene: van a mano, como 1996 a 2002 (tools/a_mano;
    # RSSSF, sin goles el Clausura y con los goles y sus minutos el Apertura; Wikipedia no tiene estadios ni días). El
    # Torneo Clausura 1995 (febrero-junio; campeón San Lorenzo) cerraba la temporada 1994-95 y fue el último con 2
    # puntos por partido ganado ("puntos_victoria"; también en sumar, por PUNTOS_VICTORIA): su "tabla anual" es la de
    # la temporada, con el Apertura 1994 (cargado a mano; a Talleres, 2 puntos menos por DESCUENTOS). Promedios de
    # 1992-93 y 1993-94, de RSSSF. Bajaron los dos últimos (Deportivo Mandiyú y Talleres). A la Copa Conmebol 1995, los
    # dos mejores de la temporada que no iban a otra copa (Wikipedia)
    "1995-clausura": {"nombre": "Torneo Clausura 1995", "anio": 1995, "liga": "a_mano", "slug": "1995-clausura",
                      "zonas": "unica", "fechas": 19, "pasan": 0, "puntos_victoria": 2,
                      "campeon_tabla": True, "temporada": "1994-95", "nombre_anual": "Temporada y copas",
                      "goleadores_nota": "RSSSF no tiene los goles de este torneo. El goleador fue José Oscar Flores "
                                         "(Vélez), con 14 goles.",
                      "anual": [("a_mano", r"^1994-apertura$", 1994)],
                      "anual_texto": "La tabla de la temporada 1994-95: suma el Torneo Apertura 1994 (a Talleres le "
                                     "descontaron 2 puntos) y el Torneo Clausura 1995. Cada partido ganado valía 2 puntos.",
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
# Puntos por partido ganado en los torneos que no daban 3 ({clave del torneo a mano: puntos}): hasta el Clausura 1995,
# 2 (se suman así también en la tabla del año 1995)
PUNTOS_VICTORIA = {"1936-honor": 2, "1990-temporada": 2, "1990-apertura": 2, "1991-clausura": 2, "1991-apertura": 2, "1992-clausura": 2, "1992-apertura": 2, "1993-clausura": 2, "1993-apertura": 2, "1994-clausura": 2, "1994-apertura": 2, "1995-clausura": 2}
DESCUENTOS = {(2014, "7"): 6, (1992, "2741", r"^1992-clausura$"): 2, (1993, "16", r"^1992-apertura$"): 2,
              (1993, "8713", r"^1992-apertura$"): 2, (1993, "17", r"^1993-clausura$"): 2, (1995, "19", r"^1994-apertura$"): 2, (2004, "6", r"^torneo-apertura-2003$"): 3, (2000, "5", r"^2000-clausura$"): 3,
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
    "dma": ("deportivo-mandiyu", "Deportivo Mandiyú"),
    "cfe": ("chaco-for-ever", "Chaco For Ever"),   # (no está en ESPN: 1990-91)
    "dar": ("deportivo-armenio", "Deportivo Armenio"),   # (no está en ESPN: 1988-89)
    "dit": ("deportivo-italiano", "Deportivo Italiano"),   # (no está en ESPN: 1986-87)
    "acc": ("alianza-cutral-co", "Alianza (Cutral Có)"),   # (no está en ESPN: la Liguilla 1985-86)
    "cfc": ("concepcion-fc", "Concepción FC (Tucumán)"),
    "gue": ("guemes", "Güemes (Santiago del Estero)"),
    "gaf": ("guarani-antonio-franco", "Guaraní Antonio Franco (Posadas)"),
    "rsa": ("santamarina", "Ramón Santamarina"),   # (no están en ESPN: el Nacional 1985)
    "ahz": ("altos-hornos-zapla", "Altos Hornos Zapla"),
    "jan": ("juventud-antoniana", "Juventud Antoniana"),
    "afi": ("argentino-firmat", "Argentino de Firmat"),
    "cip": ("cipolletti", "Cipolletti"),
    "hlh": ("huracan-las-heras", "Huracán Las Heras"),
    "cno": ("central-norte", "Central Norte (Salta)"),
    "cde": ("circulo-deportivo", "Círculo Deportivo (Otamendi)"),
    "jal": ("juventud-alianza", "Juventud Alianza (San Juan)"),
    "fgp": ("ferro-general-pico", "Ferro Carril Oeste (General Pico)"),   # (no están en ESPN: el Nacional 1984)
    "ugp": ("union-general-pinedo", "Unión (General Pinedo)"),
    "aur": ("atletico-uruguay", "Atlético Uruguay (Concepción del Uruguay)"),
    "kim": ("kimberley", "Kimberley (Mar del Plata)"),
    "led": ("ledesma", "Atlético Ledesma"),
    "usv": ("union-san-vicente", "Unión San Vicente (Córdoba)"),
    "atl": ("atlanta", "Atlanta"),   # (no está en ESPN: el Nacional y el Metropolitano 1984)
    "lne": ("loma-negra", "Loma Negra (Olavarría)"),   # (no están en ESPN: el Nacional 1983)
    "and": ("andino", "Andino (La Rioja)"),
    "rce": ("renato-cesarini", "Renato Cesarini (Rosario)"),
    "asr": ("atletico-santa-rosa", "Atlético Santa Rosa (La Pampa)"),
    "aco": ("atletico-concepcion", "Atlético Concepción (Banda del Río Salí)"),
    "dro": ("deportivo-roca", "Deportivo Roca (General Roca)"),   # (no están en ESPN: el Nacional 1982)
    "esg": ("estudiantes-santiago", "Estudiantes (Santiago del Estero)"),
    "mmo": ("mariano-moreno", "Mariano Moreno (Junín)"),
    "slm": ("san-lorenzo-mdp", "San Lorenzo (Mar del Plata)"),
    "hsr": ("huracan-san-rafael", "Huracán (San Rafael)"),   # (no está en ESPN: el Nacional 1981)
    "jpr": ("juventud-pringles", "Juventud Pringles (San Luis)"),   # (no está en ESPN: el Nacional 1979)
    "eba": ("estudiantes-buenos-aires", "Estudiantes (Buenos Aires)"),   # (no están en ESPN: 1978)
    "alv": ("alvarado", "Alvarado (Mar del Plata)"),
    "lsj": ("los-andes-san-juan", "Los Andes (San Juan)"),   # (no están en ESPN: el Nacional 1977)
    "sre": ("sarmiento-resistencia", "Sarmiento (Resistencia)"),
    "ste": ("san-telmo", "San Telmo"),   # (no están en ESPN: 1976)
    "hcr": ("huracan-comodoro-rivadavia", "Huracán (Comodoro Rivadavia)"),
    "spa": ("sportivo-patria", "Sportivo Patria (Formosa)"),
    "bmi": ("bartolome-mitre", "Bartolomé Mitre (Posadas)"),   # (no están en ESPN: 1975)
    "jne": ("jorge-newbery", "Jorge Newbery (Junín)"),
    "are": ("atletico-regina", "Atlético Regina (Villa Regina)"),   # (no están en ESPN: 1974)
    "pco": ("puerto-comercial", "Puerto Comercial (Bahía Blanca)"),
    "sde": ("sportivo-desamparados", "Sportivo Desamparados (San Juan)"),
    "itr": ("independiente-trelew", "Independiente (Trelew)"),   # (no está en ESPN: 1972)
    "dor": ("don-orione", "Don Orione (Barranqueras)"),   # (no están en ESPN: 1971)
    "hiw": ("huracan-ingeniero-white", "Huracán (Ingeniero White)"),
    "abr": ("almirante-brown", "Almirante Brown"),   # (no está en ESPN: el Torneo de Promoción 1970)
    "dmo": ("deportivo-moron", "Deportivo Morón"),   # (no está en ESPN: 1969)
    "ccr": ("central-cordoba-rosario", "Central Córdoba (Rosario)"),   # (no está en ESPN: 1959)
    "aqu": ("argentino-de-quilmes", "Argentino de Quilmes"),   # (no está en ESPN: 1939)
    "tre": ("talleres-remedios-de-escalada", "Talleres (Remedios de Escalada)"),   # (no está en ESPN: 1938)
    "utl": ("union-talleres-lanus", "Unión Talleres-Lanús"),   # (no está en ESPN: 1934; escudo, los dos juntos)
    "epo": ("estudiantil-porteno", "Estudiantil Porteño"),
    "dsu": ("dock-sud", "Dock Sud"),
    "epv": ("el-porvenir", "El Porvenir"),
    "gsm": ("general-san-martin", "General San Martín"),
    "sal": ("sportivo-alsina", "Sportivo Alsina"),
    "exc": ("excursionistas", "Excursionistas"),
    "aca": ("acassuso", "Acassuso"),
    "cmu": ("colegiales", "Colegiales"),
    "gut": ("gutenberg", "Gutenberg"),
    "sba": ("sportivo-barracas", "Sportivo Barracas"),
    "lia": ("liberal-argentino", "Liberal Argentino"),
    "rsc": ("ramsar", "Ramsar"),
    "sbs": ("sportivo-buenos-aires", "Sportivo Buenos Aires"),
    "pba": ("palermo-buenos-aires", "Palermo"),
    "spa": ("sportivo-palermo", "Sportivo Palermo"),
    "sfe": ("san-fernando", "San Fernando"),
    "alo": ("argentino-de-lomas", "Argentino de Lomas"),   # (no están en ESPN: el amateur 1931; escudos genéricos)   # (no está en ESPN: el amateur 1932; escudo genérico)
    "csi": ("san-isidro", "San Isidro"),
    "hyp": ("honor-y-patria", "Honor y Patria"),
    "ads": ("argentino-del-sud", "Argentino del Sud"),   # (no están en ESPN: 1930; escudo genérico el de Argentino del Sud)
    "pto": ("porteno", "Porteño"),   # (no está en ESPN: 1928)
    "sbc": ("sportivo-balcarce", "Sportivo Balcarce"),
    "spm": ("sportsman", "Sportsman"),
    "bal": ("boca-alumni", "Boca Alumni"),
    "alv": ("alvear", "Alvear"),
    "unv": ("universal", "Universal"),
    "dpl": ("del-plata", "Del Plata"),
    "prg": ("progresista", "Progresista"),   # (no están en ESPN: 1926; escudos genéricos los de Boca Alumni, Universal y Del Plata)
    "ate": ("argentino-de-temperley", "Argentino de Temperley"),   # (no están en ESPN: el amateur 1934; escudos genéricos los de Sportivo Alsina, Liberal Argentino y Argentino de Temperley)
    "sgu": ("sportivo-guzman", "Sportivo Guzmán (Tucumán)"),   # (no están en ESPN: 1967)
    "ddb": ("defensores-de-belgrano", "Defensores de Belgrano"),
    "rco": ("racing-cordoba", "Racing de Córdoba"),   # (no está en ESPN: 1989-90)   # (no está en ESPN: 1994-95)
    "hco": ("huracan-corrientes", "Huracán Corrientes"),   # (no está en ESPN: 1996-97)   # (no tiene id de ESPN: 1999-00)
    "ger": ("gimnasia-concepcion", "Gimnasia y Esgrima (Concepción del Uruguay)"),   # (no está en ESPN: Promoción 2002)
}

# Nombres que en la liga se confunden (en data/equipos.js están como en las copas)
NOMBRES = {"gimnasia-y-esgrima": "Gimnasia (La Plata)"}


def eventos_a_mano(clave):
    """Los partidos de un torneo que ESPN no tiene (2002), de tools/a_mano/liga-<clave>.json, con la forma de los de
    ESPN (los clubes, con su id de ESPN), para que el resto funcione igual. Cada uno lleva su fecha (_fecha_n) y el
    partido tal cual (_a_mano: día, hora, goles, nota). En los torneos por etapas (el Nacional 1983), cada fecha dice
    su etapa (va al final del slug: "1983-nacional-primera-fase") y cada partido su zona (el grupo, como en ESPN; los
    interzonales, sin zona)."""
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
                # (un partido puede decir su propia etapa: en el Metropolitano 1976, el Torneo Campeonato y el del
                # descenso se jugaban en las mismas fechas)
                "season": {"slug": f"{clave}-{p.get('etapa') or f['etapa']}" if p.get("etapa") or f.get("etapa") else clave},
                # (un partido que no se terminó, sin resultado y con "estado": Independiente-Racing 1965)
                "status": {"type": {"completed": p["gl"] is not None, "name": "STATUS_FULL_TIME" if p["gl"] is not None
                                    else "STATUS_SUSPENDED"}},
                "competitions": [{"competitors": [
                    {"homeAway": lado, "team": {"id": id_espn[p[lado2]], "displayName": p[lado2]}, "score": p[g]}
                    for lado, lado2, g in (("home", "local", "gl"), ("away", "visitante", "gv"))],
                    "venue": {"fullName": p.get("estadio")},
                    **({"group": {"name": f"Group {p['zona']}"}} if p.get("zona") else {})}],
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
    elif cfg.get("zonas_a_mano"):   # (las zonas de un torneo cargado a mano: el Nacional 1985)
        eid = {c["team"]["displayName"]: c["team"]["id"] for e in eventos for c in e["competitions"][0]["competitors"]}
        zonas_espn = {z: [eid[c] for c in ids] for z, ids in cfg["zonas_a_mano"].items()}
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
            if m.get("estado"):
                p["estado"] = m["estado"]
            p.update({"fecha": m["fecha"], "hora": m.get("hora"), "fecha_n": e["_fecha_n"], "nota": m.get("nota"),
                      "para_local": m.get("para_local"), "para_visitante": m.get("para_visitante"),
                      # (sin_goles: un partido dado por ganado en el escritorio, sin goles de verdad: Lanús-Platense 1991)
                      "sin_goles": m.get("sin_goles"),
                      # (árbitro y público, si el archivo los trae: 1931)
                      "arbitro": m.get("arbitro") or p.get("arbitro"), "publico": m.get("publico") or p.get("publico"),
                      # (los penales después de cada empate: el Campeonato 1988-89)
                      "pen_l": m.get("pen_l"), "pen_v": m.get("pen_v"),
                      # (un gol sin "jugador": no se sabe quién lo hizo; el Metropolitano 1977)
                      "goles": [{**g, **({"jid": f"{p[g['equipo']]}:{g['jugador']}"} if g.get("jugador") else {})}
                                for g in m.get("goles", [])]})
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

    # las fechas, por etapa, numeradas desde la primera fecha de cada una (a mano, ya vienen con su número)
    if etapas and cfg.get("liga") != "a_mano":
        for i, (_, _, _, primera, cuantas, *_) in enumerate(etapas):
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
        # (texto: lo que dice la leyenda de la tabla de esa etapa; el Nacional 1983)
        for i, (nombre, _, pasan, _, _, *texto) in enumerate(etapas):
            ps = [p for p in regular if p["etapa"] == i]
            zonas_etapa = {}
            for p in sorted(ps, key=lambda p: p["hora_utc"]):
                if not p["zona"]:   # (un interzonal: las zonas salen de los otros partidos)
                    continue
                for c in (p["local"], p["visitante"]):
                    if c not in zonas_etapa.setdefault(p["zona"], []):
                        zonas_etapa[p["zona"]].append(c)
            datos["etapas"].append({"nombre": nombre, "pasan": pasan, "zonas": dict(sorted(zonas_etapa.items())),
                                    "fechas": sorted({p["fecha_n"] for p in ps}),
                                    **({"texto_pasan": texto[0]} if texto else {})})
    if cfg.get("desempate_a_mano"):   # (un desempate que ESPN no tiene: River-Gimnasia 1999)
        d = cfg["desempate_a_mano"]
        desempates = [{**d, **{lado: club({"id": d[lado], "displayName": d[lado]}) for lado in ("local", "visitante")
                                if d[lado].isdigit() or d[lado] in CLUBES_NUEVOS}}]
    if desempates:
        datos["desempate"] = limpio(desempates[0])
    for k in ("temporada", "descienden", "texto_pasan", "nombre_playoffs", "nombre_anual", "desempate_texto", "goleadores_nota", "promocion", "ventaja", "triangular", "texto_triangular", "ida_y_vuelta", "gol_visitante", "cuadro_desde",
              "campeon_tabla", "anual_texto", "descensos_anulados", "sin_descensos", "nota", "cuadro", "descuentos",
              "descuentos_texto", "promedios_victoria", "puntos_victoria", "punto_penales",
              "promedios_por_temporada", "texto_promocion", "campeon_etapa", "pasan_triangular", "etapa_suma", "texto_suma", "desempate_goles", "descienden_etapa", "descienden_clubes", "descienden_texto", "sin_cuadro", "orden_a_mano", "orden_texto",
              "promedios_orden", "promedios_texto"):
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
