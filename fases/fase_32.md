# Fase 32

**Fecha:** 2026-10-07

## Commits

- `2d064c9` Liga argentina: 1969 (Metropolitano con zonas, fase final, Petit Torneo y Reclasificatorio; Nacional con desempate River-San Lorenzo)
- `d3b2f37` Liga argentina: 1968 (Metropolitano con Reclasificatorio y Torneo Promocional; Nacional con triangular final)
- `a89427a` Liga argentina: 1967 (el primer Metropolitano, con Reclasificatorio y Torneo Promocional; Nacional de 16)
- `2ce6fdf` Liga argentina: 1966 (20 equipos a dos ruedas, sin descensos)
- `d3d4885` Liga argentina: 1965 (18 equipos, con los goleadores; Independiente-Racing suspendido sin contar)
- `3a1c49c` Liga argentina: 1964 (16 equipos, sin descensos)
- `06c74d3` Liga argentina: 1963 (14 equipos, descenso anulado)
- `7121302` Liga argentina: 1962 (15 equipos; promedios 1960-62: bajaron Ferro y Quilmes)
- `4353dc3` Liga argentina: 1961 (16 equipos; promedios 1959-61: bajaron Lanús y Los Andes)
- `91269f3` Liga argentina: 1960 (16 equipos; promedios 1958-60: bajó Newell's)

## Qué se hizo

- **Liga argentina de 1960 a 1969**, cargada a mano como 1970-2002 (`tools/a_mano/liga-<clave>.json` y la entrada de
  cada torneo en `TORNEOS`, `tools/actualizar_liga.py`). Resultados y días de RSSSF; cuando Wikipedia tiene los
  resultados (Nacionales 1967-1969, Metropolitano 1967, 1961) se cruzaron partido por partido. Cada tabla calculada se
  controló contra la oficial. Antes de 1967 hay un solo campeonato por año: clave `<año>-primera`.
- Campeones: 1969 Chacarita y Boca, 1968 San Lorenzo y Vélez, 1967 Estudiantes e Independiente, 1966 Racing, 1965 Boca,
  1964 Boca, 1963 Independiente, 1962 Boca, 1961 Racing, 1960 Independiente. Títulos (`data/ligas/argentina/titulos.js`):
  `antes` llega hasta 1959 (último campeón, San Lorenzo).
- Metropolitanos 1967-1969: etapas (primera fase de 2 zonas de 11 con interzonales, Petit Torneo / Torneo Promocional,
  Torneo Reclasificatorio con equipos de la Primera B) y semifinales y final en `playoffs_a_mano`. Nacional 1968:
  triangular final (`triangular`). Nacional 1969: desempate a ida y vuelta por el segundo puesto.
- Página (`js/liga.js`) y script, lo nuevo:
  - `orden_a_mano`: el orden de los empatados en puntos cuando no se desempataba por goles (1960-1966: los puntos contra
    el otro empatado y contra los primeros; Nacional 1969: el desempate), con `orden_texto` que lo explica debajo de la tabla;
  - un partido a mano puede quedar sin resultado, con `estado` (el Independiente-Racing de 1965, suspendido y nunca
    completado: no cuenta, como en RSSSF);
  - `gana` en un partido de playoffs a un partido sin ganador en la cancha (Boca-River, semifinal 1969).
- Promedios por temporada (`promedios_por_temporada`) en 1960, 1961 y 1962, iguales a las tablas de RSSSF y Wikipedia.
- Goles: 1965 completo (RSSSF, sin minutos; falta uno de Estudiantes); de los demás años, solo los partidos que RSSSF
  trae (finales, partidos del campeonato).
- Clubes y escudos nuevos: Deportivo Morón, Sportivo Guzmán, Defensores de Belgrano.
- Errores de las fuentes anotados en el campo `fuente` de cada JSON (Newell's-Platense 1969, Lanús-Atlanta 1967 en
  Wikipedia; Ferro 0 6 Racing 1966 en RSSSF; el orden de Wikipedia en 1964-1966 no sigue el reglamento).

## Estado al cerrar

Todo commiteado, **sin subir a GitHub** (falta `git push`). Las pruebas pasan (76). Probado en el navegador cada torneo:
tablas, etapas, fases finales, promedios, descensos, cupos y número de título.

## Pendiente / próximos pasos

- Subir a GitHub (`git push`).
- Seguir hacia atrás: 1959 y antes (un campeonato por año; desde 1931, profesional).
- En el Nacional 1969 sigue la leyenda "Campeón: el primero de la tabla (no hay playoffs)" aunque hay pestaña de desempate.
- Estadios supuestos (la cancha del local) en algunos partidos del interior en los Torneos Promocionales.
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
