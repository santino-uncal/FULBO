# Fase 15

**Fecha:** 2026-09-29

## Commits

- `d090cc8` Datos del Mundial de Clubes (2000-2025) y la Copa Intercontinental (1960-2026)
- `c8f82d8` Escudos y banderas de los clubes del Mundial de Clubes y la Intercontinental
- `c997874` Mundial e Intercontinental: entrenadores desde Wikipedia y estadísticas ajustadas
- `7e85d61` Página: Copa Intercontinental y Mundial de Clubes en la cabecera
- `6ecc8f7` Portada con el mapa de América y Europa y pestañas del Mundial y la Intercontinental
- `2795025` Portada: cuadro partido en dos con los mapas de Sudamérica y Europa
- `9760db6` Mapa de Europa: se suman Turquía, Georgia, Armenia y Azerbaiyán
- `26bf571` Mapa de Europa: se suman Israel, Chipre y Kazajistán (hasta los Urales)

## Qué se hizo

- **Dos copas nuevas**, separadas porque en 2000 y 2025 se jugaron las dos el mismo año:
  - **Copa Intercontinental** (`?copa=intercontinental`): 1960–2004 desde Wikipedia (goles con minuto, formaciones
    con cambios, técnicos, árbitro, estadio, público; `tools/descargar_wikipedia.py` y `tools/leer_wikipedia.py`)
    y la Intercontinental de la FIFA desde 2024 desde ESPN (Primera ronda, Copa África-Asia-Pacífico, Derbi de las
    Américas, Copa Challenger, Final).
  - **Mundial de Clubes** (`?copa=mundial`): 2000 desde Wikipedia (sin formaciones) y 2005–2025 desde ESPN, incluido
    el de 32 equipos de 2025 (grupos sacados de la tabla de ESPN, `grupos.json`).
  - Todos los campeones coinciden con los oficiales. Configuración en `tools/copas.py` (claves `wikipedia`, `espn_desde`).
- **Clubes de otros continentes:** país (`pais_espn`), uniones de números de ESPN repetidos (`espn`) y nombres en
  castellano en `tools/equipos_ajustes.json`. Los sudamericanos se unieron solos con los de la Libertadores.
  Estadios en castellano en `tools/estadios.json` (se puede poner la copa adelante: `mundial|Estadio Nacional`).
- **Escudos** (`ESCUDOS_A_MANO` en `descargar_escudos.py`), **banderas** (`tools/descargar_banderas.py`, flagcdn) y
  **fotos de los trofeos** (Wikimedia Commons, créditos en el README; fondo sacado con `rembg`).
- **Entrenadores de la Intercontinental** sacados de las formaciones de Wikipedia (`entrenadores_de_formaciones`
  en `generar_datos.py`). Estadísticas: promedio de gol con menos partidos mínimos en estas copas, "Segunda ronda"
  del Mundial cuenta como cuartos, y goles de un mismo jugador juntados aunque juegue salteado (Cristiano Ronaldo: 7).
- **Portada nueva** (la dirección sin copa): cuadro partido en dos con los mapas de **Sudamérica** y **Europa**
  (`tools/generar_mapa.py` → `data/mapa.js`, Natural Earth). Europa incluye Turquía, Georgia, Armenia, Azerbaiyán,
  Israel, Chipre y Kazajistán, cortada en los Urales. Al tocar un continente (`?continente=europa`) aparecen sus copas
  internacionales (Libertadores y Sudamericana con link, el resto "próximamente"), los títulos de sus clubes en el
  Mundial y la Intercontinental, y sus ligas nacionales ("próximamente"). Datos a mano en `data/continentes.js`.
- **Pestañas arriba** en todas las páginas: Continentes, Mundial de Clubes, Copa Intercontinental. Cada copa muestra
  solo los trofeos de su familia. La Libertadores ahora es `?copa=libertadores`; los links viejos (`?edicion=1986`)
  siguen andando. Sitemap actualizado.

## Estado al cerrar

Todo commiteado y subido a GitHub. Probado en el navegador (computadora y celular): portada, Mundial 2010 y 2025,
Intercontinental 1961, 1986 y 2024, estadísticas de las dos copas, ficha de Boca. La Libertadores y la Sudamericana
generan exactamente los mismos datos que antes.

## Pendiente / próximos pasos

- Activar GitHub Pages y dar de alta el sitio en Google Search Console (sigue pendiente).
- Técnicos y planteles completos del Mundial de Clubes (Transfermarkt numera distinto las temporadas europeas).
- Al Ahly 0–2 Guangzhou (Mundial 2013): ESPN no trae los autores de los goles.
- Copas "próximamente" de la portada (Recopa, Champions, Europa League…) y ligas nacionales.
- Pendientes anteriores: jugador del torneo de la Sudamericana, ~25 escudos viejos sin encontrar, tandas antes de 2008.
