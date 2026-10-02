"""Unifica los nombres de clubes de RSSSF y ESPN en un único id por club.

No se usa solo: lo llama tools/generar_datos.py.

Cómo decide:
  1. País del club en ese partido (llave con país, ciudad de la tabla, países del grupo).
  2. Nombre "normalizado" (sin tildes, sin 'FC', 'Univ.' = 'Universidad', etc.) + país = club.
  3. tools/equipos_ajustes.json permite corregir a mano: unir alias, forzar país,
     elegir el nombre que se muestra, etc.
"""
import collections
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AJUSTES = RAIZ / "tools" / "equipos_ajustes.json"

# Abreviaturas que usa RSSSF (solo como palabra entera: 'atl.' sí, 'atlético' no)
ABREVIATURAS = {"univ": "universidad", "uni": "universidad", "atl": "atletico", "dep": "deportivo",
                "sp": "sportivo", "ind": "independiente", "indep": "independiente", "gral": "general",
                "stgo": "santiago", "cd": "ciudad", "jrs": "juniors", "jr": "juniors", "sta": "santa",
                "sto": "santo", "col": "colegio"}
RELLENO = r"\b(fc|sc|ca|club|ac|ec|cf|cr|se|fbpa|de futbol|futbol club|esporte clube|sport club)\b"


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def normalizar(nombre):
    t = sin_tildes(nombre).lower()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\b([a-z])\.([a-z])\.", r"\1\2", t)  # 'f.c.' -> 'fc'
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = " ".join(ABREVIATURAS.get(w, w) for w in t.split())
    t = re.sub(RELLENO, " ", t)
    return re.sub(r"\s+", " ", t).strip()


def limpiar_nombre(nombre):
    """'Tigres UANL (Monterrey)' -> 'Tigres UANL'; 'Caracas FC' -> 'Caracas'."""
    n = re.sub(r"\s*\(.*?\)", "", nombre).strip()
    n = re.sub(r"\s+(FC|F\.C\.|SC|S\.C\.|EC|CF)$", "", n).strip()
    return n or nombre


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes(t).lower()).strip("-")


def cargar_ajustes():
    if AJUSTES.exists():
        return json.loads(AJUSTES.read_text(encoding="utf-8"))
    return {}


class Resolutor:
    """Decide el país de cada club crudo de RSSSF, partido por partido."""

    def __init__(self, ediciones):
        self.ediciones = ediciones
        self.ajustes = cargar_ajustes()
        self.pais_nombre = collections.defaultdict(collections.Counter)
        for r in ediciones.values():
            for p in r["partidos"]:
                for eq, pa in (p.get("paises") or {}).items():
                    self.pais_nombre[normalizar(eq)][pa] += 1
        for clave, pa in self.ajustes.get("pais_por_nombre", {}).items():
            self.pais_nombre[normalizar(clave)][pa] += 100
        # ciudad -> país (el más frecuente)
        cp = collections.defaultdict(collections.Counter)
        for r in ediciones.values():
            for eq, ciudad in r["ciudades"].items():
                cand = self.pais_nombre.get(normalizar(eq))
                if cand and len(cand) == 1:
                    cp[ciudad][next(iter(cand))] += 1
        self.pais_ciudad = {c: v.most_common(1)[0][0] for c, v in cp.items()}
        self.pais_ciudad.update(self.ajustes.get("pais_por_ciudad", {}))

    def pais(self, anio, partido, eq):
        """anio: la edición, (copa, año). En pais_por_edicion la Libertadores va como '1980|Club' y la
        Sudamericana como 'sudamericana 2005|Club'."""
        copa, n = anio if isinstance(anio, tuple) else ("libertadores", anio)
        clave = f"{n}|{eq}" if copa == "libertadores" else f"{copa} {n}|{eq}"
        forzado = self.ajustes.get("pais_por_edicion", {}).get(clave)
        if forzado:  # corrección manual de una errata de la fuente
            return forzado
        if partido.get("paises") and eq in partido["paises"]:
            return partido["paises"][eq]
        grupo = set(partido.get("paises_grupo") or [])
        cand = collections.Counter(self.pais_nombre.get(normalizar(eq), {}))
        ciudad = self.ediciones[anio]["ciudades"].get(eq)
        m = re.search(r"\(([^)]+)\)", eq)  # 'Nacional (Asunción)': la ciudad viene en el nombre
        if m:
            ciudad = m.group(1)
        if ciudad and ciudad in self.pais_ciudad:
            cand[self.pais_ciudad[ciudad]] += 1000  # la ciudad de la tabla manda
        if grupo:
            dentro = [(pa, n) for pa, n in cand.most_common() if pa in grupo]
            if dentro:
                return dentro[0][0]
            if len(grupo) == 1:
                return next(iter(grupo))
            return self._pais_por_descarte(anio, partido, eq, grupo)
        return cand.most_common(1)[0][0] if cand else None

    def _pais_por_descarte(self, anio, partido, eq, grupo):
        """En un grupo de 2 países con 2 clubes cada uno: si ya se sabe el país de los otros, sale por descarte."""
        fase = partido["fase"]
        rivales = set()
        for p in self.ediciones[anio]["partidos"]:
            if p["fase"] == fase:
                rivales.update([p["local"], p["visitante"]])
        rivales.discard(eq)
        conteo = collections.Counter()
        for r in rivales:
            cand = self.pais_nombre.get(normalizar(r))
            ciudad = self.ediciones[anio]["ciudades"].get(r)
            pa = self.pais_ciudad.get(ciudad) if ciudad else None
            pa = pa or (next(iter(cand)) if cand and len(cand) == 1 else None)
            if pa in grupo:
                conteo[pa] += 1
        libres = sorted(grupo, key=lambda pa: conteo[pa])
        return libres[0] if libres and conteo[libres[0]] < conteo[libres[-1]] else None


