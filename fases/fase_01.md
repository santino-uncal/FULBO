# Fase 01 — Estructura base y descarga de todos los datos

**Fecha:** 2026-09-26
**Commits:** `bc4c764`, `230df0b`, `e4b4c25`, `0f636bb`, `e93e075`

## Qué se hizo

- Se creó el proyecto con la misma estructura que ROMA (HTML/CSS/JS sin build, datos en `data/`),
  con git, y se conectó al repo de GitHub `santino-uncal/FULBO`.
- Se investigaron fuentes de datos y se eligieron:
  - **RSSSF** (1960–2024): resultados y goleadores; formaciones de las finales.
  - **ESPN** (API pública, 2005–2026): goles con minuto, asistencias, formaciones, árbitro, público, colores y escudos.
  - **TheSportsDB**: escudos de clubes que no están en ESPN.
  - Transfermarkt se descartó para descarga automática (sus reglas lo prohíben).
- Scripts en `tools/`:
  - `descargar_rsssf.py`, `descargar_espn.py`, `descargar_escudos.py`: bajan los datos crudos (a `tools/cache/`, que no se sube a git).
  - `leer_rsssf.py`, `leer_espn.py`: convierten cada fuente a un formato común.
  - `equipos.py` + `equipos_ajustes.json`: unifican los nombres de clubes (alias, homónimos, países).
  - `generar_datos.py`: une las fuentes, calcula campeones y planteles, escribe `data/` y muestra un control de calidad.
- Datos generados: 67 ediciones (1960–2026), 246 clubes, 215 escudos.
- Página provisoria (`index.html` + `js/app.js`) para verificar los datos: por edición muestra campeón,
  goleadores, asistidores, partidos por fase y planteles.

## Estado al cerrar

- Campeón y subcampeón calculados correctamente en las 66 ediciones terminadas (1960–2025).
- Goles con autor en el 99% de los casos.
- Asistencias disponibles en 2005–2007 y 2014–2026 (ESPN no las tiene para 2008–2013).
- Formaciones completas desde 2005; antes, solo algunas finales.
- Planteles completos desde 2005; antes, parciales (goleadores y finalistas).
- Faltan escudos de 30 clubes, casi todos viejos o desaparecidos.
- Todo subido a GitHub.

## Pendiente / próximos pasos

- **Definir el diseño de la página** (portada con campeones, ficha por club, tablas históricas, etc.).
- Camisetas: dibujarlas con código a partir de los colores de cada club (no hay imágenes descargables).
- Decidir qué mostrar en lugar de los escudos faltantes (iniciales) o buscarlos a mano.
- Unificar jugadores de la era RSSSF (solo apellido) para rankings históricos.
- Algunas fechas de RSSSF en fases previas 2017–2018 quedaron como "01-01"; revisar.
- Actualizar 2026 a medida que avanza la copa: `python tools/descargar_espn.py 2026` y `python tools/generar_datos.py`.
- Publicar en GitHub Pages.
