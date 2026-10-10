# Fase 34

**Fecha:** 2026-10-09

## Commits

- `9cd53f3` Liga argentina: 1949 (desempates River-Platense por el segundo puesto y Huracán-Lanús por el descenso, con un partido anulado; bajó Lanús)
- `5d197b1` Liga argentina: 1948 (4 puntos descontados a Racing; sin descensos por la huelga); aviso de "no hubo descensos" en la tabla
- `f6ad050` 1947 (bajó Atlanta) · `763b864` 1946 (bajó Ferro) · `1efd815` 1945 (bajó Gimnasia) · `68b49e5` 1944 (bajó Banfield)
- `236a7b0` 1943 (bajó Gimnasia) · `191db95` 1942 (bajó Tigre)
- `dea2c14` 1941 (16 puntos descontados a Banfield por un soborno; bajó Rosario Central)
- `006e228` 1940 (partidos dados por perdidos a Banfield y Chacarita por sobornos; bajaron Vélez y Chacarita)
- `3aedd60` 1939 (desempates por la primera rueda y por el segundo puesto, compartido; bajó Argentino de Quilmes)
- `bda4cd7` 1938 (17 equipos; bajaron Almagro y Talleres de Remedios de Escalada)
- `aa73320` 1937 (desempate River-Boca por la primera rueda; bajaron Argentinos y Quilmes)
- `cc34241` 1936 (Copa de Honor, Copa Campeonato y Copa de Oro, con la tabla del año)
- `83c2c24` 1935
- `71947dc` 1934 profesional (LAF) · `66725e5` 1934 amateur
- `50c4c2d` 1933 profesional y amateur
- `a069371` 1932 profesional (final River-Independiente) · `4157d65` 1932 amateur
- `76ab603` 1931 profesional (con árbitro y público) · `6eaf3f3` 1931 amateur (final Estudiantil Porteño-Almagro)

## Qué se hizo

- **Liga argentina de 1931 a 1949**, cargada a mano como los años anteriores: un script en el scratchpad lee RSSSF
  (`rsssf.org/tablesa/argNN.html`; los amateurs, `argNNa.html`; 1936, también `arg-hon36.html` y `arg-oro36.html`) y
  escribe `tools/a_mano/liga-<clave>.json`; la entrada de cada torneo va en `TORNEOS` (`tools/actualizar_liga.py`).
  Cada tabla se controló contra la de RSSSF o la de Wikipedia (en 1940, partido por partido); las diferencias quedaron
  en el campo `fuente` de cada JSON y, cuando se ven en la página, en el texto debajo de la tabla.
- **Dos campeonatos por año de 1931 a 1934** (la AFA reconoce a los campeones de los dos): el profesional de la Liga
  Argentina de Football (`19NN-laf`) y el amateur (`19NN-amateur`, con "(amateur)" en el nombre y la explicación
  debajo de la tabla, como pidió el usuario). 1936 tiene `1936-honor` y `1936-campeonato` (con la Copa de Oro en
  "playoffs" y la tabla del año; `PUNTOS_VICTORIA` para la Copa de Honor).
- Los amateurs de 1932 a 1934 tienen los **goles de cada partido** (RSSSF, sin minutos; nombres unificados). En los
  de 1931 a 1933 RSSSF no dice la fecha de cada partido: se deduce con `repartir_fechas` y los no jugados se ubican
  donde los dos clubes tienen lugar (1931: 16 fechas, 1932: 36, una y dos más de las reales).
- Títulos (`data/ligas/argentina/titulos.js`): `antes` llega hasta 1930 (todos amateurs); `ultimo_antes`, Boca.
- Clubes nuevos (`CLUBES_NUEVOS`): Argentino de Quilmes, Talleres (Remedios de Escalada), Unión Talleres-Lanús (los dos
  escudos juntos), los 15 del amateur 1934, Sportivo Palermo, San Fernando y Argentino de Lomas. Escudos de Wikipedia;
  genéricos grises con iniciales los de Sportivo Alsina, Liberal Argentino, Argentino de Temperley, Sportivo Palermo,
  San Fernando y Argentino de Lomas. "Palermo" (Buenos Aires) va como `palermo-buenos-aires` (`palermo` es el de Italia).
- Página (`js/liga.js`): el aviso de `sin_descensos` también en la pestaña Tabla, en los torneos sin otra pestaña donde
  mostrarlo (1948 y otros).
- Script: copia `arbitro` y `publico` de los partidos cargados a mano (1931 los tiene todos).
- Canchas: las viejas, sin nombre de estadio, como "Cancha de X" (Racing antes de 1950, River antes de 1938, Boca
  antes de 1940, Huracán antes de 1947...); los de Boca de 1940 antes de la Bombonera, sin estadio.
- Memoria: aclarar cuando un campeonato es amateur.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Cada año revisado en el navegador.

## Pendiente / próximos pasos

- Seguir hacia atrás: 1930 y antes, la era amateur (marcar "amateur"; ver qué campeonatos reconoce la AFA en los años
  con dos ligas: 1912-1914, 1919-1926).
- Diferencias de un gol en las tablas del amateur 1932 (Sportivo Barracas-Estudiantil Porteño) y 1933 (All Boys-Colegiales):
  los partidos traen sus goles, pero las tablas de RSSSF y Wikipedia cuentan otra cosa.
- Argentino de Temperley (1932-1934): RSSSF dice que fue Temperley, Wikipedia lo enlaza con Argentino de Banfield;
  quedó como club aparte. Revisar si Argentino de Lomas (1931) es el mismo club.
- Escudos verdaderos de los genéricos (los de esta fase y Argentino de Firmat, Renato Cesarini, Los Andes, los Huracán).
- Pendientes anteriores: campeón del Clausura 2026 en `titulos.js`; goles que faltan (1996-2006); cupos 2021;
  Sudamericana 2014; torneos de 2027; otras ligas; GitHub Pages y Google Search Console.
