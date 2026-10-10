# Fase 35

**Fecha:** 2026-10-10

## Commits

- `fbbe9e3` 1930 · `eacd1e2` 1929 (2 zonas, desempate Boca-San Lorenzo, final Gimnasia-Boca) · `30feb25` 1928 (descensos
  puntuales: `descienden_clubes`) · `2dd7221` 1927 (desempate por el puesto 30; `sin_cuadro`)
- `c676b1c` 1926 · `bdfe4c1` 1925 (final dada en el escritorio: `gana`) · `23b9997` 1924 · `7640394` 1923 ·
  `9d5be81` 1922 · `502d33f` arreglo de una nota de 1922 · `59b700e` 1921 · `4634856` 1920 · `5c5d35c` 1919
  (dos ligas por año: `-aaf` y `-amateurs`)
- `c9c61dd` 1918 · `c6ac719` 1917 · `3155a97` 1916 · `9ea9c6e` 1915 (final Racing-San Isidro)
- `b966987` títulos seguidos en los años con dos ligas (Racing, 7 seguidos de 1913 a 1919)
- `48dcf99` 1914 · `f071f28` 1913 (tres grupos, desempate y final) · `6028749` 1912 (`-aaf` y `-faf`) · `37caab9` 1911 ·
  `9753a17` 1910

## Qué se hizo

- **Liga argentina de 1910 a 1930**, cargada a mano como los años anteriores: un script en el scratchpad lee RSSSF
  (`rsssf.org/tablesa/argNN.html`) y escribe `tools/a_mano/liga-<clave>.json`; la entrada de cada torneo va en `TORNEOS`
  (`tools/actualizar_liga.py`). Todo marcado como amateur (en el nombre y en la nota de la tabla).
- **Años con dos ligas**, cada una como un torneo: 1912-1914 (`19NN-aaf` Asociación Argentina y `19NN-faf` Federación
  Argentina) y 1919-1926 (`19NN-aaf` y `19NN-amateurs`, la Asociación Amateurs). Los años con una sola liga, `19NN-primera`.
- Cada tabla se comparó con la de RSSSF (puntos, partidos y goles de cada equipo). Las diferencias que quedaron son de la
  propia tabla de RSSSF, que no coincide con sus resultados, y están aclaradas debajo de la tabla: goles en 1910
  (Estudiantes-Quilmes), 1921 (Atlanta-Ferro), 1924 (Sportivo Barracas, Progresista, Atlanta, Ferro).
- RSSSF viene en cuatro formatos (Ciullini, Wally, Gorgazzi y uno más viejo): un lector por formato en el scratchpad. Cuando
  RSSSF no numera las fechas, cada día de partidos es una fecha; los partidos atrasados que RSSSF pone juntos (un club dos
  veces en la misma fecha) van en fechas aparte. Los suspendidos que se terminaron o se volvieron a jugar, una sola vez; los
  anulados (clubes que se fueron o se disolvieron), fuera, con la explicación en `fuente`.
- Formatos raros: 1929 (dos zonas, `zonas_a_mano`), 1913 de la Asociación (tres grupos que siguen sumando), desempates
  (1923, 1927, 1929), triangular por el descenso (1924), finales (1911, 1912, 1915, 1925, 1929, 1913).
- Página (`js/liga.js`) y script: `descienden_clubes`/`descienden_texto` (bajan clubes puntuales: 1928), `sin_cuadro` (un
  desempate de varios partidos sin cuadro), `final.gana` (final definida en el escritorio: 1925, 1912) y las **rachas de
  títulos** en los años con dos ligas: cada campeón se compara con los campeones del año anterior (Racing, 7 seguidos en
  1919; Boca y San Lorenzo, bicampeones en 1924).
- Títulos (`data/ligas/argentina/titulos.js`): `antes` llega hasta 1909 (Alumni, 8); `ultimo_antes`, Alumni.
- Clubes nuevos (`CLUBES_NUEVOS`): San Isidro, Honor y Patria, Argentino del Sud, Porteño, Sportivo Balcarce, Sportsman,
  Boca Alumni, Alvear, Universal, Del Plata, Progresista, Eureka, Columbian, Gimnasia y Esgrima (Buenos Aires), Belgrano
  Athletic, Kimberley (Villa Devoto: `kimberley-devoto`, el de Mar del Plata es `kimberley`), Comercio, Floresta,
  Ferrocarril Sud, Olivos, Riachuelo, Sportiva Argentina y Alumni. Escudos de Wikipedia; genéricos los de Argentino del
  Sud, Boca Alumni, Universal, Del Plata, Eureka, Columbian, Floresta, Ferrocarril Sud, Olivos, Riachuelo y Sportiva
  Argentina.
- Nombres viejos: van con el club de después y la aclaración en la nota (Platense II/Retiro → Universal, Urquiza → General
  San Martín, Sportivo del Norte → Colegiales, Hispano Argentino → Columbian, Argentino de Banfield → Argentino de Lomas,
  Sportivo Almagro → Almagro).

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan (76). Cada año revisado en el navegador.

## Pendiente / próximos pasos

- Seguir hacia atrás: 1909 y antes (Alumni, Belgrano Athletic, Lomas...; una sola liga). Al cargarlos, sacar sus títulos
  de `antes` en `titulos.js`.
- Escudos verdaderos de los genéricos (los de esta fase y los anteriores). Wikipedia limita las consultas: espaciarlas.
- Revisar si hace falta un nombre propio para las rachas largas ("7 títulos seguidos" ahora; `RACHA` llega a 5).
- Pendientes anteriores: diferencias de un gol en los amateurs 1932-1933; Argentino de Temperley; campeón del Clausura 2026
  en `titulos.js`; goles que faltan (1996-2006); cupos 2021; Sudamericana 2014; torneos de 2027; otras ligas; GitHub Pages y
  Google Search Console.
