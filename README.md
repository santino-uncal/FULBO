# Historia de la Copa Libertadores, la Sudamericana, la Intercontinental, el Mundial de Clubes y la Champions League

Todas las ediciones de la Libertadores desde 1960, de la Sudamericana desde 2002, de la Copa Intercontinental
desde 1960 y del Mundial de Clubes desde 2000, y las temporadas 2024/25 y 2025/26 de la Champions League: resultados, goleadores, asistidores, planteles y escudos.

## Cómo verlo

- **Publicado:** https://santino-uncal.github.io/FULBO/ (GitHub Pages). La portada es un cuadro partido en dos, con los mapas de Sudamérica y Europa: tocando un
  continente (`?continente=sudamerica`) aparecen sus copas internacionales, sus ligas nacionales (próximamente) y los títulos
  de sus clubes en el Mundial y la Intercontinental. Arriba, en todas las páginas, están las pestañas Continentes,
  Mundial de Clubes e Intercontinental.
  La Libertadores es `?copa=libertadores`; cada edición tiene su link: `?edicion=1986`, y cada club el suyo: `?equipo=river-plate`.
  La Sudamericana es la misma página con `copa=sudamericana` adelante: `?copa=sudamericana`, `?copa=sudamericana&edicion=2014`,
  `?copa=sudamericana&equipo=lanus`, `?copa=sudamericana&estadisticas`. Lo mismo con `copa=intercontinental` y `copa=mundial`
  (`?copa=mundial&edicion=2012`). En la cabecera, tocando el nombre de otra copa se cambia de copa.
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
| `js/app.js` | Lógica: lista de ediciones, partidos, rankings y planteles (de la copa que diga la dirección). | Comportamiento e interacción. |
| `data/equipos.js` | Catálogo de clubes de todas las copas (nombre, país, ciudad, escudo, colores). | **Generado**. |
| `data/colores.js` | Colores de cada campeón para vestir la página. | A mano. |
| `data/continentes.js` | Los continentes de la portada: confederación, copas internacionales (con link si ya están cargadas), ligas nacionales y países. | A mano. |
| `data/mapa.js` | Los mapas de Sudamérica y Europa de la portada (fuente: Natural Earth, dominio público). | **Generado** (`tools/generar_mapa.py`). |
| `data/jugador-torneo.js` | Mejor jugador de cada Libertadores. | A mano. |
| `data/indice.js` | Años disponibles con campeón y subcampeón. | **Generado** — no editar a mano. |
| `data/historial.js` | Historia de cada club (ediciones, títulos, partidos, rivales, goleadores) para el buscador. Se carga recién al usar el buscador. | **Generado** (`tools/generar_historial.py`). |
| `data/entrenadores.js` | Entrenador(es) de cada club en cada edición. | **Generado** (`tools/descargar_entrenadores.py`). |
| `data/estadisticas.js` | Estadísticas históricas (goleadores de siempre, por edición y por instancia, títulos, goleadas…). Se carga al tocar "Estadísticas históricas" (`?estadisticas`). | **Generado** (`tools/generar_estadisticas.py`). |
| `data/ediciones/<año>.js` | Una edición: fases, partidos, goles, formaciones, planteles. | **Generado**. |
| `data/sudamericana/…` | Lo mismo para la Sudamericana (`indice.js`, `historial.js`, `entrenadores.js`, `estadisticas.js`, `ediciones/<año>.js`). | **Generado**. |
| `data/champions/…` | La Champions League (solo 2024/25 y 2025/26). Cada edición lleva el año en que empieza la temporada (`ediciones/2024.js` es la 2024/25; en la página, `?copa=champions&edicion=2024`). | **Generado**. |
| `data/intercontinental/…`, `data/mundial/…` | Lo mismo para la Copa Intercontinental y el Mundial de Clubes. Los entrenadores de la Intercontinental salen de las formaciones de Wikipedia; el Mundial todavía no tiene. | **Generado**. |
| `assets/escudos/<club>.png` | Escudos. | Se bajan con `tools/descargar_escudos.py`. |
| `assets/banderas/<país>.png` | Banderas (código de la FIFA: `ARG`, `ENG`…). | Se bajan con `tools/descargar_banderas.py`. |
| `tools/` | Scripts de Python que descargan y arman los datos. `tools/copas.py` dice dónde vive cada cosa de cada copa. | Ver abajo. |

La página carga cada edición recién cuando se la elige. Los **goleadores y asistidores no se escriben
a mano**: se calculan a partir de los goles de cada partido.

## De dónde salen los datos

| Años | Fuente | Qué trae |
|---|---|---|
| hasta 2004 | **RSSSF** (rsssf.org) | Resultados, goleadores, formaciones de las finales. |
| 2005–2024 | **RSSSF + ESPN** | RSSSF da la lista completa de partidos; ESPN agrega goles con minuto, asistencias, formaciones, árbitro y público. |
| 2025 en adelante | **ESPN** | Todo lo anterior. |
| Todos | **Transfermarkt** | El entrenador de cada equipo en cada edición (cruzando su historial de entrenadores con las fechas de los partidos) y el plantel de cada temporada. |

Vale igual para la Libertadores y la Sudamericana (la Sudamericana empieza en 2002).

La **Copa Intercontinental** y el **Mundial de Clubes** tienen otras fuentes:

| Copa | Años | Fuente |
|---|---|---|
| Intercontinental | 1960–2004 | **Wikipedia** (en inglés): goles con minuto, formaciones con los cambios, entrenadores, árbitro, estadio y público. |
| Intercontinental de la FIFA | 2024 en adelante | **ESPN**. |
| Mundial de Clubes | 2000 | **Wikipedia** (sin formaciones). |
| Mundial de Clubes | 2005 en adelante | **ESPN** (incluye el de 32 equipos de 2025). |
| Champions League | 2024/25 y 2025/26 | **ESPN** (desde la fase de liga; sin las fases previas). Qué temporadas se cargan lo dice `ediciones` en `tools/copas.py`. |

