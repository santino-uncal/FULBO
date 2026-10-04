# Fase 26

**Fecha:** 2026-10-04

## Commits

- `5eb42e3` Liga argentina: Torneo Clausura 1995 (el último con 2 puntos por partido ganado) y Torneo Apertura 1995 (con los goles y sus minutos); escudo de Deportivo Mandiyú
- `0519e6f` Liga argentina: Torneo Clausura 1994 y Torneo Apertura 1994 (con el descuento a Talleres)
- `eecfcde` Liga argentina: Torneo Clausura 1993 (descuento a Rosario Central, cuatro partidos definidos en el escritorio) y Torneo Apertura 1993
- `58ea005` Liga argentina: Torneo Clausura 1992 (con la Liguilla Pre-Libertadores) y Torneo Apertura 1992 (descuentos a River y San Martín de Tucumán)
- `47d4fb5` Liga argentina: Torneo Clausura 1991 (con los goles, la final por el campeonato 1990-91 y la Liguilla) y Torneo Apertura 1991; escudo de Chaco For Ever
- `0b9d350` Liga argentina: Campeonato 1989-90 (38 fechas, Liguilla, desempate por el descenso) y Torneo Apertura 1990 (con los goles); escudo de Racing de Córdoba

## Qué se hizo

- **Liga argentina, de 1990 a 1995**, cargada a mano como 1996-2002 (`tools/a_mano/liga-<torneo>.json`, RSSSF y
  Wikipedia). Cada torneo se controló contra las tablas finales y los promedios de RSSSF (y de Wikipedia cuando la hay).
  - Campeones: 1995 San Lorenzo / Vélez; 1994 Independiente / River; 1993 Vélez / River; 1992 Newell's / Boca;
    1991 Boca / River (campeón 1990-91: Newell's, en la final con Boca); 1990: Campeonato 1989-90 River / Apertura Newell's.
  - Goles: con minuto en el Apertura 1995; sin minuto en el Clausura 1991 y el Apertura 1990; los demás, sin goles
    (la página da el goleador según RSSSF).
  - En 1990, el **Campeonato 1989-90** (una sola tabla de 38 fechas) va con el año en que terminó, con clave
    `1990-temporada`, al lado del Apertura 1990.
  - Liguillas Pre-Libertadores (1989-90, 1990-91, 1991-92), la final por el campeonato 1990-91 y el desempate por el
    descenso Chaco For Ever-Racing de Córdoba, cargados como playoffs a mano (`playoffs_a_mano`, con su cuadro).
  - Descuentos de puntos en la tabla del torneo y en las sumas (`DESCUENTOS`), partidos perdidos por los dos
    (`para_local`/`para_visitante`) y partidos dados en el escritorio.
  - La tabla de la temporada de cada Clausura (de 1991 a 1996) sale ahora de los partidos cargados del Apertura
    anterior.
- **2 puntos por partido ganado** hasta el Clausura 1995: `puntos_victoria` en el torneo (`js/liga.js` lo usa en la
  tabla y lo aclara abajo) y `PUNTOS_VICTORIA` en `sumar` (`tools/actualizar_liga.py`).
- `js/liga.js`: la nota de goleadores se ve también con la lista completa; `sin_goles` para un partido dado por ganado
  sin goles de verdad (Lanús-Platense 1991), que no cuenta como "faltan goles".
- `tools/convertir_rsssf.py`: goles del local y del visitante en corchetes separados (1990-91), el formato de
  Wikipedia de 1989-90 (5 columnas), notas `{{Refn|1=...}}`, Racing de Córdoba, filas vacías.
- Errores de las fuentes corregidos (en los comentarios y en el campo `fuente` de cada JSON): partidos repetidos o
  continuados otro día, resultados dados por el Tribunal que RSSSF deja como se jugaron, localía de Boca-Gimnasia 1993,
  la tabla del Apertura 1990 de RSSSF (Unión y Talleres), nombres de goleadores escritos de dos formas.
- Escudos nuevos (Wikipedia): Deportivo Mandiyú, Chaco For Ever, Racing de Córdoba.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (la de la tabla anual acepta 2 puntos por victoria). Probado en
el navegador cada año (tabla, temporada y copas, promedios, playoffs, goleadores).

## Pendiente / próximos pasos

- Seguir con 1989 (Campeonato 1988-89): después de cada empate había penales y el ganador sumaba un punto extra; hay
  que mostrarlo en la tabla y en los partidos. RSSSF: `tablesa/arg89.html`.
- Revisar si el Clausura 1996 (misma página de RSSSF que el Apertura 1995) tiene goleadores con el nombre escrito de
  dos formas.
- La fecha 11 del Clausura 1995 va toda el 5 de mayo (RSSSF no dice qué partido se jugó el 6).
- Pendientes anteriores: goles que faltan (1996-2006), cupos 2021, Sudamericana 2014, torneos de 2027, otras ligas,
  GitHub Pages y Google Search Console.
