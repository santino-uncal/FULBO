# Fase 10

**Fecha:** 2026-09-27

## Commits

- `d4c61b7` Cabecera: lema "La Gloria Eterna" debajo del título
- `273b1b1` Ediciones: jugador del torneo arriba de los goleadores (premio oficial desde 2008)
- `26e917a` Equipos: historial contra todos los rivales, con botón Ver para ver cada partido entre ellos
- `84f8442` Tablas: columnas de números centradas y alineadas con su título (planteles, rankings, historial y estadísticas)
- `3b758de` Planteles: plantilla completa de cada club según Transfermarkt (número, posición y nombre completo)

## Qué se hizo

- **Cabecera:** "LA GLORIA ETERNA" debajo de "Copa Libertadores", en dorado y mayúsculas.
- **Jugador del torneo** arriba de los goleadores de cada edición. Datos cargados a mano en `data/jugador-torneo.js`
  (fuente: Wikipedia en español). Antes de 2008: "Ninguno (no se entregaba el premio)"; 2023: no se entregó;
  2026: "A definir" hasta que haya campeón.
- **Historial contra cada rival** (ficha de un club): ahora están todos los rivales (10 a la vista, el resto con
  "Ver todos") y cada uno tiene "Ver" con todos los partidos entre ellos (resultado, año, fase, penales).
  `tools/generar_historial.py` guarda la lista de partidos; `data/historial.js` pasó de ~470 KB a ~1,2 MB
  (se carga solo al abrir un club).
- **Números en las tablas:** todas las columnas numéricas centradas y con el título alineado (antes el título iba a
  la izquierda y el número a la derecha). El # de camiseta de los planteles también.
- **Planteles de Transfermarkt:** nuevo `tools/descargar_planteles.py`. Baja la página de plantel de cada club en
  cada temporada (1.852 de 1.856; caché en `tools/cache/transfermarkt/kader/`), guarda `tools/planteles_tm.json` y
  lo mezcla con los planteles de cada edición: los jugadores que ya estaban ganan número, posición y nombre completo
  ("D.Onega" → "Daniel Onega"); los que faltaban se agregan con 0 partidos. `generar_datos.py` también aplica la
  mezcla, así no se pierde al regenerar. Sin jugadores repetidos (chequeado en todas las ediciones).
  - Los equipos sin ninguna formación cargada (antes de 2005, todos menos los finalistas) muestran "–" en PJ.

## Estado al cerrar

Todo commiteado y subido a GitHub. Probado en el navegador: jugador del torneo (1990, 2018, 2023, 2025, 2026),
historial River–Boca (28 partidos), alineación de tablas y planteles de 1966 y 2018.

## Pendiente / próximos pasos

- Activar GitHub Pages y dar de alta el sitio en Google Search Console.
- Cargar el jugador del torneo 2026 cuando termine la Copa (`data/jugador-torneo.js`).
- Planteles recientes muy largos (ej. Flamengo 2025: 76) porque Transfermarkt incluye juveniles del año; ver si
  conviene mostrar solo los que jugaron la Copa.
- Decidir si las columnas de años también van centradas.
