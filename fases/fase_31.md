# Fase 31

**Fecha:** 2026-10-06

## Commits

- `cb08682` Liga argentina: 1979 (Metropolitano por etapas con desempate Vélez-Argentinos y Torneo por el descenso; Nacional de 4 zonas de 7)
- `c14eb52` Liga argentina: 1978 (Metropolitano de 21 equipos; Nacional de 4 zonas de 8, tres partidos dados por ganados)
- `89abf3f` Liga argentina: 1977 (Metropolitano de 23 equipos con goles y desempate Platense-Lanús; Nacional, campeón Independiente por gol de visitante)
- `4b4e995` Liga argentina: 1976 (Metropolitano con Torneo Campeonato y Torneo por el descenso; Nacional de 4 zonas con desempates)
- `a6abd1e` Liga argentina: 1975 (Metropolitano sin descensos; Nacional con torneo final de 8 y descuento a Banfield)
- `5257da9` Liga argentina: 1974 (Metropolitano con cuadrangular final; Nacional con octogonal y Reducido por la Libertadores)
- `ef42855` Liga argentina: 1973 (Metropolitano de 17 equipos; Nacional de 2 zonas de 15 y cuadrangular final)
- `f505c74` Liga argentina: 1972 (Metropolitano con descuento a Banfield y Torneo Reclasificatorio sumado; Nacional con semifinal y final)
- `3db93c6` Liga argentina: 1971 (Metropolitano de 19 equipos con goles; Nacional de 2 zonas de 14)
- `3f81621` Liga argentina: 1970 (Metropolitano con Petit Torneo, Reclasificatorio y Promoción; Nacional de 2 zonas de 10)

## Qué se hizo

- **Liga argentina de 1970 a 1979**, cargada a mano como 1980-2002 (`tools/a_mano/liga-<clave>.json` y la entrada de
  cada torneo en `TORNEOS`, `tools/actualizar_liga.py`). Resultados de RSSSF; días y estadios de Wikipedia cuando los
  tiene; de las fases finales, goles, minutos y árbitros de Wikipedia. En 1971, 1976 y 1977 RSSSF trae los goleadores
  (solo apellido, sin minutos); los goles que faltan van sin autor (`{"equipo": ...}`, se ven como "?"). Se cruzaron
  las dos fuentes partido por partido y cada tabla calculada se controló contra la oficial.
- Campeones: 1979 River y River, 1978 Quilmes e Independiente, 1977 River e Independiente, 1976 Boca y Boca,
  1975 River y River, 1974 Newell's y San Lorenzo, 1973 Huracán y Rosario Central, 1972 San Lorenzo y San Lorenzo,
  1971 Independiente y Rosario Central, 1970 Independiente y Boca. Títulos (`data/ligas/argentina/titulos.js`): `antes`
  llega hasta el Nacional 1969 (último campeón, Boca).
- Página (`js/liga.js`), lo nuevo:
  - el campeón de una final a ida y vuelta sale de la serie (global y gol de visitante), no del partido de ida;
  - torneos por etapas: campeón por la tabla de una etapa (`campeon_etapa`, antes que el triangular), descenso por
    etapa (`descensos: "etapa"`, o una lista por etapa con `descienden_etapa`), desempate entre dos de la misma zona
    (`desempate_a_mano`, ordena la tabla y se muestra abajo), descuentos en la primera etapa, zonas con nombre largo
    ("Posiciones") y la tabla de la suma para el descenso (`etapa_suma`, el Reclasificatorio de 1972);
  - triangular con clasificados (`pasan_triangular`, el Reducido por la Libertadores 1974);
  - desempate por goles a favor y después en contra (`desempate_goles: "gf"`, 1970).
- Script: una fecha o cada partido puede decir su etapa (en 1976 el Torneo Campeonato y el del descenso comparten
  fechas); goles sin autor; clubes nuevos en `CLUBES_NUEVOS`.
- Escudos nuevos de Wikipedia; sin escudo, uno gris genérico: Los Andes (San Juan) "LA", Huracán (Comodoro Rivadavia)
  "CAH", Huracán (Ingeniero White) "HIW".
- Errores de las fuentes corregidos (anotados en el campo `fuente` de cada JSON): Boca-Estudiantes 1973 (3-1),
  Atlético Tucumán-Gimnasia de Jujuy en la fecha 4 del Nacional 1973 (las dos fuentes ponían San Martín), Huracán-Los
  Andes 1970 (5-3), resultados de las listas de Wikipedia de los Metropolitanos 1977 y 1978, local de los clásicos
  tucumanos del Nacional 1979.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Probado en el navegador cada torneo: tablas, etapas,
fases finales, descensos, cupos y número de título.

## Pendiente / próximos pasos

- Seguir hacia atrás: 1969 (Metropolitano y Nacional) y antes (desde 1967 hay Metropolitano y Nacional; antes, un
  solo campeonato por año).
- Escudos verdaderos de Argentino de Firmat, Renato Cesarini, Los Andes (San Juan) y los dos Huracán del sur.
- Al terminar el Clausura 2026 (y cada torneo nuevo), agregar su campeón a `data/ligas/argentina/titulos.js`.
- Pendientes anteriores:
  - goleadores del Clausura 1996 con el nombre escrito de dos formas;
  - goles que faltan (1996-2006);
  - cupos 2021;
  - Sudamericana 2014;
  - torneos de 2027;
  - otras ligas;
  - GitHub Pages y Google Search Console.
