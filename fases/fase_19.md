# Fase 19

**Fecha:** 2026-10-02

## Commits

- `dc542a9` Conference League: temporada 2026/27 en curso (fase de liga, primera fecha el 15/10)
- `1674399` Conference League completa desde 2021/22 (ESPN), con clubes, escudos y banderas nuevas
- `9e30639` Rondas clasificatorias de la Champions, la Europa League y la Conference League desde 1992/93

## Qué se hizo

- **Nueva copa: Conference League** (`?copa=conference`, datos en `data/conference/`, `window.UECL`), las seis
  temporadas de 2021/22 a 2026/27, todas de ESPN ("uefa.europa.conf"). Trofeo: dibujo de Wikimedia Commons
  (MacMoreno, CC BY 4.0). En la portada de Europa ya no figura como "próximamente". La 2026/27 está cargada hasta
  la primera fecha de la fase de liga (15/10, todavía sin jugar). La tarea programada (ahora "Actualizar Champions,
  Europa y Conference League") también la actualiza.
- **Rondas clasificatorias** de las tres copas europeas desde 1992/93 (~2.660 partidos de la Champions, ~5.070 de la
  Europa League y ~1.600 de la Conference). Se ven en la pestaña "Fase previa" de cada edición (en las ediciones
  sin grupos: "Fase previa" y "Cuadro") y en la historia de cada club, pero no cuentan en las estadísticas históricas
  (como en los registros de la UEFA: `es_previa_uefa` en `tools/copas.py`). Nombres: "Ronda preliminar",
  "Primera / Segunda / Tercera fase previa", "Playoff de clasificación".
  - 1992/93–2000/01: Wikipedia (páginas nuevas en `paginas_champions` / `paginas_uefa`).
  - 2001/02–2019/20: ESPN completado con Wikipedia (`pagina_previas` en `copas.py`, `completar_previas` en
    `generar_datos.py`). Wikipedia no es una fuente más: cada partido se busca en ESPN por fecha y equipos, le pone
    el nombre de la ronda, los goles y el país de los clubes, corrige resultados y equipos que ESPN tiene mal (2009),
    agrega los que faltan y saca los de ESPN que sobran. En todas esas temporadas la cantidad coincide con Wikipedia.
    Así ESPN no "aprende" clubes equivocados de los partidos chicos.
  - 2020/21 en adelante: ESPN, con las ligas clasificatorias aparte ("uefa.champions_qual", "uefa.europa_qual",
    "uefa.europa.conf_qual", en `espn_ligas`; `_liga` en el calendario).
  - La Copa UEFA 2001–2010 en ESPN trae todas las previas juntas: `separar_previas` las separa por fecha (solo se
    usa si no hay Wikipedia).
  - `descargar_wikipedia.py` sigue las subpáginas de partidos (Europa League 2009–2017) y el lector entiende
    `{{#invoke:Football box}}`. `equipos.normalizar` ahora convierte ł, ø, æ, ð, þ… (antes se perdían).
  - Los rivales "a definir" de partidos viejos sin jugar y los equipos de relleno de ESPN ("Bulgaria No. 3") ya no
    crean clubes.
- **Clubes**: ~470 nuevos (con 2021–2025 de la Conference). Muchos ajustes en `equipos_ajustes.json`: duplicados
  juntados (`unir`), fichas de ESPN asignadas a mano (`espn`: Víkingur Gøta/Reykjavík, las dos Santa Coloma, Inter
  Turku/Bakú, Kauno Žalgiris/Žalgiris Vilnius, CSKA 1948, Dnipro-1, Lausanne, Lincoln, NŠ Mura, Riga FC) y países.
  Banderas nuevas: Andorra, Gibraltar, Gales, Estonia, Kosovo, Islas Feroe, Liechtenstein, Montenegro, San Marino.
- La página de estadísticas ya no se rompe con una copa sin partidos o sin campeón.
- 4 pruebas nuevas (71 en total).

## Estado al cerrar

Todo commiteado y subido a GitHub. Las 71 pruebas pasan. Comparado contra lo publicado antes: lo que ya estaba no
cambió, salvo clubes separados a propósito (Riga FC, Kauno Žalgiris) y la ronda preliminar de la Copa UEFA 1989/90
(Auxerre–Dinamo Zagreb), que antes se descartaba por error.

## Pendiente / próximos pasos

- ~200 clubes nuevos (los chicos de las previas) sin escudo: se ven las iniciales.
- Desde 2020 las previas son solo de ESPN: algunos partidos sin goleadores (p. ej. 10 en la Conference 2021).
- Pendientes anteriores: GitHub Pages y Google Search Console, "Run now" de la tarea programada, escudos europeos
  chicos, Champions con "Copa de Campeones" en el título hasta 1991/92, técnicos y planteles del Mundial de Clubes,
  ligas nacionales y demás copas "próximamente" (Supercopa de Europa…).
