# Fase 18

**Fecha:** 2026-10-01

## Commits

- `a2ac30b` Europa League: temporadas 2024/25 y 2025/26 (ESPN), con trofeo, escudos y clubes nuevos
- `484e6f6` Europa League completa desde 1971/72 (Copa UEFA): Wikipedia hasta 2000/01, ESPN después, con los clubes unificados
- `3802ddb` Europa League: el título dice Copa UEFA en las ediciones hasta 2008/09
- `7f4b190` Champions y Europa League: temporada 2026/27 en curso (primera fecha de la fase de liga)
- `45d3aec` Script para actualizar la temporada en curso de la Champions y la Europa League

## Qué se hizo

- **Nueva copa: Europa League** (`?copa=europa`, datos en `data/europa/`, `window.UEL`), las 56 ediciones de 1971/72
  a 2026/27 (~8.900 partidos). Como en la Champions, cada edición lleva el año en que empieza la temporada y no se
  cargan las rondas clasificatorias. El título de la página dice "Copa UEFA" hasta 2008/09 (`titulos` en `app.js`).
  - 1971/72–2000/01: Wikipedia (`paginas_uefa` en `tools/copas.py`): la página de cada temporada y la de la final;
    desde 1999/2000, una página por ronda. Las rondas se nombran por cantidad de partidos (treintaidosavos…).
  - 2001/02 en adelante: ESPN. La Copa UEFA ("uefa.uefa", hasta 2008/09) y la Europa League ("uefa.europa") son
    dos ligas de ESPN: `espn_ligas` junta los calendarios. Los nombres de fase de ESPN se traducen según la
    temporada (`slug_uel` en `leer_espn.py`). No se baja el detalle de las clasificatorias (`espn_saltear`).
  - ESPN no tiene el detalle de las fases de grupos 2004–2008 ni algunos partidos de primera ronda (2002, 2004,
    2006): se completan con Wikipedia (misma edición en las dos fuentes, se emparejan solos).
  - Correcciones: partidos dados por escritorio leídos del texto de Wikipedia ("awarded"), partido suspendido y
    vuelto a jugar (Inter–Dukla 1986), gol de oro (final 2001), `&ndash;` en los resultados, países escritos con
    el nombre completo ("West Germany"), campeones por gol de visitante (`campeones_europa`), penales de la final
    2007 (`resultados`).
- **Clubes**: ~600 clubes europeos nuevos. Sección nueva `unir` en `equipos_ajustes.json` (id → id) para juntar
  duplicados (~190: checos con Checoslovaquia y Chequia, Videoton/Fehérvár, Terek/Akhmat…). Los clubes europeos que
  solo aparecen en ESPN toman el país de su ficha de ESPN (`tools/cache/espn_equipos.json`, lo baja
  `descargar_espn.py`) o del país de su estadio, y se buscan por nombre y país (`club_europeo` en `generar_datos.py`).
  Todos con su país actual. Escudos de ~300 clubes; trofeo de la Europa League (Wikimedia Commons, CC BY-SA 4.0).
- **Temporada 2026/27** de la Champions y la Europa League (primera fecha de la fase de liga jugada).
- **Actualización automática**: `tools/actualizar_europa.py` (baja los dos años de la temporada en curso de las dos
  copas, arma y prueba) y una tarea programada de la app ("Actualizar Champions y Europa League", miércoles, jueves
  y viernes a las 9:00) que lo corre y sube los cambios a GitHub si las pruebas pasan.
- `descargar_espn.py`: no reintenta los partidos que no existen (404). `descargar_wikipedia.py` sigue redirecciones.
- 4 pruebas nuevas (67 en total).

## Estado al cerrar

Todo commiteado y subido a GitHub. Las 67 pruebas pasan. Las otras copas no cambiaron (salvo dos nombres de la
Champions 1980 y 1984 que tenían un `&nbsp;` de más).

## Pendiente / próximos pasos

- ~55 escudos de clubes europeos chicos o desaparecidos (no están en TheSportsDB).
- Europa League: asistencias recién desde 2014/15; Crusaders–Servette 1993 sin la ida (0–0, no está en Wikipedia);
  sin entrenadores ni planteles de Transfermarkt (igual que la Champions).
- Champions: el título podría decir "Copa de Campeones" hasta 1991/92, como la Europa League con la Copa UEFA.
- Al empezar la temporada 2027/28, sumarla a `ediciones` (y 2028 a `espn_anios`) en `tools/copas.py`.
- Hacer una vez "Run now" de la tarea programada para aprobar sus permisos.
- Pendientes anteriores: GitHub Pages y Google Search Console, técnicos y planteles del Mundial de Clubes,
  Al Ahly–Guangzhou 2013 sin autores de goles, Conference League y demás copas "próximamente", ligas nacionales,
  jugador del torneo de la Sudamericana, planteles de 1994–2004 de más de 40, 26 escudos sudamericanos.
