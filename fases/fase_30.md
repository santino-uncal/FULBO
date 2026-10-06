# Fase 30

**Fecha:** 2026-10-05

## Commits

- `078d851` Liga argentina: 1983 (Nacional con dos fases de zonas e interzonales; Metropolitano con promedios, bajaron Racing y Nueva Chicago)
- `818e372` Liga argentina: 1982 (Nacional de 4 zonas de 8; Metropolitano con descenso por tabla y desempate Unión-Quilmes)
- `78a8587` Liga argentina: 1981 (Metropolitano, bajaron San Lorenzo y Colón; Nacional de 4 zonas de 7, descuento a Racing de Córdoba)
- `2ec1625` Liga argentina: 1980 (Metropolitano, bajaron Quilmes, All Boys y Tigre; Nacional de 4 zonas de 7; River tricampeón)

## Qué se hizo

- **Liga argentina de 1980 a 1983**, cargada a mano como 1984-2002 (`tools/a_mano/liga-<clave>.json` y la entrada de
  cada torneo en `TORNEOS`, `tools/actualizar_liga.py`). Resultados de RSSSF; días y estadios de Wikipedia; de las fases
  finales de los Nacionales, también goles, minutos y árbitros de Wikipedia. Se cruzaron las dos fuentes partido por
  partido y las tablas calculadas se controlaron contra las oficiales.
  - 1983: Nacional (Estudiantes; bicampeón con el Metropolitano 1982) y Metropolitano (Independiente). Vuelven los
    promedios por temporada (1982 y 1983); bajaron Racing Club y Nueva Chicago.
  - 1982: Nacional (Ferro; 4 zonas de 8, fechas 5 y 13 de interzonales, cuartos a ida y vuelta) y Metropolitano
    (Estudiantes; bajaban los dos últimos de la tabla, desempate Unión-Quilmes en Junín).
  - 1981: Metropolitano (Boca; bajaron San Lorenzo y Colón; Talleres-Argentinos dado a Argentinos por doping) y Nacional
    (River; 4 zonas de 7 con interzonales, 4 puntos menos a Racing de Córdoba, gol de visitante en la fase final).
  - 1980: Metropolitano (River; bajaron los tres últimos) y Nacional (Rosario Central; mismo formato que 1981;
    San Lorenzo de Mar del Plata-Boca dado a San Lorenzo por doping).
- Script:
  - torneos por etapas cargados a mano (el Nacional 1983, con dos fases de zonas): en el JSON, `etapa` por fecha y
    `zona` por partido (los interzonales sin zona); cada etapa puede tener su texto (`texto_pasan`).
  - clubes nuevos en `CLUBES_NUEVOS` (Loma Negra, Andino, Renato Cesarini, Atlético Santa Rosa, Atlético Concepción,
    Deportivo Roca, Estudiantes de Santiago, Mariano Moreno, San Lorenzo de Mar del Plata, Huracán de San Rafael).
- Página (`js/liga.js`):
  - descenso por tabla (`descensos: "tabla"`, los últimos `descienden`), para antes de 1983.
  - etiqueta "Interzonal" en las fechas (estaba en el código pero nunca aparecía; se ve también en torneos modernos de
    dos zonas) y en los torneos por etapas.
  - el cuadro de la fase final también en los torneos por etapas.
- Títulos (`data/ligas/argentina/titulos.js`): `antes` llega hasta el Nacional 1979; nuevo `seguidos_antes` (River
  venía de ganar los dos torneos de 1979: el Metropolitano 1980 sale como tricampeonato).
- Escudos de Wikipedia de los clubes nuevos; Renato Cesarini no tiene: uno gris genérico con "CRC".
- Datos dudosos o corregidos (anotados en el campo `fuente` de cada JSON y en notas de los partidos):
  - Metropolitano 1983: San Lorenzo-Ferro, 2-1 (Wikipedia pone el 2-0 de la AFA, pero las tablas cuentan 2-1).
  - Nacional 1983: Andino jugó de local "en Vargas" según RSSSF (Wikipedia: estadio Mercado Luna).
  - Nacional 1982: penales de Quilmes-Unión 4-3 (Wikipedia, con cada remate; RSSSF dice 5-4); la tabla de Wikipedia de
    Central Norte no cuadra con sus propios resultados.
  - Metropolitano 1981: Wikipedia le pone 58 goles en contra a San Lorenzo; son 48.
  - Metropolitanos 1980, 1981 y 1982: sin los partidos en Wikipedia (o en un formato que no se pudo leer): solo RSSSF;
    el estadio es la cancha que dice RSSSF o, si no dice, la del local.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Probado en el navegador cada torneo: tablas, zonas, fases
finales, descensos, cupos y número de título.

## Pendiente / próximos pasos

- Seguir hacia atrás: 1979 (Metropolitano y Nacional).
- Escudos verdaderos de Argentino de Firmat y de Renato Cesarini.
- Al terminar el Clausura 2026 (y cada torneo nuevo), agregar su campeón a `data/ligas/argentina/titulos.js`.
- Pendientes anteriores:
  - goleadores del Clausura 1996 con el nombre escrito de dos formas;
  - goles que faltan (1996-2006);
  - cupos 2021;
  - Sudamericana 2014;
  - torneos de 2027;
  - otras ligas;
  - GitHub Pages y Google Search Console.
