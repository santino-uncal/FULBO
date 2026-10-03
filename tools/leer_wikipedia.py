"""Convierte las páginas de Wikipedia (tools/cache/wikipedia-<copa>) en datos estructurados, en el mismo formato
que leer_rsssf: goles con minuto, estadio, árbitro, público, penales y formaciones con los cambios.

No se usa solo: lo llama tools/generar_datos.py. Para revisar una edición suelta:
    python tools/leer_wikipedia.py --copa intercontinental 1985
Cada partido es un "{{Football box ...}}" de la página; la fase sale del título de la sección
("Group A", "Final", "Play-off"…) y las formaciones, de las dos tablas que vienen debajo del partido.
"""
import datetime
import re

from copas import COPAS, copa_de_argumentos

MESES = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                     "september", "october", "november", "december"], 1)}
# Códigos de país de Wikipedia que se escriben distinto en la página (Alemania Federal = Alemania)
PAISES = {"FRG": "GER", "SPA": "ESP", "DDR": "GDR", "CSK": "TCH", "ROM": "ROU", "USS": "URS", "SWI": "SUI",
          "SLO": "SVN", "LAT": "LVA", "LIT": "LTU", "DNK": "DEN", "GRC": "GRE", "IRE": "IRL", "DEU": "GER", "SCG": "FRY"}
# A veces la bandera lleva el nombre del país en vez del código ({{fbaicon|West Germany}})
NOMBRES_PAIS = {"west germany": "GER", "germany": "GER", "east germany": "GDR", "soviet union": "URS", "ussr": "URS",
                "czechoslovakia": "TCH", "czech republic": "CZE", "yugoslavia": "YUG", "fr yugoslavia": "FRY",
                "socialist federal republic of yugoslavia": "YUG", "spain": "ESP", "belgium": "BEL", "scotland": "SCO",
                "netherlands": "NED", "italy": "ITA", "sweden": "SWE", "portugal": "POR", "romania": "ROU",
                "france": "FRA", "switzerland": "SUI", "austria": "AUT", "greece": "GRE", "england": "ENG",
                "hungary": "HUN", "bulgaria": "BUL", "iceland": "ISL", "denmark": "DEN", "turkey": "TUR",
                "russia": "RUS", "poland": "POL", "ireland": "IRL", "republic of ireland": "IRL", "finland": "FIN",
                "wales": "WAL", "norway": "NOR", "northern ireland": "NIR", "malta": "MLT", "luxembourg": "LUX",
                "cyprus": "CYP", "ukraine": "UKR", "slovenia": "SVN", "slovakia": "SVK", "albania": "ALB"}
# Posiciones de Wikipedia -> las que usa la página (las mismas siglas que ESPN)
POSICIONES = {"GK": "G", "CB": "CD", "DF": "D", "FB": "D", "MF": "M", "HB": "M", "WH": "M", "FW": "F", "CF": "F",
              "ST": "F", "SS": "F", "RW": "RF", "OR": "RF", "LW": "LF", "OL": "LF", "IR": "AM-R", "IL": "AM-L",
              "RWB": "RB", "LWB": "LB", "RH": "RM", "LH": "LM", "CH": "CD", "AM": "AM", "LM": "LM", "RM": "RM",
              "DM": "DM", "CM": "CM", "LB": "LB", "RB": "RB", "SW": "SW", "RF": "RF", "LF": "LF"}


def limpiar(texto):
    """Saca referencias, comentarios y etiquetas HTML."""
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    texto = re.sub(r"<ref[^>/]*/>", "", texto)
    texto = re.sub(r"<ref[^>]*>.*?</ref>", "", texto, flags=re.S)
    return texto.replace("&ndash;", "–").replace("&nbsp;", " ")


