# Fase 36

**Fecha:** 2026-10-11 y 2026-10-12

## Commits

- `4815b99` 1891 (título compartido Saint Andrew's-Old Caledonians y partido por las medallas) · `d5ec266` 1893 ·
  `4681985` 1894 · `2192a33` 1895 · `89f6dfb` partidos sin resultado conocido y sin día · `72b0661` 1896 · `7a61e71` 1897
  (desempate de tres partidos) · `71ee69f` 1898 (desempate) · `4a7065b` 1899 · `2f21afd` 1900
- `b4367be` 1901 · `48da634` 1902 · `e6c4ab0` 1903 · `4db65eb` 1904 · `05b5398` 1905 · `a75af8a` 1906 (dos grupos y final) ·
  `f1c7c1f` aclaración de interzonales solo donde los hay · `59c4d76` 1907 · `e5e0d85` 1908 · `5532252` 1909

## Qué se hizo

- **Liga argentina completa desde el primer campeonato**: 1891 y de 1893 a 1909 (en 1892 no hubo campeonato), cargados a
  mano como los años anteriores: un script por año en el scratchpad lee RSSSF (`rsssf.org/tablesa/argAAAA.html`) y escribe
  `tools/a_mano/liga-<clave>.json`, la entrada en `TORNEOS` (`tools/actualizar_liga.py`), `titulos.js` y el README. Cada
  tabla se comparó con la de RSSSF; las diferencias son de RSSSF y están aclaradas (1909: un gol de Argentino de Quilmes y
  Lomas; 1899 y 1891: RSSSF trae dos tablas, va la que coincide con los partidos; 1905: el orden de Reformer y Lomas).
- **Formatos raros**: grupos y final (1906, `zonas_a_mano`); desempates (1898; 1897, tres partidos, con `sin_cuadro` y el
  último como "Final"); título compartido (1891: el segundo campeón como otro título del torneo en `titulos.js`, y el
  partido por las medallas aparte); descuentos (1906, 1908); equipos que abandonaron con los partidos dados por perdidos,
  cada uno en una fecha aparte (1898, 1905, 1907); tercera rueda anulada (1893); clubes que perdieron la afiliación con
  `descienden_clubes` (1893, 1894, 1895).
- **Página y script**: `sin_resultado` (se sabe quién ganó, no el resultado: "? - ?", sin goles en la tabla; 1894-1895);
  partidos sin día en los torneos a mano (para ordenar, el día del partido anterior); la aclaración de los interzonales
  solo en los torneos que los tienen.
- **Nombres viejos**, con el club de después: English High School → Alumni; Quilmes Rovers / Quilmes Club → Quilmes;
  Lomas Academicals → Lomas Academy; Banfield Athletic Club → Banfield; Atlético Estudiantes → Estudiantes (Buenos Aires);
  Belgrano B → Belgrano Extra (segundo equipo de Belgrano Athletic; Lomas Academy, de Lomas Athletic, va aparte porque la
  AFA le cuenta el título).
- **Clubes nuevos** (`CLUBES_NUEVOS`): Reformer, Lomas Athletic, Lobos, Rosario Athletic (escudos de Wikipedia); Lomas
  Academy y Belgrano Extra (con el escudo de su club); San Martín Athletic, Barracas Athletic, Flores Athletic, Lanús
  Athletic, United Banks, Palermo Athletic, Retiro Athletic, Saint Andrew's, Buenos Aires al Rosario Railway, Old
  Caledonians, Buenos Aires FC y Belgrano FC (escudos genéricos).
- `titulos.js`: `antes` vacío y `ultimo_antes` null (1891 es el primero).

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Cada año revisado en el navegador.

## Pendiente / próximos pasos

- Escudos verdaderos de los genéricos (los de esta fase y los anteriores). Wikipedia limita las consultas: espaciarlas.
- La leyenda "Campeón: el primero de la tabla" en 1891 (título compartido) podría decir otra cosa.
- Revisar si hace falta un nombre propio para las rachas largas ("7 títulos seguidos"; `RACHA` llega a 5).
- Pendientes anteriores: diferencias de un gol en los amateurs 1932-1933; Argentino de Temperley; campeón del Clausura 2026
  en `titulos.js`; goles que faltan (1996-2006); cupos 2021; Sudamericana 2014; torneos de 2027; otras ligas; GitHub Pages y
  Google Search Console.
