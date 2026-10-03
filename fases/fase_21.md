# Fase 21

**Fecha:** 2026-10-03

## Commits

- `7a39956` Liga Profesional argentina: Torneo Clausura 2026 (tabla por zonas, fechas, goleadores y playoffs), de ESPN
- `acb261b` Liga argentina: tabla anual y promedios del descenso (2024-2026), con los dos descensos marcados
- `6f720ad` Liga argentina: lugares para la Libertadores y la Sudamericana 2027 en la tabla anual
- `5aa0592` Liga argentina: Torneo Apertura 2026 completo (con playoffs y campeón) y selector de torneo; mejor reparto de fechas
- `dd0f018` Liga argentina: torneos Apertura y Clausura 2025, con tabla anual, promedios, descensos y cupos 2026
- `2988917` Liga argentina: temporada 2024 (Copa de la Liga y Liga Profesional), con tabla anual, promedios y cupos 2025; reparación de fechas con postergados cruzados
- `e458dc5` Liga argentina: cuadro de los playoffs en cada torneo
- `3213e53` Liga argentina: temporada 2023 (Liga Profesional y Copa de la Liga), con el desempate por el descenso y los cupos 2024
- `279d100` Liga argentina: temporada 2022 (Copa de la Liga y Liga Profesional), descensos por promedios y cupos 2023; promedios sin redondear
- `a3fcfeb` Liga argentina: temporada 2021 (Copa de la Liga y Liga Profesional), sin descensos, con cupos 2022
- `2a9b8f1` Liga argentina: Copa Diego Maradona 2020, con sus etapas y sus finales
- `e4a918f` Liga argentina: se elige primero el año y después el torneo
- `5449bcf` Liga argentina: cuadro de la Copa Diego Maradona 2020 (las dos finales y el repechaje)

## Qué se hizo

- **Primera liga nacional: la Liga Profesional argentina**, en una página aparte: `liga.html` + `js/liga.js`
  (datos en `data/ligas/argentina/<torneo>.js` y `indice.js`, `window.LIGA`). Desde la portada (Sudamérica →
  Ligas nacionales → Liga Profesional) hay link; las demás ligas siguen "próximamente".
- **Torneos cargados (2020-2026)**, todos de ESPN ("arg.1"; la Copa de la Liga es "arg.copa_lpf"):
  Copa Diego Maradona 2020; Copa de la Liga y Liga Profesional 2021, 2022, 2023 y 2024; Apertura y Clausura 2025 y 2026.
  Se elige primero el año y después el torneo (`?anio=2025`, `?torneo=2025-apertura`).
- **Pestañas:** Tabla (zonas, o tabla única, o etapas en 2020), Fechas (una por vez, con goles), Playoffs (con el cuadro;
  antes de que empiecen, los cruces "si terminara hoy"), Tabla anual, Promedios y Goleadores. La tabla de posiciones,
  la anual y los promedios los calcula la página con los resultados.
- **Tabla anual, promedios, descensos y cupos** (Libertadores / Sudamericana del año siguiente) de cada año, según el
  reglamento de cada temporada, controlados contra lo que pasó (ESPN, La Nación, Infobae, Wikipedia): descensos por
  tabla anual y promedios (2023-2026), por los dos últimos promedios (2022), anulados (2024, se dice quiénes hubiesen
  bajado), sin descensos (2020-2021); el desempate Gimnasia-Colón 2023; títulos extra (Rosario Central "Campeón de Liga
  2025"); lugares aparte (campeón de la Sudamericana; Banfield 2021 como subcampeón de la Copa Maradona).
- **`tools/actualizar_liga.py`:** baja, deduce el número de fecha (ESPN no lo da; con reparación para postergados
  cruzados), arma los datos. Sin argumentos baja solo los torneos que no terminaron; `todos` rehace todo.
  Partidos que ESPN no tiene (Copa de la Superliga 2020) en `PARTIDOS_A_MANO`.
- **Tarea programada nueva** "Actualizar liga argentina": todas las noches (~0:00) actualiza el torneo en curso, corre
  las pruebas y sube a GitHub.
- 5 clubes nuevos con escudo (Instituto, Gimnasia de Mendoza, Aldosivi, Sarmiento, Estudiantes de Río Cuarto) y San
  Martín de San Juan. Pruebas nuevas en `tests/test_liga.py`. README actualizado.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (74). Probado en el navegador (computadora y celular).
El Clausura 2026 va por la fecha 11-12 y se actualiza solo cada noche.

## Pendiente / próximos pasos

- Clausura 2026: cuando terminen los playoffs (diciembre) se completan solos el campeón y los cupos; después, sumar los
  torneos de 2027 a `TORNEOS` cuando se conozca el formato.
- Temporadas anteriores a 2020 (Superliga, torneos cortos…) si se quieren.
- Otras ligas nacionales (Brasileirão, Premier League…).
- Pendientes anteriores: GitHub Pages y Google Search Console, escudos de clubes chicos europeos, técnicos y planteles
  del Mundial de Clubes, técnicos de la Supercopa de Europa desde 2005, Recopa 2027.
