# Fase 23

**Fecha:** 2026-10-03

## Commits

- `1bc56cb` Liga argentina: temporada 2019 (Superliga 2018-19, Copa de la Superliga 2019 y Superliga 2019-20), con promedios, descensos y cupos 2020; arreglo de la tabla anual
- `8210e7d` Liga argentina: Superliga 2017-18 (año 2018), con promedios de cuatro temporadas, descensos y cupos 2019
- `fba778f` Liga argentina: Campeonato 2016-17 (año 2017), con promedios, descensos y cupos 2018
- `ddd1e54` Liga argentina: Campeonato 2016 (zonas, final y tercer puesto), con promedios, descenso y cupos 2017
- `7f96c36` Liga argentina: Campeonato 2015 con las liguillas Pre-Libertadores y Pre-Sudamericana, promedios, descensos y cupos 2016
- `f9c88ea` Liga argentina: Torneo Final y Torneo de Transición 2014, con la temporada 2013-14, promedios, descuento a Colón, desempates y cupos

## Qué se hizo

- **Liga argentina, años 2014 a 2019** (todos de ESPN y controlados contra Wikipedia: tablas, promedios, descensos y
  cupos):
  - **2019:** Superliga 2018-19 (Racing), Copa de la Superliga 2019 (Tigre; eliminación directa a ida y vuelta, con
    gol de visitante y penales; el cuadro arranca en octavos) y Superliga 2019-20 (Boca; sin descensos).
  - **2018:** Superliga 2017-18 (Boca). **2017:** Campeonato 2016-17 (Boca). **2016:** Campeonato 2016 (Lanús; dos
    zonas, final y tercer puesto). **2015:** Campeonato 2015 (Boca) con las liguillas Pre-Libertadores y
    Pre-Sudamericana. **2014:** Torneo Final (River, con la Copa Campeonato 2013-14) y Torneo de Transición (Racing).
- **La página (`js/liga.js`)**, cosas nuevas: torneos sin fase regular (solo cuadro), series de ida y vuelta con el
  global, pestaña "Copas y descenso" para las temporadas sin tabla anual, promedios con el nombre de la temporada
  ("2018-19"), cantidad de descensos variable, cupos fijos (2014 y 2015, cuando el reparto no sigue una regla),
  desempates en los promedios y en la tabla, nombres de pestañas por torneo ("Liguillas", "Copa Campeonato").
- **`tools/actualizar_liga.py`**, nuevo: `PENALES_A_MANO`, `GOLES_A_MANO`, `RESULTADOS_A_MANO` (Colón-Rafaela 2013),
  `NO_SUMAN` (la final de 2016 no suma en los promedios), `DESCUENTOS` (los 6 puntos de Colón en 2013-14), zonas desde
  los grupos de ESPN, partidos de playoffs por su id, el lugar de la Copa Argentina para el subcampeón, y en los
  promedios un club que bajó y volvió cuenta solo desde que volvió (Aldosivi).
- **Arreglado:** la pestaña "Tabla anual" no cargaba (error de la sesión anterior).
- Clubes nuevos con escudo: San Martín de Tucumán, Chacarita, Olimpo, Temperley, Atlético de Rafaela, Nueva Chicago,
  Crucero del Norte y All Boys. README y pruebas actualizados.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan. Probado en el navegador cada año.

## Pendiente / próximos pasos

- Cupos para las copas 2021 en la Superliga 2019-20 (se definieron junto con la Copa Maradona; no se cargaron).
- La lista de la Sudamericana 2014 es la menos segura (dos fuentes de Wikipedia que no coincidían del todo).
- Años anteriores a 2014 (Inicial/Final 2012-2013, Apertura/Clausura…) si se quieren.
- Pendientes anteriores: torneos de 2027, otras ligas nacionales, GitHub Pages y Google Search Console, y los de las copas.
