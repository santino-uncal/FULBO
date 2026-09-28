# Fase 11

**Fecha:** 2026-09-28

## Commits

- `966355e` Planteles: se saltean los jugadores sin nombre (rompían las ediciones 2005-2007)
- `5e00536` Años: botón para volver al último año visto (se recuerda entre visitas)
- `47787fd` Años: botón de último año visto también al lado de las flechas
- `ee275be` Ediciones: debajo del campeón, cuántas veces lo fue hasta ese año

## Qué se hizo

- **Arreglo 2005, 2006 y 2007:** esas ediciones mostraban "Cannot read properties of undefined (reading
  'localeCompare')". Causa: algunas formaciones de ESPN traen jugadores sin nombre (7 en total) y al ordenar el
  plantel se rompía. La página ahora los saltea (`js/app.js`) y `tools/generar_datos.py` ya no los suma al
  regenerar (este segundo cambio no se probó porque no se regeneraron los datos).
- **Botón "último año visto":** "↩ 2006" al lado de las flechas ◀ ▶ y "↩ Último visto: 2006" dentro del panel
  de años, al lado del buscador. Lleva al año que se miraba antes del actual; se guarda en el navegador de cada
  persona (`localStorage`, clave `aniosVistos`), así que se acuerda entre visitas. Sin año anterior no aparece.
- **Veces campeón:** debajo del campeón de cada edición, en letra chica, cuántas Copas llevaba contando esa
  (River 2018: "4 veces campeón"; Grêmio 1983: "1 vez campeón"). Solo al campeón.

## Estado al cerrar

Todo commiteado y subido a GitHub. Probado en el navegador: 2005-2007 cargan con planteles y orden; botón de último
año (ida y vuelta 1986 ↔ 2006, también en tamaño celular sin desborde); "4 veces campeón" en 2018.
Quedan sin commitear cambios previos en `.claude/launch.json` y `sitemap.xml` (no son de esta sesión).

## Pendiente / próximos pasos

- Activar GitHub Pages y dar de alta el sitio en Google Search Console.
- Cargar el jugador del torneo 2026 cuando termine la Copa (`data/jugador-torneo.js`).
- Regenerar los datos para que los jugadores sin nombre desaparezcan también de `data/ediciones/*.js`.
- Planteles recientes muy largos (ej. Flamengo 2025: 76); ver si conviene mostrar solo los que jugaron la Copa.
- Decidir si las columnas de años también van centradas.
