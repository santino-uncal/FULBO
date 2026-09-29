"""Descarga las fotos de los campeones con la copa (Wikimedia Commons) y genera data/fotos-campeones.js.

Las fotos se eligen a mano en tools/fotos_campeones.json:
    {"libertadores/1986": {"archivo": "File:....jpg", "descripcion": "Texto que va debajo de la foto"}, ...}
Este script baja cada una achicada (1000 px de ancho) a assets/campeones/<copa>/<año>.jpg y guarda autor y licencia
para mostrar el crédito. Las que ya están descargadas no se vuelven a bajar.
"""
import html
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ELEGIDAS = RAIZ / "tools" / "fotos_campeones.json"
SALIDA = RAIZ / "data" / "fotos-campeones.js"
CARPETA = RAIZ / "assets" / "campeones"
AGENTE = {"User-Agent": "FULBO/1.0 (https://santino-uncal.github.io/FULBO/)"}
ANCHO = 1000


def pedir(url):
    for intento in range(6):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=AGENTE), timeout=60).read()
        except urllib.error.HTTPError as ex:
            if ex.code != 429:
                raise
            time.sleep(15 * (intento + 1))
    raise RuntimeError(f"Demasiados reintentos: {url}")


def sin_html(texto):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", texto or ""))).strip()


def prolijo(dato):
    """Autor y licencia en castellano ("Unknown authorUnknown author" → "Autor desconocido")."""
    autor = re.sub(r"^(.+?)\1$", r"\1", dato["autor"])
    if re.fullmatch(r"(?i)unknown( author)?|desconocido", autor):
        autor = "Autor desconocido"
    licencia = "Dominio público" if dato["licencia"].lower() == "public domain" else dato["licencia"]
    return {**dato, "autor": autor, "licencia": licencia}


def info(archivo):
    params = {"action": "query", "format": "json", "titles": archivo, "prop": "imageinfo",
              "iiprop": "url|extmetadata", "iiurlwidth": ANCHO}
    datos = json.loads(pedir("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)))
    pagina = next(iter(datos["query"]["pages"].values()))
    ii = pagina["imageinfo"][0]
    meta = ii["extmetadata"]
    return {
        "url": ii.get("thumburl") or ii["url"],
        "fuente": ii["descriptionurl"],
        "autor": sin_html(meta.get("Artist", {}).get("value")) or "Autor desconocido",
        "licencia": sin_html(meta.get("LicenseShortName", {}).get("value")) or "Ver en Commons",
    }


def guardar_jpg(contenido, destino):
    """Guarda la foto como JPG liviano (algunas vienen en PNG y pesan varios MB)."""
    foto = Image.open(io.BytesIO(contenido)).convert("RGB")
    foto.thumbnail((ANCHO, ANCHO))
    foto.save(destino, "JPEG", quality=82, optimize=True)


def main():
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8"))
    anterior = {}
    if SALIDA.exists():
        m = re.search(r"= (\{.*\});", SALIDA.read_text(encoding="utf-8"), re.S)
        anterior = json.loads(m.group(1)) if m else {}
    fotos = {}
    for clave, e in sorted(elegidas.items()):
        copa, anio = clave.split("/")
        destino = CARPETA / copa / f"{anio}.jpg"
        previa = anterior.get(copa, {}).get(anio)
        if previa and previa.get("commons") == e["archivo"] and destino.exists():
            dato = previa
        else:
            i = info(e["archivo"])
            destino.parent.mkdir(parents=True, exist_ok=True)
            guardar_jpg(pedir(i["url"]), destino)
            dato = {"commons": e["archivo"], "fuente": i["fuente"], "autor": i["autor"], "licencia": i["licencia"]}
            print(f"{clave}: {e['archivo']} ({i['autor']}, {i['licencia']})")
            time.sleep(1.5)
        dato = {**prolijo(dato), "archivo": destino.relative_to(RAIZ).as_posix(), "descripcion": e["descripcion"]}
        fotos.setdefault(copa, {})[anio] = dato
    SALIDA.write_text("/* Generado por tools/descargar_fotos_campeones.py — no editar a mano */\n"
                      "window.FOTOS_CAMPEONES = " + json.dumps(fotos, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"{sum(len(v) for v in fotos.values())} fotos en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
