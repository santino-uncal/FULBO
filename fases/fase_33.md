# Fase 33

**Fecha:** 2026-10-08

## Commits

- `07a4197` Liga argentina: 1950 (18 equipos; desempates Boca-Independiente por el segundo puesto y Huracán-Tigre por el descenso)
- `b265a75` Liga argentina: 1951 (17 equipos, uno libre por fecha; final Racing-Banfield por el título)
- `2d7f062` Liga argentina: 1952 (bajó Atlanta)
- `b5e310a` Liga argentina: 1953 (bajó Estudiantes por el cociente de goles)
- `f06bbe4` Liga argentina: 1954 (once partidos suspendidos y terminados otro día; bajó Banfield)
- `5440205` Liga argentina: 1955 (tres partidos de River suspendidos; bajó Platense)
- `3504b6b` Liga argentina: 1956 (desempate del último puesto: bajó Chacarita); pestaña "Descenso"
- `5c80586` Liga argentina: 1957 (promedios de 1956 y 1957: bajó Ferro)
- `52807ce` Liga argentina: 1958 (descuento a River, desempate Boca-San Lorenzo; bajó Tigre)
- `c4d6bc2`, `63775fa` Liga argentina: 1959 (desempate Gimnasia-Central Córdoba en los promedios)

## Qué se hizo

- **Liga argentina de 1950 a 1959**, cargada a mano como los años anteriores: un script en el scratchpad lee la página
  de RSSSF (`rsssf.org/tablesa/argNN.html`) y escribe `tools/a_mano/liga-<año>-primera.json`; la entrada de cada torneo
  va en `TORNEOS` (`tools/actualizar_liga.py`). Cada tabla calculada se controló contra la de RSSSF y, cuando RSSSF no la
  trae (1951, 1952, 1954), contra la de Wikipedia; cuando Wikipedia trae los partidos, se cruzaron uno por uno. Los
  errores de las fuentes quedaron en el campo `fuente` de cada JSON.
- Campeones: 1959 San Lorenzo, 1958 Racing, 1957 River, 1956 River, 1955 River, 1954 Boca, 1953 River, 1952 River,
  1951 Racing (final con Banfield), 1950 Racing. Títulos (`data/ligas/argentina/titulos.js`): `antes` llega hasta 1949
  (último campeón, Racing).
- Descensos: hasta 1956 bajaba el último de la tabla (`"descensos": "tabla"`; 1950 y 1951, los dos últimos); de 1957 a
  1959, por promedios por temporada.
- Página (`js/liga.js`), lo nuevo:
  - `promedios_orden` y `promedios_texto`: el desempate a mano de dos empatados en el promedio (Gimnasia y Central
    Córdoba, 1959), con la explicación debajo de los promedios;
  - pestaña "Descenso" (la tabla del año con los que bajan) en los torneos sin copas con descenso por la tabla;
  - la leyenda "Campeón: el primero de la tabla" ya no dice "(no hay playoffs)" si hay desempate (pendiente de la fase 32).
- Desempates en "playoffs": por el segundo puesto (1958, Boca-San Lorenzo, a ida y vuelta; 1950, Boca-Independiente,
  tres partidos, con `gana` en el último), la final de 1951 y Huracán-Tigre por el descenso (1950). En 1950, con
  `cuadro` a mano para que los dos desempates no se dibujen como una llave.
- Partidos dados por ganados (`para_local`/`para_visitante`, `sin_goles`): Newell's-Huracán 1959 y River-Huracán 1958
  (no jugado, con 2 puntos descontados a River). Suspendidos y terminados otro día, con su nota (1954, 1955, 1953, 1959).
- Club y escudo nuevos: Central Córdoba de Rosario (`central-cordoba-rosario`).
- Goles: solo los del partido en que se definió el campeonato (y la final de 1951), de RSSSF.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Probado en el navegador cada año: tabla, fechas, desempates,
promedios, descenso y número de título.

## Pendiente / próximos pasos

- Seguir hacia atrás: 1949 y antes (profesional desde 1931; antes, el amateurismo).
- En los años sin canchas en RSSSF (1953 y otros) va la cancha del local; Atlanta, antes de 1960, "Cancha de Atlanta".
- Estadios supuestos en algunos partidos del interior en los Torneos Promocionales (fase 32).
- Escudos verdaderos de Argentino de Firmat, Renato Cesarini, Los Andes (San Juan) y los dos Huracán del sur.
- Al terminar el Clausura 2026 (y cada torneo nuevo), agregar su campeón a `data/ligas/argentina/titulos.js`.
- Pendientes anteriores: goleadores del Clausura 1996 con el nombre escrito de dos formas; goles que faltan (1996-2006);
  cupos 2021; Sudamericana 2014; torneos de 2027; otras ligas; GitHub Pages y Google Search Console.
