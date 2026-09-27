# Fase 06

**Fecha:** 2026-09-27

## Commits

- `98f05b3` Buscador de equipos con la historia de cada club en la Copa
- `e9b061e` Ficha de equipo: números centrados debajo de su columna
- `d3f716f` El título Copa Libertadores lleva a la edición actual
- `498345c` Título Copa Libertadores: también funciona abriendo index.html con doble clic
- `7621bac` Ficha de equipo: mejor y peor participación

## Qué se hizo

- **Buscador de equipos:** cuadro arriba de los años (`index.html`, `.buscador`). Al escribir ("river") lista los
  clubes que coinciden, sin importar tildes, con cantidad de ediciones y títulos. Flechas + Enter y Esc funcionan.
  Al elegir uno se abre su ficha con dirección propia (`?equipo=river-plate`), que también anda con el botón "atrás".
- **Ficha del equipo** (`mostrarEquipo` en `js/app.js`): ediciones jugadas, títulos, finales perdidas, partidos
  (G/E/P), goles, % de puntos, mejor y peor participación, mayor goleada y peor derrota, tabla edición por
  edición (campeón en dorado), rivales más frecuentes y goleadores del club. Años y rivales son links.
  Si el club fue campeón alguna vez, la página toma sus colores.
- **Datos nuevos:** `data/historial.js` (~460 KB, 245 clubes), generado por `tools/generar_historial.py` a partir de
  `data/ediciones/*.js`. `generar_datos.py` lo llama al final. La página lo baja recién al usar el buscador.
- **Mejor / peor participación:** se calcula en la página con `NIVEL_FASE` (previas → grupos → … → campeón).
  "Primera fase" (nombre viejo) cuenta igual que "Fase de grupos". La edición en juego no cuenta para la peor.
- **Título "Copa Libertadores":** es un link a la edición actual. Usa `location.pathname` porque con `./`
  no funcionaba al abrir `index.html` con doble clic.
- Tablas de la ficha: números centrados bajo su título.

## Estado al cerrar

- Todo commiteado y subido a GitHub.

## Pendiente / próximos pasos

- Confirmar que el título lleva a la edición actual abriendo `index.html` con doble clic (no se pudo probar acá).
- Goleadores del club: en ediciones viejas RSSSF trae solo apellidos ("D.Onega"), así que un mismo jugador puede
  aparecer dos veces si en otra fuente figura con nombre completo.
- Sumar las fichas de equipos (`?equipo=…`) al `sitemap.xml` para Google.
- Estadios sin resolver (Libertad 2005, Palmeiras 2000, Real Potosí 2007) y huecos en los cuadros de 1988, 1990 y 2009.
- Sigue pendiente activar GitHub Pages y Search Console.
