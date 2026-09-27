# Fase 05

**Fecha:** 2026-09-27

## Commits

- `b41f310` Fases eliminatorias: ordenar partidos por llave (ida y vuelta juntas) o por fecha
- `a9deb1c` Planteles: estadio de cada equipo al lado del nombre
- `e2396cd` Planteles: en ediciones sin estadios, usar el estadio del club de años posteriores
- `eced417` Cuadro de la fase previa: pestaña al lado de Fase de grupos con las llaves hasta la fase de grupos
- `9ab51d7` 2018: corregidas las fechas de la primera fase previa (sin partidos duplicados ni en la fase equivocada)
- `a3800ed` Estadios: nombres unificados y corregidos (sin errores de tipeo ni patrocinadores), con su ciudad
- `d69f1c9` Tablas de grupos: los que pasan de fase, en verde oscuro
- `26e4f08` Últimos partidos: victoria en verde
- `db181e5` Últimos partidos: tilde, guion y cruz en vez de V, E y D

## Qué se hizo

- **Orden de los partidos en fases eliminatorias:** botones "Por llave / Por fecha" dentro de cada fase
  (`eliminatoriaHTML` en `js/app.js`). La elección vale para todas las fases y se recuerda en el navegador
  (localStorage). En fases de partido único no aparecen los botones.
- **Estadio en Planteles:** al lado de cada equipo, la cancha donde más jugó de local esa edición (sin contar
  finales, que pueden ser en cancha neutral). Antes de 2005 las fuentes no traen estadios: se usa el campo
  `estadio` de `data/equipos.js`, que `tools/generar_datos.py` calcula con la primera edición posterior que lo tenga.
- **Cuadro de la fase previa:** pestaña "Fase previa" a la izquierda de "Fase de grupos" (`cuadroPreviaHTML`).
  El dibujo del árbol se separó en `juntarLlaves` + `dibujarCuadro` y lo comparten los dos cuadros.
  Casillas vacías (equipos que entran directo) sin líneas; corchetes a medias cuando solo hay una llave.
  No aparece en 1998–2003 (la previa fue un mini torneo México–Venezuela, no llaves).
- **2018, primera fase previa:** el lector de RSSSF (`tools/leer_rsssf.py`) tomaba el "1" de
  "Qualifying Round 1 (Jan 22 & 26)" como 1 de enero; ahora solo lee las fechas entre paréntesis. Solo cambió 2018.
- **Nombres de estadios:** nueva lista `tools/estadios.json` (nombre, ciudad, variantes de las fuentes) que el
  generador aplica en `unificar_estadios`. De ~300 nombres quedaron 179. A los que no están en la lista se les
  saca el "Estadio" de adelante. Formato en pantalla: "Nombre, Ciudad".
- **Tablas de grupos:** los que pasan de fase en verde oscuro (`--pasa`); Sudamericana sigue celeste.
  Últimos partidos: ✓ verde (victoria), – gris (empate), ✕ rojo (derrota).

## Estado al cerrar

- Todo commiteado y subido a GitHub.

## Pendiente / próximos pasos

- Estadios sin resolver (9 partidos): "Alfredo Stroessner" (Libertad 2005), "São Paulo" (Palmeiras 2000),
  "Tacuary" y "Vaca Guzmán" (Real Potosí 2007).
- Huecos en el cuadro de 1988, 1990 y 2009 (equipos que entraron directo o partidos que faltan).
- Falta la marca "(v.)" de gol de visitante y los números de cabeza de serie del cuadro.
- Sigue pendiente activar GitHub Pages y Search Console.
- Revisar a ojo los colores de cada campeón en `data/colores.js`.