class Catalogo:
    """Arma el catálogo final de clubes: id -> {nombre, pais, ciudad, alias, espn}."""

    def __init__(self):
        self.ajustes = cargar_ajustes()
        self.clubes = {}
        self.indice = {}  # (nombre normalizado, pais) -> id
        self.nombres = collections.defaultdict(collections.Counter)
        # alias manuales: "Medellín|COL" -> "independiente-medellin"
        self.alias = {}
        for crudo, id_ in self.ajustes.get("alias", {}).items():
            nombre, _, pais = crudo.partition("|")
            self.alias[(normalizar(nombre), pais or None)] = id_

    def id_de(self, nombre, pais, ciudad=None, espn=None):
        clave = (normalizar(nombre), pais)
        id_ = self.alias.get(clave) or self.alias.get((clave[0], None)) or self.indice.get(clave)
        if not id_:
            base = slug(normalizar(nombre))
            id_ = base
            # mismo nombre en otro país (Nacional URU / Nacional PAR): agregar el país al id
            if id_ in self.clubes and self.clubes[id_]["pais"] != pais:
                id_ = f"{base}-{(pais or 'xx').lower()}"
            self.indice[clave] = id_
        # "unir": dos ids que son el mismo club (Slavia Prague de Checoslovaquia y de Chequia, Espanyol y Español…)
        id_ = self.ajustes.get("unir", {}).get(id_, id_)
        club = self.clubes.setdefault(id_, {"pais": pais, "ciudad": None, "espn": set()})
        if pais and not club["pais"]:
            club["pais"] = pais
        if ciudad and not club["ciudad"]:
            club["ciudad"] = ciudad
        if espn:
            club["espn"].add(str(espn))
        self.nombres[id_][nombre] += 1
        return id_

    def asegurar(self, id_, nombre, pais=None):
        """El club con ese id (lo crea si todavía no existe: un club que se conoce por un ajuste a mano)."""
        id_ = self.ajustes.get("unir", {}).get(id_, id_)
        if id_ not in self.clubes:
            self.clubes[id_] = {"pais": pais, "ciudad": None, "espn": set()}
            self.nombres[id_][nombre] += 1
        return self.clubes[id_]

    def exportar(self):
        fijos = self.ajustes.get("nombres", {})
        res = {}
        for id_, c in sorted(self.clubes.items()):
            # nombre a mostrar: el ajuste manual, o el más largo entre los más usados
            usados = self.nombres[id_].most_common()
            nombre = fijos.get(id_) or limpiar_nombre(max((n for n, k in usados if k >= usados[0][1] / 3), key=len))
            res[id_] = {"nombre": nombre, "pais": self.ajustes.get("pais_club", {}).get(id_) or c["pais"], "ciudad": c["ciudad"],
                        "escudo": f"assets/escudos/{id_}.png"}
            if c["espn"]:
                res[id_]["espn"] = sorted(c["espn"])
        return res
