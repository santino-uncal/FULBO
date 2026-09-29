# Fase 16

**Fecha:** 2026-09-29

## Commits

- `8cde1bf` Pruebas automáticas de las herramientas y de los datos (probar.bat)
- `b60379e` Goles de RSSSF anotados al equipo correcto (unos 400 partidos) y pruebas de ese caso
- `926ca79` Planteles: con formaciones, solo los convocados; sin formaciones, sin los que llegaron después de la copa

## Qué se hizo

- **Pruebas automáticas** (Python, sin instalar nada): doble clic en `probar.bat` o `py -m unittest discover tests`.
  - `tests/test_herramientas.py`: las funciones de `tools/` (lectura de RSSSF, Wikipedia y ESPN, ganador de llave,
    nombres de clubes, estadísticas, mezcla de planteles).
  - `tests/test_datos.py`: coherencia de `data/` en las cuatro copas (índice = ediciones, campeón jugó la final,
    clubes en el catálogo, penales y tandas, goles que cuadran con el resultado, planteles sin repetidos…).
  - Hoy son 63 y pasan todas.
- **Goles al equipo equivocado** (~400 partidos de la Libertadores y la Sudamericana, casi todos antes de 2005):
  RSSSF no siempre separa los goles de cada equipo con `;` (local sin goles, empates, gol en contra primero,
  desempates escritos al revés). Nueva `goles_por_lado` en `leer_rsssf.py`: si la lista no cuadra con el resultado,
  se reparte de la forma que cuadra. Excepción: partidos con `x` (ganados en los escritorios) que ya traen el `;`.
  En `generar_datos.py`, los goles de ESPN se usan solo si cuadran con el resultado de cada equipo (Caracas–Peñarol
  2012). Se corrigieron también los rankings de goleadores y las fichas de los clubes.
- **Planteles inflados** (Inter 2007 tenía 70): Transfermarkt da la plantilla de toda la temporada.
  - Con formaciones (desde 2005): el plantel son los que estuvieron en alguna formación; Transfermarkt solo completa
    número, posición y nombre (`mezclar(..., ed)` en `descargar_planteles.py`).
  - Sin formaciones: se descartan los que llegaron al club después de su último partido de la copa (se guarda la
    fecha de llegada, `llegada`, en `planteles_tm*.json`, releída de las páginas ya guardadas).
  - Mejor emparejamiento de nombres ("Alexandre" = "Alexandre Pato"; primero el nombre exacto).
  - Plantel más grande: 85 → 52 (Libertadores), 91 → 57 (Sudamericana). Inter 2007: 22.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las 63 pruebas pasan. Al regenerar solo cambiaron los goles y los planteles
(comparado partido por partido contra la versión anterior).

## Pendiente / próximos pasos

- Planteles de 1994–2004 que siguen pasando de 40 (Transfermarkt no dice quién se fue antes de la copa).
- De 2005 a 2007 ESPN no trae el banco de suplentes: el plantel son solo los que jugaron.
- 31 escudos sin descargar (la página los oculta).
- Leer las páginas guardadas de Transfermarkt es lento en Windows (~10 min por copa; el antivirus revisa cada archivo).
- Pendientes anteriores: GitHub Pages y Google Search Console, técnicos y planteles del Mundial de Clubes,
  Al Ahly–Guangzhou 2013 sin autores de goles, copas "próximamente" de la portada, jugador del torneo de la Sudamericana.
