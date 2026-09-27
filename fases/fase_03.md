# Fase 03

**Fecha:** 2026-09-26

## Commits

- `45dab20` Fondo de la página con los colores del campeón de cada edición
- `df82a3c` Toda la página se viste con los colores del campeón: fondo y letras
- `9d0bc66` Partidos de cada grupo separados por fecha (Grupo A · Fecha 1…) y grupos en orden alfabético
- `6940dae` 1990, 1992, 1993 y 1995: el desempate por el 3.er puesto de un grupo ya no se confunde con el partido por el tercer puesto
- `ebfe06c` Goleadores y asistidores: botón Ver con el detalle de cada gol o asistencia
- `6c58842` Goleadores y asistidores: botón Ver todos para desplegar la lista completa
- `e6d2e49` Goleadores y asistidores: botón Mostrar/Ocultar arriba de cada tabla

## Qué se hizo

- **Colores del campeón:** la página toma el fondo y el color de letras de la camiseta del campeón de cada
  edición (ej. 2018 River: fondo blanco, letras rojas; 2000 Boca: fondo azul, letras amarillas).
  Los pares [fondo, letras] están cargados a mano en `data/colores.js` (los de ESPN venían mal).
  Paneles, bordes y textos suaves se calculan mezclando esos dos colores (`color-mix` en `css/estilos.css`).
  Sin campeón (2026) queda el diseño original azul oscuro y dorado.
- **Fechas de grupos:** en la lista de partidos de cada grupo, títulos "Grupo A · Fecha 1", etc.
  Los datos no traen el número de fecha: se deduce juntando partidos sin equipos repetidos
  (`porFechas` en `js/app.js`), así un partido postergado queda en su fecha. Grupos ordenados A, B, C…
  con cada desempate justo después de su grupo.
- **Corrección 1990/1992/1993/1995:** el "Third Place Playoff" dentro de un grupo (RSSSF) se tomaba como el
  partido por el tercer puesto del torneo y arrastraba a los grupos siguientes. Arreglado en
  `tools/leer_rsssf.py` y datos regenerados.
- **Goleadores y asistidores:**
  - Botón "Ver" por jugador con el detalle de cada gol/asistencia (minuto, partido, fase, fecha, penal, asistidor).
  - Lista completa: se ven los 15 primeros y "Ver todos (N)" despliega el resto.
  - Botón "Mostrar/Ocultar" al lado del título; las tablas arrancan cerradas.

## Estado al cerrar

- Todo commiteado y subido a GitHub.

## Pendiente / próximos pasos

- Revisar a ojo los colores de cada campeón en `data/colores.js` (el usuario puede pedir cambios, ej. Racing con fondo celeste).
- Fechas de las listas de partidos en formato AAAA-MM-DD: evaluar mostrarlas como DD/MM/AAAA.
- Siguen los pendientes de la fase 02: rondas mal nombradas en 1962–1999, nombres cortos, Universitario (Bolivia) 1970,
  marcas de clasificados 2009/2010, y lo de la fase 01 (diseño general, camisetas, escudos faltantes, GitHub Pages).
