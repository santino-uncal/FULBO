"""Arma data/mapa.js: los dos mapas de la portada, Sudamérica y Europa, con cada país dibujado.

Uso:  python tools/generar_mapa.py
Fuente: Natural Earth (naturalearthdata.com, dominio público), países a escala 1:110 millones.
Se baja una sola vez a tools/cache/mapa/paises.geojson.
Cada mapa usa la proyección Robinson centrada en su continente y recortada a su zona (Europa, desde Islandia
hasta los Urales). Queda como texto de dibujo SVG: así la página lo muestra sin pedir otro archivo (funciona
también abriendo index.html con doble clic).
"""
import json
import math
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
CACHE = RAIZ / "tools" / "cache" / "mapa" / "paises.geojson"
ANCHO = 600
MARGEN = 6   # aire alrededor del dibujo

# Cada mapa: el continente de Natural Earth, el meridiano del centro y el recorte (oeste, este, sur, norte).
# extras: países que Natural Earth pone en otro continente pero se dibujan en este (Turquía, Armenia, Georgia y Azerbaiyán
# figuran en Asia, pero en el fútbol son de Europa: juegan en la UEFA; lo mismo Israel, Chipre y Kazajistán.
# El norte de Chipre viene aparte y se dibuja para que la isla no quede cortada)
MAPAS = {
    "sudamerica": {"continente": "South America", "centro": -60, "recorte": (-95, -30, -57, 14)},
    "europa": {"continente": "Europe", "centro": 18, "recorte": (-25, 62, 29, 71),
               "extras": {"TUR", "ARM", "GEO", "AZE", "ISR", "CYP", "CYN", "KAZ"}},
}
# Territorios que se dibujan aparte de su país (ver continente_de_parte)
TERRITORIOS = {("Francia", "South America"): "Guayana Francesa"}

# Proyección Robinson: tabla cada 5 grados de latitud (largo del paralelo y altura)
TABLA_X = [1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600, 0.9427, 0.9216, 0.8962,
           0.8679, 0.8350, 0.7986, 0.7597, 0.7186, 0.6732, 0.6213, 0.5722, 0.5322]
TABLA_Y = [0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720, 0.4340, 0.4958, 0.5571,
           0.6176, 0.6769, 0.7346, 0.7903, 0.8435, 0.8936, 0.9394, 0.9761, 1.0000]


def robinson(lon, lat):
    a = min(abs(lat), 90) / 5
    i = min(int(a), 17)
    t = a - i
    px = TABLA_X[i] + (TABLA_X[i + 1] - TABLA_X[i]) * t
    py = TABLA_Y[i] + (TABLA_Y[i + 1] - TABLA_Y[i]) * t
    return 0.8487 * px * math.radians(lon), -1.3523 * py * (1 if lat >= 0 else -1)   # (y crece hacia abajo)


def recortar(anillo, eje, limite, menor):
    """Corta un contorno con un meridiano (eje 0) o un paralelo (eje 1): se queda con lo que está del lado menor
    (o mayor) del límite. Es el algoritmo de Sutherland-Hodgman para un solo borde."""
    dentro = (lambda p: p[eje] <= limite) if menor else (lambda p: p[eje] >= limite)
    res = []
    for i, p in enumerate(anillo):
        q = anillo[i - 1]
        if dentro(p) != dentro(q):
            t = (limite - q[eje]) / (p[eje] - q[eje])
            corte = [q[0] + (p[0] - q[0]) * t, q[1] + (p[1] - q[1]) * t]
            corte[eje] = limite
            res.append(tuple(corte))
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


def armar(datos, conf):
    oeste, este, sur, norte = conf["recorte"]
    paises = []   # (nombre, [contornos proyectados])
    for f in datos["features"]:
        p = f["properties"]
        g = f["geometry"]
        poligonos = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        anillos = []
        for pol in poligonos:
            if continente_de_parte(p["CONTINENT"], pol) != conf["continente"] and p["ADM0_A3"] not in conf.get("extras", ()):
                continue
            for anillo in pol:
                for eje, limite, menor in ((0, este, True), (0, oeste, False), (1, norte, True), (1, sur, False)):
                    anillo = recortar(anillo, eje, limite, menor) if len(anillo) >= 3 else []
                if len(anillo) >= 3:
                    anillos.append([robinson(lon - conf["centro"], lat) for lon, lat in anillo])
        if anillos:
            nombre = p.get("NAME_ES") or p["NAME"]
            paises.append((TERRITORIOS.get((nombre, conf["continente"]), nombre), anillos))
    # Encuadre: lo justo para que entre todo lo dibujado
    xs = [x for _, an in paises for a in an for x, _ in a]
    ys = [y for _, an in paises for a in an for _, y in a]
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

    return {"ancho": ANCHO, "alto": alto, "paises": [{"n": n, "d": "".join(trazo(a) for a in an)} for n, an in paises]}


def main():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FUENTE, CACHE)
    datos = json.loads(CACHE.read_text(encoding="utf-8"))
    salida = {clave: armar(datos, conf) for clave, conf in MAPAS.items()}
    (RAIZ / "data" / "mapa.js").write_text(
        "/* Generado por tools/generar_mapa.py (fuente: Natural Earth, dominio público) — no editar a mano */\n"
        "window.MAPA = " + json.dumps(salida, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    for clave, m in salida.items():
        print(f"{clave}: {len(m['paises'])} países, {m['ancho']}x{m['alto']}")


if __name__ == "__main__":
    main()
