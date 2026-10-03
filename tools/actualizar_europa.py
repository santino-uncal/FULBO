"""Actualiza la temporada en curso de la Champions League, la Europa League y la Conference League (y la Supercopa de Europa): baja de ESPN los dos años que toca
la temporada (la última de "ediciones" en copas.py: la 2026/27 son 2026 y 2027), arma los datos y corre las pruebas.

Uso:  python tools/actualizar_europa.py
Termina con error si algo falla (por ejemplo, si no pasan las pruebas). No hace commit: eso queda para quien lo corre.
"""
import subprocess
import sys
from pathlib import Path

from copas import COPAS

RAIZ = Path(__file__).resolve().parent.parent


def correr(*args):
    print("»", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=RAIZ, check=True)


def main():
    for clave in ("champions", "europa", "conference"):
        anio = max(COPAS[clave]["ediciones"])
        correr("tools/descargar_espn.py", "--copa", clave, str(anio), str(anio + 1))
    # la Supercopa de Europa: la del año (se juega en agosto)
    correr("tools/descargar_espn.py", "--copa", "supercopa", str(max(COPAS["champions"]["ediciones"])))
    correr("tools/generar_datos.py")
    correr("-m", "unittest", "discover", "tests")


if __name__ == "__main__":
    main()
