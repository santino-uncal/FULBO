"""Descarga el escudo de cada club de data/equipos.js.

Uso:  python tools/descargar_escudos.py
Orden de búsqueda:
  1. ESPN (clubes que jugaron desde 2005: tienen id de ESPN en equipos.js)
  2. TheSportsDB (API gratuita), buscando por nombre y país
  (y a mano, para los que no están en ninguno de los dos: la imagen de la ficha del club en Wikipedia)
  (antes que nada, ESCUDOS_A_MANO: clubes que no se encuentran solos, con su número en ESPN o en TheSportsDB)
Guarda assets/escudos/<id>.png (120x120 aprox.) y no vuelve a bajar los que ya existen.
Si un escudo viene con fondo de color liso (blanco, por ejemplo), se lo saca para que quede transparente.
Al final lista los que no encontró, para buscarlos a mano o dejar que la web muestre las iniciales.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from equipos import normalizar  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "escudos"
ESPN = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/{}.png&h=120&w=120"
TSDB = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="
TSDB_ID = "https://www.thesportsdb.com/api/v1/json/3/lookupteam.php?id="
# Clubes cuyo escudo no se encuentra solo (en ESPN figuran con otro número o sin escudo; en TheSportsDB, con otro nombre)
ESCUDOS_A_MANO = {
    "ajax": "espn:139", "feyenoord": "espn:142", "psv": "espn:148", "nottingham-forest": "espn:393",
    "red-star-belgrade": "espn:2290", "kashiwa-reysol": "espn:7476", "hamburger-sv": "espn:127",
    "steaua-bucuresti": "tsdb:143176", "raja-casablanca": "tsdb:136404", "tp-mazembe": "tsdb:138139",
    "pyramids": "tsdb:139838", "jeonbuk-motors": "tsdb:138111", "sepahan": "tsdb:139014", "etoile-sahel": "tsdb:138999",
    "al-wahda": "tsdb:137836", "shabab-al-ahli": "tsdb:137828", "seongnam-ilhwa": "tsdb:138114",
    "hekari-united": "tsdb:139102", "waitakere-united": "tsdb:139101", "hienghene-sport": "tsdb:137649",
    "as-pirae": "tsdb:144956",
    # Champions League
    "1-kaiserslautern": "tsdb:133663", "hertha-bsc": "tsdb:133658", "heerenveen": "tsdb:133759", "willem-ii": "tsdb:133827",
    "kispest-honved": "tsdb:134070", "fram": "tsdb:140780", "ia": "tsdb:137972", "hamrun-spartans": "tsdb:138133",
    "artmedia-petrzalka": "tsdb:146306",
    # los que no están ni en ESPN ni en TheSportsDB: el escudo de la ficha del club en Wikipedia ("wiki:<idioma>:<archivo>";
    # 1. FC Frankfurt es el continuador del Vorwärts Berlin)
    "avenir-beggen": "wiki:en:FC_Avenir_Beggen_logo.svg", "ifk-helsingfors": "wiki:en:HIFK-Jalkapallo.svg", "kb": "wiki:en:Kjøbenhavns_Boldklub_logo.png",
    "vorwarts-berlin": "wiki:en:Logo_1._FC_Frankfurt_(Oder).svg", "cork-celtic": "wiki:en:Cork Celtic FC logo.png", "cork-hibernians": "wiki:en:Cork Hibs logo.png",
    "dinamo-minsk": "wiki:en:Dinamo Minsk logo.svg", "gwardia-warsaw": "wiki:en:Gwardia Warszawa Logo.png", "hapoel-tel-aviv": "wiki:en:Hapoel_Tel_Aviv_F.C._logo.svg",
    "polonia-bytom": "wiki:en:Polonia Bytom crest.png", "rabat-ajax": "wiki:en:Rabat Ajax Crest.jpg", "rapid-bucuresti": "wiki:en:FC Rapid Bucuresti logo.svg",
    "szombierki-bytom": "wiki:en:Szombierki Bytom badge.png", "unirea-urziceni": "wiki:en:Unirea Urziceni.png", "boldklubben-1903": "wiki:en:Boldklubben 1903.png",
    "ops": "wiki:fi:OPS logo.png", "aris-bonnevoie": "wiki:en:Aris Bonnevoie (logo).png",
    "atletico-chalaco": "wiki:es:EscudoClubAtleticoChalaco2021.jpg", "atletico-torino": "wiki:es:Logo_de_Club_Atletico_Torino.png",
    "coronel-bolognesi": "wiki:es:Club_Coronel_Bolognesi_(logo).svg",
    "everest": "wiki:es:Logo_del_Club_Deportivo_Everest.png", "rangers": "wiki:es:Rangers_de_Talca_-_Escudo.svg",
    # (clubes que ya no existen con ese nombre: el escudo de su continuador — 17 Nëntori es el KF Tirana,
    # Karl-Marx-Stadt el Chemnitzer, Rapid JC el Roda JC, Stade Dudelange el F91…)
    "17-nentori": "tsdb:134037", "ab": "tsdb:141778", "admira-no-energie-wien": "tsdb:134008", "banik-ostrava": "tsdb:136684",
    "bfc-dynamo": "tsdb:138384", "bohemians-prague": "tsdb:136681", "boldklubben-1909": "tsdb:143431", "boldklubben-1913": "tsdb:143422",
    "cervena-hviezda-bratislava": "tsdb:134029", "derry-city": "tsdb:134354", "dinamo-tirana": "tsdb:140666", "dukla-prague": "tsdb:136682",
    "dws": "tsdb:155108", "helsingin-palloseura": "tsdb:155348", "ifk-norrkoping": "tsdb:134165", "ka": "tsdb:137970",
    "karl-marx-stadt": "tsdb:137957", "kr": "tsdb:133968", "labinoti": "tsdb:140668", "lausanne-sports": "tsdb:138990",
    "molenbeek": "tsdb:135924", "progres-niedercorn": "tsdb:138347", "rapid-jc": "tsdb:133761", "red-boys-differdange": "tsdb:134064",
    "reims": "tsdb:133934", "reipas-lahti": "tsdb:136686", "sarajevo": "tsdb:134013", "sparta-rotterdam": "tsdb:133866",
    "spartak-hradec-kralove": "tsdb:141109", "spora-luxembourg": "tsdb:139740", "stade-dudelange": "tsdb:133947", "vardar": "tsdb:133979",
    "vitkovice": "tsdb:153228", "voest-linz": "tsdb:139412", "vv-dos": "tsdb:133764", "wisla-krakow": "tsdb:135303",
    "wismut-karl-marx-stadt": "tsdb:134445", "zbrojovka-brno": "tsdb:140094", "zeljeznicar": "tsdb:137934", "zorya-voroshilovgrad": "tsdb:134422",
}
PAISES = {"ARG": "Argentina", "BRA": "Brazil", "URU": "Uruguay", "PAR": "Paraguay", "CHI": "Chile",
          "COL": "Colombia", "PER": "Peru", "ECU": "Ecuador", "BOL": "Bolivia", "VEN": "Venezuela", "MEX": "Mexico",
          # clubes del Mundial de Clubes y la Intercontinental que no están en ESPN
          "ESP": "Spain", "ITA": "Italy", "ENG": "England", "SCO": "Scotland", "GER": "Germany", "NED": "Netherlands",
          "POR": "Portugal", "ROU": "Romania", "SWE": "Sweden", "GRE": "Greece", "YUG": "Serbia", "KSA": "Saudi Arabia",
          "AUS": "Australia",
          # clubes de la Champions League
          "FRA": "France", "AUT": "Austria", "BEL": "Belgium", "CRO": "Croatia", "DEN": "Denmark", "TUR": "Turkey",
          "CYP": "Cyprus", "UKR": "Ukraine", "CZE": "Czech Republic", "SVK": "Slovakia", "SUI": "Switzerland",
          "NOR": "Norway", "FIN": "Finland", "IRL": "Ireland", "ISL": "Iceland", "LTU": "Lithuania", "LUX": "Luxembourg",
          "LVA": "Latvia", "MLT": "Malta", "NIR": "Northern Ireland", "POL": "Poland", "HUN": "Hungary", "BUL": "Bulgaria",
          "ALB": "Albania", "SRB": "Serbia", "SVN": "Slovenia", "MDA": "Moldova", "BLR": "Belarus", "ISR": "Israel",
          "RUS": "Russia", "KAZ": "Kazakhstan", "AZE": "Azerbaijan",
          "GEO": "Georgia", "ARM": "Armenia", "BIH": "Bosnia-Herzegovina", "MKD": "North Macedonia"}


def leer_equipos():
    texto = (RAIZ / "data" / "equipos.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.LIB\.equipos\s*=\s*(\{.*\});", texto, re.S).group(1))


UA = "FULBO-historia/1.0 (https://santino-uncal.github.io/FULBO/)"   # Wikipedia pide que los programas se identifiquen


def bajar(url, archivo, ua=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua} if ua else {}), timeout=30) as r:
        datos = r.read()
    if len(datos) < 500:  # respuesta vacía o imagen "no disponible"
        return False
    archivo.write_bytes(datos)
    return True


def quitar_fondo(archivo):
    """Si las 4 esquinas son del mismo color opaco, borra ese fondo (relleno desde cada esquina). Devuelve True si cambió."""
    im = Image.open(archivo).convert("RGBA")
    w, h = im.size
    esquinas = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    colores = [im.getpixel(p) for p in esquinas]
    if not all(c[3] > 200 for c in colores):
        return False  # ya tiene fondo transparente
    if max(abs(a - b) for c in colores for a, b in zip(c, colores[0])) > 30:
        return False  # esquinas de distinto color: probablemente el escudo ocupa toda la imagen
    for p in esquinas:
        if im.getpixel(p)[3]:
            ImageDraw.floodfill(im, p, (0, 0, 0, 0), thresh=60)
    im.save(archivo)
    return True


def pedir_tsdb(url):
    """TheSportsDB corta con "Too Many Requests" si se le pide mucho seguido: se espera un minuto y se reintenta."""
    for intento in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or intento == 3:
                raise
            time.sleep(60)


def buscar_tsdb(eq, id_=""):
    """Busca en TheSportsDB probando variantes del nombre (también el id, que suele ser el nombre original:
    'Niza' se busca como 'nice'); exige que coincida el país."""
    nombres = [eq["nombre"], re.sub(r"\s*\(.*\)", "", eq["nombre"]), re.sub(r"-[a-z]{3}$", "", id_).replace("-", " ")]
    for nombre in dict.fromkeys(n for n in nombres if n):
        equipos = pedir_tsdb(TSDB + urllib.parse.quote(nombre)).get("teams") or []
        time.sleep(2)  # la API gratuita limita la cantidad de pedidos por minuto
        for t in equipos:
            if t.get("strSport") != "Soccer" or not t.get("strBadge"):
                continue
            if eq.get("pais") and t.get("strCountry") != PAISES.get(eq["pais"]):
                continue
            if normalizar(t["strTeam"]) == normalizar(nombre) or normalizar(nombre) in normalizar(t["strTeam"]):
                return t["strBadge"] + "/small"
    return None


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    faltan = []
    for id_, eq in leer_equipos().items():
        archivo = DESTINO / f"{id_}.png"
        if archivo.exists():
            continue
        ok = False
        fuente, _, num = ESCUDOS_A_MANO.get(id_, "").partition(":")
        try:
            if fuente == "espn":
                ok = bajar(ESPN.format(num), archivo)
            elif fuente == "wiki":   # la imagen achicada a 120 px (Wikipedia la da en PNG aunque el archivo sea SVG)
                idioma, _, archivo_wiki = num.partition(":")
                q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url",
                                            "iiurlwidth": 120, "titles": "File:" + archivo_wiki})
                req = urllib.request.Request(f"https://{idioma}.wikipedia.org/w/api.php?{q}", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as r:
                    info = next(iter(json.load(r)["query"]["pages"].values()))["imageinfo"][0]
                ok = bajar(info["thumburl"], archivo, UA)
            elif fuente == "tsdb":
                ok = bajar(pedir_tsdb(TSDB_ID + num)["teams"][0]["strBadge"] + "/small", archivo)
        except Exception:
            ok = False
        if ok:
            print(f"  ✓ {eq['nombre']} (a mano)", flush=True)
        for eid in [] if ok else reversed(eq.get("espn", [])):
            try:
                ok = bajar(ESPN.format(eid), archivo)
            except Exception:
                ok = False
            if ok:
                print(f"  ✓ {eq['nombre']} (ESPN)", flush=True)
                break
        if not ok:
            try:
                url = buscar_tsdb(eq, id_)
                ok = bool(url) and bajar(url, archivo)
            except Exception:
                ok = False
            if ok:
                print(f"  ✓ {eq['nombre']} (TheSportsDB)", flush=True)
        if not ok:
            faltan.append(f"{id_} ({eq['nombre']}, {eq.get('pais')})")
        time.sleep(0.3)
    for archivo in sorted(DESTINO.glob("*.png")):
        if quitar_fondo(archivo):
            print(f"  ✓ fondo quitado: {archivo.name}")
    print(f"\nNo encontrados ({len(faltan)}):", *faltan, sep="\n  ")


if __name__ == "__main__":
    main()
