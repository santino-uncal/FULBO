# Fase 17

**Fecha:** 2026-09-30

## Commits

- `63c4c30` Champions League: temporadas 2024/25 y 2025/26 (ESPN), con la fase de liga en una sola tabla
- `1f8ea14` Champions League: trofeo en la cabecera y en la portada
- `e90d761` Champions League desde 1991/92 (Wikipedia hasta 2000/01, ESPN después), clubes y banderas nuevos
- `2e3fa1c` Champions League completa desde 1955/56 (Copa de Campeones de Europa), con los clubes unificados en toda su historia
- `1b62868` Escudos de los clubes de la Champions
- `ae57627` Escudos que faltaban, buscados a mano (TheSportsDB y Wikipedia)
- `0220081` Colores de los campeones de Europa que faltaban

## Qué se hizo

- **Nueva copa: Champions League** (`?copa=champions`, datos en `data/champions/`, `window.UCL`), las 71 ediciones
  de 1955/56 a 2025/26 (~6.300 partidos). Cada edición lleva el año en que empieza la temporada (`edicion=2024` es
  la 2024/25) y la página la muestra como "2024/25" (`nombreAnio` en `app.js`).
  - 1955/56–1990/91: Wikipedia, la página de cada temporada + la de la final. Las rondas se llaman según cuántos
    equipos las jugaron (dieciseisavos, octavos…); desempates, partidos anulados y "no se jugó" marcados.
  - 1991/92–2000/01: Wikipedia, una página por fase (`paginas_champions` en `tools/copas.py`); en el archivo de
    cada temporada, cada página va precedida por `@@ETAPA <fase>@@`.
  - 2001/02 en adelante: ESPN (`uefa.champions`, años calendario de `espn_anios`, se queda con las temporadas de
    `ediciones`). Sin rondas clasificatorias. Asistencias recién desde 2011/12.
  - Formatos: fase de liga 2024+ en una sola tabla (8 directos a octavos, 9.º–24.º a playoffs), dos fases de
    grupos 1999–2003, grupos después de octavos en 1991–93 (pestaña "Primera y segunda ronda").
  - Correcciones: goles repetidos de ESPN (se limpian solos, también mejoró ~15 partidos de la Libertadores y la
    Sudamericana), semis de 2002/03 rotuladas como cuartos y penales de la final 2003 (`resultados` en
    `equipos_ajustes.json`), partidos postergados repetidos, Leeds–Stuttgart 1992 (resultado de escritorio),
    erratas de año en Wikipedia.
- **Clubes**: ~350 clubes europeos. Cada club va con su país actual (Estrella Roja = Serbia, Dukla = Chequia…)
  para que quede uno solo en toda su historia; se unificaron ~70 nombres históricos (alias "Nombre|" en
  `equipos_ajustes.json`). Efecto colateral: en la Intercontinental el título de 1991 cuenta para Serbia.
  Banderas de ~35 países nuevos.
- **Escudos**: `descargar_escudos.py` ahora prueba también el id como nombre, espera si TheSportsDB corta por
  exceso de pedidos y acepta `wiki:<idioma>:<archivo>` (imagen de la ficha del club en Wikipedia). Clubes que ya
  no existen usan el escudo de su continuador (17 Nëntori → KF Tirana, Karl-Marx-Stadt → Chemnitzer…).
- **Trofeo** de la Orejona en la cabecera y en la tarjeta de Europa de la portada (Wikimedia Commons, CC BY 2.0).
- **Colores** de los campeones de Europa que faltaban en `data/colores.js`.
- `descargar_espn.py`: si un partido falla, lo saltea (se vuelve a pedir la próxima vez) en vez de cortar.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las 63 pruebas pasan. Las otras copas no cambiaron salvo las mejoras de goles
mencionadas y el país del Estrella Roja.

## Pendiente / próximos pasos

- Champions sin entrenadores ni planteles de Transfermarkt; formaciones de 1955–1991 solo en las finales.
- 26 escudos de clubes sudamericanos chicos o desaparecidos (no están en TheSportsDB ni en Wikipedia).
- Pruebas automáticas específicas de la Champions (fase de liga, `@@ETAPA`, goles repetidos de ESPN).
- Pendientes anteriores: GitHub Pages y Google Search Console, técnicos y planteles del Mundial de Clubes,
  Al Ahly–Guangzhou 2013 sin autores de goles, Europa League y demás copas "próximamente", ligas nacionales,
  jugador del torneo de la Sudamericana, planteles de 1994–2004 de más de 40.
