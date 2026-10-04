# Historia de la Copa Libertadores, la Sudamericana, la Recopa, la Intercontinental, el Mundial de Clubes, la Champions League, la Europa League, la Conference League y la Supercopa de Europa

Todas las ediciones de la Libertadores desde 1960, de la Sudamericana desde 2002, de la Recopa Sudamericana desde 1989, de la Copa Intercontinental
desde 1960 y del Mundial de Clubes desde 2000, de la Champions League (Copa de Campeones de Europa hasta 1992) desde 1955/56 de la Europa League (Copa UEFA hasta 2009) desde 1971/72 de la Conference League desde 2021/22 y de la Supercopa de Europa desde 1972: resultados, goleadores, asistidores, planteles y escudos.

## Cómo verlo

- **Publicado:** https://santino-uncal.github.io/FULBO/ (GitHub Pages). La portada es un cuadro partido en dos, con los mapas de Sudamérica y Europa: tocando un
  continente (`?continente=sudamerica`) aparecen sus copas internacionales, sus ligas nacionales (próximamente) y los títulos
  de sus clubes en el Mundial y la Intercontinental. Arriba, en todas las páginas, están las pestañas Continentes,
  Mundial de Clubes e Intercontinental.
  La Libertadores es `?copa=libertadores`; cada edición tiene su link: `?edicion=1986`, y cada club el suyo: `?equipo=river-plate`.
  La Sudamericana es la misma página con `copa=sudamericana` adelante: `?copa=sudamericana`, `?copa=sudamericana&edicion=2014`,
  `?copa=sudamericana&equipo=lanus`, `?copa=sudamericana&estadisticas`. Lo mismo con `copa=recopa`, `copa=intercontinental` y `copa=mundial`
  (`?copa=mundial&edicion=2012`). En la cabecera, tocando el nombre de otra copa se cambia de copa.
  La **Liga Profesional argentina** está en `liga.html` (desde 1987: el Campeonato 1986-87, a 38 fechas, con la Liguilla Pre-Libertadores y el desempate por el descenso; el Campeonato 1987-88, a 38 fechas, con las liguillas Pre-Libertadores y Clasificación y el desempate por el descenso; el Campeonato 1988-89, a 38 fechas, con penales después de cada empate y la Liguilla Pre-Libertadores; el Campeonato 1989-90, a 38 fechas, con la Liguilla Pre-Libertadores y el desempate por el descenso, y el Torneo Apertura 1990, el Torneo Clausura 1991 con la final por el campeonato 1990-91 y la Liguilla Pre-Libertadores y el Torneo Apertura 1991, el Torneo Clausura 1992 con la Liguilla Pre-Libertadores y el Torneo Apertura 1992, el Torneo Clausura 1993 y el Torneo Apertura 1993, el Torneo Clausura 1994 y el Torneo Apertura 1994 (con 2 puntos por partido ganado), el Torneo Clausura 1995 (el último con 2 puntos por partido ganado) y el Torneo Apertura 1995, el Torneo Clausura 1996 con el desempate por la Libertadores y el Torneo Apertura 1996, el Torneo Clausura 1997 con el desempate por la Libertadores y el Torneo Apertura 1997, el Torneo Clausura 1998 y el Torneo Apertura 1998, el Torneo Clausura 1999 con el desempate por la Libertadores y el Torneo Apertura 1999, el Torneo Clausura 2000 con la Promoción y el Torneo Apertura 2000, el Torneo Clausura 2001 con la Promoción y el Torneo Apertura 2001, el Torneo Clausura 2002 con la Promoción y el Torneo Apertura 2002, el Torneo Clausura 2003 con la Promoción y el Torneo Apertura 2003, el Torneo Clausura 2004 con la Promoción y el Torneo Apertura 2004, el Torneo Clausura 2005 con la Promoción y el Torneo Apertura 2005, el Torneo Clausura 2006 con la Promoción y el Torneo Apertura 2006 con la final por el desempate, el Torneo Clausura 2007 con la Promoción y el Torneo Apertura 2007, el Torneo Clausura 2008 con la Promoción y el Torneo Apertura 2008 con el triangular final, el Torneo Clausura 2009 con la Promoción y el Torneo Apertura 2009, el Torneo Clausura 2010 con la Promoción y el Torneo Apertura 2010, el Torneo Clausura 2011 con el desempate y la Promoción y el Torneo Apertura 2011, el Torneo Clausura 2012 con la Promoción y el Torneo Inicial 2012, el Torneo Final 2013 con la Superfinal y el Torneo Inicial 2013, el Torneo Final y el de Transición 2014, el Campeonato 2015, el Campeonato 2016, el Campeonato 2016-17, la Superliga 2017-18, la Superliga 2018-19, la Copa de la Superliga 2019 y la Superliga 2019-20, la Copa Diego Maradona 2020, la Copa de la Liga y la
  Liga Profesional de 2021, 2022, 2023 y 2024, y los torneos Apertura y Clausura de 2025 y 2026, que se eligen arriba: primero el año y después el torneo de ese año.
  `liga.html?anio=2024` abre el último torneo de ese año (el que tiene la tabla anual); `liga.html?torneo=2024-copa`, uno en particular): la tabla de las dos zonas,
  todas las fechas con resultados y goles, los goleadores, los playoffs (con su cuadro), la tabla anual y los promedios del descenso
  (`liga.html?vista=fechas&fecha=5`, `?vista=anual`, `?vista=promedios`).
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
| `data/champions/…` | La Champions League desde 1955/56. Cada edición lleva el año en que empieza la temporada (`ediciones/2024.js` es la 2024/25; en la página, `?copa=champions&edicion=2024`). | **Generado**. |
| `data/europa/…` | La Europa League (Copa UEFA hasta 2009) desde 1971/72, igual que la Champions (`?copa=europa`). | **Generado**. |
| `data/conference/…` | La Conference League desde 2021/22, igual que la Champions (`?copa=conference`). | **Generado**. |
| `data/recopa/…` | La Recopa Sudamericana desde 1989 (`?copa=recopa`): solo la final. Hasta 2014 sale de Wikipedia y desde 2015 de ESPN; los entrenadores, de las formaciones de Wikipedia y, lo que falta, de la historia de cada club en Transfermarkt. | **Generado**. |
| `data/supercopa/…` | La Supercopa de Europa desde 1972 (`?copa=supercopa`): solo la final, cada edición con el año en que se jugó. Hasta 2004 (y 2013) sale de Wikipedia y el resto de ESPN. La de 1972 se ve pero no cuenta en las estadísticas (no es oficial). | **Generado**. |
| `data/intercontinental/…`, `data/mundial/…` | Lo mismo para la Copa Intercontinental y el Mundial de Clubes. Los entrenadores de la Intercontinental salen de las formaciones de Wikipedia; el Mundial todavía no tiene. | **Generado**. |
| `liga.html`, `js/liga.js` | La página de la liga argentina. La tabla de posiciones la calcula `liga.js` con los resultados. | Comportamiento de la liga. |
| `data/ligas/argentina/<torneo>.js` | Un torneo de la liga (`2026-clausura.js`): zonas, fechas con sus partidos y goles, playoffs y clubes. `indice.js`: los torneos cargados. | **Generado** (`tools/actualizar_liga.py`). |
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
| Champions League | 1955/56–1990/91 | **Wikipedia** (en inglés): la página de cada temporada y la de la final, con goles, estadio, árbitro y público (formaciones, solo de las finales). |
| Champions League | 1991/92–2000/01 | **Wikipedia** (en inglés): una página por fase (primera y segunda ronda, grupos, eliminatorias y final), con goles, formaciones, árbitro y público. |
| Champions League | 2001/02 en adelante | **ESPN**. |
| Copa UEFA | 1971/72–2000/01 | **Wikipedia** (en inglés): la página de cada temporada (desde 1999/2000, una por ronda) y la de la final, con goles, estadio, árbitro y público (formaciones, solo de las finales). |
| Copa UEFA / Europa League | 2001/02 en adelante | **ESPN** (la Copa UEFA, hasta 2008/09, es otra "liga" de ESPN: `espn_ligas` en `tools/copas.py`). Las fases de grupos 2004/05–2008/09, que ESPN tiene sin detalle, se completan con Wikipedia. |
| Conference League | 2021/22 en adelante | **ESPN** ("uefa.europa.conf"). |

