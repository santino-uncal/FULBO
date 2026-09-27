# Fase 09

**Fecha:** 2026-09-27

## Commits

- `d049115` Años: flechas ◀ ▶ al lado del botón 📅 para ir al año anterior y al siguiente
- `c9e0a44` Estadísticas: goleadores de todos los mata-mata, promedio de gol, entrenadores con más partidos y victorias, estadios de las finales
- `fd86a56` Finales: estadios cargados a mano para 1984-1997 y 2004, vuelta 1991 en el Monumental, 1985 con locales corregidos y 1988 sin partidos repetidos

## Qué se hizo

- **Flechas de año:** ◀ y ▶ a los costados del botón 📅. Llevan a la edición anterior / siguiente; se apagan en 1960, en la
  última edición y fuera de una edición (estadísticas, ficha de club). En el celular bajan con el 📅 a su propio renglón.
- **Estadísticas nuevas** (calculadas en `tools/generar_estadisticas.py`):
  - Pestaña "Todos los mata-mata" (suma octavos, cuartos, semis y final). La "Segunda fase" de 1988-2004 ahora cuenta
    como octavos, porque lo era.
  - Mejor promedio de gol: goles por partido jugado, solo desde 2005 (hay formaciones) y con 20 partidos o más.
  - Entrenadores con más partidos y con más partidos ganados (G/E/P y títulos). `tools/descargar_entrenadores.py` ahora
    también guarda quién dirigió cada partido en `tools/entrenadores_partidos.json` (sale de la caché de Transfermarkt).
  - Estadios con más finales (cuenta cada partido de la final).
- **Correcciones a mano de finales** en `tools/finales_ajustes.json` (las aplica `generar_datos.py`):
  - Estadios de las finales 1984-1986, 1988-1990, 1992-1997 y la vuelta de 2004 (chequeados en Wikipedia).
  - 1991: la vuelta fue en el Monumental David Arellano, no en el Nacional.
  - 1985: la fuente tenía los locales al revés en ida y vuelta; desempate con su fecha real (24/10).
  - 1988: se sacaron dos partidos repetidos y una nota de RSSSF que se había cargado como goles.
  - `generar_datos.py` además saca cualquier partido repetido de forma automática.

## Estado al cerrar

Todo commiteado y subido a GitHub. La página de estadísticas y las ediciones corregidas se probaron en el navegador.

## Pendiente / próximos pasos

- Activar GitHub Pages y dar de alta el sitio en Google Search Console.
- Entrenadores: en las ediciones viejas faltan algunos equipos (323 equipos-edición sin dato en Transfermarkt).
- Revisar si hay otras finales viejas de RSSSF con los locales invertidos, como la de 1985.
