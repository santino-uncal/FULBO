# Fase 12

**Fecha:** 2026-09-28

## Commits

- `34a7097` Scripts: las descargas y el generador sirven para la Libertadores y la Sudamericana
- `514cd2e` Página: selector Copa Libertadores / Copa Sudamericana en la cabecera; ediciones, clubes y estadísticas de cada copa
- `d3d6e92` Datos de la Copa Sudamericana 2002-2026 (RSSSF + ESPN + Transfermarkt), clubes unificados con la Libertadores
- `6815d5b` Sudamericana: el ejemplo del buscador de años es 2014

## Qué se hizo

- **Copa Sudamericana completa (2002–2026):** mismas fuentes que la Libertadores (RSSSF hasta 2024, ESPN desde
  2005, Transfermarkt para entrenadores y planteles). Datos en `data/sudamericana/` (`window.SUD`); los clubes son
  los mismos para las dos copas (`data/equipos.js`).
- **Cabecera:** "Copa Libertadores" y "Copa Sudamericana" con la misma letra; la actual resaltada, la otra apagada
  y lleva a esa copa. Dirección: `?copa=sudamericana` (`&edicion=2014`, `&equipo=lanus`, `&estadisticas`).
  "Desde 2002", sin el lema "La Gloria Eterna" y ejemplo de año 2014 en la Sudamericana.
- **Scripts:** `tools/copas.py` dice dónde vive cada cosa de cada copa; los de descarga aceptan
  `--copa sudamericana`; `generar_datos.py` arma las dos copas juntas. Comprobado que las 67 ediciones de la
  Libertadores salen idénticas a las del generador anterior.
- **Página:** ediciones sin grupos (Sudamericana hasta 2020) muestran el cuadro completo; desde 2023 se marca
  quién va directo a octavos y quién a los playoffs; nota visible en ediciones especiales (2007 gol de visitante,
  2016 Chapecoense); récord de títulos compartido en estadísticas.
- **Ajustes a mano** (`tools/equipos_ajustes.json`): ~50 alias de clubes, `campeones_sudamericana`,
  `notas_ediciones`; ids de Transfermarkt en `entrenadores_ajustes.json`. Erratas de RSSSF corregidas al leer
  ("Ap 3:", "May 4;", "1–1" con guion largo, siglas "CS/CD/CA…").
- Banderas nuevas: Estados Unidos, Costa Rica, Honduras. Colores de los campeones de la Sudamericana.
- Arreglo viejo: Verón (jugador del torneo 2009) figuraba con Estudiantes de Mérida.

## Estado al cerrar

Todo commiteado y subido a GitHub. Probado en el navegador: Sudamericana 2024 (grupos, playoffs), 2010 (cuadro),
2016 (nota), ficha de Lanús, estadísticas; la Libertadores sigue igual.

## Pendiente / próximos pasos

- Activar GitHub Pages y dar de alta el sitio en Google Search Console.
- Cargar el campeón y el jugador del torneo 2026 cuando terminen las copas.
- Jugador del torneo de la Sudamericana (no hay lista cargada).
- ~25 escudos sin encontrar (sobre todo clubes viejos); formaciones y goleadores de las finales 2002–2004 de la
  Sudamericana (RSSSF las trae en otro formato que no se lee).
- Pendientes anteriores: planteles recientes muy largos; columnas de años centradas.
