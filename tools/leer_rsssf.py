"""Convierte las páginas de RSSSF (tools/cache/rsssf) en datos estructurados.

No se usa solo: lo llama tools/generar_datos.py. Para revisar una edición suelta:
    python tools/leer_rsssf.py 1975
    python tools/leer_rsssf.py --copa sudamericana 2010
Muestra los partidos leídos y las líneas que no entendió.
"""
import html
import json
import re
import sys

from copas import COPAS, copa_de_argumentos

MESES = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

FASES = [  # (patrón en inglés, nombre en castellano, tipo)
    (r"preliminary|qualifying|play-?offs? [a-f]$|first stage|second stage|third stage", "Fase previa", "eliminatoria"),
    (r"^group phase|^group stage", "Fase de grupos", "grupos"),
    (r"^first round", "Primera fase", None),
    (r"^second round", "Segunda fase", None),
    (r"^third round", "Tercera fase", None),
    (r"round of 16|eighth-?finals|^octavos", "Octavos de final", "eliminatoria"),
    (r"quarter-?finals", "Cuartos de final", "eliminatoria"),
    (r"semi-?finals", "Semifinales", None),
    (r"^finals?\b", "Final", "eliminatoria"),
    (r"third place", "Tercer puesto", "eliminatoria"),
]
# La Sudamericana nombra sus rondas distinto: "First Phase" (con "First/Second Stage" adentro, 2003-2016),
# "Second Phase", "Playoff Round" (desde 2023, contra los terceros de la Libertadores), "1/8 Finals"…
FASES_SUD = [
    (r"^preliminary round", "Fase previa", "eliminatoria"),
    (r"^preliminary phase|^first (phase|round)|^(first|second) stage", "Primera fase", "eliminatoria"),
    (r"^second (phase|round)", "Segunda fase", "eliminatoria"),
    (r"^group phase|^group stage", "Fase de grupos", "grupos"),
    (r"^playoff round|^knockout", "Playoffs de octavos", "eliminatoria"),
    (r"^round of 16|^1/8 finals|^eighth-?finals", "Octavos de final", "eliminatoria"),
    (r"^quarter-?finals", "Cuartos de final", "eliminatoria"),
    (r"^semi-?finals", "Semifinales", "eliminatoria"),
    (r"^finals?\b", "Final", "eliminatoria"),
]

RE_ESC = r"(\d+)-(\d+)"
RE_FECHA = r"(?:([A-Z][a-z]{2})\s+(\d{1,2})|(\d{1,2})\s+([A-Z][a-z]{2}))"
RE_PARTIDO = re.compile(
    r"^\s*(?:" + RE_FECHA + r"\s*:)?\s*(?P<a>\S.*?)(?:\s+-\s+|\s{2,}|\s+–\s+)(?P<b>\S.*?)\s+"
    r"(?P<ga>\d+)-(?P<gb>\d+)(?P<resto>.*)$")
_COD = r"(?:Arg|Bra|Uru|Par|Chi|Col|Per|Ecu|Bol|Ven|Mex|USA|CRi|Hon)"
# El nombre puede ir pegado al código de país cuando es largo: 'Independiente (Avellaneda)Arg'
RE_LLAVE = re.compile(r"^(?P<a>\S.*?)(?:\s+|(?<=\)))(?P<pa>" + _COD + r")\s+(?P<b>\S.*?)(?:\s+|(?<=\)))(?P<pb>" + _COD +
                      r")\s+(?P<resto>(?:\d|\[|awd|bye|n/p).*)$")
RE_TABLA = re.compile(r"^\s*(?:\d+\.)?\s*(?P<nombre>\S.*?)\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+-\s*\d+\s+-?\d+[a-z*]*(\s|$)")
RE_DETALLE = re.compile(r"^(1st|2nd|2st|3rd) leg[.,]|^(play-?off|replay|final|match)[.,]|^(first|second|third) leg\s*(\[|$)",
                        re.I)
RE_MINUTO = re.compile(r"^\s*(?:(\d+|\?)(?:\+\d+)?'\s+)?([^\d:,]+?)\s+(\d+)-(\d+)\b.*$")
PAISES_NOMBRE = {"Argentina": "ARG", "Brazil": "BRA", "Uruguay": "URU", "Paraguay": "PAR", "Chile": "CHI",
                 "Colombia": "COL", "Peru": "PER", "Ecuador": "ECU", "Bolivia": "BOL", "Venezuela": "VEN",
                 "Mexico": "MEX"}
