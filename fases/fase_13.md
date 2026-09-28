# Fase 13

**Fecha:** 2026-09-28

## Commits

- `e0ef3cc` Tandas de penales: quién pateó cada penal y si lo metió (datos de ESPN desde 2008)
- `c52c04b` Cabecera: foto de cada trofeo con el nombre de la copa abajo; se resalta bien la copa actual en la Sudamericana
- `647bf97` README: créditos de las fotos de los trofeos
- `74c2c5c` Cabecera: la Sudamericana tiene su lema, "La Gran Conquista"

## Qué se hizo

- **Tandas de penales remate por remate:** "Penales: x – y · ver quién pateó" se despliega y muestra cada ronda,
  un equipo de cada lado (punto verde = gol, cruz roja y nombre tachado = errado) y quién empezó pateando.
  - `descargar_espn.py` ahora guarda el bloque `shootout` de ESPN y vuelve a pedir solo los partidos con penales
    que se habían bajado sin él.
  - `leer_espn.py` arma `tanda` ordenada por ronda (`shotNumber`), abriendo con el equipo del primer remate.
  - `generar_datos.py` la pasa a los datos (dada vuelta si ESPN tomó al otro como local) y la descarta si los goles
    no suman el resultado de los penales (errores de ESPN, p. ej. Boca–Inter 2020, Monagas–Royal Pari 2019).
  - Cobertura: 72 de 77 tandas de la Libertadores y 117 de 127 de la Sudamericana desde 2005 (ESPN no trae
    detalle hasta 2007; antes de 2005 solo RSSSF con el resultado).
- **Cabecera con los trofeos:** foto de cada copa con su nombre abajo (`assets/img/copa-*.webp`, de Wikimedia
  Commons, CC BY-SA 4.0, créditos en el README). La de la Sudamericana se recortó del fondo con `rembg`
  (modelo `birefnet-general-lite`).
- **Arreglo:** en la Sudamericana la copa actual no se resaltaba (`aria-current` quedaba vacío en vez de "page").
- **Lema por copa:** "La Gloria Eterna" (Libertadores) y "La Gran Conquista" (Sudamericana), en `COPAS` de `app.js`.

## Estado al cerrar

Todo commiteado y subido a GitHub. Probado en el navegador: tandas de la final Sudamericana 2018 y
Palestino–Nacional 2024; cabecera en escritorio y celular en las dos copas.

## Pendiente / próximos pasos

- Activar GitHub Pages y dar de alta el sitio en Google Search Console.
- Cargar el campeón y el jugador del torneo 2026 cuando terminen las copas.
- Jugador del torneo de la Sudamericana (no hay lista cargada).
- Tandas anteriores a 2008: no hay fuente con el detalle por ahora.
- Pendientes anteriores: ~25 escudos sin encontrar; formaciones de las finales 2002–2004 de la Sudamericana;
  planteles recientes muy largos; columnas de años centradas.