Los textos de Wikipedia tienen licencia CC BY-SA. Los clubes de otros continentes llevan su país y su nombre en
castellano en `tools/equipos_ajustes.json` (`pais_espn` y `nombres`), y los estadios en `tools/estadios.json`.
Los datos de RSSSF de la Libertadores son de Juan Pablo Andrés, Pablo Ciullini y Frank Ballesteros, y los de la
Sudamericana de Karel Stokkermans, Osvaldo José Gorgazzi y otros (Rec.Sport.Soccer Statistics Foundation), que
permiten copiarlos citando a los autores.

## Actualizar los datos

Cada script de descarga trabaja con la Libertadores; con `--copa sudamericana` (o `intercontinental`, o `mundial`),
con esa copa. `generar_datos.py` arma todas las copas juntas (los clubes son los mismos).

```bash
python tools/descargar_rsssf.py     # baja las páginas nuevas de RSSSF
python tools/descargar_espn.py      # baja partidos de ESPN (la 1ra vez tarda ~2 horas)
python tools/descargar_rsssf.py --copa sudamericana
python tools/descargar_espn.py --copa sudamericana
python tools/generar_datos.py       # arma data/ (las dos copas) y muestra un control de calidad por edición
python tools/descargar_escudos.py   # baja los escudos que falten
python tools/descargar_entrenadores.py  # entrenadores de cada equipo (Transfermarkt), arma data/entrenadores.js
python tools/descargar_entrenadores.py --copa sudamericana
python tools/descargar_planteles.py     # planteles de Transfermarkt
python tools/descargar_planteles.py --copa sudamericana
python tools/descargar_wikipedia.py --copa intercontinental   # Intercontinental 1960-2004 (una sola vez)
python tools/descargar_wikipedia.py --copa mundial            # Mundial 2000 (una sola vez)
python tools/descargar_espn.py --copa intercontinental
python tools/descargar_espn.py --copa mundial
python tools/descargar_espn.py --copa champions      # baja los años de "espn_anios" en tools/copas.py
python tools/descargar_banderas.py  # banderas de los países nuevos
```

Para la temporada en curso alcanza con `python tools/descargar_espn.py 2026` (y `--copa sudamericana 2026`)
y después `generar_datos.py`.

### Corregir clubes

`tools/equipos_ajustes.json` guarda las correcciones manuales:

- `alias`: unir nombres distintos del mismo club (`"Atl. Nacional|COL": "atletico-nacional"`).
- `pais_por_nombre`: el país de un club cuando la fuente no lo dice.
- `nombres`: el nombre que se muestra en la web.
- `campeones`: forzar campeón y subcampeón de un año de la Libertadores (`"1960": ["penarol", "olimpia"]`), por si hiciera falta.
  `campeones_sudamericana`: lo mismo para la Sudamericana (2007 se definió por gol de visitante y la final de 2016 no se jugó).
- `pais_espn`: el país de un club que solo aparece en ESPN (los del Mundial de Clubes).
- `espn`: unir un club de ESPN a uno nuestro (ESPN tiene al Al Ahly con dos números, por ejemplo).

Después de tocarlo, volver a correr `generar_datos.py`.

`tools/entrenadores_ajustes.json` dice a qué club de Transfermarkt corresponde cada club nuestro cuando el
emparejamiento automático se confunde (dos "Nacional", dos "River Plate"…): `"nacional-par": 7098`.

## Pruebas

Doble clic en `probar.bat` (o `py -m unittest discover tests`). Conviene correrlas después de `generar_datos.py`.

- `tests/test_herramientas.py`: las funciones de `tools/` (leer goles, fechas y formaciones de RSSSF, Wikipedia y
  ESPN; quién gana una llave; nombres de clubes; estadísticas).
- `tests/test_datos.py`: que los datos de `data/` sean coherentes en las cuatro copas (el índice coincide con las
  ediciones, el campeón jugó la final, todos los clubes están en el catálogo, los penales y las tandas cuadran…).

Al final dice `OK` si todo anda. Hoy hay una "expected failure" (falla conocida): en unos 400 partidos viejos de
RSSSF los goles del visitante quedaron anotados al local.

## Créditos de imágenes

Trofeos de la cabecera (`assets/img/`), de Wikimedia Commons:
- Copa Libertadores: [Mathiaseditorxd](https://commons.wikimedia.org/wiki/File:328-3287452_copa-libertadores-primer-trofeo-hd-png-download.png), CC BY-SA 4.0.
- Copa Sudamericana: [ChapeTerror](https://commons.wikimedia.org/wiki/File:Ta%C3%A7a_da_Copa_Sul-Americana_de_2016.jpg), CC BY-SA 4.0
  (recortada del fondo y achicada).
- Copa Intercontinental (la de Boca, exhibida en La Plata): [BugWarp](https://commons.wikimedia.org/wiki/File:Intercontinental_de_Boca_exhibida_en_el_Dardo_Rocha_01.jpg),
  CC BY 4.0 (recortada del fondo y achicada).
- Mundial de Clubes (en el museo de Anfield): [Daniel from Glasgow](https://commons.wikimedia.org/wiki/File:Anfield_Stadium_Tour_(51930554120).jpg),
  CC BY 2.0 (recortada del fondo y achicada).

Banderas: [flagcdn.com](https://flagcdn.com) (dominio público); la de Yugoslavia, de Wikimedia Commons.

## Fases

Cada sesión se cierra con un `fases/fase_NN.md`. Para saber en qué fase vamos, mirá el último archivo de `fases/`.
