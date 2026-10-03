"""Arma data/entrenadores.js: el entrenador (o los entrenadores) de cada equipo en cada edición.

Fuente: Transfermarkt.
  1. La lista de participantes de cada edición da el número de cada club en Transfermarkt.
  2. El historial de entrenadores de cada club trae quién dirigió y desde/hasta qué fecha.
  3. Cruzando esas fechas con las fechas de los partidos de la Copa sale quién dirigió cada partido.
Las páginas bajadas quedan en tools/cache/transfermarkt/ (la segunda vez no se vuelve a pedir nada).
    python tools/descargar_entrenadores.py
    python tools/descargar_entrenadores.py --copa sudamericana   (arma data/sudamericana/entrenadores.js)
"""
import datetime
import difflib
import html
import json
import re
import time
import urllib.request
from collections import Counter, defaultdict

import equipos as E
from copas import COPAS, copa_de_argumentos, prefijo_js
from generar_historial import DATA, RAIZ, leer_ediciones

CACHE = RAIZ / "tools" / "cache" / "transfermarkt"
BASE = "https://www.transfermarkt.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
# Quién dirigió cada partido: {año: {"fecha|local|visitante": {"local": dt, ...}}} (ver COPAS[clave]["entrenadores_partidos"])
AJUSTES = RAIZ / "tools" / "entrenadores_ajustes.json"   # correcciones a mano: {"club-nuestro": id_transfermarkt}


