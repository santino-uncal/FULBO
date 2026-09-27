# Fase 07

**Fecha:** 2026-09-27

## Commits

- `0ae694b` Planteles: ordenar por posición o por nombre
- `acd8ce6` Planteles: contemplar posiciones RCM y '-' al ordenar
- `9fd86eb` Planteles: posiciones en castellano (Arquero, Lateral derecho…)
- `57c2ef3` Partidos: goles del local a la izquierda y del visitante a la derecha
- `2606d0c` Grupos: botones 'Ir a: Fecha N' para saltar a una fecha
- `d4eb072` Grupos: en cada fecha, botones para volver al inicio o saltar a otra fecha
- `ac60122` Ficha de equipo: botón Ver en cada edición con su campaña

## Qué se hizo

- **Planteles ordenables:** botones "Por posición" / "Por nombre" arriba de los planteles de cada edición.
  Por posición = arquero → defensores → volante central → volantes → enganches → delanteros → sin posición
  (`lineaDe` en `js/app.js`); dentro de cada línea, alfabético. La elección se guarda en el navegador (`ordenPlantel`).
- **Posiciones en castellano:** las siglas en inglés de las fuentes (G, CD-L, AM…) se muestran como
  "Arquero", "Defensor central izq.", "Enganche (10)"… (`POSICIONES` / `nombrePos`). La columna ahora dice "Posición".
- **Goles de cada lado:** en cada partido, los goles del local van a la izquierda y los del visitante a la derecha
  (`golesPartido`). Los goles en contra van del lado del equipo al que le suman. La asistencia va en un renglón chico abajo.
- **Navegación por fechas en los grupos:** arriba de cada grupo, "Ir a: Fecha 1 … Fecha N". Debajo del título de
  cada fecha (desde la 2) la misma barra con "↑ Inicio" (vuelve al título del grupo) y la fecha actual resaltada.
- **Campaña por edición en la ficha del equipo:** en "Edición por edición", botón "Ver" en cada año que despliega
  rendimiento de local y de visitante, goleadores, asistidores, todos los partidos por fase y el plantel.
  La edición se carga recién al tocar "Ver" (`campaniaHTML`). La tabla del plantel se reutiliza (`tablaPlantel`).

## Estado al cerrar

- Todo commiteado y subido a GitHub.

## Pendiente / próximos pasos

- Ediciones viejas: los planteles no traen posiciones, así que "Por posición" ordena solo por nombre.
- Finales en cancha neutral: en la campaña cuentan como "de local" o "de visitante" según figuren en los datos.
- Sigue lo pendiente de la fase 06: fichas de equipos en `sitemap.xml`, estadios sin resolver, huecos en
  cuadros de 1988/1990/2009, y activar GitHub Pages y Search Console.
