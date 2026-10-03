# Fase 20

**Fecha:** 2026-10-03

## Commits

- `9d41ed5` Recopa Sudamericana completa desde 1989 (Wikipedia hasta 2014, ESPN después), con trofeo y técnicos
- `4d8c29d` Supercopa de Europa completa desde 1972 (Wikipedia hasta 2004, ESPN después), con trofeo

## Qué se hizo

- **Nueva copa: Recopa Sudamericana** (`?copa=recopa`, datos en `data/recopa/`, `window.REC`), 1989–2026:
  - 1989–2014 de Wikipedia (una página por año), 2015 en adelante de ESPN ("conmebol.recopa"). No se jugó en
    1999–2002.
  - 1991: no se jugó; Olimpia campeón (había ganado la Libertadores y la Supercopa 1990). Ajuste
    `campeones_recopa` y nota en `notas_ediciones`.
  - Técnicos: de las formaciones de Wikipedia y, lo que falta (todo desde 2015), de la historia de cada club en
    Transfermarkt (`dt_conmebol` en `descargar_entrenadores.py`, usa los clubes ya conocidos por la Libertadores y la
    Sudamericana). Correcciones a mano en `DT_A_MANO` (San Lorenzo 2015: Bauza; Fluminense 2024: Diniz).
  - País de algunos clubes en `pais_por_edicion` (1996, 1997, 2003, 2004).
  - Trofeo: foto del museo de Palmeiras (Roberto Sabino, CC BY 2.0), recortada con `rembg`.
  - En la cabecera va junto a la Libertadores y la Sudamericana; en la portada de Sudamérica ya tiene link.
- **Nueva copa: Supercopa de Europa** (`?copa=supercopa`, datos en `data/supercopa/`, `window.USC`), 1972–2026:
  - 1972–2004 de Wikipedia, 2005 en adelante de ESPN ("uefa.super_cup"); 2013 de las dos (ESPN no trae goles ni
    formaciones). No se jugó en 1974, 1981 y 1985. Cada edición es el año del partido (no una temporada).
  - 1972 no es oficial: se ve con nota pero sin campeón y fuera de las estadísticas (`no_oficiales` en `copas.py`,
    `notaEst` en `app.js`). 1980: Valencia campeón por gol de visitante (`campeones_supercopa`).
  - Clubes unidos: `kv-mechelen` → `mechelen`, `sv-werder-bremen` → `werder-bremen`.
  - Trofeo: foto del museo del Barcelona (Rafael Curtinaz Severo, CC BY 2.0). Portada de Europa con link.
  - `actualizar_europa.py` (tarea programada) también baja la Supercopa del año.
- **Lectores:** Wikipedia entiende fechas `1993-09-29` y resultados con el signo "−"; ESPN: la Recopa y la Supercopa
  son siempre "Final". Estadísticas con mínimo de partidos bajo para estas copas.
- README actualizado (fuentes, comandos y créditos de las fotos).

## Estado al cerrar

Todo commiteado y subido a GitHub. Las 71 pruebas pasan. Probado en el navegador (computadora y celular): ediciones,
estadísticas y portadas de las dos copas. Las demás copas no cambiaron.

## Pendiente / próximos pasos

- Técnicos de la Supercopa de Europa desde 2005 (salvo 2013): no hay fuente cargada.
- Cargar la Recopa 2027 (febrero): `descargar_espn.py --copa recopa 2027` y `generar_datos.py`.
- Pendientes anteriores: GitHub Pages y Google Search Console, ~200 escudos de clubes chicos europeos, técnicos y
  planteles del Mundial de Clubes, ligas nacionales.