RE_PAIS = {"Arg": "ARG", "Bra": "BRA", "Uru": "URU", "Par": "PAR", "Chi": "CHI", "Col": "COL",
           "Per": "PER", "Ecu": "ECU", "Bol": "BOL", "Ven": "VEN", "Mex": "MEX",
           "USA": "USA", "CRi": "CRC", "Hon": "HON"}   # los tres últimos, invitados a la Sudamericana


def leer_html(anio, copa="libertadores"):
    crudo = (COPAS[copa]["cache_rsssf"] / COPAS[copa]["rsssf"](anio)).read_bytes()
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError:
        texto = crudo.decode("cp1252", errors="replace")  # Windows: incluye el guion largo –
    texto = texto.split('name="about"')[0]
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = html.unescape(texto).replace("\xa0", " ").expandtabs(8)
    lineas = [l.rstrip() for l in texto.splitlines()]
    if copa == "sudamericana":
        lineas = [arreglar_sudamericana(l) for l in lineas]
    # Unir listas de goleadores o formaciones que siguen en la línea de abajo
    # (solo si el renglón siguiente es continuación: sangrado y sin pinta de partido;
    #  RSSSF a veces se olvida de cerrar el corchete)
    unidas = []
    for l in lineas:
        abierta = unidas and unidas[-1].count("[") > unidas[-1].count("]")
        continua = l.startswith((" ", "\t")) and l.strip() and not l.strip().startswith("[") \
            and not RE_PARTIDO.match(l) and not re.match(r"^\s*\d+\.", l)
        if abierta and continua:
            unidas[-1] += " " + l.strip()
        else:
            if abierta:
                unidas[-1] += "]"
            unidas.append(l)
    return unidas


# Sigla de la sociedad delante del nombre del club ("CS Emelec", "CSD Colo-Colo", "CA Paranaense"): la usan las
# páginas recientes de la Sudamericana y duplicaría clubes. "FBC" al final ("Melgar FBC"), lo mismo.
RE_SIGLA_CLUB = re.compile(r"\b(?:CD|CSD|CS|CA|SC|CDP|CI|CDSC|CCD|EMD|CDU|CR|SE|EC)\s+(?=[A-ZÁÉÍÓÚÑ])")


def arreglar_sudamericana(linea):
    """Erratas y siglas de las páginas de la Sudamericana (no se toca lo que está entre corchetes: goleadores)."""
    if linea.strip().startswith("["):
        return linea
    linea = re.sub(r"^(\s*)Ap(\s+\d{1,2}:)", r"\1Apr\2", linea)                  # 'Ap   3: Rayo Zuliano - …'
    linea = re.sub(r"^(\s*[A-Z][a-z]{2}\s+\d{1,2});", r"\1:", linea)            # 'May  4; Fortaleza EC - …'
    linea = re.sub(r"(\d)–(\d)", r"\1-\2", linea)                                # '1–1' con guion largo
    linea = RE_SIGLA_CLUB.sub("", linea)
    return re.sub(r"\s+FBC\b", "", linea)


def fechas_de(texto, anio):
    """'Apr 20 & May 3' -> ['1960-04-20', '1960-05-03']. También '24 Apr'."""
    res, mes = [], None
    for tok in re.findall(r"[A-Za-z]{3,}|\d+", texto):
        if tok[:3].lower() in MESES:
            mes = MESES[tok[:3].lower()]
            # formato '24 Apr': el número anterior era el día de este mes
            if res and res[-1][1] is None:
                res[-1] = (res[-1][0], mes)
        elif tok.isdigit() and int(tok) <= 31:
            res.append((int(tok), mes))
    return [f"{anio}-{m:02d}-{d:02d}" for d, m in res if m]


def fecha_partido(m, anio):
    if m.group(1):
        mes, dia = m.group(1), m.group(2)
    elif m.group(4):
        mes, dia = m.group(4), m.group(3)
    else:
        return None
    if mes.lower() not in MESES:
        return None
    return f"{anio}-{MESES[mes.lower()]:02d}-{int(dia):02d}"


