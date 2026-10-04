# Conversor usado en la fase 25 para cargar a mano los torneos 1995-2002 (tools/a_mano/liga-*.json).
# Lee el texto de una página de RSSSF (tablesa/argNN.html pasada a texto) y el wikitext de Wikipedia de cada torneo,
# los cruza y avisa las diferencias. Los archivos de entrada se bajan aparte, en la misma carpeta que este script.
# Al final de cada año se corrigieron a mano notas, nombres y errores de las fuentes (ver fases/fase_25.md).

"""Cruza RSSSF (resultados y goleadores) con Wikipedia (estadio, día, hora, notas) y arma tools/a_mano/liga-<clave>.json"""
import json, re, sys, unicodedata
from pathlib import Path

AQUI = Path(__file__).parent
SALIDA = Path(r"C:\Users\munca\Desktop\FULBO\tools\a_mano")
MESES_EN = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
MESES_ES = {m: i + 1 for i, m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}


def norm(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


CLUBES = [  # (patrón normalizado al principio del nombre, id)
    ("argentinos", "argentinos-juniors"), ("racing", "racing-club"), ("river", "river-plate"), ("boca", "boca-juniors"),
    ("sanlorenzo", "san-lorenzo"), ("velez", "velez-sarsfield"), ("independiente", "independiente"),
    ("gimnasiaer", "ger"), ("gimnasiayesgj", "gimnasia-jujuy"), ("gimnasias", "gimnasia-y-tiro"), ("gimnasiaytiro", "gimnasia-y-tiro"), ("gimnasiaj", "gimnasia-jujuy"), ("gimnasiayesgrimaj", "gimnasia-jujuy"),
    ("gimnasia", "gimnasia-y-esgrima"), ("ginmasia", "gimnasia-y-esgrima"), ("ferro", "ferro-carril-oeste"), ("estudiantes", "estudiantes-de-la-plata"),
    ("newell", "newell-s-old-boys"), ("rosario", "rosario-central"), ("colon", "colon"), ("union", "union"),
    ("lanus", "lanus"), ("banfield", "banfield"), ("chacarita", "chacarita-juniors"), ("nuevachicago", "nueva-chicago"),
    ("talleres", "talleres"), ("huracanta", "huracan-tres-arroyos"), ("huracanc", "huracan-corrientes"), ("talleres", "talleres"), ("huracan", "huracan"), ("belgrano", "belgrano"),
    ("olimpo", "olimpo"), ("arsenal", "arsenal-de-sarandi"),
    ("almagro", "almagro"), ("argj", "argentinos-juniors"), ("depespanol", "deportivo-espanol"),
    ("deportivoespanol", "deportivo-espanol"), ("platense", "platense"), ("losandes", "los-andes"), ("quilmes", "quilmes"), ("instituto", "instituto"),
    ("depmandiyu", "deportivo-mandiyu"), ("deportivomandiyu", "deportivo-mandiyu"), ("mandiyu", "deportivo-mandiyu")]


def club(nombre):
    n = norm(nombre)
    for p, c in CLUBES:
        if n.startswith(p) and not (p == "gimnasiayesgrimaj" and n.startswith("gimnasiayesgrimalp")):
            return c
    raise ValueError(nombre)


def leer_rsssf(archivo, desde, hasta, anio_de):
    """[(ronda, fecha, local, visitante, gl, gv, goleadores, nota)]"""
    crudas = (AQUI / archivo).read_text(encoding="utf-8").splitlines()[desde - 1:hasta]
    lineas = []   # (los corchetes que siguen en la línea de abajo, juntos)
    for l in crudas:
        abierto = lineas and lineas[-1].count("[") > lineas[-1].count("]")
        if l.startswith(" ") and l.rstrip().endswith("]") and "[" not in l and not abierto:   # (RSSSF a veces no abre el corchete)
            l = l.replace(l.strip(), "[" + l.strip(), 1)
        if lineas and lineas[-1].count("[") > lineas[-1].count("]"):
            if l.startswith(" ") and not l.strip().startswith("["):   # (sigue abajo)
                lineas[-1] += " " + l.strip()
                continue
            lineas[-1] += "]"   # (RSSSF a veces no cierra el corchete)
            lineas.append(l)
        else:
            lineas.append(l)
    partidos, ronda, dia, actual = [], None, None, None
    for l in lineas:
        m = re.match(r"\s*(Round (\d+)|First Leg|Second Leg)", l)
        if m:
            ronda = int(m.group(2)) if m.group(2) else m.group(1)
        corchetes = re.findall(r"\[([^\]]*)\]", l)
        resto = re.sub(r"\[[^\]]*\]", "", l).rstrip()
        m = re.match(r"^(\S.*?)\s+(\d+ ?- ?\d+|abd|awd)\s+(.+?)\s*$", resto)
        if m and ronda is not None:
            r = m.group(2).replace(" ", "")
            actual = {"ronda": ronda, "fecha": dia, "local": club(m.group(1)), "visitante": club(m.group(3)),
                      "gl": int(r.split("-")[0]) if "-" in r else None, "gv": int(r.split("-")[1]) if "-" in r else None,
                      "goleadores": None, "nota": None, "abd": r == "abd"}
            if r != "abd":   # (los suspendidos que se completaron después aparecen de nuevo con el resultado final)
                partidos.append(actual)
        for t in corchetes:
            t = t.strip()
            mf = re.fullmatch(r"(\w{3}) (\d+)(?:, ?\w+)?", t)
            if mf and mf.group(1) in MESES_EN:
                mes = MESES_EN[mf.group(1)]
                dia = f"{anio_de(mes)}-{mes:02d}-{int(mf.group(2)):02d}"
            elif actual is not None and re.match(r"(played )?at ", t):   # (la cancha, si no es la del local)
                actual["sede"] = re.sub(r"^(played )?at ", "", t).strip()
            elif actual is None or t.startswith(("Agg", "In extra", "Note")):
                continue
            elif t.startswith(("Abandoned", "abandoned", "abd ", "Remaining", "remaining", "Score", "Suspended", "The match")):
                actual["nota"] = (actual["nota"] + " " if actual["nota"] else "") + t
                ma = re.search(r"Awarded (\d+)-(\d+)", t)
                if ma:
                    actual["gl"], actual["gv"] = int(ma.group(1)), int(ma.group(2))
                    actual["real"] = tuple(map(int, re.search(r"Abandoned (\d+)-(\d+)", t).groups()))
            else:
                actual["goleadores"] = t
    return partidos


def goles_minuto_nombre(txt, lado):
    """1995-96: "3' Maradona (p), 24', 27' (p) and 72 (p) Francescoli" -> goles con minuto"""
    lista, minutos = [], []
    for parte in [x.strip() for x in txt.split(",") if x.strip()]:
        while True:
            m = re.match(r"(\d+)'?(?:\+\d+)?\s*(\((?:p|o\.?g\.?)\))?\s*(?:(?:and|y)\s+)?", parte)
            if not m or not m.group(0):
                break
            minutos.append((int(m.group(1)), m.group(2)))
            parte = parte[m.end():]
        nombre = parte.strip()
        if not nombre:   # (solo minutos: el nombre viene después)
            continue
        mt = re.search(r"\s*\((p|o\.?g\.?)\)$", nombre)
        if mt:
            nombre = nombre[:mt.start()].strip()
            minutos = [(mi, x or f"({mt.group(1)})") for mi, x in minutos]
        for mi, x in minutos:
            g = {"jugador": nombre, "min": mi, "equipo": lado}
            if x and "p" in x and "o" not in x:
                g["tipo"] = "pen"
            elif x and "o" in x:
                g["tipo"] = "ec"
            lista.append(g)
        minutos = []
    if minutos:
        raise ValueError("minutos sin nombre: " + txt)
    return lista


def goles_nombre_minuto(txt, lado):
    """1996-97: "Mena 13pen, Morales 81, Di Carlos 33, 44, 45" -> goles con minuto"""
    lista, nombre = [], None
    for parte in [x.strip() for x in txt.split(",") if x.strip()]:
        m = re.fullmatch(r"(.*?)\s*(\d+)\s*(pen|og)?", parte)
        if not m:
            raise ValueError("no se entiende: " + txt)
        if m.group(1):
            nombre = m.group(1).strip()
        g = {"jugador": nombre, "min": int(m.group(2)), "equipo": lado}
        if m.group(3) == "pen":
            g["tipo"] = "pen"
        elif m.group(3) == "og":
            g["tipo"] = "ec"
        lista.append(g)
    return lista


def goles(p):
    """Los goles de RSSSF: [{jugador, tipo, equipo}]"""
    t = (p["goleadores"] or "").replace("o,g", "o.g")
    if not t:
        return []
    gl, gv = p.get("real", (p["gl"], p["gv"]))
    if re.match(r"\d+('|\s)", t):   # (1995-96: el minuto antes del nombre)
        lados = t.split(" - ") if gl and gv else ([t, ""] if gl else ["", t])
        if len(lados) != 2:
            raise ValueError("sin separar: " + t)
        return [g for lado, txt in zip(("local", "visitante"), lados) for g in goles_minuto_nombre(txt, lado)]
    if re.search(r"[^\s(,\d]\s+\d+(pen|og)?(,|;|$)", t):   # (1996-97: el nombre y después los minutos)
        lados = t.split(";") if gl and gv else ([t, ""] if gl else ["", t])
        if len(lados) != 2:
            raise ValueError("sin separar: " + t)
        return [g for lado, txt in zip(("local", "visitante"), lados) for g in goles_nombre_minuto(txt, lado)]
    if gl and gv and ";" in t:   # (1996-97: los dos equipos separados por ";")
        lados = t.split(";")
    elif gl and gv:
        lados = re.split(r"\s+-\s*|\s*-\s+", t.replace("-,", "-"))
        if len(lados) != 2:
            raise ValueError("sin separar: " + t)
    elif gl:
        lados = [t, ""]
    else:
        lados = ["", t.lstrip("- ")]
    lista = []
    for lado, txt in zip(("local", "visitante"), lados):
        for parte in re.findall(r"[^,(]+(?:\([^)]*\))?", txt):
            parte = parte.strip()
            if not parte:
                continue
            m = re.match(r"(.+?)\s*(?:\((.*)\))?$", parte)
            nombre, extra = m.group(1).strip(), (m.group(2) or "").strip()
            cuantos, pen, ec = 1, 0, False
            for x in [e.strip() for e in extra.split(",") if e.strip()]:
                if x.isdigit():
                    cuantos = int(x)
                elif re.fullmatch(r"(\d+ )?pen\.?", x):
                    pen = int(x.split()[0]) if " " in x else 1
                elif re.fullmatch(r"o[.,]?g\.?", x):
                    ec = True
                else:
                    raise ValueError(f"{parte} en {t}")
            for i in range(cuantos):
                g = {"jugador": nombre, "equipo": lado}
                if ec:
                    g["tipo"] = "ec"
                elif i < pen:
                    g["tipo"] = "pen"
                lista.append(g)
    return lista


def limpiar(c):
    c = re.sub(r"<ref[^>]*/>", "", c)
    c = re.sub(r"<ref[^>]*>.*?</ref>", "", c)
    if "|" in c and not c.startswith("[["):   # atributos: 'bgcolor=...|texto'
        partes = re.split(r"\|(?![^\[]*\]\])", c)
        c = partes[-1]
    c = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", c)
    return c.replace("'''", "").replace("''", "").strip()


def sacar_refn(c):
    """La nota {{refn|group=n.|texto}} (con plantillas adentro) y la celda sin ella"""
    i = c.find("{{refn")
    if i < 0:
        return c, None
    nivel, j = 0, i
    while j < len(c):
        if c.startswith("{{", j):
            nivel += 1; j += 2; continue
        if c.startswith("}}", j):
            nivel -= 1; j += 2
            if not nivel:
                break
            continue
        j += 1
    nota = c[i + 2:j - 2]
    nota = re.sub(r"<ref[^>]*>.*?</ref>", "", nota, flags=re.S)
    nota = re.sub(r"^refn\|group=[^|]*\|", "", nota)
    nota = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", nota).strip()
    return c[:i] + c[j:], nota


def leer_wiki(archivo, anio_de):
    """{ronda: [(local, visitante, gl, gv, estadio, fecha, hora, nota)]}"""
    t = (AQUI / archivo).read_text(encoding="utf-8")
    rondas = {}
    # (6 o 7 columnas: con estadio, día y hora; 3: solo el resultado, 1996)
    for m in re.finditer(r"!colspan=\"?([367])\"?[^|\n]*\|Fecha (\d+)[^\n]*\n(.*?)(?=\n!colspan|\n\|\})", t, re.S):
        n, columnas = int(m.group(2)), int(m.group(1))
        filas = m.group(3).split("\n|-")[1:]
        filas = [f for f in filas if not f.strip().startswith("!")]
        span = {}   # columna: [valor, filas que quedan]
        for f in filas:
            celdas = [x[1:] for x in f.strip().split("\n") if x.startswith("|")]
            fila, k = [], 0
            for col in range(columnas):
                if col in span and span[col][1] > 0:
                    fila.append(span[col][0]); span[col][1] -= 1
                    continue
                if k >= len(celdas):
                    fila.append(None); continue
                c = celdas[k]; k += 1
                c, nota = sacar_refn(c)
                rs = re.search(r'rowspan="?(\d+)"?', c)
                v = limpiar(c)
                if rs:
                    span[col] = [v, int(rs.group(1)) - 1]
                fila.append((v, nota) if nota else v)
            fila += [None] * (6 - len(fila))
            notas = [x[1] for x in fila if isinstance(x, tuple)]
            fila = [x[0] if isinstance(x, tuple) else x for x in fila]
            mr = re.match(r"(\d+)\s*-\s*(\d+)", fila[1] or "")
            if not mr:   # (una fila sin resultado: se usa la de RSSSF)
                continue
            gl, gv = map(int, mr.groups())
            md = re.match(r"(\d+) de (\w+)(?: de (\d{4}))?", fila[4] or "")
            if md:
                mes = MESES_ES[md.group(2)]
                fecha = f"{md.group(3) or anio_de(mes)}-{mes:02d}-{int(md.group(1)):02d}"
            else:
                fecha = None
            hora = fila[5] if fila[5] and re.fullmatch(r"\d\d:\d\d", fila[5]) else None
            rondas.setdefault(n, []).append((club(fila[0]), club(fila[2]), gl, gv, fila[3] or None, fecha, hora,
                                             notas[0] if notas else None))
    return rondas


def armar(clave, rsssf, wiki, anio_de, nombre, fuente):
    rs = leer_rsssf(*rsssf, anio_de)
    wk = leer_wiki(wiki, anio_de)
    fechas, problemas = {}, []
    for p in rs:
        w = [x for x in wk.get(p["ronda"], []) if {x[0], x[1]} == {p["local"], p["visitante"]}]
        if len(w) != 1:
            problemas.append(f"fecha {p['ronda']}: {p['local']}-{p['visitante']} no está en Wikipedia")
            w = [(p["local"], p["visitante"], p["gl"], p["gv"], f"Cancha de {p['sede']}" if p.get("sede") else None,
                  p["fecha"], None, None)]
        w = w[0]
        if (w[0], w[2], w[3]) != (p["local"], p["gl"], p["gv"]):
            problemas.append(f"fecha {p['ronda']}: RSSSF {p['local']} {p['gl']}-{p['gv']} {p['visitante']}; "
                             f"Wikipedia {w[0]} {w[2]}-{w[3]} {w[1]}")
        if w[5] is None:   # (Wikipedia sin el día: el de RSSSF)
            w = w[:5] + (p["fecha"],) + w[6:]
        if w[5] != p["fecha"]:
            problemas.append(f"fecha {p['ronda']}: {p['local']}-{p['visitante']} día RSSSF {p['fecha']}, Wikipedia {w[5]}")
            if w[5] is None:
                w = w[:5] + (p["fecha"],) + w[6:]
        try:
            g = goles(p)
        except ValueError as x:
            g = []
            problemas.append(f"fecha {p['ronda']}: {p['local']}-{p['visitante']}: {x}")
        real = p.get("real", (p["gl"], p["gv"]))
        if len(g) != sum(real) or sum(x["equipo"] == "local" for x in g) != real[0]:
            problemas.append(f"fecha {p['ronda']}: {p['local']} {p['gl']}-{p['gv']} {p['visitante']}: goles {p['goleadores']}")
        q = {"fecha": w[5], "hora": w[6], "local": p["local"], "visitante": p["visitante"], "gl": p["gl"], "gv": p["gv"],
             "estadio": w[4] or (f"Cancha de {p['sede']}" if p.get("sede") else None), "goles": g}
        if w[7] or p["nota"]:
            q["nota_wikipedia"], q["nota_rsssf"] = w[7], p["nota"]
        fechas.setdefault(p["ronda"], []).append({k: v for k, v in q.items() if v is not None})
    # partidos de Wikipedia que RSSSF no tiene
    for n, ws in wk.items():
        for w in ws:
            if not any({w[0], w[1]} == {p["local"], p["visitante"]} for p in rs if p["ronda"] == n):
                problemas.append(f"fecha {n}: {w[0]}-{w[1]} está en Wikipedia y no en RSSSF")
    print(clave, sum(map(len, fechas.values())), "partidos")
    print("\n".join(problemas))
    return {"nombre": nombre, "fuente": fuente,
            "fechas": [{"numero": n, "partidos": fechas[n]} for n in sorted(fechas)]}


if __name__ == "__main__":
    d = armar("1995-clausura", ("arg95.txt", 467, 790), "w_Torneo_Clausura_1995_(Argentina).txt", lambda m: 1995,
              "Torneo Clausura 1995", "")
    (AQUI / "c1995.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    d = armar("1995-apertura", ("arg96.txt", 10, 491), "w_Torneo_Apertura_1995_(Argentina).txt", lambda m: 1995,
              "Torneo Apertura 1995", "")
    (AQUI / "a1995.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