def plantilla(texto, inicio):
    """Devuelve el final de la plantilla {{...}} que empieza en 'inicio' (contando llaves anidadas)."""
    nivel, i = 0, inicio
    while i < len(texto) - 1:
        par = texto[i:i + 2]
        if par == "{{":
            nivel += 1
            i += 2
            continue
        if par == "}}":
            nivel -= 1
            i += 2
            if nivel == 0:
                return i
            continue
        i += 1
    return len(texto)


def partir(cuerpo):
    """Separa los parámetros de una plantilla por '|', sin cortar dentro de {{ }} ni de [[ ]]."""
    partes, actual, nivel, i = [], "", 0, 0
    while i < len(cuerpo):
        par = cuerpo[i:i + 2]
        if par in ("{{", "[["):
            nivel += 1
            actual += par
            i += 2
            continue
        if par in ("}}", "]]"):
            nivel -= 1
            actual += par
            i += 2
            continue
        if cuerpo[i] == "|" and nivel == 0:
            partes.append(actual)
            actual = ""
        else:
            actual += cuerpo[i]
        i += 1
    partes.append(actual)
    return partes


def parametros(cuerpo):
    res = {}
    for p in partir(cuerpo)[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            res[k.strip().lower()] = v.strip()
    return res


def texto_plano(t):
    """'[[Club Atlético Peñarol|Peñarol]] {{flagicon|URU}}' -> 'Peñarol'."""
    # {{ill|Alberto Tejada Burga|es}} (link a otra Wikipedia) y {{nowrap|…}}: queda el texto
    t = re.sub(r"\{\{\s*(?:ill|nowrap|interlanguage link)\s*\|([^|{}]*)[^{}]*\}\}", r"\1", t, flags=re.I)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip(" *,")


def pais_de(t):
    m = re.search(r"\{\{\s*(?:flagicon|fbaicon|flag|fb)\s*\|\s*([^|}]+)", t, re.I)
    if not m:
        return None
    arg = m.group(1).strip()
    if arg.lower() in NOMBRES_PAIS:
        return NOMBRES_PAIS[arg.lower()]
    return PAISES.get(arg[:3].upper(), arg[:3].upper()) if re.match(r"[A-Za-z]{3}", arg) else None


def fecha_de(t):
    m = re.search(r"\{\{\s*start date[^}]*?\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", t, re.I)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)   # (también viene escrita así: 1993-09-29)
    if m:
        return "-".join(m.groups())
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", t) or re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", t)
    if not m:
        return None
    a, b, anio = m.groups()
    dia, mes = (a, b) if a.isdigit() else (b, a)
    if mes.lower() not in MESES:
        return None
    return f"{anio}-{MESES[mes.lower()]:02d}-{int(dia):02d}"


def minuto(t):
    """'90+2' -> (90, 2)"""
    m = re.match(r"\s*(\d+)(?:\s*\+\s*(\d+))?", t)
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else None) if m else (None, None)


def leer_goles(texto, lado):
    """'*[[Michel Platini|Platini]] {{goal|63|pen.}} <br> [[Laudrup]] {{goal|82}}' -> goles con minuto y tipo.
    {{goal|2||8}} son dos goles (minutos 2 y 8): los parámetros van de a pares, minuto y aclaración."""
    goles = []
    # el gol de oro (Liverpool-Alavés 2001) y el de plata se escriben con su propia plantilla
    texto = re.sub(r"\{\{\s*(?:golden|silver) goal\s*\|", "{{goal|", texto, flags=re.I)
    for renglon in re.split(r"<br\s*/?>|\n", texto):
        if "{{goal" not in renglon.lower():
            continue
        nombre = texto_plano(re.sub(r"\{\{\s*goal[^}]*\}\}", "", renglon, flags=re.I))
        for g in re.findall(r"\{\{\s*goal\s*\|([^}]*)\}\}", renglon, re.I):
            p = g.split("|")
            for i in range(0, len(p), 2):
                if not p[i].strip():
                    continue
                nota = (p[i + 1] if i + 1 < len(p) else "").lower()
                mi, extra = minuto(p[i])
                tipo = "ec" if re.search(r"o\.?g", nota) else "pen" if re.search(r"pen|^p\.?$", nota) else None
                x = {"jugador": nombre, "min": mi, "tipo": tipo, "lado": lado}
                if extra:
                    x["extra"] = extra
                goles.append(x)
    return goles


