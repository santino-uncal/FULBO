# Fase 24

**Fecha:** 2026-10-03

## Commits

- `24f00cf` Liga argentina: Torneo Final 2013 (con la Superfinal, la temporada 2012-13, promedios, descensos y cupos de la Sudamericana 2013) y Torneo Inicial 2013 (con los cupos de la Libertadores 2014)
- `178a141` Liga argentina: Torneo Clausura 2012 (con la Promoción, la temporada 2011-12, promedios y descensos) y Torneo Inicial 2012 (con la tabla del año y los cupos de la Libertadores 2013)
- `632a486` Liga argentina: Torneo Clausura 2011 (con el desempate Huracán-Gimnasia, la Promoción cargada a mano, promedios, descensos y cupos de la Sudamericana 2011) y Torneo Apertura 2011 (con la tabla del año y los cupos 2012)
- `502040a` Liga argentina: Torneo Clausura 2010 (con la Promoción, …) y Torneo Apertura 2010 (…)
- `12d9dce` Liga argentina: Torneo Clausura 2009 y Torneo Apertura 2009; escudo de Gimnasia de Jujuy
- `eeec4f6` Liga argentina: Torneo Clausura 2008 y Torneo Apertura 2008 (con el triangular final)
- `a6c46eb` Liga argentina: el gol de Bernardello en Newell's 3-0 Racing (Apertura 2008), que ESPN no tiene
- `b4dd24c` Liga argentina: Torneo Clausura 2007 y Torneo Apertura 2007; el Almagro-Boca suspendido de 2005 en los promedios
- `9af54e6` Liga argentina: Torneo Clausura 2006 (Promoción a mano) y Torneo Apertura 2006 (final Estudiantes-Boca); escudo de Tiro Federal
- `e4f6b5d` Liga argentina: Torneo Clausura 2005 y Torneo Apertura 2005; Almagro-Boca perdido por los dos; escudos de Almagro y Huracán de Tres Arroyos
- `84e2d59` Liga argentina: Torneo Clausura 2004 y Torneo Apertura 2004; descuento a Chacarita; resultados y goles que ESPN tenía mal
- `58d3d11` Liga argentina: Torneo Clausura 2003 (Apertura 2002 y promedios viejos a mano) y Torneo Apertura 2003; aviso cuando faltan goles

## Qué se hizo

- **Liga argentina, años 2003 a 2013** (dos torneos por año; tablas, fechas, goleadores, temporada/año, promedios,
  descensos, Promoción y cupos, todo controlado contra Wikipedia y, en los años viejos, RSSSF):
  - **2013:** Final 2013 (Newell's) con la Superfinal (Vélez 1-0 Newell's, a mano: ESPN no la tiene) e Inicial 2013
    (San Lorenzo). **2012:** Clausura (Arsenal) e Inicial (Vélez). **2011:** Clausura (Vélez), con el desempate
    Huracán-Gimnasia, y Apertura (Boca). **2010:** Clausura (Argentinos) y Apertura (Estudiantes). **2009:** Clausura
    (Vélez) y Apertura (Banfield). **2008:** Clausura (River) y Apertura (Boca, por el triangular). **2007:** Clausura
    (San Lorenzo) y Apertura (Lanús). **2006:** Clausura (Boca) y Apertura (Estudiantes, por la final con Boca).
    **2005:** Clausura (Vélez) y Apertura (Boca). **2004:** Clausura (River) y Apertura (Newell's). **2003:** Clausura
    (River) y Apertura (Boca).
  - Promoción (2004 a 2012) en una pestaña con su cuadro; las de 2003, 2004, 2005, 2006 y 2011 no están en ESPN y van a
    mano (`playoffs_a_mano`).
- **La página (`js/liga.js`)**, cosas nuevas: equipos de Promoción marcados en naranja (`promocion`), ventaja deportiva
  en las series (`ventaja`), triangular final (`triangular`), partidos con nota (dados por la AFA, suspendidos),
  partidos perdidos por los dos (`para_local`), cupos de la Libertadores y la Sudamericana de años distintos
  (`anio_sudamericana`), leyenda solo de las copas que tienen lugares, el ganador de un desempate queda arriba en los
  promedios, y aviso en Goleadores cuando faltan goles (`goleadores_nota`).
- **`tools/actualizar_liga.py`**, nuevo: `playoffs_a_mano` (también con clubes que no están en ESPN), tabla anual y
  temporadas de promedios puestas a mano (diccionarios, para lo que ESPN no tiene: Apertura 2001 y 2002),
  `GOLES_CORREGIDOS`, `PIERDEN_LOS_DOS`, descuentos que se aplican solo a una fase (Chacarita 2003-04), notas en
  `RESULTADOS_A_MANO`, y los equipos de la B Nacional no entran en la tabla del torneo.
- Correcciones a ESPN: resultados (Estudiantes 1-4 Independiente 2004, Huracán 1-3 Lanús 2003, suspendidos de 2003) y
  goles que faltaban (2004, 2005, 2006, 2008).
- Clubes nuevos con escudo: Gimnasia de Jujuy, Tiro Federal, Almagro, Huracán de Tres Arroyos y San Martín de Mendoza
  (los que ESPN no tiene, de Transfermarkt). README actualizado.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan. Probado en el navegador cada año.

## Pendiente / próximos pasos

- Goles con datos incompletos: Clausura 2003 (ESPN casi no tiene goles; hay aviso), Promoción 2003 sin goles, ida
  Belgrano-Olimpo 2006 sin goles, algunos goles sin minuto o solo con apellido (Vizcarra 2011, Gandín 2004).
- 2002 y antes: ESPN no tiene esos partidos; habría que cargar todo a mano (tablas, promedios, Promoción), sin fechas ni
  goles partido por partido.
- Pendientes anteriores: cupos 2021 en la Superliga 2019-20, Sudamericana 2014, torneos de 2027, otras ligas nacionales,
  GitHub Pages y Google Search Console, y los de las copas.
