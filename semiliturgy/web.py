"""Interfaz web para revisar el borrador semanal y generar la hoja.

    python -m semiliturgy web            # http://127.0.0.1:5000

Está pensada para uso local del encargado de liturgia: sin usuarios ni contraseñas,
por eso escucha solo en 127.0.0.1 salvo que se indique otra cosa con --host.
Los YAML de `semanas/` siguen siendo la fuente de verdad (y el historial de cantos).
"""
from __future__ import annotations

import re
import shutil
from datetime import date
from io import BytesIO
from pathlib import Path

from flask import Flask, Response, abort, redirect, render_template, request, send_file, url_for

from .borrador import OPCIONES_HIMNO, RAIZ, generar_borrador, guardar_borrador
from .calendario import domingo_de
from .cantos import catalogo
from .hoja import cargar_hoja, render_html

ID_SEMANA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MOMENTOS_CANTO = ["entrada", "ofertorio", "comunion"]
ETIQUETAS = {
    "laudes": "Laudes", "eucaristia": "Eucaristía", "visperas": "Vísperas", "cantos": "Cantos",
    "de": "De", "himno": "Himno", "salmodia": "Salmodia", "benedictus": "Benedictus",
    "magnificat": "Magnificat", "formulario": "Formulario", "prefacio": "Prefacio",
    "entrada": "Entrada", "ofertorio": "Ofertorio", "comunion": "Comunión",
}
SECCIONES = ["laudes", "eucaristia", "cantos", "visperas"]


def ruta_semana(semana: str, carpeta: Path) -> Path:
    """Valida el identificador (evita rutas tipo ../) y devuelve el YAML de esa semana."""
    if not ID_SEMANA.match(semana):
        abort(404)
    return carpeta / f"{semana}.yaml"


def aplicar_formulario(hoja: dict, form) -> dict:
    """Vuelca en `hoja` los campos del formulario, conservando lo que el formulario no toca.

    Campos: `titulo`, `avisos`, `d<i>.celebracion` y `d<i>.<seccion>.<clave>`.
    """
    for clave in ("titulo", "avisos"):
        if clave in form:
            hoja[clave] = form[clave].strip() if clave == "titulo" else form[clave].replace("\r\n", "\n").strip()
    for i, dia in enumerate(hoja["dias"]):
        if f"d{i}.celebracion" in form:
            dia["celebracion"] = form[f"d{i}.celebracion"].strip()
        for sec in SECCIONES:
            bloque = dia.get(sec)
            claves = list(bloque) if isinstance(bloque, dict) else []
            if sec == "cantos":
                claves = list(dict.fromkeys(claves + MOMENTOS_CANTO))
            for k in claves:
                campo = f"d{i}.{sec}.{k}"
                if campo in form:
                    dia.setdefault(sec, {})[k] = form[campo].strip()
    return hoja


def lista_semanas(carpeta: Path) -> list[dict]:
    out = []
    for p in sorted(carpeta.glob("*.yaml"), reverse=True):
        if not ID_SEMANA.match(p.stem):
            continue
        try:
            titulo = (cargar_hoja(p) or {}).get("titulo", "")
        except Exception:  # YAML roto a mano: se lista igualmente para poder abrirlo
            titulo = "(YAML ilegible)"
        out.append({"id": p.stem, "titulo": titulo})
    return out


def crear_app(carpeta: Path | None = None) -> Flask:
    carpeta = Path(carpeta) if carpeta else RAIZ / "semanas"
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "plantillas_web"))

    @app.get("/")
    def index():
        return render_template("index.html", semanas=lista_semanas(carpeta),
                               hoy=date.today().isoformat(), error=request.args.get("error"))

    @app.post("/crear")
    def crear():
        try:
            f = date.fromisoformat(request.form["fecha"])
        except (KeyError, ValueError):
            return redirect(url_for("index", error="Fecha no válida."))
        semana = domingo_de(f).isoformat()
        ruta = ruta_semana(semana, carpeta)
        regenerar = request.form.get("forzar") == "1"
        if not ruta.exists() or regenerar:
            if ruta.exists():  # copia de seguridad: regenerar descarta las ediciones
                shutil.copy(ruta, ruta.with_suffix(".yaml.bak"))
            guardar_borrador(generar_borrador(f, carpeta_semanas=carpeta), ruta)
        return redirect(url_for("editar", semana=semana))

    @app.route("/semana/<semana>", methods=["GET", "POST"])
    def editar(semana):
        ruta = ruta_semana(semana, carpeta)
        if not ruta.exists():
            abort(404)
        hoja = cargar_hoja(ruta)
        guardado = False
        if request.method == "POST":
            aplicar_formulario(hoja, request.form)
            guardar_borrador(hoja, ruta)
            guardado = True
        cantos = [c.etiqueta_hoja() for c in sorted(catalogo().values(), key=lambda c: c.n) if not c.excluir]
        himnos = OPCIONES_HIMNO
        return render_template("editar.html", semana=semana, hoja=hoja, guardado=guardado,
                               cantos=cantos, himnos=himnos, etiquetas=ETIQUETAS,
                               momentos=MOMENTOS_CANTO, secciones=SECCIONES)

    @app.get("/semana/<semana>/hoja")
    def vista_hoja(semana):
        ruta = ruta_semana(semana, carpeta)
        if not ruta.exists():
            abort(404)
        return Response(render_html(cargar_hoja(ruta)), mimetype="text/html")

    @app.get("/semana/<semana>/hoja.pdf")
    def pdf(semana):
        ruta = ruta_semana(semana, carpeta)
        if not ruta.exists():
            abort(404)
        try:
            from weasyprint import HTML
        except (ImportError, OSError):
            return Response("WeasyPrint no está disponible: instala sus dependencias para generar el PDF.",
                            status=503)
        from .hoja import PLANTILLAS
        buf = BytesIO()
        HTML(string=render_html(cargar_hoja(ruta)), base_url=str(PLANTILLAS)).write_pdf(buf)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf", download_name=f"hoja-liturgia-{semana}.pdf")

    return app
