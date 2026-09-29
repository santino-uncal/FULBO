"""Arma data/mapa.js: el mapa de la portada (América y Europa), con cada país dibujado y agrupado por continente.

Uso:  python tools/generar_mapa.py
Fuente: Natural Earth (naturalearthdata.com, dominio público), países a escala 1:110 millones.
Se baja una sola vez a tools/cache/mapa/paises.geojson.
El mapa usa la proyección Robinson (la de los mapamundis de la escuela), recortada a América y Europa (Rusia
llega hasta los Urales), y queda como texto de dibujo SVG: así la página lo muestra sin pedir otro archivo
(funciona también abriendo index.html con doble clic).
"""
import json
import math
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
CACHE = RAIZ / "tools" / "cache" / "mapa" / "paises.geojson"
ANCHO = 1000
LAT_ARRIBA, LAT_ABAJO = 80, -57          # sin el Ártico vacío (Groenlandia queda casi entera)
LON_OESTE, LON_ESTE = -170, 60           # desde Alaska hasta los Urales
MARGEN = 8                               # aire alrededor del dibujo

# Continentes que se dibujan (los de Natural Earth -> la clave que usa la página, la de data/continentes.js)
CONTINENTES = {"South America": "sudamerica", "North America": "norteamerica", "Europe": "europa"}
# Territorios que se dibujan aparte de su país (ver continente_de_parte)
TERRITORIOS = {("Francia", "sudamerica"): "Guayana Francesa"}

# Proyección Robinson: tabla cada 5 grados de latitud (largo del paralelo y altura)
TABLA_X = [1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600, 0.9427, 0.9216, 0.8962,
           0.8679, 0.8350, 0.7986, 0.7597, 0.7186, 0.6732, 0.6213, 0.5722, 0.5322]
TABLA_Y = [0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720, 0.4340, 0.4958, 0.5571,
           0.6176, 0.6769, 0.7346, 0.7903, 0.8435, 0.8936, 0.9394, 0.9761, 1.0000]


def robinson(lon, lat):
    lat = max(min(lat, LAT_ARRIBA), LAT_ABAJO)
    a = min(abs(lat), 90) / 5
    i = min(int(a), 17)
    t = a - i
    px = TABLA_X[i] + (TABLA_X[i + 1] - TABLA_X[i]) * t
    py = TABLA_Y[i] + (TABLA_Y[i + 1] - TABLA_Y[i]) * t
    return 0.8487 * px * math.radians(lon), -1.3523 * py * (1 if lat >= 0 else -1)   # (y crece hacia abajo)


def recortar(anillo, lon, queda_a_la_izquierda):
    """Corta un contorno con un meridiano (algoritmo de Sutherland-Hodgman para un solo borde)."""
    dentro = (lambda p: p[0] <= lon) if queda_a_la_izquierda else (lambda p: p[0] >= lon)
    res = []
    for i, p in enumerate(anillo):
        q = anillo[i - 1]
        if dentro(p) != dentro(q):
            t = (lon - q[0]) / (p[0] - q[0])
            res.append((lon, q[1] + (p[1] - q[1]) * t))
        if dentro(p):
            res.append(tuple(p[:2]))
    return res


def continente_de_parte(continente, poligono):
    """Los territorios lejanos van con su continente geográfico: la Guayana Francesa (parte de Francia) es de
    Sudamérica, no de Europa."""
    lons = [p[0] for p in poligono[0]]
    lats = [p[1] for p in poligono[0]]
    lon, lat = sum(lons) / len(lons), sum(lats) / len(lats)
    if continente in ("Europe", "Asia", "Africa") and -170 < lon < -30:   # (la punta de Rusia pasa de -170)
        return "South America" if lat < 13 else "North America"
    return continente


def main():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FUENTE, CACHE)
    datos = json.loads(CACHE.read_text(encoding="utf-8"))
    paises = []   # (nombre, continente, [contornos proyectados])
    for f in datos["features"]:
        p = f["properties"]
        g = f["geometry"]
        poligonos = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        partes = {}
        for pol in poligonos:
            c = CONTINENTES.get(continente_de_parte(p["CONTINENT"], pol))
            if not c:
                continue   # África, Asia, Oceanía y la Antártida no se dibujan
            for anillo in pol:
                anillo = recortar(recortar(anillo, LON_ESTE, True), LON_OESTE, False)
                if len(anillo) >= 3:
                    partes.setdefault(c, []).append([robinson(lon, lat) for lon, lat in anillo])
        nombre = p.get("NAME_ES") or p["NAME"]
        for c, anillos in partes.items():
            paises.append((TERRITORIOS.get((nombre, c), nombre), c, anillos))
    # Encuadre: lo justo para que entre todo lo dibujado
    xs = [x for _, _, an in paises for a in an for x, _ in a]
    ys = [y for _, _, an in paises for a in an for _, y in a]
    escala = (ANCHO - 2 * MARGEN) / (max(xs) - min(xs))
    alto = round((max(ys) - min(ys)) * escala + 2 * MARGEN)

    def trazo(anillo):
        pts, previo = [], None
        for x, y in anillo:
            q = (round((x - min(xs)) * escala + MARGEN, 1), round((y - min(ys)) * escala + MARGEN, 1))
            if q != previo:
                pts.append(q)
                previo = q
        return "M" + "L".join(f"{a:g},{b:g}" for a, b in pts) + "Z" if len(pts) >= 3 else ""

    salida = {"ancho": ANCHO, "alto": alto,
              "paises": [{"n": n, "c": c, "d": "".join(trazo(a) for a in an)} for n, c, an in paises]}
    (RAIZ / "data" / "mapa.js").write_text(
        "/* Generado por tools/generar_mapa.py (fuente: Natural Earth, dominio público) — no editar a mano */\n"
        "window.MAPA = " + json.dumps(salida, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"mapa.js: {len(paises)} países, {ANCHO}x{alto}")


if __name__ == "__main__":
    main()
