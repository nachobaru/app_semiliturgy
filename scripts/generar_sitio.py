"""Genera el sitio estático (GitHub Pages) en `sitio/`.

    python scripts/generar_sitio.py [--semanas 80] [--salida sitio]

Las reglas litúrgicas siguen en Python: aquí se pregeneran los borradores de las próximas
semanas (encadenados, para que los cantos no se repitan entre semanas consecutivas) y se
guardan en `datos.json`. La página (`sitio_src/`) solo edita y maqueta en el navegador.
Las semanas que ya existen en `semanas/*.yaml` (revisadas a mano) se respetan tal cual.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from semiliturgy.borrador import RAIZ, cargar_config, cargar_himnos, generar_borrador, guardar_borrador  # noqa: E402
from semiliturgy.calendario import domingo_de  # noqa: E402
from semiliturgy.cantos import catalogo  # noqa: E402
from semiliturgy.hoja import PLANTILLAS, cargar_hoja  # noqa: E402

ORIGEN = RAIZ / "sitio_src"


def css_de_la_hoja() -> str:
    """El CSS de la hoja se toma de la plantilla de Python: una sola fuente de verdad."""
    html = (PLANTILLAS / "hoja.html").read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", html, re.S).group(1).strip()


def semanas(n: int, desde: date) -> dict[str, dict]:
    cfg = cargar_config()
    out: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for p in sorted((RAIZ / "semanas").glob("*.yaml")):  # revisadas a mano: historial y prioridad
            shutil.copy(p, tmp / p.name)
            out[p.stem] = cargar_hoja(p)
        for i in range(n):
            d = domingo_de(desde) + timedelta(weeks=i)
            if d.isoformat() in out:
                continue
            hoja = generar_borrador(d, cfg, carpeta_semanas=tmp)
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
        "cantos": [c.etiqueta_hoja() for c in sorted(catalogo().values(), key=lambda c: c.n) if not c.excluir],
        "himnos": sorted({h["titulo"] for h in cargar_himnos() if isinstance(h, dict) and "titulo" in h}),
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
