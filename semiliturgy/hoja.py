"""Renderiza la hoja de liturgia (YAML del borrador) a HTML y PDF."""
from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from .cantos import NUM_CANTO

PLANTILLAS = Path(__file__).resolve().parent / "plantillas"


def _filtro_canto(texto: str) -> Markup:
    """'11 · Alabad siervos de Dios (L. Deiss)' -> 'Alabad siervos de Dios (L. Deiss) <n.º 11>'."""
    m = NUM_CANTO.match(texto or "")
    if not m:
        return escape(texto)
    titulo = texto[m.end():].strip()
    return Markup(f'{escape(titulo)} <span class="n">(n.º {m.group(1)})</span>')


def render_html(hoja: dict) -> str:
    env = Environment(loader=FileSystemLoader(PLANTILLAS), autoescape=select_autoescape(["html"]))
    env.filters["canto"] = _filtro_canto
    return env.get_template("hoja.html").render(hoja=hoja)


def cargar_hoja(ruta: Path) -> dict:
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def exportar(ruta_yaml: Path, salida: Path | None = None, pdf: bool = True) -> list[Path]:
    hoja = cargar_hoja(ruta_yaml)
    html = render_html(hoja)
    base = salida or ruta_yaml.with_suffix("")
    html_path = base.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    out = [html_path]
    if pdf:
        from weasyprint import HTML  # import diferido: es pesado y opcional
        pdf_path = base.with_suffix(".pdf")
        HTML(string=html, base_url=str(PLANTILLAS)).write_pdf(pdf_path)
        out.append(pdf_path)
    return out
