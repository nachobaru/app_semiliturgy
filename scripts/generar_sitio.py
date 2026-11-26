"""Genera el sitio estático (GitHub Pages) en `sitio/`.

    python scripts/generar_sitio.py [--semanas 80] [--salida sitio]

Las reglas litúrgicas siguen en Python: aquí se pregeneran los borradores de las próximas
semanas (encadenados, para que los cantos no se repitan entre semanas consecutivas) y se
guardan en `datos.json`. La página (`sitio_src/`) solo edita y maqueta en el navegador.
Las semanas que ya existen en `semanas/*.yaml` (revisadas a mano) se respetan tal cual.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from semiliturgy.borrador import OPCIONES_HIMNO, RAIZ, cargar_config, generar_borrador, guardar_borrador  # noqa: E402
from semiliturgy.calendario import domingo_de  # noqa: E402
from semiliturgy.cantos import catalogo  # noqa: E402
from semiliturgy.hoja import PLANTILLAS, cargar_hoja  # noqa: E402

ORIGEN = RAIZ / "sitio_src"


def css_de_la_hoja() -> str:
    """El CSS de la hoja se toma de la plantilla de Python: una sola fuente de verdad."""
    html = (PLANTILLAS / "hoja.html").read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", html, re.S).group(1).strip()


CAMPOS_VARIANTE = ("celebracion", "color", "laudes_con_eucaristia", "laudes", "eucaristia", "cantos", "visperas",
                   "adecuados")


def injertar_opciones(real: dict, cfg: dict, carpeta: Path) -> dict:
    """Añade a una hoja revisada a mano lo que usa la web: opciones de los días con memorias libres
    y cantos adecuados de cada día.

    Lo que hay en el YAML revisado manda: pasa a ser la variante activa (la que coincide por formulario;
    si ninguna coincide, la primera) y las demás variantes salen del borrador calculado.
    """
    gen = generar_borrador(date.fromisoformat(real["semana"]), cfg, carpeta_semanas=carpeta, para_web=True)
    por_fecha = {d["fecha"]: d for d in gen["dias"]}
    hoja = copy.deepcopy(real)
    for dia in hoja["dias"]:
        g = por_fecha.get(dia["fecha"])
        if not g:
            continue
        if "adecuados" in g:
            dia["adecuados"] = copy.deepcopy(g["adecuados"])
        if "opciones" not in g:
            continue
        opciones = copy.deepcopy(g["opciones"])
        formulario = (dia.get("eucaristia") or {}).get("formulario")
        idx = next((i for i, o in enumerate(opciones) if (o.get("eucaristia") or {}).get("formulario") == formulario), 0)
        for k in CAMPOS_VARIANTE:
            opciones[idx].pop(k, None)
            if k in dia:
                opciones[idx][k] = copy.deepcopy(dia[k])
        dia["opciones"], dia["opcion"] = opciones, idx
    hoja["notas"] = [n for n in hoja.get("notas", []) if "memoria libre opcional" not in n]
    return hoja


def semanas(n: int, desde: date) -> dict[str, dict]:
    cfg = cargar_config()
    out: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for p in sorted((RAIZ / "semanas").glob("*.yaml")):  # revisadas a mano: historial y prioridad
            shutil.copy(p, tmp / p.name)
        for p in sorted((RAIZ / "semanas").glob("*.yaml")):
            out[p.stem] = injertar_opciones(cargar_hoja(p), cfg, tmp)
        for i in range(n):
            d = domingo_de(desde) + timedelta(weeks=i)
            if d.isoformat() in out:
                continue
            hoja = generar_borrador(d, cfg, carpeta_semanas=tmp, para_web=True)
            guardar_borrador(hoja, tmp / f"{d.isoformat()}.yaml")  # para el historial de la siguiente
            out[d.isoformat()] = hoja
    return dict(sorted(out.items()))


def construir(salida: Path, n: int, desde: date) -> None:
    if salida.exists():
        shutil.rmtree(salida)
    shutil.copytree(ORIGEN, salida)
    datos = {
        "generado": date.today().isoformat(),
        "semanas": semanas(n, desde),
        "cantos": [{"n": c.n, "titulo": c.titulo, "pagina": c.pagina, "subseccion": c.subseccion,
                    "momentos": c.momentos, "etiqueta": c.etiqueta_hoja()}
                   for c in sorted(catalogo().values(), key=lambda c: c.n) if not c.excluir],
        "himnos": OPCIONES_HIMNO,
        "css": css_de_la_hoja(),
    }
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, default=str), encoding="utf-8")
    (salida / ".nojekyll").touch()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--semanas", type=int, default=80)
    ap.add_argument("--salida", default=str(RAIZ / "sitio"))
    a = ap.parse_args()
    construir(Path(a.salida), a.semanas, date.today())
    print(f"Sitio en {a.salida}")
