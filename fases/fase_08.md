# Fase 08

**Fecha:** 2026-09-27

## Commits

- `89047d0` Planteles: buscador para filtrar por equipo
- `c085550` Estadísticas históricas: goleadores de siempre, de cada edición y de cada mata-mata, títulos, goleadas y más
- `757db45` Estadísticas históricas: el botón pasa al lado del buscador de equipos
- `53696b0` Entrenador de cada equipo en cada edición (Transfermarkt): en planteles, campañas y ficha del club
- `5e78ab5` Años: la lista queda plegada detrás de un botón 📅 con buscador, al lado de Estadísticas

## Qué se hizo

- **Buscador en los planteles:** cuadro "Buscar equipo…" en la sección Planteles de cada edición. Filtra los
  equipos mientras se escribe (sin importar acentos) y avisa si no hay ninguno.
- **Estadísticas históricas** (`?estadisticas`): botón 📊 al lado del buscador de equipos. Página con resumen
  (ediciones, partidos, goles, club y país más ganadores, máximo goleador), máximos goleadores históricos,
  goleador de cada edición, goleadores por instancia (Octavos / Cuartos / Semifinales / Final), clubes y países
  campeones, clubes con más partidos, mayores goleadas, partidos con más goles, jugadores con 3+ goles en un partido,
  máximos asistidores (desde 2005) y promedio de goles por edición con barras. Botones para saltar a cada sección.
  - Se calcula con `tools/generar_estadisticas.py` → `data/estadisticas.js` (se carga al abrir la sección).
    `generar_datos.py` lo llama solo al final. Agregada al `sitemap.xml`.
  - Antes de 2005 las fuentes traen muchas veces solo el apellido: se junta a un jugador en varios clubes solo si
    parece la misma carrera (sin dos clubes el mismo año, sin huecos largos; apellidos comunes no se juntan).
    Por eso Spencer figura con 44 (Peñarol) y no con los 54 oficiales. Aviso en la página.
- **Entrenadores:** cada plantel muestra su DT (o sus DT en orden, si cambió durante la Copa). También en la
  campaña de la ficha del club y en una columna nueva "Entrenador" de "Edición por edición".
  - Fuente: Transfermarkt. `tools/descargar_entrenadores.py` baja los participantes de cada edición (para saber
    el número de cada club en Transfermarkt) y el historial de entrenadores de cada club (titulares e interinos),
    y cruza fechas con los partidos → `data/entrenadores.js`. Caché en `tools/cache/transfermarkt/`.
  - `tools/entrenadores_ajustes.json`: correcciones a mano de clubes con el mismo nombre (dos Nacional, dos River…).
  - Cobertura: 1.533 de 1.856 planteles (83%). Desde 2010 casi 100%, años 2000 90%, 60s–90s entre 50% y 75%.
- **Buscador de años:** la grilla de años ya no se ve siempre. Botón "📅 2026 ▾" al lado de Estadísticas que abre
  un panel con los años y un cuadro para escribir (filtra; Enter abre el año). Se cierra al elegir, al tocar afuera
  o con Esc. En celular, Estadísticas y 📅 comparten renglón debajo del buscador.
- README actualizado (archivos nuevos, fuente Transfermarkt, cómo actualizar entrenadores).

## Estado al cerrar

Todo funcionando y probado en el navegador (compu y celular). Cambios subidos a GitHub.
`.claude/launch.json` tiene una configuración local extra (puerto 8780) que no se commitea.

## Pendiente / próximos pasos

- Activar GitHub Pages y Search Console (sigue pendiente de sesiones anteriores).
- Entrenadores faltantes en ediciones viejas: completar a mano o con otra fuente si se quiere.
- Posible lista de excepciones para goleadores históricos conocidos (ej.: sumar los goles de Spencer en Barcelona).
- El escudo "a-definir" da 404 en la edición en curso (menor).