def resultado(t):
    m = re.search(r"(\d+)\s*[–\-−]\s*(\d+)", texto_plano(t) if "[[" in t else t)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


RE_JUGADOR = re.compile(r"^\|\s*([A-Z]{1,3})\s*\|\|\s*(?:'''\s*(\d*)\s*'''\s*)?\|\|(.*)$")


def leer_formaciones(bloque):
    """Las dos tablas de formaciones que siguen al partido: '|GK ||'''1''' ||{{flagicon|ITA}} [[Tacconi]] || {{suboff|64}}'.
    La primera tabla es del equipo 1 (local) y la segunda del equipo 2."""
    equipos = [{"titulares": [], "suplentes": [], "dt": None}, {"titulares": [], "suplentes": [], "dt": None}]
    n, suplentes, espera_dt = 0, False, False
    for linea in bloque.splitlines():
        s = linea.strip()
        if n > 1:
            break
        if espera_dt and s.startswith("|") and not s.startswith("|-"):
            nombre = texto_plano(re.sub(r"^\|\s*(colspan\s*=\s*\"?\d+\"?\s*\|)?", "", s))
            if nombre:
                equipos[n]["dt"] = nombre
                espera_dt, suplentes = False, False
                n += 1
            continue
        if re.search(r"'''\s*(Manager|Coach|Head coach)\s*:?\s*'''", s, re.I):
            m = re.search(r"'''\s*(?:Manager|Coach|Head coach)\s*:?\s*'''\s*(.*)$", s, re.I)
            resto = texto_plano(m.group(1)) if m else ""
            if resto:
                equipos[n]["dt"] = resto
                suplentes = False
                n += 1
            else:
                espera_dt = True
            continue
        if re.search(r"'''\s*Substitut", s, re.I):
            suplentes = True
            continue
        m = RE_JUGADOR.match(s)
        if not m:
            continue
        pos, num, resto = m.groups()
        celdas = resto.split("||")
        nombre = texto_plano(re.sub(r"\((?:\[\[[^\]]*\]\]|c|captain)\)", "", celdas[0], flags=re.I))
        if not nombre:
            continue
        j = {"nombre": nombre, "pos": POSICIONES.get(pos, pos)}
        if num:
            j["num"] = num
        todo = resto   # el cambio a veces está pegado al nombre, en la misma celda
        sale = re.search(r"\{\{\s*suboff\s*\|\s*([\d+]+)", todo, re.I)
        entra = re.search(r"\{\{\s*subon\s*\|\s*([\d+]+)", todo, re.I)
        roja = re.search(r"\{\{\s*sent off\s*\|\s*\d*\s*\|\s*([\d+]+)", todo, re.I)
        if roja:
            j["roja"] = minuto(roja.group(1))[0]
        if suplentes:
            j["jugo"] = bool(entra)
            if entra:
                j["min"] = minuto(entra.group(1))[0]
            equipos[n]["suplentes"].append(j)
        else:
            if sale:
                j["_sale"] = minuto(sale.group(1))[0]
            equipos[n]["titulares"].append(j)
    # A quién reemplazó cada suplente: el que salió en ese mismo minuto (en el orden de la tabla)
    for eq in equipos:
        salieron = [j for j in eq["titulares"] + eq["suplentes"] if j.get("_sale") is not None]
        for s in eq["suplentes"]:
            if not s.get("jugo"):
                continue
            x = next((j for j in salieron if j["_sale"] == s.get("min") and not j.get("_usado")), None)
            if x:
                s["por"] = x["nombre"]
                x["_usado"] = True
        for j in eq["titulares"] + eq["suplentes"]:
            j.pop("_sale", None)
            j.pop("_usado", None)
    return [eq if eq["titulares"] else None for eq in equipos]


