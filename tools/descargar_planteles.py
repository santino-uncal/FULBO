"""Completa los planteles de cada edición con la plantilla de Transfermarkt.

Los planteles que arma generar_datos.py salen de las formaciones y los goles de cada partido: en las ediciones
viejas (antes de 2005) quedan solo los que hicieron goles. Acá se baja la plantilla de cada club en esa
temporada y se suma a la lista: los que ya estaban ganan número/posición/nombre completo, los que faltan se agregan.

  1. Los clubes se emparejan con Transfermarkt igual que en descargar_entrenadores.py.
  2. Se baja la página "kader" (plantel) de cada club en cada temporada → tools/planteles_tm.json.
  3. Se mezcla con los planteles de data/ediciones/*.js (lo hace también generar_datos.py al final).
Las páginas bajadas quedan en tools/cache/transfermarkt/kader/ (la segunda vez no se vuelve a pedir nada).
    python tools/descargar_planteles.py
    python tools/descargar_planteles.py --copa sudamericana
"""
import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import descargar_entrenadores as D
import equipos as E
from copas import COPAS, copa_de_argumentos
from generar_historial import DATA, leer_ediciones

# Planteles de Transfermarkt de cada copa: {año: {club: [{nombre, tid, num, pos}]}} (ver COPAS[clave]["planteles_tm"])

# Posición de Transfermarkt → las mismas siglas que usan las formaciones de ESPN
POSICIONES = {
    "Goalkeeper": "G", "Sweeper": "SW", "Centre-Back": "CD", "Left-Back": "LB", "Right-Back": "RB", "Defender": "D",
    "Defensive Midfield": "DM", "Central Midfield": "CM", "Left Midfield": "LM", "Right Midfield": "RM",
    "Attacking Midfield": "AM", "Midfield": "M", "Left Winger": "LF", "Right Winger": "RF",
    "Second Striker": "F", "Centre-Forward": "F", "Striker": "F", "Attack": "F",
}


def plantel_tm(id_tm, anio):
    """Plantel del club en la temporada de esa Copa (Transfermarkt numera la temporada con el año anterior)."""
    t = D.pedir(f"{D.BASE}/x/kader/verein/{id_tm}/saison_id/{anio - 1}/plus/1", f"kader/{id_tm}_{anio - 1}.html")
    i = t.find('<table class="items">')
    if i < 0:
        return []
    jugadores = []
    for fila in re.split(r'<tr class="(?:odd|even)">', t[i:])[1:]:
        # (después del nombre puede venir un ícono: lesión, suspensión…)
        m = re.search(r'<a href="/[^"]+/profil/spieler/(\d+)"[^>]*>\s*([^<]+?)\s*<', fila)
        if not m:
            continue
        num = re.search(r'<div class=rn_nummer>([^<]*)</div>', fila)
        pos = re.search(r'</tr>\s*<tr>\s*<td>\s*([^<]+?)\s*</td>', fila)
        num = num.group(1).strip() if num else ""
        # Fecha de llegada al club (la de la última vez que llegó: si volvió años después, es la de la vuelta)
        llegada = re.search(r'<td class="zentriert">(\d\d)/(\d\d)/(\d{4})</td>', fila)
        jugadores.append({"nombre": html.unescape(m.group(2)), "tid": m.group(1),
                          "num": num if num.isdigit() else None,
                          "pos": POSICIONES.get(pos.group(1).strip()) if pos else None,
                          **({"llegada": "-".join(reversed(llegada.groups()))} if llegada else {})})
    return jugadores


def descargar(clave="libertadores"):
    js = (DATA / "equipos.js").read_text(encoding="utf-8")
    D.E_NOMBRES = {k: v["nombre"] for k, v in json.loads(js[js.index(".equipos = ") + 11:].rstrip().rstrip(";")).items()}
    eds = leer_ediciones(clave)
    ids, _ = D.ids_tm(clave)
    salida = {}
    pares = [(anio, club) for anio, ed in eds.items()
             for club in sorted({p[l] for f in ed["fases"] for p in f["partidos"] for l in ("local", "visitante")}
                                - {"a-definir", None}) if club in ids]
    # Se bajan de a 4 a la vez (cada uno igual espera un poco entre pedido y pedido)
    faltan = [(anio, club) for anio, club in pares if not (D.CACHE / "kader" / f"{ids[club]}_{anio - 1}.html").exists()]
    with ThreadPoolExecutor(4) as pool:
        for n, _ in enumerate(pool.map(lambda x: plantel_tm(ids[x[1]], x[0]), faltan), 1):
            if n % 25 == 0 or n == len(faltan):
                print(f"  [{n}/{len(faltan)}] bajados", flush=True)
    for anio, club in pares:
        lista = plantel_tm(ids[club], anio)
        if lista:
            salida.setdefault(str(anio), {})[club] = lista
    ruta = COPAS[clave]["planteles_tm"]
    ruta.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{ruta.name}: {sum(len(v) for v in salida.values())} planteles de {len(pares)}")


# ---------------------------------------------------------------- mezcla

def palabras(nombre):
    return [p for p in re.split(r"[^a-z0-9]+", E.normalizar(nombre)) if p]


def mismo_jugador(nuestro, suyo):
    """¿Es la misma persona? Nombre igual, o mismo apellido y misma inicial, o solo el apellido (ediciones viejas)."""
    a, b = palabras(nuestro), palabras(suyo)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) == 1:   # "Francescoli" / "Enzo Francescoli"; ESPN a veces pone solo el nombre: "Alexandre" / "Alexandre Pato"
        return a[0] in b
    if len(b) == 1:   # apodos de Transfermarkt ("Ronaldinho")
        return b[0] in a
    return a[-1] == b[-1] and a[0][0] == b[0][0] or " ".join(a) in " ".join(b) or " ".join(b) in " ".join(a)