**Rondas clasificatorias** (Champions, Europa League y Conference League, desde 1992/93): se ven en cada edición, en la
pestaña "Fase previa", y en la historia de cada club, pero no cuentan en las estadísticas históricas (como en los
registros de la UEFA: ver `es_previa_uefa` en `tools/copas.py`). Las rondas se llaman "Ronda preliminar", "Primera /
Segunda / Tercera fase previa" y "Playoff de clasificación".
- 1992/93–2000/01: Wikipedia (una página por temporada; en la Copa UEFA 1994–1998, una sección de la página de la temporada).
- 2001/02–2019/20: ESPN (hasta 2019 dentro de cada copa) **completado con Wikipedia** (`pagina_previas` en
  `tools/copas.py`): ESPN tiene rondas enteras sin cargar, muchos partidos sin goleadores y algunos resultados y
  equipos mal. Wikipedia no es una fuente más sino un complemento (`completar_previas` en `generar_datos.py`):
  cada partido se busca en ESPN por fecha y equipos, le da el nombre de la ronda, los goles y el país de los clubes,
  y agrega los que faltan. Así no cambia ningún club de los que ya estaban.
- 2020/21 en adelante: ESPN, que tiene las clasificatorias en otra "liga" ("uefa.champions_qual", "uefa.europa_qual",
  "uefa.europa.conf_qual": `espn_ligas`), completas.