def fase_de(titulo, copa):
    t = titulo.lower()
    m = re.match(r"group\s+(\w+)$", t)
    if m:
        return f"Fase de grupos — Grupo {m.group(1).upper()}"
    if "third" in t:
        return "Tercer puesto"
    if "fifth" in t:
        return "Quinto puesto"
    if "semi" in t:
        return "Semifinales"
    if "quarter" in t:
        return "Cuartos de final"
    return "Final" if copa in ("intercontinental", "recopa") or "final" in t else None


def fase_etapa(etapa, titulos):
    """Fase de un partido de la Champions según la página (etapa) y los títulos de sección de esa página."""
    if etapa in ("Fase de grupos", "Segunda fase de grupos"):
        letra = next((m.group(1).upper() for t in reversed(titulos) for m in [re.match(r"group\s+(\w+)$", t, re.I)] if m), None)
        return f"{etapa} — Grupo {letra}" if letra else None
    if etapa == "Eliminatorias":   # la ronda sale del título de la sección ("First leg" y "Play-off" no son rondas)
        return next((f for f in map(ronda_champions, reversed(titulos)) if f), None)
    return etapa


def ronda_champions(titulo):
    t = titulo.lower().strip()
    if re.match(r"^(semi-?final|final) round$", t):
        return None   # la ronda preliminar de 2018-2020 (cuatro equipos: semifinales y final) es una sola ronda
    for patron, nombre in ((r"^preliminary", "Ronda preliminar"), (r"^first qualifying", "Primera fase previa"),
                           (r"^second qualifying", "Segunda fase previa"), (r"^third qualifying", "Tercera fase previa"),
                           (r"qualifying", "Fase previa"), (r"^play-?off round", "Playoff de clasificación"),
                           (r"^first round", "Primera ronda"), (r"^second round", "Segunda ronda"),
                           (r"^third round", "Tercera ronda"), (r"^fourth round", "Cuarta ronda"), (r"^quarter", "Cuartos de final"),
                           (r"^semi", "Semifinales"), (r"^final$", "Final")):
        if re.search(patron, t):
            return nombre
    return None


def rondas_por_cantidad(partidos, por_partidos=False):
    """Champions hasta 1990/91 y Copa UEFA: las rondas se llaman según cuántos equipos las jugaron (64 equipos:
    treintaidosavos de final; 32: dieciseisavos; 16: octavos; las de 96 y 48 equipos de la Copa UEFA 1999-2001 quedan
    como "primera ronda" y "segunda ronda"). Y si hay una página de la final, la final de la página de la temporada
    sobra (es el mismo partido)."""
    for ronda in ("Primera ronda", "Segunda ronda", "Tercera ronda", "Cuarta ronda"):
        equipos = {x for p in partidos if p["fase"] == ronda for x in (p["local"], p["visitante"])}
        if equipos:
            n = len(equipos)
            if por_partidos:   # Copa UEFA: el mismo club a veces está escrito distinto en la ida y la vuelta
                n = min(n, sum(p["fase"] == ronda and p["notas"] != "partido desempate" for p in partidos))
            nombre = "Octavos de final" if 8 < n <= 16 else "Dieciseisavos de final" if 16 < n <= 32 else                 "Treintaidosavos de final" if 56 <= n <= 64 else ronda
            for p in partidos:
                if p["fase"] == ronda:
                    p["fase"] = nombre
    if any(p.get("_pagina_final") for p in partidos):
        partidos[:] = [p for p in partidos if p["fase"] != "Final" or p.get("_pagina_final")]
    for p in partidos:
        p.pop("_pagina_final", None)


