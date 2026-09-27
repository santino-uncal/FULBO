# Fase 04

**Fecha:** 2026-09-26

## Commits

- `a97a3b6` Goleadores y asistidores: ahora van después de las fechas y antes de los planteles
- `83ca3b9` Fase eliminatoria: pestaña al lado de Fase de grupos con el cuadro de llaves hasta la final
- `feb887b` Cuadro eliminatorio: bandera del país de cada equipo
- `f1c38bb` 2018: Independiente-Santos, ida 3-0 por escritorio y vuelta 0-0 suspendida

## Qué se hizo

- **Orden de la página:** Final → tablas de grupos → fases con sus fechas → Goleadores → Asistidores → Planteles.
- **Pestañas "Fase de grupos" / "Fase eliminatoria":** al lado del título de la última etapa de grupos.
  La segunda muestra un cuadro de llaves (`cuadroHTML` y `llaveHTML` en `js/app.js`, estilos al final de
  `css/estilos.css`): una columna por ronda, líneas que unen las llaves, goles de ida/vuelta, total,
  penales entre paréntesis y el ganador en negrita.
  - El árbol se arma hacia atrás desde la final: la llave anterior de cada equipo es la última que jugó.
  - Los equipos "a definir" (2026) toman la primera llave libre de la ronda anterior.
  - Las llaves se ordenan por fase, número de llave y fecha (2002 tiene las fechas mal cargadas).
  - Si varias rondas comparten el nombre de fase (2002, "Segunda fase"), se titulan Octavos/Cuartos/Semis.
  - Sin eliminación directa antes de la final (1971–1987), no aparece la pestaña.
- **Banderas:** `assets/banderas/<PAÍS>.png` (11 países, bajadas de flagcdn.com), a la izquierda del escudo en el cuadro.
- **2018 Independiente–Santos:** ida 3-0 por escritorio (Santos hizo jugar a Carlos Sánchez, suspendido) y
  vuelta 0-0 suspendida a los 81'. Cargado en `"resultados"` de `tools/equipos_ajustes.json` y datos regenerados.
- `.claude/launch.json`: segundo servidor de prueba (`libertadores-2`, puerto 8779) por si el 8778 está ocupado.

## Estado al cerrar

- Todo commiteado y subido a GitHub.

## Pendiente / próximos pasos

- Huecos en el cuadro de 1988, 1990 y 2009 (equipos que entraron directo o partidos que faltan).
- Falta la marca "(v.)" de gol de visitante y los números de cabeza de serie del cuadro (no están en los datos).
- Sigue pendiente activar GitHub Pages y Search Console.
- Revisar a ojo los colores de cada campeón en `data/colores.js`.
