# Fase 29

**Fecha:** 2026-10-04

## Commits

- `8de1c0b` Liga argentina: Campeonato 1988-89 (penales después de cada empate, Liguilla con doble eliminación)
- `f398892` Liga argentina: Campeonato 1987-88 (liguillas Pre-Libertadores y Clasificación, desempate por el descenso)
- `e728f95` Liga argentina: Campeonato 1986-87 (partido dado a Temperley por doping, desempate Platense-Temperley)
- `b7f10ee` Liga argentina: Campeonato 1985-86 (19 equipos, promedios por temporada, Octogonal en el que bajó Huracán)
- `68ec44a` Liga argentina: Campeonato Nacional 1985 (8 zonas y doble eliminación)
- `0fcfe98` Liga argentina: 1984 (Nacional con 8 zonas y fase final; Metropolitano de 19 equipos)

## Qué se hizo

- **Liga argentina de 1984 a 1989**, cargada a mano como 1990-2002 (`tools/a_mano/liga-<clave>.json` y la entrada
  de cada torneo en `TORNEOS`, `tools/actualizar_liga.py`). Cada torneo se controló club por club contra las tablas
  finales y los promedios de RSSSF y de Wikipedia.
  - 1989: Campeonato 1988-89 (Independiente). 3 puntos por ganar, 1 por empatar y 1 más para el que ganaba los penales
    después de cada empate (`punto_penales`; columna "Pen." en la tabla). Promedios con 2 puntos por partido ganado y sin
    el punto de los penales (`promedios_victoria`, ahora con los descuentos). Liguilla con rueda de ganadores
    (Octogonal) y de perdedores (Clasificación); ganó River.
  - 1988: Campeonato 1987-88 (Newell's). Liguillas Pre-Libertadores (San Lorenzo) y Clasificación (Platense),
    desempate Unión-Racing de Córdoba por el descenso.
  - 1987: Campeonato 1986-87 (Rosario Central). Liguilla (Independiente), desempate Platense-Temperley.
  - 1986: Campeonato 1985-86 (River). 19 equipos (uno libre por fecha). Promedios **por temporada**
    (`promedios_por_temporada`: puntos divididos por temporadas jugadas). Huracán jugó el Octogonal con la Primera B y
    bajó (`promocion` con `texto_promocion`). Liguilla con equipos del Torneo del Interior (Boca).
  - 1985: Campeonato Nacional 1985 (Argentinos). 8 zonas de 4 y doble eliminación: Vélez ganó la primera final y
    Argentinos la segunda.
  - 1984: Campeonato Nacional 1984 (Ferro; 8 zonas y fase final a ida y vuelta, descuento de 6 a Chacarita) y
    Campeonato Metropolitano 1984 (Argentinos; 19 equipos, promedios por temporada).
- Goles: de las liguillas de 1989 y 1986 (RSSSF, sin minutos) y de las fases finales de los Nacionales 1984 y 1985
  (Wikipedia, con minutos y árbitros). Del resto, no hay.
- Página (`js/liga.js`):
  - Tabla: el punto extra por penales.
  - Promedios: por temporada.
  - Llaves: `pasa` en la vuelta, para el que pasó con el global igualado por la posición en el campeonato.
  - Texto propio para la promoción.
- Script: zonas en los torneos cargados a mano (`zonas_a_mano`), penales de la fase regular cargada a mano, clubes nuevos
  en `CLUBES_NUEVOS`.
- Títulos (`data/ligas/argentina/titulos.js`): `antes` llega ahora hasta el Metropolitano 1983 (se sumó Ferro, con 1).
- Escudos nuevos (Wikipedia) de unos 25 clubes del interior y de la B. Argentino de Firmat no tiene escudo en Wikipedia
  ni en Commons: tiene uno genérico gris con las iniciales "CAA".
- Datos corregidos o dudosos (anotados en el campo `fuente` de cada JSON y en notas de los partidos):
  - 1988-89:
    - penales de Rosario-Instituto (de El Gráfico);
    - Vélez-Mandiyú: penales dados vuelta (el 2-3 se supuso).
  - 1986-87:
    - Estudiantes-Ferro: 1-0 en la lista de partidos, pero en la tabla cuenta como empate, como en las tablas finales;
    - River-Temperley: dado a Temperley por doping.
  - Metropolitano 1984: las tablas tienen un gol menos para Rosario y para Chacarita que los partidos.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76; la de los promedios acepta los de por temporada). Probado en el
navegador cada año: tabla, zonas, llaves, promedios, descensos, cupos y número de título.

## Pendiente / próximos pasos

- Seguir hacia atrás: 1983 (Nacional y Metropolitano).
- Escudo verdadero de Argentino de Firmat.
- Al terminar el Clausura 2026 (y cada torneo nuevo), agregar su campeón a `data/ligas/argentina/titulos.js`.
- Pendientes anteriores:
  - goleadores del Clausura 1996 con el nombre escrito de dos formas;
  - goles que faltan (1996-2006);
  - cupos 2021;
  - Sudamericana 2014;
  - torneos de 2027;
  - otras ligas;
  - GitHub Pages y Google Search Console.
