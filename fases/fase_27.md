# Fase 27

**Fecha:** 2026-10-04

## Commits

- `de5cdd8` Liga argentina: al lado de cada campeón, qué número de título de liga es (cuenta oficial de la AFA, con los de antes de 1990)
- `09ed02e` Liga argentina: al lado del número de título, si es un bicampeonato, tricampeonato, etc.

## Qué se hizo

- **Número de título al lado del campeón** de cada torneo de la liga argentina ("🏆 Campeón: River Plate · título de
  liga n.º 23").
  - Datos en `data/ligas/argentina/titulos.js` (cargado a mano, separado del código):
    - `antes`: los títulos de cada club hasta el Campeonato 1988-89;
    - `ultimo_antes`: el campeón de 1988-89 (Independiente);
    - `torneos`: el campeón de cada torneo, y los otros títulos que se definieron en ese torneo, con su texto (la
      final de la temporada 1990-91, la Superfinal 2012-13 y el "Campeón de Liga" 2025);
    - `notas`: por qué no suman título las Copas de la Liga, la Copa de la Superliga, la Copa Maradona y los dos
      torneos de 1990-91.
  - Cuenta oficial de la AFA según Wikipedia ("List of Argentine Primera División champions"): las Copas de la Liga
    son copas nacionales, no títulos de liga. Totales al día: River 38, Boca 35, Racing 18, Independiente 16,
    San Lorenzo 15, Vélez 11, Estudiantes 7, Newell's 6, Rosario Central 5.
  - `js/liga.js` calcula el número sumando los títulos en el orden del índice. En la tabla anual de 2025 también se
    ve el número del "Campeón de Liga".
- **Títulos seguidos:** bicampeonato, tricampeonato, etc., al lado del número. Salen 7: Vélez en el Clausura 1996,
  River en el Clausura 1997 y el Apertura 1997 (tricampeonato), Boca en el Clausura 1999, River en el Clausura 2000,
  Boca en el Clausura 2006 y Boca en la Superliga 2017-18.
- Prueba nueva en `tests/test_liga.py`:
  - avisa si un torneo terminado no tiene su campeón (o una nota) en `titulos.js`;
  - controla los totales de la AFA.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (77). Probado en el navegador en todos los torneos: en cada uno,
el campeón que calcula la página coincide con el de `titulos.js`.

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
