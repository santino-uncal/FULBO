# Fase 25

**Fecha:** 2026-10-03

## Commits

- `6858159` Liga argentina: Torneo Clausura 2002 (Promoción, temporada 2001-02, promedios, cupos) y Torneo Apertura 2002, cargados a mano; escudo de Gimnasia de Concepción del Uruguay
- `79bb6d8` Liga argentina: Torneo Clausura 2001 (Promoción, descuento a Los Andes, cupos de la Copa Mercosur 2001 y la Libertadores 2002) y Torneo Apertura 2001; escudo de Los Andes
- `1ca397f` Liga argentina: Torneo Clausura 2000 (la primera Promoción, descuentos a Boca y Lanús, cupos de la Mercosur 2000 y la Libertadores 2001) y Torneo Apertura 2000
- `f41877c` Liga argentina: Torneo Clausura 1999 (desempate River-Gimnasia, descuento a Colón, cupos de la Copa Conmebol 1999 y la Libertadores 2000) y Torneo Apertura 1999 (con los descuentos)
- `826cc30` Liga argentina: Torneo Clausura 1998 y Torneo Apertura 1998 (cupos de la Conmebol 1998 y la Libertadores 1999); escudos de Deportivo Español y Gimnasia y Tiro
- `de3d9d3` Liga argentina: Torneo Clausura 1997 (desempate Colón-Independiente, promedios con 2 puntos por victoria) y Torneo Apertura 1997 (San Lorenzo-Huracán perdido por los dos); escudo de Huracán Corrientes
- `2d8a2e0` Liga argentina: Torneo Clausura 1996 (con los goles y sus minutos, desempate Racing-Gimnasia) y Torneo Apertura 1996

## Qué se hizo

- **Liga argentina, años 1996 a 2002** (dos torneos por año). ESPN no tiene ningún partido de antes de 2003, así que
  todo va **cargado a mano** en `tools/a_mano/liga-<torneo>.json`: resultados (y goles, cuando los hay) de RSSSF;
  estadio, día y hora de Wikipedia. Cada torneo se controló contra las tablas finales de las dos fuentes.
  - Campeones: 2002 River / Independiente; 2001 San Lorenzo / Racing; 2000 River / Boca; 1999 Boca / River;
    1998 Vélez / Boca; 1997 River / River; 1996 Vélez / River.
  - Goles: solo con el apellido y sin minutos de 1999 a 2002 (RSSSF); con minuto en el Clausura 1996; no hay goles del
    Clausura 1999, de 1998 ni de 1997, y del Apertura 1996 solo de algunas fechas (la página avisa y da el goleador
    según Wikipedia).
  - Promoción en 2000, 2001 y 2002; desempates entre subcampeones por la Libertadores en 1996, 1997 y 1999; cupos de
    la Libertadores, la Sudamericana, la Copa Mercosur y la Copa Conmebol según el año.
  - La "tabla anual" de cada Clausura suma el Apertura anterior: ahora sale de los partidos cargados (salvo el más
    viejo, el Apertura 1995, que va como tabla).
- **`tools/actualizar_liga.py`**: torneos con `liga: "a_mano"` (`eventos_a_mano` arma eventos con la forma de los de
  ESPN), `desempate_a_mano`, `descuentos` en la tabla del torneo y `DESCUENTOS` para la tabla que los suma,
  `para_local`/`para_visitante` (con un tercer valor: el resultado que cuenta), `promedios_victoria` (2 puntos por
  victoria en los promedios hasta 1996-97) y `nombre_sudamericana`/`nota` en los cupos fijos.
- **`js/liga.js`**: descuentos en la tabla del torneo, promedios con 2 puntos por victoria, un resultado distinto para
  cada equipo (también para el visitante), otro nombre para la segunda copa (Mercosur, Conmebol) y la nota de los
  cupos fijos.
- Errores de las fuentes corregidos (documentados en los comentarios y en el campo `fuente` de cada JSON): tablas y
  promedios de RSSSF y Wikipedia con números mal, resultados (Boca-Newell's 1998, Newell's-Talleres 2002), localía
  (Chacarita-Gimnasia 1999), partidos repetidos o suspendidos.
- Escudos nuevos (de Wikipedia, con el fondo blanco sacado): Gimnasia de Concepción del Uruguay, Los Andes, Deportivo
  Español, Gimnasia y Tiro, Huracán Corrientes.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan. Probado en el navegador cada año (tabla, temporada y copas,
promedios, Promoción, goleadores).

## Pendiente / próximos pasos

- Seguir hacia atrás (1995 y antes): RSSSF tiene esos años; ojo que el formato cambia y las tablas de promedios de
  Wikipedia tienen errores.
- Goles que faltan: River 4-1 Talleres y Almagro 1-1 Huracán (Apertura 2000), Lanús 3-1 River (Apertura 1996), y los
  torneos sin goles (Clausura 1999, 1998, 1997, gran parte del Apertura 1996).
- Los goles de 1999 a 2002 van solo con el apellido; se podrían completar los nombres de los goleadores principales.
- El conversor (RSSSF + Wikipedia → JSON) quedó en `tools/convertir_rsssf.py`; para más años hay que bajar las
  páginas de entrada y ajustar el bloque final (qué torneo y qué líneas).
- Pendientes anteriores: goles incompletos de 2003-2006, cupos 2021, Sudamericana 2014, torneos de 2027, otras ligas,
  GitHub Pages y Google Search Console.
