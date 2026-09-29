# Fase 14

**Fecha:** 2026-09-28

## Commits

- `620d350` Panel de años: los años agrupados según el nombre que tenía la copa cada año
- `5309c25` y `1d68326` Foto del campeón con la copa al tocar su nombre (se deshizo después)
- `5932740` y `9f2a9a5` Se deshacen los dos commits de las fotos de campeones

## Qué se hizo

- **Panel de años con los nombres de la copa:** los años aparecen agrupados bajo el nombre oficial de cada época.
  - Libertadores: Copa Campeones de América (1960–1964), Copa Libertadores de América (1965–2016),
    Copa Conmebol Libertadores (2017 en adelante).
  - Sudamericana: Copa Sudamericana (2002–2016), Copa Conmebol Sudamericana (2017 en adelante).
  - Al escribir un año se ocultan los grupos sin resultados. Los nombres están en `COPAS` (`js/app.js`).
- **Fotos del campeón levantando la copa:** se armó y se probó (fotos libres de Wikimedia Commons), pero solo había
  fotos útiles de 19 ediciones. El usuario decidió no usarlas y se deshizo todo con `git revert`.

## Estado al cerrar

- El panel de años agrupado por nombre funciona en las dos copas.
- No quedan rastros de las fotos de campeones en la página (el código está en el historial de git por si algún día se retoma).

## Pendiente / próximos pasos

- Activar GitHub Pages y Search Console (sigue pendiente de fases anteriores).