def leer_goles(texto):
    """'[Spencer(4), Borges(2); Alcácer]' -> ([goles del local], [goles del visitante])."""
    texto = texto.strip().strip("[]")
    lados = texto.split(";")
    res = []
    for lado in lados[:2]:
        goles, anterior = [], None
        for tok in [t.strip() for t in lado.split(",") if t.strip()]:
            tipo = None
            if re.search(r"\bo/?g\b|\d+og$|\(og\)", tok):
                tipo = "ec"
            elif re.search(r"\d+pen$|\(pen\)|\bpen\b", tok):
                tipo = "pen"
            tok2 = re.sub(r"\s*\(?\bo/?g\)?$|(?<=\d)og$|(?<=\d)pen$|\s*\(pen\)|\s+pen$", "", tok).strip()
            cant = 1
            m = re.search(r"\((\d+)\)\s*$", tok2)
            if m:
                cant = int(m.group(1))
                tok2 = tok2[:m.start()].strip()
            minuto = None
            m = re.search(r"(?:^|\s)(\d+)(?:\+(\d+))?\s*$", tok2)
            if m:
                minuto = int(m.group(1))
                tok2 = tok2[:m.start()].strip()
            nombre = tok2 or anterior
            if not nombre:
                continue
            anterior = nombre
            for _ in range(cant):
                goles.append({"jugador": nombre, "min": minuto, "tipo": tipo})
        res.append(goles)
    while len(res) < 2:
        res.append([])
    return res


def goles_por_lado(texto, gl, gv, mesa=False):
    """Goles de '[...]' con su lado ('local' o 'visitante'). RSSSF no siempre separa los dos equipos con un ';':
      - si el local no hizo goles escribe solo los del visitante: '[Klinger(2), Pizarro(2)]' en un 0-4;
      - en los empates a veces falta el ';': '[Pizzi, Morigi]' en un 1-1;
      - el gol en contra a veces va primero y con un ';' de más: '[Miño o/g; Usuriaga]' en un 2-0;
      - en los desempates en cancha neutral a veces va primero el que figura de visitante.
    Si la lista no cuadra con el resultado, se reparte de la forma que sí cuadre. Salvo en los partidos con 'x'
    (mesa: en general, ganados en los escritorios) que ya separan los dos equipos con ';': ahí los goles son los de
    la cancha y el resultado, el del reglamento."""
    local, visita = leer_goles(texto)
    gl, gv = gl or 0, gv or 0
    if (len(local), len(visita)) != (gl, gv) and not (mesa and ";" in texto):
        partes = texto.strip().strip("[]").split(";")
        todos = [g for parte in partes for g in leer_goles(parte)[0]]
        if (len(visita), len(local)) == (gl, gv):
            local, visita = visita, local
        elif len(todos) == gl + gv:
            local, visita = todos[:gl], todos[gl:]   # RSSSF nombra siempre primero los goles del local
        elif len(partes) == 1 and gl < len(local) <= gv:
            local, visita = [], local                 # lista incompleta de un equipo que no le entra al local
    return [{**g, "lado": "local"} for g in local] + [{**g, "lado": "visitante"} for g in visita]


def fase_de(titulo, copa="libertadores"):
    t = titulo.lower().strip()
    for patron, nombre, tipo in (FASES_SUD if copa == "sudamericana" else FASES):
        if re.search(patron, t):
            return nombre, tipo
    return None, None


def separar_sin_espacios(linea, conocidos):
    """'Feb 19: Guaraní-Cerro Porteño   1-0' (1997): elegir el guion que separa dos clubes
    conocidos, para no partir nombres como 'Colo-Colo'."""
    m = re.match(r"^(\s*(?:" + RE_FECHA + r"\s*:)?\s*)(\S.*?)(\s+\d+-\d+.*)$", linea)
    if not m or " - " in linea:
        return linea
    equipos = m.group(6)
    guiones = [i for i, c in enumerate(equipos) if c == "-"]
    for i in guiones:
        a, b = equipos[:i].strip(), equipos[i + 1:].strip()
        if a in conocidos or b in conocidos:
            return m.group(1) + a + " - " + b + m.group(7)
    return linea


