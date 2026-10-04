# Fase 28

**Fecha:** 2026-10-04

## Commits

- `597307f` Liga argentina: buscador de años (📅) y flechas ◀ ▶ para pasar al año anterior o siguiente, igual que en la Libertadores
- `2ad3f27` Liga argentina: pestaña de máximos asistidores (desde el Inicial 2013)
- `191cc96` Liga argentina: en goleadores y asistidores se ve el club con su escudo (la columna quedaba aplastada)

## Qué se hizo

- **Buscador de años en la liga argentina**, como en la Libertadores.
  - La fila con todos los años se cambió por **◀ 📅 año ▾ ▶**:
    - ◀ y ▶ llevan al año anterior o siguiente (apagadas en 1990 y en el último año);
    - 📅 abre un panel con los años agrupados por década y un cuadro para escribir el año (filtra mientras se
      escribe, Enter abre el elegido, Escape o tocar afuera lo cierra).
  - Debajo siguen los botones de los torneos del año (Apertura, Clausura…).
  - Código en `js/liga.js`. Reusa los estilos del panel de años de la Libertadores (`css/estilos.css`).
- **Pestaña "Asistidores"** al lado de "Goleadores": los 40 con más asistencias del torneo.
  - Sale del campo `asistencia` de cada gol, que ESPN tiene desde el Inicial 2013. En los torneos de antes, la
    pestaña no aparece.
  - Como ESPN da solo el nombre del que asiste, el club que se muestra es el del que hizo el gol.
- **Escudos en goleadores y asistidores:** la columna "Club" quedaba aplastada (las dos columnas de texto pedían
  todo el ancho) y no se veía. Ahora se reparten el ancho por la mitad.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Probado en el navegador: las flechas, el buscador de
años, la pestaña de asistidores (Clausura 2026; no aparece en el Apertura 1997) y los escudos en goleadores.

## Pendiente / próximos pasos

- Al terminar el Clausura 2026 (y cada torneo nuevo), agregar su campeón a `data/ligas/argentina/titulos.js` (la
  prueba avisa).
- Pendientes anteriores:
  - 1989 (Campeonato 1988-89, con penales después de cada empate);
  - goleadores del Clausura 1996 con el nombre escrito de dos formas;
  - goles que faltan (1996-2006);
  - cupos 2021;
  - Sudamericana 2014;
  - torneos de 2027;
  - otras ligas;
  - GitHub Pages y Google Search Console.