def pedir(url, archivo):
    ruta = CACHE / archivo
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=40) as r:
                texto = r.read().decode("utf-8")
            break
        except Exception as e:   # noqa: BLE001
            print(f"  reintento {i + 1} ({e}): {url}")
            time.sleep(10 * (i + 1))
    else:
        raise RuntimeError(f"No se pudo bajar {url}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    time.sleep(1.5)   # sin apurar al sitio
    return texto


def participantes(anio, clave="libertadores"):
    """[(id_tm, nombre)] de la edición. Transfermarkt numera la temporada con el año anterior."""
    slug, codigo = COPAS[clave]["tm"]
    archivo = f"participantes/{anio}.html" if clave == "libertadores" else f"participantes-{clave}/{anio}.html"
    t = pedir(f"{BASE}/{slug}/teilnehmer/pokalwettbewerb/{codigo}/saison_id/{anio - 1}", archivo)
    vistos = {}
    for nombre, id_ in re.findall(r'<a title="([^"]+)" href="/[^"/]+/startseite/verein/(\d+)"', t):
        vistos.setdefault(int(id_), html.unescape(nombre))
    return list(vistos.items())


# Palabras que no ayudan a reconocer un club ("CA Peñarol" = "Peñarol")
RUIDO = {"ca", "club", "fc", "cd", "sc", "ec", "se", "cr", "cf", "ac", "sd", "de", "del", "la", "el", "los", "y", "e", "do", "da",
         "futbol", "football", "clube", "esporte", "sociedade", "esportiva", "deportes", "sport", "social", "asociacion",
         "corporacion", "sa", "cs", "ad", "fbc", "afc"}


def clave_nombre(texto):
    return " ".join(p for p in re.split(r"[^a-z0-9]+", E.normalizar(texto)) if p and p not in RUIDO)


def parecido(nuestro_id, nombre_tm):
    a = {clave_nombre(E_NOMBRES.get(nuestro_id, nuestro_id)), clave_nombre(nuestro_id.replace("-", " "))}
    b = clave_nombre(nombre_tm)
    mejor = 0
    for x in a:
        ratio = difflib.SequenceMatcher(None, x, b).ratio()
        tx, tb = set(x.split()), set(b.split())
        jac = len(tx & tb) / len(tx | tb) if tx | tb else 0
        cont = 1.0 if x and (x in b or b in x) else 0
        mejor = max(mejor, ratio, jac, 0.9 * cont)
    return mejor


def emparejar(eds, clave="libertadores"):
    """{club_nuestro: id_tm}: en cada edición se empareja cada club con el participante más parecido."""
    votos = defaultdict(Counter)
    dudosos = []
    for anio, ed in eds.items():
        nuestros = sorted({p[l] for f in ed["fases"] for p in f["partidos"] for l in ("local", "visitante")
                           if p[l] and p[l] != "a-definir"})
        suyos = participantes(anio, clave)
        pares = sorted(((parecido(n, s[1]), n, s) for n in nuestros for s in suyos), reverse=True)
        usados_n, usados_s = set(), set()
        for score, n, s in pares:
            if n in usados_n or s[0] in usados_s or score < 0.5:
                continue
            usados_n.add(n)
            usados_s.add(s[0])
            votos[n][s[0]] += 1
            if score < 0.75:
                dudosos.append((anio, n, s[1], round(score, 2)))
        for n in nuestros:
            if n not in usados_n:
                dudosos.append((anio, n, "— sin pareja —", 0))
    elegido = {n: v.most_common(1)[0][0] for n, v in votos.items()}
    ajustes = json.loads(AJUSTES.read_text(encoding="utf-8")) if AJUSTES.exists() else {}
    elegido.update({k: v for k, v in ajustes.items() if v})
    return elegido, [d for d in dudosos if d[1] not in ajustes]   # los corregidos a mano ya no se avisan


def fecha(texto):
    try:
        return datetime.datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def historial_dt(id_tm):
    """[(nombre, desde, hasta)] de los entrenadores del club, primero los titulares y después los interinos."""
    salida = []
    for rol, interino in ((1, False), (10, True)):
        t = pedir(f"{BASE}/x/mitarbeiterhistorie/verein/{id_tm}/personalie_id/{rol}", f"dt/{id_tm}_{rol}.html")
        for fila in re.split(r'<tr class="(?:odd|even)">', t)[1:]:
            m = re.search(r'<a title="([^"]+)" id="\d+" href="/[^"]+/profil/trainer/\d+"', fila)
            fechas = re.findall(r'<td class="zentriert">([^<]*)</td>', fila)
            if not m or not fechas:
                continue
            desde = fecha(fechas[0])
            hasta = fecha(fechas[1]) if len(fechas) > 1 else None
            if desde:
                salida.append({"nombre": html.unescape(m.group(1)), "desde": desde, "hasta": hasta, "interino": interino})
    return salida


def clave_partido(p):
    return f'{p.get("fecha")}|{p["local"]}|{p["visitante"]}'


def quien_dirigio(dts, dia):
    """El entrenador a cargo ese día (si hay titular e interino, el titular)."""
    candidatos = [d for d in dts if d["desde"] <= dia and (d["hasta"] is None or dia <= d["hasta"])]
    candidatos.sort(key=lambda d: (d["interino"], -d["desde"].toordinal()))   # el más reciente en asumir
    return candidatos[0]["nombre"] if candidatos else None


def ids_tm(clave):
    """{club: id_tm} de la copa. La Sudamericana suma lo que ya se sabe por la Libertadores (así un club que
    jugó las dos no depende solo del parecido de nombres en la Sudamericana)."""
    ids, dudosos = emparejar(leer_ediciones(clave), clave)
    if clave != "libertadores":
        base, _ = emparejar(leer_ediciones("libertadores"))
        ids = {**ids, **base}
        dudosos = [d for d in dudosos if d[1] not in base]
    return ids, dudosos


def cargar_nombres():
    global E_NOMBRES
    js = (DATA / "equipos.js").read_text(encoding="utf-8")
    E_NOMBRES = {k: v["nombre"] for k, v in json.loads(js[js.index(".equipos = ") + 11:].rstrip().rstrip(";")).items()}


# Transfermarkt tiene a algunos ayudantes como técnicos titulares en las mismas fechas que el técnico de verdad
DT_A_MANO = {("san-lorenzo", "2015"): "Edgardo Bauza", ("fluminense", "2024"): "Fernando Diniz"}


def dt_conmebol():
    """Para las copas sin participantes en Transfermarkt (la Recopa): una función (club, 'aaaa-mm-dd') -> quién lo
    dirigía ese día, con los clubes que ya se conocen por la Libertadores y la Sudamericana (sale de lo guardado en
    tools/cache/transfermarkt; un club nuevo se baja)."""
    cargar_nombres()
    ids, _ = ids_tm("sudamericana")
    historiales = {}

    def dt(club, dia):
        if club not in ids or not dia:
            return None
        if club not in historiales:
            historiales[club] = historial_dt(ids[club])
        d = datetime.date.fromisoformat(dia)
        if (club, dia[:4]) in DT_A_MANO:
            return DT_A_MANO[club, dia[:4]]
        return quien_dirigio(historiales[club], d)
    return dt


def main(clave="libertadores"):
    cargar_nombres()
    eds = leer_ediciones(clave)
    ids, dudosos = ids_tm(clave)
    print(f"{len(ids)} clubes emparejados con Transfermarkt")
    for d in dudosos:
        print("  revisar:", *d)

    historiales = {}
    for i, (club, id_tm) in enumerate(sorted(ids.items()), 1):
        if not (CACHE / "dt" / f"{id_tm}_1.html").exists():
            print(f"  [{i}/{len(ids)}] {club}")
        historiales[club] = historial_dt(id_tm)

    salida, sin_dato = {}, 0
    por_partido = {}   # quién dirigió a cada lado en cada partido (lo usa generar_estadisticas.py)
    for anio, ed in eds.items():
        por_club = defaultdict(list)
        for f in ed["fases"]:
            for p in f["partidos"]:
                dia = p.get("fecha") and datetime.date.fromisoformat(p["fecha"])
                if not dia:
                    continue
                for lado in ("local", "visitante"):
                    club = p[lado]
                    if club not in historiales:
                        continue
                    dt = quien_dirigio(historiales[club], dia)
                    if dt:
                        por_partido.setdefault(str(anio), {}).setdefault(clave_partido(p), {})[lado] = dt
                    if dt and dt not in por_club[club]:
                        por_club[club].append(dt)
        equipos_ed = {p[l] for f in ed["fases"] for p in f["partidos"] for l in ("local", "visitante")} - {"a-definir", None}
        sin_dato += len(equipos_ed - set(por_club))
        salida[anio] = dict(sorted(por_club.items()))
    total = sum(len(v) for v in salida.values())
    print(f"entrenadores.js: {total} equipos con entrenador, {sin_dato} sin dato")
    cuerpo = json.dumps(salida, ensure_ascii=False, separators=(",", ":"))
    ns = COPAS[clave]["ns"]
    (COPAS[clave]["data"] / "entrenadores.js").write_text(
        "/* Generado por tools/descargar_entrenadores.py (fuente: Transfermarkt) — no editar a mano */\n" +
        prefijo_js(clave) + f"window.{ns}.entrenadores = " + cuerpo + ";\n", encoding="utf-8")
    ruta = COPAS[clave]["entrenadores_partidos"]
    ruta.write_text(json.dumps(por_partido, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{ruta.name}: {sum(len(v) for v in por_partido.values())} partidos con entrenador")


E_NOMBRES = {}

if __name__ == "__main__":
    main(copa_de_argumentos()[0])