def leer(anio, copa="intercontinental"):
    texto = limpiar((COPAS[copa]["cache_wikipedia"] / f"{anio}.txt").read_text(encoding="utf-8"))
    # Títulos de sección con su posición, para saber en qué fase está cada partido
    secciones = [(m.start(), m.group(2).strip()) for m in re.finditer(r"^(={2,4})\s*(.*?)\s*\1\s*$", texto, re.M)]
    # ("{{Football box…}}" o, en las páginas más nuevas, "{{#invoke:Football box|main…}}")
    cajas = [m.start() for m in re.finditer(r"\{\{\s*(?:#invoke:\s*)?football ?box", texto, re.I)]
    # La Champions: cada página del archivo es una fase ("@@ETAPA Fase de grupos@@", ver descargar_wikipedia.py)
    etapas = [(m.start(), m.group(1)) for m in re.finditer(r"^@@ETAPA (.*?)@@$", texto, re.M)]
    partidos, raros = [], []
    for n, inicio in enumerate(cajas):
        fin = plantilla(texto, inicio)
        par = parametros(texto[inicio + 2:fin - 2])
        titulos = [t for pos, t in secciones if pos < inicio and not re.match(r"^(details|match|summary)$", t, re.I)]
        titulo = titulos[-1] if titulos else ""
        etapa = next((e for pos, e in reversed(etapas) if pos < inicio), None)
        if etapa:
            titulos = [t for pos, t in secciones if pos < inicio and pos > max(x for x, _ in etapas if x < inicio)
                       and not re.match(r"^(details|match|summary)$", t, re.I)]
            fase = fase_etapa(etapa, titulos)
        else:
            fase = fase_de(titulo, copa) or next((f for f in (fase_de(t, copa) for t in reversed(titulos)) if f), None)
        if not fase:
            raros.append(f"sin fase: {titulo}")
            continue
        if re.search(r"annulled|void", par.get("score", ""), re.I):
            continue   # partido anulado y vuelto a jugar (Panathinaikos-CSKA Sofia 1972): vale el otro
        gl, gv = resultado(par.get("score", ""))
        if gl is None and par.get("score1"):
            gl, gv = int(par["score1"]), int(par["score2"])
        local, visitante = texto_plano(par.get("team1", "")), texto_plano(par.get("team2", ""))
        p = {"fase": fase, "fecha": fecha_de(par.get("date", "")), "local": local, "visitante": visitante,
             "gl": gl, "gv": gv, "notas": None,
             "paises": {local: pais_de(par.get("team1", "")), visitante: pais_de(par.get("team2", ""))},
             "goles": leer_goles(par.get("goals1", ""), "local") + leer_goles(par.get("goals2", ""), "visitante")}
        # Formaciones y aclaraciones: entre este partido y el siguiente (o la sección siguiente)
        hasta = min([c for c in cajas if c > inicio] + [pos for pos, _ in secciones if pos > fin] + [len(texto)])
        goles_cancha = len(p["goles"]) != (gl or 0) + (gv or 0)
        if copa == "europa" and re.search(r"abandoned[^.]*replayed", texto[fin:hasta], re.I):
            continue   # suspendido y vuelto a jugar (Inter-Dukla 1986, por la niebla): vale el otro
        # Resultado dado en los escritorios: lo dice el partido o, en la Copa UEFA, el texto de abajo ("UEFA awarded…")
        if re.search(r"awarded", par.get("scorenote", "") + par.get("score", ""), re.I) or (
                copa == "europa" and goles_cancha and re.search(r"awarded|by default|forfeit", texto[fin:hasta], re.I)):
            # Resultado dado en los escritorios (Leeds-Stuttgart 1992): los goles de la cancha no cuentan
            en_cancha = sum(g["lado"] == "local" for g in p["goles"]), sum(g["lado"] == "visitante" for g in p["goles"])
            p["notas"] = f"resultado dado por la UEFA (en la cancha terminó {en_cancha[0]}–{en_cancha[1]})"
            p["goles"] = []
        if etapa == "Final":
            p["_pagina_final"] = True
        if copa in ("champions", "europa") and (re.search(r"play-?off", par.get("id", ""), re.I) or
                                    re.search(r"play-?off|replay|decider", titulo, re.I)):
            p["notas"] = "partido desempate"
        if copa in ("intercontinental", "recopa"):
            p["llave"] = 1
            if re.search(r"play-?off|replay", titulo, re.I):
                p["notas"] = "partido desempate"
        # 'Estadio, Ciudad': las comas que están dentro de un link ([[National Stadium (Tokyo, 1958)|…]]) no cuentan
        estadio = re.sub(r"\[\[[^\]]*\]\]", lambda m: m.group(0).replace(",", "\x00"), par.get("stadium", ""))
        lugares = [texto_plano(x.replace("\x00", ",")) for x in estadio.split(",")]
        lugares = [x for x in lugares if x]
        if lugares:
            p["estadio"] = lugares[0]
            if len(lugares) > 1:
                p["ciudad"] = lugares[-1]
        if par.get("location") and "ciudad" not in p:
            p["ciudad"] = texto_plano(par["location"])
        publico = re.sub(r"[^\d]", "", texto_plano(par.get("attendance", "")).split("(")[0])
        if publico:
            p["publico"] = int(publico)
        arbitro = re.sub(r"\s*\(.*$", "", texto_plano(par.get("referee", "")))
        if arbitro:
            p["arbitro"] = arbitro
        if par.get("penaltyscore"):
            p["pen_l"], p["pen_v"] = resultado(par["penaltyscore"])
        if "a.e.t" in par.get("score", "").lower() or "aet" in par.get("aet", "").lower() or                 re.search(r"golden goal|silver goal", par.get("goals1", "") + par.get("goals2", ""), re.I):
            p["alargue"] = True
        forms = leer_formaciones(texto[fin:hasta])
        if any(forms):
            p["formaciones"] = {lado: f for lado, f in zip(("local", "visitante"), forms) if f}
        total = (gl or 0) + (gv or 0)
        if len(p["goles"]) != total and not p["notas"]:
            raros.append(f"{local} {gl}-{gv} {visitante}: {len(p['goles'])} goles con autor")
        partidos.append(p)
    if copa in ("champions", "europa"):
        rondas_por_cantidad(partidos, copa == "europa")
        for p in partidos:
            if p["gl"] is None:
                p["notas"] = p["notas"] or "no se jugó"   # retiros y prohibiciones (Linfield-Vorwärts 1961…)
            # erratas en el año (Basel-Wacker 1977 figura en 1967): la temporada va de julio a junio
            if p.get("fecha") and int(p["fecha"][:4]) not in (anio, anio + 1):
                p["fecha"] = f"{anio if int(p['fecha'][5:7]) >= 7 else anio + 1}{p['fecha'][4:]}"
    return {"anio": anio, "partidos": partidos, "goleadores": [], "ciudades": {}, "raros": raros}


def anios(copa):
    carpeta = COPAS[copa].get("cache_wikipedia")
    if not carpeta or not carpeta.exists():
        return []
    return sorted(int(f.stem) for f in carpeta.glob("*.txt") if int(f.stem) <= datetime.date.today().year)


if __name__ == "__main__":
    clave, args = copa_de_argumentos()
    for a in [int(x) for x in args] or anios(clave):
        r = leer(a, clave)
        for p in r["partidos"]:
            f = p.get("formaciones", {})
            print(f"{a} {p['fase']:<28} {p['fecha'] or '?':<11} {p['local']:>24} {p['gl']}-{p['gv']} {p['visitante']:<24} "
                  f"{len(p['goles'])}g {'F' + str(len(f)) if f else '-'} {p.get('pen_l', '')}-{p.get('pen_v', '')} "
                  f"{p['paises']} {p.get('estadio')}, {p.get('ciudad')} · {p.get('arbitro')} · {p.get('publico')} {p.get('notas') or ''}")
        for x in r["raros"]:
            print("   ??", x)
