# Fase 22

**Fecha:** 2026-10-03

## Commits

- `f248a73` Copa Maradona 2020: el cuadro separa la final (campeón Boca) del repechaje por la Sudamericana; nota corregida

## Qué se hizo

- **Cuadro de la Copa Diego Maradona 2020:** la última columna era el repechaje por la Sudamericana (lo ganó Banfield) y
  parecía la final, así que Banfield parecía el campeón. Ahora el cuadro va en dos partes (`cuadro.bloques` en
  `tools/actualizar_liga.py`): "Final del torneo" (Banfield-Boca, con "🏆 Campeón: Boca Juniors") y "Por un lugar en la
  Copa Sudamericana 2021" (la final de la Complementación y el repechaje).
- **Nota de la pestaña Tabla de 2020 corregida:** al repechaje no fueron "los ganadores de las dos finales" sino el
  ganador de la Complementación (Vélez) y el subcampeón (Banfield).
- En el cuadro, una columna con un solo partido ahora va unida a la siguiente con una línea recta (antes quedaba mal
  armada). README actualizado.

## Estado al cerrar

Todo commiteado y subido a GitHub. Las pruebas pasan. Probado en el navegador: 2020 y el cuadro de los demás torneos.

## Pendiente / próximos pasos

- Los de la fase 21: torneos de 2027 cuando se conozca el formato, años anteriores a 2020, otras ligas nacionales,
  GitHub Pages y Google Search Console, y los pendientes de las copas.
