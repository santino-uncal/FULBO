"""Descarga la bandera de cada país que aparece en data/equipos.js (assets/banderas/<código>.png, 40 px de ancho).

Uso:  python tools/descargar_banderas.py
Fuente: flagcdn.com (banderas de dominio público). Yugoslavia, que ya no existe, sale de Wikimedia Commons.
No vuelve a bajar las que ya están.
"""
import json
import re
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "banderas"
# Nuestro código de país (el de la FIFA) -> el de flagcdn (ISO de dos letras; Inglaterra y Escocia van aparte)
ISO = {"ARG": "ar", "BOL": "bo", "BRA": "br", "CHI": "cl", "COL": "co", "ECU": "ec", "MEX": "mx", "PAR": "py",
       "PER": "pe", "URU": "uy", "VEN": "ve", "USA": "us", "CRC": "cr", "HON": "hn",
       "ESP": "es", "ITA": "it", "ENG": "gb-eng", "SCO": "gb-sct", "GER": "de", "NED": "nl", "POR": "pt",
       "ROU": "ro", "SWE": "se", "GRE": "gr", "FRA": "fr", "AUT": "at", "KSA": "sa", "EGY": "eg", "UAE": "ae",
       "QAT": "qa", "TUN": "tn", "ALG": "dz", "MAR": "ma", "RSA": "za", "COD": "cd", "JPN": "jp", "KOR": "kr",
       "CHN": "cn", "IRN": "ir", "AUS": "au", "NZL": "nz", "TAH": "pf", "NCL": "nc", "PNG": "pg",
       # clubes de la Champions League
       "MCO": "mc", "NOR": "no", "BEL": "be", "CRO": "hr", "DEN": "dk", "AZE": "az", "TUR": "tr", "KAZ": "kz",
       "CYP": "cy", "UKR": "ua", "CZE": "cz", "SVK": "sk", "SUI": "ch",
       "FIN": "fi", "IRL": "ie", "ISL": "is", "LTU": "lt", "LUX": "lu", "LVA": "lv", "MLT": "mt", "NIR": "gb-nir", "POL": "pl", "HUN": "hu", "BUL": "bg", "ALB": "al", "SRB": "rs", "SVN": "si", "MDA": "md", "BLR": "by", "ISR": "il", "RUS": "ru"}
OTRAS = {"YUG": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Flag_of_Yugoslavia_%281946-1992%29.svg/"
                "40px-Flag_of_Yugoslavia_%281946-1992%29.svg.png"}
UA = "FULBO-historia/1.0 (https://santino-uncal.github.io/FULBO/)"


def main():
    texto = (RAIZ / "data" / "equipos.js").read_text(encoding="utf-8")
    equipos = json.loads(re.search(r"window\.LIB\.equipos\s*=\s*(\{.*\});", texto, re.S).group(1))
    paises = sorted({e["pais"] for e in equipos.values() if e.get("pais")})
    for pais in paises:
        archivo = DESTINO / f"{pais}.png"
        if archivo.exists():
            continue
        url = OTRAS.get(pais) or (f"https://flagcdn.com/w40/{ISO[pais]}.png" if pais in ISO else None)
        if not url:
            print(f"  ✗ {pais}: no sé de dónde bajarla (agregarla en ISO)")
            continue
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            archivo.write_bytes(r.read())
        print(f"  ✓ {pais}")


if __name__ == "__main__":
    main()
