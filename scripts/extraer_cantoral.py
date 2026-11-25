"""Extrae el catálogo del cantoral (número, título, página, sección) a data/cantoral.json.

Uso:
    python scripts/extraer_cantoral.py fuentes/CANTORAL_LITURGICO.pdf

Solo extrae metadatos (títulos y páginas), no letras ni partituras.
Necesita `pdftotext` (poppler-utils).

Los momentos y etiquetas que no se deducen de la sección se completan a mano
en data/etiquetas_cantos.yaml, que tiene prioridad sobre lo extraído.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NUM = re.compile(r"^(\d{1,3})\.\s*(.*)$")


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


# Subsección del cantoral -> (momentos en los que se propone, etiquetas)
# momentos: entrada | ofertorio | comunion | salida ;  [] = no se propone en misa
MAPA = {
    "ordinario": ([], ["ordinario_misa"]),
    "antifonas_de_entrada": (["entrada"], []),          # son para fiestas concretas: etiquetar a mano
    "cantos_de_entrada": (["entrada"], ["general"]),
    "cantos_para_la_presentacion_de_los_dones": (["ofertorio"], ["general"]),
    "cantos_de_comunion": (["comunion"], ["general"]),
    "adviento": (["entrada", "comunion", "salida"], ["adviento"]),
    "navidad": (["entrada", "comunion", "salida"], ["navidad"]),
    "cuaresma_y_semana_santa": (["entrada", "comunion"], ["cuaresma"]),
    "pascua": (["entrada", "comunion", "salida"], ["pascua"]),
    "b_v_maria": (["entrada", "comunion", "salida"], ["virgen"]),
    "b_v_maria_de_covadonga": (["entrada", "ofertorio", "salida"], ["virgen", "covadonga"]),
    "sagrado_corazon_de_jesus": (["entrada", "comunion", "salida"], ["sagrado_corazon"]),
    "santisimo_sacramento": (["comunion"], ["santisimo"]),
    "espiritu_santo": (["entrada", "comunion"], ["espiritu_santo"]),
    "san_jose": (["entrada", "salida"], ["san_jose"]),
    # Cantos de un santo concreto: solo se proponen con `solo_si` (etiquetas_cantos.yaml)
    "san_francisco_y_buen_consejo": (["entrada", "salida"], []),
    "otros_santos": (["entrada", "salida"], []),
    "exequias": (["entrada", "ofertorio", "comunion"], ["difuntos"]),
}


def texto_pagina(pdf: str, p: int) -> list[str]:
    out = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"],
                         capture_output=True, text=True, check=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def num_paginas(pdf: str) -> int:
    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def limpiar_titulo(t: str) -> str:
    t = re.sub(r"(?<=[a-záéíóúñ)])\d+$", "", t)          # llamadas de nota pegadas
    return re.sub(r"\s+", " ", t).strip(" .")


def encabezados_indice(pdf: str, paginas=range(3, 9)) -> set[str]:
    """Nombres de secciones/subsecciones según el índice (líneas sin número)."""
    nombres = set()
    for p in paginas:
        out = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf, "-"],
                             capture_output=True, text=True, check=True).stdout
        for linea in out.splitlines():
            for trozo in re.split(r"\s{3,}", linea.strip()):
                m = re.match(r"^([A-ZÁÉÍÓÚÑ][^\d.]+?)\s*\.{3,}\s*\d+$", trozo)
                if m:
                    nombres.add(slug(m.group(1)))
    return nombres


def extraer(pdf: str, primera: int = 9) -> list[dict]:
    cantos: dict[int, dict] = {}
    encabezados = encabezados_indice(pdf) | set(MAPA)
    seccion = subseccion = ""
    for p in range(primera, num_paginas(pdf) + 1):
        lineas = texto_pagina(pdf, p)
        if len(lineas) < 2:
            continue
        cab = [l for l in lineas[:3] if not NUM.match(l) and l != "Cantoral Litúrgico" and not l.isdigit()]
        if cab:
            seccion = cab[0]
        for i, l in enumerate(lineas):
            m = NUM.match(l)
            if not m:
                continue
            n = int(m.group(1))
            titulo = m.group(2)
            j = i + 1
            if not titulo:                        # "104." en una línea y el título más abajo
                while j < len(lineas) and lineas[j] in (seccion, "Cantoral Litúrgico"):
                    j += 1
                titulo = lineas[j] if j < len(lineas) else ""
                j += 1
            if titulo.count("(") > titulo.count(")") and j < len(lineas):
                titulo += " " + lineas[j]
            if n in cantos or n > 400:
                continue
            previa = lineas[i - 1] if i > 0 else ""
            if slug(previa) in encabezados and previa != seccion:
                subseccion = previa
            elif slug(previa) == slug(seccion) and lineas.count(seccion) > 1:
                subseccion = seccion          # primera página de una sección sin subsecciones
            cantos[n] = {"n": n, "titulo": limpiar_titulo(titulo), "pagina": p,
                         "seccion": seccion, "subseccion": subseccion}

    for c in cantos.values():
        momentos, etiquetas = MAPA.get(slug(c["subseccion"]), ([], []))
        c["momentos"] = momentos
        c["etiquetas"] = etiquetas
    return [cantos[k] for k in sorted(cantos)]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cantos = extraer(sys.argv[1])
    destino = RAIZ / "data" / "cantoral.json"
    destino.write_text(json.dumps(cantos, ensure_ascii=False, indent=1), encoding="utf-8")
    faltan = [i for i in range(1, max(c["n"] for c in cantos) + 1) if i not in {c["n"] for c in cantos}]
    print(f"{len(cantos)} cantos -> {destino}")
    if faltan:
        print("No encontrados (añadir a mano en etiquetas_cantos.yaml):", faltan)


if __name__ == "__main__":
    main()