def con_formaciones(ed, club):
    """Si el club tiene formación en la mayoría de sus partidos de la edición (desde 2005, con ESPN)."""
    jugados = [p for f in ed["fases"] for p in f["partidos"] if club in (p["local"], p["visitante"]) and p.get("gl") is not None]
    con = [p for p in jugados if (p.get("formaciones") or {}).get("local" if p["local"] == club else "visitante")]
    return bool(jugados) and len(con) * 2 > len(jugados)


def ultimo_partido(ed, club):
    fechas = [p["fecha"] for f in ed["fases"] for p in f["partidos"]
              if club in (p["local"], p["visitante"]) and p.get("fecha")]
    return max(fechas) if fechas else None


def llego_tarde(s, ultimo, anio):
    """Llegó al club después de que terminó de jugar la copa, ese mismo año (la plantilla de Transfermarkt es la de
    toda la temporada). Si la fecha es de años después, es la de una vuelta al club y no dice nada."""
    return bool(ultimo and s.get("llegada") and ultimo < s["llegada"] <= f"{anio}-12-31")


def mezclar(planteles, tm, ed=None):
    """Suma la plantilla de Transfermarkt a los planteles de una edición ({club: [jugadores]}).
    Con la edición (ed): si el club tiene formaciones, el plantel son los que estuvieron en ellas (titulares y
    suplentes) y Transfermarkt solo completa número, posición y nombre; si no, se suman los de Transfermarkt,
    menos los que llegaron al club después de su último partido de la copa."""
    for club, suyos in tm.items():
        nuestros = planteles.setdefault(club, [])
        cerrado = ed is not None and con_formaciones(ed, club)
        ultimo = ultimo_partido(ed, club) if ed is not None else None
        sueltos = []
        for s in suyos:
            libres = [j for j in nuestros if not j.get("tid")]
            candidatos = ([j for j in nuestros if j.get("tid") == s["tid"]]
                          or [j for j in libres if palabras(j.get("nombre") or "") == palabras(s["nombre"])]
                          or [j for j in libres if mismo_jugador(j.get("nombre") or "", s["nombre"])])
            if len(candidatos) == 1:
                completar(candidatos[0], s)
            elif not candidatos:
                sueltos.append(s)
        # Apodos ("Nacho Fernández" / "Ignacio Fernández"): mismo apellido y único de cada lado
        apellido = lambda n: (palabras(n) or [""])[-1]
        libres = [j for j in nuestros if not j.get("tid")]
        for s in sueltos:
            mios = [j for j in libres if apellido(j.get("nombre") or "") == apellido(s["nombre"])]
            suyos_igual = [x for x in sueltos if apellido(x["nombre"]) == apellido(s["nombre"])]
            if len(mios) == 1 and len(suyos_igual) == 1 and len(palabras(s["nombre"])) > 1:
                completar(mios[0], s)
                libres.remove(mios[0])
                continue
            if cerrado or llego_tarde(s, ultimo, ed["anio"] if ed else 0):
                continue
            nuevo = {"nombre": s["nombre"], "tid": s["tid"], "pj": 0, "goles": 0, "asist": 0}
            nuevo.update({k: s[k] for k in ("num", "pos") if s.get(k)})
            nuestros.append(nuevo)
    return planteles


def completar(j, s):
    """El jugador ya estaba: gana el número de Transfermarkt, la posición y (si solo había apellido) el nombre completo."""
    j["tid"] = s["tid"]
    nuestro = palabras(j.get("nombre") or "")
    if all(len(x) == 1 for x in nuestro[:-1]) and len(palabras(s["nombre"])) > 1:
        j["nombre"] = s["nombre"]   # solo el apellido ("Loayza", "D.Onega") → nombre completo
    for k in ("num", "pos"):
        if s.get(k) and not j.get(k):
            j[k] = s[k]


def cargar_tm(clave="libertadores"):
    ruta = COPAS[clave]["planteles_tm"]
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def mezclar_ediciones(clave="libertadores"):
    """Aplica la mezcla directamente sobre las ediciones ya generadas (sin tener que regenerar todo)."""
    tm = cargar_tm(clave)
    for ruta in sorted((COPAS[clave]["data"] / "ediciones").glob("*.js")):
        texto = ruta.read_text(encoding="utf-8")
        cabeza, cuerpo = texto[:texto.index("] = ") + 4], texto[texto.index("] = ") + 4:].rstrip().rstrip(";")
        ed = json.loads(cuerpo)
        if str(ed["anio"]) not in tm:
            continue
        # se parte de los planteles sin lo agregado antes, para que correrlo dos veces dé lo mismo
        base = {c: [j for j in js if j.get("id") or j.get("pj") or j.get("goles") or j.get("asist") or not j.get("tid")]
                for c, js in (ed.get("planteles") or {}).items()}
        ed["planteles"] = mezclar(base, tm[str(ed["anio"])], ed)
        nuevo = cabeza + json.dumps(ed, ensure_ascii=False, separators=(",", ":")) + ";\n"
        if nuevo == texto:
            continue
        for intento in range(5):   # en Windows a veces el archivo queda tomado un instante (antivirus)
            try:
                ruta.write_text(nuevo, encoding="utf-8")
                break
            except OSError:
                time.sleep(1 + intento)
    print(f"planteles mezclados en las ediciones ({clave})")


if __name__ == "__main__":
    copa, _ = copa_de_argumentos()
    if "--solo-mezclar" not in sys.argv:
        descargar(copa)
    mezclar_ediciones(copa)
