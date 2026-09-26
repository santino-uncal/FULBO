# Historia de la Copa Libertadores

Todas las ediciones desde 1960: resultados, goleadores, asistidores, planteles, escudos y camisetas.

## Cómo verlo

- **Rápido:** doble clic en `index.html`.
- **Con servidor local:**
  ```bash
  python -m http.server 8778
  ```
  y abrir http://localhost:8778

## Estructura del proyecto

| Archivo | Qué contiene | Cuándo tocarlo |
|---|---|---|
| `index.html` | Esqueleto de la página. | Cambios de maquetación. |
| `css/estilos.css` | Estilos y paleta (`:root`). | Colores, tipografías, responsive. |
| `js/app.js` | Lógica: arma la lista de ediciones, partidos y rankings. | Comportamiento e interacción. |
| `data/indice.js` | Lista de años disponibles. | Al agregar una edición. |
| `data/equipos.js` | Catálogo de clubes (nombre, país, escudo). | Agregar/corregir clubes. |
| `data/jugadores.js` | Catálogo de jugadores (un id único por jugador). | Agregar/corregir jugadores. |
| `data/ediciones/<año>.js` | Una edición: fases, partidos, goles, formaciones, planteles. | Cargar resultados. |
| `assets/escudos/<club>.png` | Escudos. | Se bajan con `tools/descargar_escudos.py`. |
| `assets/camisetas/<club>/<año>.png` | Camisetas por temporada. | — |
| `tools/` | Scripts de Python para descargar y convertir datos. | — |

Orden de carga en `index.html`: `indice.js` → `equipos.js` → `jugadores.js` → `app.js`.
Cada edición se carga sola cuando se la elige.

Los **goleadores y asistidores no se escriben a mano**: se calculan a partir de los goles de cada partido.

## Fuentes

- **RSSSF** (rsssf.org/sacups) — resultados, goles y formaciones de todas las ediciones.
- **TheSportsDB** — escudos y camisetas.

## Fases

Cada sesión se cierra con un `fases/fase_NN.md`. Para saber en qué fase vamos, mirá el último archivo de `fases/`.