def leer(anio, copa="libertadores"):
    lineas = leer_html(anio, copa)
    conocidos = set()
    for l in lineas:  # nombres de las tablas de posiciones
        mt = RE_TABLA.match(l)
        if mt:
            conocidos.add(re.sub(r"\s*\(.*$", "", mt.group("nombre")).strip())
    lineas = [separar_sin_espacios(l, conocidos) if re.match(r"^\s*" + RE_FECHA + r"\s*:\s*(?:\d+ )?[^\d]*\S-\S", l) else l
              for l in lineas]
    partidos, raros, goleadores = [], [], []
    ciudades = {}  # nombre crudo -> ciudad (de las tablas de grupos)
    fase, subfase, tipo_fase = "Fase de grupos", None, "grupos"
    fechas_llave = []
    pendientes = []        # partidos que esperan su renglón de goleadores
    detalle = None         # bloque '1st leg. Estadio, Ciudad, 12- 6-1960'
    en_goleadores = False
    llave_n = 0
    en_formacion = None
    paises_grupo = []

    def nuevo(**kw):
        p = {"fase": fase if not subfase else f"{fase} — {subfase}", "fecha": None,
             "goles": [], "notas": None, **kw}
        if subfase and subfase.startswith("Grupo") and paises_grupo:
            p["paises_grupo"] = paises_grupo
        partidos.append(p)
        return p

    for linea in lineas:
        s = linea.strip()
        if not s or s.startswith(("Overview Page", "About this document")) or re.match(r"^\d{4}\s*(\||$)", s):
            continue

        # --- Tabla de goleadores del torneo ---
        if re.match(r"^top ?scorers?", s, re.I):
            en_goleadores = True
            continue
        if en_goleadores:
            m = re.match(r"^(.+?)\s{2,}(.+?)\s{2,}(\d+)\b", s) or re.match(r"^(.+?)\s{2,}(\S.*?)\s+(\d+)$", s)
            if m:
                goleadores.append({"jugador": m.group(1).strip(), "equipo": m.group(2).strip(),
                                   "goles": int(m.group(3))})
                continue
            en_goleadores = False

        # --- Bloque de detalle de un partido (sobre todo finales) ---
        #   '1st leg. Centenario, Montevideo, 12- 6-1960'   o bien   'First Leg' + '14 June 2000.  Buenos Aires ARG'
        if RE_DETALLE.match(s):
            if detalle is not None:
                cerrar_detalle(detalle)
            idx = 0 if re.match(r"^(1st|first)", s, re.I) else 1 if re.match(r"^(2nd|2st|second)", s, re.I) else 2
            de_llave = [p for p in partidos if p.get("llave") == llave_n and llave_n]
            partes = re.split(r"[.,]", s, 1)
            partes = [x.strip() for x in partes[1].split(",")] if len(partes) > 1 else []
            m = re.search(r"(\d+)-\s*(\d+)-(\d{4})", s)
            fecha = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
            estadio = ", ".join(x for x in partes[:-1] if x) or None
            mc = re.match(r"^\w+ leg\s*\[(.*)\]?$", s, re.I)
            if mc:  # 'First Leg [Jul 17, Defensores del Chaco, Asunción, att: 32.212, ref: Néstor Pitana (ARG)]'
                trozos = [x.strip() for x in mc.group(1).rstrip("]").split(",")]
                f = fechas_de(trozos[0], anio) if trozos else []
                fecha = f[0] if f else None
                lugar = [x for x in trozos[1:] if not re.match(r"^(att|ref)\b", x, re.I)]
                estadio = ", ".join(lugar) or None
                mr = re.search(r"ref:\s*([^\]]+?)\s*(\(\w+\))?\]?$", s)
                arbitro_det = mr.group(1).strip() if mr else None
            else:
                arbitro_det = None
            detalle = {"estadio": estadio, "fecha": fecha, "arbitro": arbitro_det,
                       "partido": de_llave[idx] if idx < len(de_llave) else None,
                       "orientado": False, "minutos": [], "formaciones": {}, "goles_texto": None}
            if detalle["partido"] is None and detalle["fecha"]:
                cand = [p for p in partidos if p["fecha"] == detalle["fecha"]]
                detalle["partido"] = cand[-1] if cand else None
            en_formacion = None
            continue
        if detalle is not None:
            p = detalle["partido"]
            # renglón con fecha larga: '14 June 2000.  Buenos Aires ARG (att: 50580)'
            m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\.?\s*(.*?)\s*(\(.*)?$", s)
            if m and m.group(2)[:3].lower() in MESES:
                detalle["fecha"] = f"{m.group(3)}-{MESES[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}"
                if m.group(4):
                    detalle["estadio"] = re.sub(r"\s+[A-Z]{3}$", "", m.group(4))
                continue
            # renglón del partido: 'Peñarol - Olimpia 1-0'  o  'Boca Juniors  2-2  Palmeiras'
            m = RE_PARTIDO.match(s) or re.match(r"^(?P<a>\S.*?)\s{2,}(?P<ga>\d+)-(?P<gb>\d+)\s{2,}(?P<b>\S.*)$", s)
            if m and not detalle["orientado"]:
                a, b = m.group("a").strip(), m.group("b").strip()
                ga, gb = int(m.group("ga")), int(m.group("gb"))
                cand = [x for x in partidos if not x.get("_detalle") and (
                        ((x["local"], x["visitante"]) == (a, b) and (x["gl"], x["gv"]) == (ga, gb)) or
                        ((x["local"], x["visitante"]) == (b, a) and (x["gl"], x["gv"]) == (gb, ga)))]
                if p is None or (p not in cand and cand):
                    p = cand[-1] if cand else p
                if p is not None and (p["local"], p["gl"]) != (a, ga) and (p["visitante"], p["gv"]) == (a, ga):
                    # desempate en cancha neutral escrito al revés: dar vuelta el partido
                    p["local"], p["visitante"], p["gl"], p["gv"] = p["visitante"], p["local"], p["gv"], p["gl"]
                    p["pen_l"], p["pen_v"] = p.get("pen_v"), p.get("pen_l")
                    for g in p["goles"]:
                        g["lado"] = "visitante" if g["lado"] == "local" else "local"
                if p is None:
                    raros.append("detalle sin partido: " + s)
                detalle["partido"] = p
                detalle["orientado"] = True
                continue
            if p is None:
                detalle = None
            else:
                m = RE_MINUTO.match(linea)
                if m and not re.match(r"^\s*[A-Z][A-Za-z ]+:", linea):
                    minuto = int(m.group(1)) if m.group(1) and m.group(1).isdigit() else None
                    detalle["minutos"].append((minuto, m.group(2).strip(), int(m.group(3)), int(m.group(4))))
                    continue
                if linea.startswith(" "):
                    # renglón que sigue al de arriba (formación larga, tarjetas, etc.)
                    if en_formacion:
                        detalle["formaciones"][en_formacion] += " " + s
                    continue
                m = re.match(r"^([A-Za-z][^:\[\]]{0,40}?)\s*:\s*(.*)$", s)
                if m and not re.match(r"^" + RE_FECHA + r"\s*:", s):
                    clave, valor = m.group(1).strip(), m.group(2).strip()
                    en_formacion = None
                    if re.match(r"^(Referee|Ref\.?)$", clave, re.I):
                        p["arbitro"] = re.sub(r"\s+[A-Z]{3}$", "", valor)
                    elif re.match(r"^(Stadium|Venue)$", clave, re.I):
                        detalle["estadio"] = valor
                    elif re.match(r"^Goals?$", clave, re.I):
                        detalle["goles_texto"] = valor
                    elif re.match(r"^Penalt", clave, re.I):
                        detalle["penales"] = True  # lo que sigue son los pateadores, no formaciones
                    elif re.match(r"^(NB|Note|Att|Attendance|Yellow|Red|Sent|Scored|Missed|Coach|T)\b", clave, re.I):
                        pass
                    elif not detalle.get("penales"):
                        en_formacion = clave
                        detalle["formaciones"][clave] = valor
                    continue
                if re.match(r"^\d+-\d+ on (aggregate|penalties)|^Coach", s, re.I):
                    continue
                # fin del bloque: volcar lo juntado al partido
                cerrar_detalle(detalle)
                detalle = None
                en_formacion = None

        # --- Goleadores de los partidos recién leídos ---
        if s.startswith("["):
            if not pendientes:
                raros.append("goles sin partido: " + s)
                continue
            p = pendientes.pop(0)
            p["goles"] = goles_por_lado(s, p["gl"], p["gv"], p.get("_mesa"))
            continue

        # --- Fechas de una ronda eliminatoria: '(Apr 19 & 30)' ---
        if re.match(r"^\(.*\)?$", s) and fechas_de(s, anio):
            fechas_llave = fechas_de(s, anio)
            continue

        # --- Llave de ida y vuelta: 'Peñarol  Uru  Olimpia  Par  1-0 1-1 2-1' ---
        m = RE_LLAVE.match(s)
        if m and m.group("pa") in RE_PAIS and m.group("pb") in RE_PAIS:
            a, b = m.group("a").strip(), m.group("b").strip()
            previa = [p for p in partidos if p.get("llave") == llave_n]
            repite = previa and {previa[0]["local"], previa[0]["visitante"]} == {a, b}
            if not repite:
                llave_n += 1
            resto = m.group("resto")
            pais = {a: RE_PAIS[m.group("pa")], b: RE_PAIS[m.group("pb")]}
            toks = resto.split()
            normales, desempate, penales, notas = [], None, None, []
            for t in toks:
                mm = re.match(r"^\[(\d+)-(\d+)(aet)?\]", t)
                if mm:
                    desempate = (int(mm.group(1)), int(mm.group(2)))
                    continue
                mm = re.match(r"^(\d+)-(\d+)p", t)
                if mm:
                    penales = (int(mm.group(1)), int(mm.group(2)))
                    continue
                mm = re.match(r"^(\d+)-(\d+)", t)
                if mm:
                    normales.append((int(mm.group(1)), int(mm.group(2))))
                    continue
                if t == "awd":
                    normales.append(None)
                    notas.append("partido dado por ganado")
                    continue
                notas.append(t)
            if len(normales) >= 3:
                normales = normales[:2]   # el tercero es el global
            if repite and len(normales) == 1:  # es el partido desempate de la llave anterior
                desempate, normales = normales[0], []
            nuevos = []
            for i, r in enumerate(normales):
                ida = i == 0
                p = nuevo(local=a if ida else b, visitante=b if ida else a,
                          gl=(r[0] if ida else r[1]) if r else None,
                          gv=(r[1] if ida else r[0]) if r else None,
                          fecha=fechas_llave[i] if i < len(fechas_llave) else None,
                          llave=llave_n, paises=pais)
                if r is None:
                    p["notas"] = "dado por ganado"
                nuevos.append(p)
            if desempate:
                p = nuevo(local=a, visitante=b, gl=desempate[0], gv=desempate[1], llave=llave_n, paises=pais,
                          fecha=fechas_llave[len(normales)] if len(fechas_llave) > len(normales) else None,
                          notas="partido desempate")
                nuevos.append(p)
            if penales and nuevos:
                ult = nuevos[-1]
                ult["pen_l"], ult["pen_v"] = (penales if ult["local"] == a else penales[::-1])
            pendientes = [p for p in nuevos if (p["gl"] or 0) + (p["gv"] or 0) > 0]
            continue

        # --- Tabla de posiciones: solo se usa para saber la ciudad de cada club ---
        m = RE_TABLA.match(linea)
        if m and not RE_PARTIDO.match(linea.split(":")[-1] if ":" in linea[:8] else "x"):
            nombre = m.group("nombre").strip()
            mc = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", nombre)
            if mc:
                ciudades[mc.group(1).strip()] = mc.group(2).strip()
            continue

        # --- Partido no jugado, suspendido o dado por ganado: 'Boca Juniors - Universitario   n/p [awarded...]' ---
        m = re.match(r"^\s*(?:" + RE_FECHA + r"\s*:)?\s*(\S.*?)\s+-\s+(\S.*?)\s+(n/p|awd|abd)\b\s*(.*)$", linea)
        if m:
            nota = m.group(8).strip(" []*") or {"n/p": "no se jugó", "awd": "dado por ganado",
                                                "abd": "suspendido"}[m.group(7)]
            p = nuevo(local=m.group(5).strip(), visitante=m.group(6).strip(), gl=None, gv=None,
                      fecha=fecha_partido(m, anio), notas=nota)
            if p["fecha"] is None and len(partidos) > 1:
                p["fecha"] = partidos[-2]["fecha"]
            pendientes = []
            continue

        # --- Partido suelto (grupos, desempates): 'Feb 28: Rosario Central - Newell's  1-1' ---
        m = RE_PARTIDO.match(linea)
        if m and (m.group(1) or m.group(3) or linea.startswith(" ") or " - " in s):
            resto = m.group("resto")
            p = nuevo(local=m.group("a").strip(), visitante=m.group("b").strip(),
                      gl=int(m.group("ga")), gv=int(m.group("gb")), fecha=fecha_partido(m, anio))
            if p["fecha"] is None and partidos[:-1]:
                p["fecha"] = partidos[-2]["fecha"]  # misma fecha que el renglón de arriba
            mp = re.search(r"(\d+)-(\d+)p", resto)
            if mp:
                p["pen_l"], p["pen_v"] = int(mp.group(1)), int(mp.group(2))
            mn = re.search(r"\((.+)\)", resto)
            if mn:
                p["notas"] = mn.group(1)
            if resto.startswith("x"):   # '3-0x': resultado dado por reglamento (los goles no tienen por qué cuadrar)
                p["_mesa"] = True
            pendientes = [p] if p["gl"] + p["gv"] > 0 else []
            continue

        # --- Partido no jugado: 'Botafogo - Millonarios        x' ---
        if re.match(r"^" + RE_FECHA + r"\s*:.+\s-\s.+\s+[a-z*]$", s):
            continue

        # --- Títulos de fase ---
        titulo = re.sub(r"\(.*?\)|\[.*?\]", "", s).strip()
        nombre, tipo = fase_de(titulo, copa)
        # ('Group Phase' de la Sudamericana es el título de la fase, no un grupo)
        if re.match(r"^group\s+\w+", titulo, re.I) and not (copa == "sudamericana" and nombre):
            subfase = "Grupo " + titulo.split()[1]
            mp = re.search(r"\[(.*?)\]", s)
            paises_grupo = [PAISES_NOMBRE.get(x.strip(), x.strip()) for x in mp.group(1).split(",")] if mp else []
            continue
        # 'Third Place Playoff' dentro de un grupo (1990, 1992, 1993, 1995) es el desempate por el 3.er puesto
        # de ese grupo, no el partido por el tercer puesto del torneo
        en_grupo = bool(subfase and subfase.startswith("Grupo"))
        if re.search(r"playoff|play-off", titulo, re.I) and (not nombre or en_grupo) and nombre != "Playoffs de octavos" \
                and not (copa == "sudamericana" and len(titulo) > 40):   # una frase que menciona un "play-off"
            subfase = (subfase.split(" — ")[0] if subfase else "") + " — Desempate" if subfase else "Desempate"
            continue
        if nombre:
            fase, tipo_fase, subfase = nombre, tipo, None
            fechas_llave = fechas_de(s[s.index("("):], anio) if "(" in s else []   # sin el "1" de "Round 1"
            continue

        # Notas al pie ('x 1st leg in Valencia'), byes, etc.
        if (re.match(r"^[a-z*]\s|^NB|^Note|^Competing|^Copa Libertadores|^<|^Att(endance)?\b|^[A-Z][a-z]+\s+-\s", s)
                or re.search(r"\bbye\b", s)):
            continue
        raros.append(s)

    if detalle is not None:
        cerrar_detalle(detalle)
    for p in partidos:
        p.pop("_detalle", None)
    return {"anio": anio, "partidos": partidos, "goleadores": goleadores, "ciudades": ciudades, "raros": raros}


def partir_arriba(texto, seps=",;"):
    """Separa por comas/punto y coma, pero no dentro de paréntesis."""
    partes, nivel, actual = [], 0, ""
    for c in texto:
        nivel += c == "("
        nivel -= c == ")"
        if c in seps and nivel == 0:
            partes.append(actual.strip())
            actual = ""
        else:
            actual += c
    if actual.strip():
        partes.append(actual.strip())
    return partes


def leer_formacion(texto):
    """'Maidana, W.Martínez (Majewski), ... Coach: Bianchi'
       -> {'titulares': [...], 'cambios': [{'sale','entra','min'}], 'dt': ...}"""
    dt = None
    m = re.search(r"\b(Coach|DT|T)\s*:\s*(.+?)\.?\s*$", texto, re.I)
    if m:
        dt, texto = m.group(2).strip(), texto[:m.start()]
    titulares, cambios = [], []
    for item in partir_arriba(texto.strip().rstrip(".")):
        item = re.sub(r"\((c|cap)\)", "", item).strip()
        entradas = re.findall(r"\(([^()]*)\)", item)
        nombre = re.sub(r"\s*\([^()]*\)", "", item).strip()
        if not nombre:
            continue
        titulares.append(nombre)
        sale = nombre
        for e in entradas:
            # '(65 César La Paglia)' o '(Guilherme 64)': el minuto puede ir antes o después
            me = re.match(r"^(\d+)?'?\s*(.+?)\s*(\d+)?'?$", e.strip())
            entra = me.group(2).strip()
            mins = me.group(1) or me.group(3)
            cambios.append({"sale": sale, "entra": entra, "min": int(mins) if mins else None})
            sale = entra
    return {"titulares": titulares, "cambios": cambios, "dt": dt}


def cerrar_detalle(detalle):
    """Pasa estadio, fecha, goles y formaciones del bloque de detalle al partido."""
    p = detalle["partido"]
    if p is None:
        return
    p["_detalle"] = True
    if detalle["estadio"]:
        p["estadio"] = detalle["estadio"]
    if detalle["fecha"]:
        p["fecha"] = detalle["fecha"]
    if detalle.get("arbitro"):
        p["arbitro"] = detalle["arbitro"]
    total = (p["gl"] or 0) + (p["gv"] or 0)
    minutos = detalle["minutos"]
    if minutos and len(minutos) == total:
        goles, la = [], 0
        for minuto, nombre, a, b in minutos:
            lado = "local" if a > la else "visitante"
            la = a
            tipo = "ec" if re.search(r"\bo/?g\b", nombre) else ("pen" if re.search(r"\bpen\b", nombre) else None)
            nombre = re.sub(r"\s*\((o/?g|pen)\)|\s+(o/?g|pen)$", "", nombre).strip()
            goles.append({"jugador": nombre, "min": minuto, "tipo": tipo, "lado": lado})
        p["goles"] = goles
    elif detalle["goles_texto"] and re.search(r"\d+-\d+\s*\(\d+", detalle["goles_texto"]):
        # 'Goals: 0-1 (79) Marcelo Delgado' -> el marcador dice de qué lado fue
        goles, la = [], 0
        for a, b, minuto, nombre in re.findall(r"(\d+)-(\d+)\s*\((\d+)[^)]*\)\s*([^,;]+)", detalle["goles_texto"]):
            goles.append({"jugador": nombre.strip(), "min": int(minuto), "tipo": None,
                          "lado": "local" if int(a) > la else "visitante"})
            la = int(a)
        if len(goles) == total:
            p["goles"] = goles
    elif detalle["goles_texto"]:
        # 'Goals: 22 Arruabarrena, 61 Arruabarrena; 43 Pena' -> el minuto va adelante
        texto = ";".join(",".join(re.sub(r"^(\d+)\s+(.+)$", r"\2 \1", t.strip()) for t in lado.split(","))
                         for lado in detalle["goles_texto"].split(";"))
        goles = goles_por_lado(texto, p["gl"], p["gv"])
        if len(goles) == total:
            p["goles"] = goles
    forms = {k: leer_formacion(v) for k, v in detalle["formaciones"].items() if not k.startswith("_")}
    if forms:
        p["formaciones_crudas"] = forms


if __name__ == "__main__":
    clave, args = copa_de_argumentos()
    for a in [int(x) for x in args] or [COPAS[clave]["desde"]]:
        r = leer(a, clave)
        for p in r["partidos"]:
            print(f"{p['fase']:<40} {p['fecha'] or '?':<11} {p['local']:>28} {p['gl']}-{p['gv']} {p['visitante']:<28} "
                  f"{len(p['goles'])}g {p.get('notas') or ''}")
        print("GOLEADORES:", r["goleadores"][:5])
        print("NO ENTENDIDAS:", *r["raros"], sep="\n  ")