Qué temporadas se cargan lo dice `ediciones` en `tools/copas.py`.

Los textos de Wikipedia tienen licencia CC BY-SA. Los clubes de otros continentes llevan su país y su nombre en
castellano en `tools/equipos_ajustes.json` (`pais_espn` y `nombres`), y los estadios en `tools/estadios.json`.
Los datos de RSSSF de la Libertadores son de Juan Pablo Andrés, Pablo Ciullini y Frank Ballesteros, y los de la
Sudamericana de Karel Stokkermans, Osvaldo José Gorgazzi y otros (Rec.Sport.Soccer Statistics Foundation), que
permiten copiarlos citando a los autores.

## Actualizar los datos

Cada script de descarga trabaja con la Libertadores; con `--copa sudamericana` (o `recopa`, `intercontinental`, `mundial`…),
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
python tools/descargar_wikipedia.py --copa recopa   # Recopa 1989-2014 (una sola vez)
python tools/descargar_espn.py --copa recopa        # Recopa desde 2015 (cada febrero, la del año)
python tools/descargar_wikipedia.py --copa intercontinental   # Intercontinental 1960-2004 (una sola vez)
python tools/descargar_wikipedia.py --copa mundial            # Mundial 2000 (una sola vez)
python tools/descargar_espn.py --copa intercontinental
python tools/descargar_espn.py --copa mundial
python tools/descargar_espn.py --copa champions      # baja los años de "espn_anios" en tools/copas.py (la 1ra vez, horas)
python tools/descargar_wikipedia.py --copa champions  # Champions 1955/56-2000/01 y las previas hasta 2019/20 (una sola vez)
python tools/descargar_espn.py --copa europa         # Copa UEFA y Europa League desde 2001/02 (la 1ra vez, horas)
python tools/descargar_wikipedia.py --copa europa    # Copa UEFA 1971/72-2000/01 y las previas hasta 2019/20 (una sola vez)
python tools/descargar_espn.py --copa conference     # Conference League desde 2021/22
python tools/descargar_wikipedia.py --copa supercopa  # Supercopa de Europa 1972-2004 y 2013 (una sola vez)
python tools/descargar_espn.py --copa supercopa       # Supercopa de Europa desde 2005
python tools/descargar_banderas.py  # banderas de los países nuevos
python tools/actualizar_liga.py     # liga argentina: baja de ESPN ("arg.1") los torneos que no terminaron y arma data/ligas/argentina/ (tarea programada, todas las noches)
python tools/actualizar_liga.py todos            # todos los torneos, también los terminados (después de cambiar el script)
python tools/actualizar_liga.py 2025-clausura    # solo ese torneo
python tools/actualizar_europa.py   # temporada en curso de la Champions, la Europa League y la Conference, y la Supercopa del año (bajar, armar, probar)
```

Para la temporada en curso alcanza con `python tools/descargar_espn.py 2026` (y `--copa sudamericana 2026`)
y después `generar_datos.py`. En la Champions y la Europa League la temporada toca dos años: para la 2026/27,
`--copa champions 2026 2027`, `--copa europa 2026 2027` y `--copa conference 2026 2027`. Cuando empiece una temporada nueva, sumarla a `ediciones`
(y el año siguiente a `espn_anios`) en `tools/copas.py`.

### Liga argentina

`tools/actualizar_liga.py` baja todo de ESPN, salvo 1987 a 2002 (en 1987, el Campeonato 1986-87 va como "1987-temporada"; en 1988, el Campeonato 1987-88 va como "1988-temporada"; en 1989, el Campeonato 1988-89 va como "1989-temporada"; en 1990, el Campeonato 1989-90 va como "1990-temporada"), que ESPN no tiene: esos partidos están en
`tools/a_mano/liga-<torneo>.json` (resultados y goles de RSSSF, solo con el apellido y sin minutos; estadio, día y hora
de Wikipedia) y el script los lee como si fueran de ESPN (`liga: "a_mano"`). ESPN no dice a qué fecha pertenece cada partido: se deduce
recorriendo los partidos en orden (empieza una fecha nueva cuando aparece un club que ya jugó en la que está en curso)
y mandando los postergados a la fecha en la que les falta jugar a los dos clubes (`repartir_fechas`). Si igual
sobra una fecha (postergados que se cruzan, como en diciembre de 2024), las fechas incompletas del final se vuelven a
armar con los partidos sueltos, dejando cada partido en su fecha cuando se puede (`reparar`). Las zonas salen
de la tabla de ESPN, que solo muestra las del torneo en curso: el Apertura 2026 usa las del Clausura, que fueron las
mismas (`zonas_de`; el script avisa si algún club tiene más de 2 partidos contra la otra zona). Si no cambió ningún
dato, el archivo del torneo no se toca (un torneo terminado no cambia cada noche).

**Tabla anual y promedios** (reglamento 2026): la tabla anual suma la fase de zonas del Apertura y del Clausura (sin
playoffs); los promedios, los puntos de 2024, 2025 y 2026 divididos por los partidos jugados (2024: la fase de zonas de
la Copa de la Liga, que en ESPN es otra liga, "arg.copa_lpf", y la Liga 2024; los recién ascendidos dividen solo por
sus partidos en Primera). Descienden el último de la tabla anual y el peor promedio; si es el mismo club, el anteúltimo
de la tabla anual. El script guarda lo ya jugado (el Apertura y las temporadas anteriores, `anual` y `promedios` en
`TORNEOS`) y la página le suma el torneo en curso. Los puntos descontados por sanciones van en `DESCUENTOS`.
Los números se controlaron contra futbolargentino.com y aquehorajuegan.com (octubre de 2026).

**Cupos para las copas** (`cupos` en `TORNEOS`, reglamento de la AFA de marzo de 2026): a la Libertadores 2027 van los
campeones del Apertura, del Clausura y de la Copa Argentina 2026 y los mejores de la tabla anual hasta completar 6; a la
Sudamericana, los 6 siguientes. Si un campeón ya entra por la tabla (o gana dos títulos), su lugar pasa al siguiente;
los que descienden no juegan copas. Los campeones salen solos de la final en ESPN (la Copa Argentina es "arg.copa");
la página los marca en la tabla anual. Un campeón "extra" (el de la Sudamericana, que va a la Libertadores por la
Conmebol: Lanús en 2025) no ocupa un lugar de la liga. 2025 tuvo las mismas reglas (promedios 2023-2025) y, además, el
título de "Campeón de Liga" que la AFA le dio en noviembre de 2025 a Rosario Central por ganar la tabla anual
(`titulo_anual`). Controlado contra lo que pasó: descendieron San Martín de San Juan (promedios) y Godoy Cruz (tabla
anual), y los clasificados a las copas 2026 coinciden con la lista de ESPN.

**2024** tuvo otro formato: la Copa de la Liga (en ESPN, otra liga: "arg.copa_lpf"; dos zonas de 14, desde cuartos de
final) y la Liga Profesional (una sola tabla, 27 fechas, sin playoffs: el campeón es el primero, `campeon_tabla`). La
tabla anual sumó la fase de zonas de la Copa y la Liga entera. No hubo descensos (los anuló la AFA): la página dice
quiénes hubiesen bajado con el reglamento (`descensos_anulados`). Los clasificados a las copas 2025 coinciden con la
lista de ESPN (Racing fue a la Libertadores aparte, por ganar la Sudamericana 2024).

**2023**, al revés: primero la Liga Profesional (una sola tabla) y después la Copa de la Liga (zonas y playoffs). El
campeón de la Liga, para los cupos, sale de su tabla (`"tabla"` en `campeones`). Descendieron Arsenal (promedios) y
Colón, que empató en puntos con Gimnasia en la tabla anual y perdió el partido desempate (`desempate`: ESPN lo tiene en
la Copa de la Liga como "relegation"; la página lo muestra en la tabla anual). Promedios, tabla anual y clasificados a
las copas 2024 controlados contra canchallena.lanacion.com.ar y ESPN.

**2022**: la Copa de la Liga y la Liga Profesional (Boca ganó las dos). Bajaron los dos últimos de los promedios
(`"descensos": "promedios"`: Aldosivi y Patronato; Patronato igual jugó la Libertadores 2023 como campeón de la Copa
Argentina). Los promedios contaban 2019-20 (temporadas con nombre propio: en `promedios`, cada fuente puede llevar su
año), 2021 y 2022. La Copa de la Superliga 2020, de la que solo se jugó una fecha, no está en ESPN: sus 12 resultados
van en `PARTIDOS_A_MANO` (de Wikipedia). El promedio se muestra con tres decimales sin redondear, como la AFA.

**2021**: la Copa de la Liga (zonas de 13, campeón Colón) y la Liga Profesional (una tabla de 26, campeón River). Sin
descensos (suspendidos por la pandemia: `sin_descensos`). A la Sudamericana 2022 fue también el subcampeón de la Copa
Diego Maradona 2020-21, Banfield (`sudamericana_titulos`: un lugar que se gana por un torneo y le resta uno a la tabla).
La final de la Copa Argentina en ESPN a veces se llama "copa-argentina---final" (por eso el patrón `(^|-)final$`).
Los clasificados a las copas 2022 coinciden con la lista de Infobae.

**2020**: la Copa Diego Maradona, el único torneo del año (octubre de 2020 - marzo de 2021: el torneo toca dos años de
ESPN, `anios`). Va por etapas (`etapas`: cada una con sus zonas, que salen del grupo de cada partido en ESPN, y sus
fechas): la primera fase (6 zonas de 4), la Fase Campeón y la Fase Complementación (2 zonas de 6 cada una, en las
mismas fechas). Las finales tienen nombres propios (`playoffs`: la final, la de la Complementación y el repechaje por la
Sudamericana). Como no son una eliminación directa común, el cuadro va armado a mano y en dos partes (`cuadro`):
la final del torneo, sola (con el campeón), y el camino al lugar en la Sudamericana (la final de la Complementación y el
repechaje, al que fueron su ganador y el subcampeón). Sin descensos ni tabla anual.

**2019** (las temporadas cruzaban los años: `anios`): la Superliga 2018-19 (una tabla de 26, campeón Racing), la Copa de
la Superliga 2019 (campeón Tigre) y la Superliga 2019-20 (una tabla de 24, campeón Boca). Las Superligas no tenían tabla
anual: la pestaña "Copas y descenso" usa la tabla del torneo, y los promedios nombran la temporada (`temporada`:
"2018-19"). En 2018-19 bajaron los cuatro últimos de los promedios (`descienden`: 4) y los cupos 2020 salieron de la
tabla, los campeones (Superliga, Copa de la Superliga, Copa Argentina) y un lugar en la Sudamericana para el mejor de
la Copa de la Superliga que no tenía lugar (Argentinos: un `sudamericana_titulos` puesto a mano). Un club que bajó y
volvió cuenta en los promedios solo desde que volvió (Aldosivi). La Copa de la Superliga (`copa`: sin fase regular; en
ESPN, "arg.copa_de_la_superliga") fue eliminación directa a ida y vuelta (`ida_y_vuelta`, `gol_visitante`: el cuadro
muestra el global de cada serie) y el cuadro arranca en octavos (`cuadro_desde`). Tres definiciones por penales y un
gol en contra que ESPN no tiene van en `PENALES_A_MANO` y `GOLES_A_MANO`. En 2019-20 no hubo descensos; los cupos
2021 no se cargaron. Todo controlado contra Wikipedia.

**2018**: solo la Superliga 2017-18 (una tabla de 28, campeón Boca; la 2018-19 está en 2019). Bajaron los cuatro
últimos de los promedios, que contaban cuatro temporadas (2015, 2016, 2016-17 y 2017-18). Del torneo 2016, ESPN mete
en la fase regular la final y un desempate: no suman (`NO_SUMAN`). River fue a la Libertadores 2019 aparte, como
campeón de la Libertadores 2018 (en ESPN, la final se llama "finals"). Controlado contra Wikipedia.

**2017**: solo el Campeonato 2016-17 (una tabla de 30, 30 fechas con la de clásicos; campeón Boca). Bajaron los
cuatro últimos de los promedios (2014, que es el Torneo de Transición, 2015, 2016 y 2016-17). River ganó la Copa
Argentina 2017 pero ya entraba por la tabla: el lugar fue para el subcampeón, Atlético Tucumán (en `campeones`, el
modo "perdedor"; `nota` lo explica en la página). Independiente fue aparte como campeón de la Sudamericana 2017.
Controlado contra Wikipedia.

**2016**: el Campeonato 2016 (de transición: dos zonas de 15 con 2 interzonales contra el clásico; final Lanús 4-0
San Lorenzo y partido por el tercer puesto entre los segundos). Las zonas salen del grupo que ESPN le pone a cada
partido (`zonas: "grupos"`); la final y el del tercer puesto ESPN los tiene en la fase regular y van por su id
(`playoffs_ids`). Los cupos 2017 salen de la tabla general (las dos zonas juntas). Bajó solo el último de los
promedios (Argentinos; `descienden`: 1). En los promedios, Colón-Rafaela del Inicial 2013, que no se jugó y la AFA le
dio ganado a Rafaela, va en `RESULTADOS_A_MANO`. Controlado contra Wikipedia.

**2015**: el Campeonato 2015 (una tabla de 30, campeón Boca) y sus dos liguillas, en la pestaña "Liguillas"
(`nombre_playoffs`): la Pre-Libertadores (cuadro, ganó Racing) y la Pre-Sudamericana (sus partidos). Los cupos 2016 no
siguen la regla de los otros años (River como campeón de la Libertadores, el subcampeón de la Copa Argentina porque la
ganó Boca, Huracán como mejor argentino en la Sudamericana, las liguillas): van fijos, como los publicó la AFA
(`cupos.fijos`). Bajaron los dos últimos de los promedios (2012-13, 2013-14, 2014 y 2015): Nueva Chicago y Crucero
del Norte. Controlado contra Wikipedia.

**2014**: dos torneos de 20 a una rueda. El Torneo Final 2014 (campeón River) cerraba la temporada 2013-14: su pestaña
"Temporada y copas" (`nombre_anual`) es la tabla de la temporada (el Inicial 2013 y el Final 2014). Bajaron los tres
últimos de los promedios; Colón, con 6 puntos menos por una sanción de la FIFA (`DESCUENTOS`: se restan en la tabla de
la temporada, no en la del torneo), empató con Rafaela y perdió el desempate (`desempate` y `desempate_texto`). La
pestaña "Copa Campeonato" tiene la final entre los campeones del Inicial y del Final. El Torneo de Transición 2014
(campeón Racing) no tuvo descensos; su tabla anual suma el Final y el Transición, y muestra el desempate Boca-Vélez
(enero de 2015) por el lugar en la Libertadores del mejor de la temporada 2013-14. Los cupos de los dos, fijos. Tres
goles de Defensa y Justicia que ESPN no tiene, en `GOLES_A_MANO`. Controlado contra Wikipedia.

Para sumar un torneo, agregarlo a `TORNEOS` en el script;
los clubes que no jugaron copas (y no están en `data/equipos.js`) van en `CLUBES_NUEVOS`, y su escudo se baja solo.

### Corregir clubes

`tools/equipos_ajustes.json` guarda las correcciones manuales:

- `alias`: unir nombres distintos del mismo club (`"Atl. Nacional|COL": "atletico-nacional"`).
- `pais_por_nombre`: el país de un club cuando la fuente no lo dice.
- `nombres`: el nombre que se muestra en la web.
- `campeones`: forzar campeón y subcampeón de un año de la Libertadores (`"1960": ["penarol", "olimpia"]`), por si hiciera falta.
  `campeones_sudamericana`: lo mismo para la Sudamericana (2007 se definió por gol de visitante y la final de 2016 no se jugó).
- `pais_espn`: el país de un club que solo aparece en ESPN (los del Mundial de Clubes).
- `espn`: unir un club de ESPN a uno nuestro (ESPN tiene al Al Ahly con dos números, por ejemplo).
- `unir`: juntar dos ids que son el mismo club (`"slavia-prague-cze": "slavia-praga"`: Wikipedia pone a los clubes
  checos con Checoslovaquia hasta 1993 y con Chequia después, y quedan dos). `pais_club`: el país de hoy de un club.
- `campeones_europa`: campeones de la Copa UEFA definidos por gol de visitante en finales de ida y vuelta.

Los clubes europeos que solo aparecen en ESPN toman el país de su ficha de ESPN (`tools/cache/espn_equipos.json`,
lo baja `descargar_espn.py`) o del país de su estadio, y se buscan entre los clubes de Wikipedia por nombre y país.

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
- Recopa Sudamericana (en el museo de Palmeiras): [Roberto Sabino](https://commons.wikimedia.org/wiki/File:Recopa_Sudamericana_-_2022_(53799976602).jpg),
  CC BY 2.0 (recortada del fondo y achicada).
- Copa Intercontinental (la de Boca, exhibida en La Plata): [BugWarp](https://commons.wikimedia.org/wiki/File:Intercontinental_de_Boca_exhibida_en_el_Dardo_Rocha_01.jpg),
  CC BY 4.0 (recortada del fondo y achicada).
- Mundial de Clubes (en el museo de Anfield): [Daniel from Glasgow](https://commons.wikimedia.org/wiki/File:Anfield_Stadium_Tour_(51930554120).jpg),
  CC BY 2.0 (recortada del fondo y achicada).
- Europa League: [Damine178](https://commons.wikimedia.org/wiki/File:Europa_league_trophy.jpg),
  CC BY-SA 4.0 (recortada del fondo y achicada).
- Conference League (dibujo): [MacMoreno](https://commons.wikimedia.org/wiki/File:Trofeo_UEFA_Europa_Conference_League.svg),
  CC BY 4.0 (achicada).
- Supercopa de Europa (en el museo del Barcelona): [Rafael Curtinaz Severo](https://commons.wikimedia.org/wiki/File:Trof%C3%A9u_da_UEFA_Super_Cup.jpg),
  CC BY 2.0 (recortada del fondo y achicada).
- Champions League: [dom fellowes](https://commons.wikimedia.org/wiki/File:Champions_League_Trophy_(52736201132).jpg),
  CC BY 2.0 (recortada del fondo y achicada).

Banderas: [flagcdn.com](https://flagcdn.com) (dominio público); la de Yugoslavia, de Wikimedia Commons.

## Fases

Cada sesión se cierra con un `fases/fase_NN.md`. Para saber en qué fase vamos, mirá el último archivo de `fases/`.
