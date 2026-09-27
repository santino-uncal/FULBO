# Historia de la Copa Libertadores

Todas las ediciones desde 1960: resultados, goleadores, asistidores, planteles y escudos.

## Cómo verlo

- **Publicado:** https://santino-uncal.github.io/FULBO/ (GitHub Pages). Cada edición tiene su link: `?edicion=1986`, y cada club el suyo: `?equipo=river-plate`.
  `sitemap.xml` (lo arma `tools/generar_datos.py`) y `robots.txt` le indican a Google qué páginas indexar.

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
| `js/app.js` | Lógica: lista de ediciones, partidos, rankings y planteles. | Comportamiento e interacción. |
| `data/indice.js` | Años disponibles con campeón y subcampeón. | **Generado** — no editar a mano. |
| `data/equipos.js` | Catálogo de clubes (nombre, país, ciudad, escudo, colores). | **Generado**. |
| `data/historial.js` | Historia de cada club (ediciones, títulos, partidos, rivales, goleadores) para el buscador. Se carga recién al usar el buscador. | **Generado** (`tools/generar_historial.py`). |
| `data/entrenadores.js` | Entrenador(es) de cada club en cada edición. | **Generado** (`tools/descargar_entrenadores.py`). |
| `data/estadisticas.js` | Estadísticas históricas (goleadores de siempre, por edición y por instancia, títulos, goleadas…). Se carga al tocar "Estadísticas históricas" (`?estadisticas`). | **Generado** (`tools/generar_estadisticas.py`). |
| `data/ediciones/<año>.js` | Una edición: fases, partidos, goles, formaciones, planteles. | **Generado**. |
| `assets/escudos/<club>.png` | Escudos. | Se bajan con `tools/descargar_escudos.py`. |
| `tools/` | Scripts de Python que descargan y arman los datos. | Ver abajo. |

La página carga cada edición recién cuando se la elige. Los **goleadores y asistidores no se escriben
a mano**: se calculan a partir de los goles de cada partido.

## De dónde salen los datos

| Años | Fuente | Qué trae |
|---|---|---|
| 1960–2004 | **RSSSF** (rsssf.org) | Resultados, goleadores, formaciones de las finales. |
| 2005–2024 | **RSSSF + ESPN** | RSSSF da la lista completa de partidos; ESPN agrega goles con minuto, asistencias, formaciones, árbitro y público. |
| 2025 en adelante | **ESPN** | Todo lo anterior. |
| Todos | **Transfermarkt** | El entrenador de cada equipo en cada edición (cruzando su historial de entrenadores con las fechas de los partidos). |

Los datos de RSSSF son de Juan Pablo Andrés, Pablo Ciullini y Frank Ballesteros (Rec.Sport.Soccer
Statistics Foundation), que permiten copiarlos citando a los autores.

## Actualizar los datos

```bash
python tools/descargar_rsssf.py     # baja las páginas nuevas de RSSSF
python tools/descargar_espn.py      # baja partidos de ESPN (la 1ra vez tarda ~2 horas)
python tools/generar_datos.py       # arma data/ y muestra un control de calidad por año
python tools/descargar_escudos.py   # baja los escudos que falten
python tools/descargar_entrenadores.py  # entrenadores de cada equipo (Transfermarkt), arma data/entrenadores.js
```

Para la temporada en curso alcanza con `python tools/descargar_espn.py 2026` y después `generar_datos.py`.

### Corregir clubes

`tools/equipos_ajustes.json` guarda las correcciones manuales:

- `alias`: unir nombres distintos del mismo club (`"Atl. Nacional|COL": "atletico-nacional"`).
- `pais_por_nombre`: el país de un club cuando la fuente no lo dice.
- `nombres`: el nombre que se muestra en la web.
- `campeones`: forzar campeón y subcampeón de un año (`"1960": ["penarol", "olimpia"]`), por si hiciera falta.

Después de tocarlo, volver a correr `generar_datos.py`.

`tools/entrenadores_ajustes.json` dice a qué club de Transfermarkt corresponde cada club nuestro cuando el
emparejamiento automático se confunde (dos "Nacional", dos "River Plate"…): `"nacional-par": 7098`.

## Fases

Cada sesión se cierra con un `fases/fase_NN.md`. Para saber en qué fase vamos, mirá el último archivo de `fases/`.
