# Fase 02 — Tablas de grupos, correcciones de datos y final arriba

**Fecha:** 2026-09-26
**Commits:** `4a4f935`, `a8c93cd`, `7ef9069`, `247a887`, `45f9f75`, `ec82a7e`

## Qué se hizo

- **Tablas de posiciones de los grupos** (estilo de la referencia: fondo oscuro, PTS, J, GOL, +/-, G, E, P
  y últimos 5 resultados V/E/D, el más reciente a la izquierda). Se calculan en `js/app.js` a partir de los partidos.
  - Clasificados en azul (se detecta viendo quién juega la ronda siguiente); desde 2017, el 3° en celeste (Sudamericana).
  - 2 puntos por victoria hasta 1994, 3 desde 1995.
  - En celular se ocultan G/E/P.
- **1960 y 1961** (sin grupos): cada llave se muestra como una mini tabla, porque se definían por puntos;
  el campeón va en dorado.
- **La final** se muestra arriba de todo en cada edición (y su desempate, si hubo).
- **Escudos:**
  - Goiás tenía fondo blanco: se lo sacó. `tools/descargar_escudos.py` ahora quita solo los fondos lisos.
  - Universitario tenía el escudo de Universitario de Sucre: se puso el correcto (lo mandó el usuario).
- **Correcciones en `tools/generar_datos.py`:**
  - 2014–2020 y 2022 no tenían grupos (ESPN no los trae): ahora se toman de RSSSF.
  - Partidos que ESPN no tiene usan el nombre de fase de ESPN (p. ej. Boca–River 2015 queda en octavos).
  - Homónimos mezclados (Nacional URU/PAR, River ARG/URU): se corrigen con ESPN y con un control por grupo.
  - Universitario de Sucre (ESPN 6149) estaba unido a Universitario (Perú): separado con `"espn"` en
    `tools/equipos_ajustes.json`.
  - El emparejamiento RSSSF–ESPN ya no une la ida con la vuelta (arregló Sucre–Wanderers y Capiatá–Táchira 2017).
  - Nuevo ajuste `"resultados"` en `equipos_ajustes.json`: Colo-Colo 0–3 Fortaleza (2025, por escritorio).

## Estado al cerrar

- Desde 2000 todas las ediciones tienen sus grupos completos y consistentes (mismos partidos jugados por equipo).
- 1960–1961 con tablas de llaves.
- Todo commiteado y subido a GitHub.

## Pendiente / próximos pasos

- Tablas de 1962–1999: algunas salen raras porque RSSSF nombra mal las rondas (p. ej. 1968: la primera
  ronda figura como "Semifinales"); hay que revisar esas páginas una por una.
- Nombres cortos para las tablas ("Estudiantes" en vez de "Estudiantes de La Plata") y nombre actual de Cusco
  (figura como "Real Garcilaso").
- "Universitario (Bolivia)" de 1970 figura con ciudad Lima: revisar.
- 2009 y 2010: en dos grupos el que pasó no aparece marcado (retiro/entrada directa de los clubes mexicanos).
- Sigue pendiente lo de la fase 01: diseño general, camisetas, escudos faltantes, publicar en GitHub Pages.
