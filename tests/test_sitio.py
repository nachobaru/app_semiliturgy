"""Sitio estático: datos pregenerados coherentes y semanas revisadas a mano respetadas."""
import json
from datetime import date

from scripts.generar_sitio import construir


def test_construir_sitio(tmp_path):
    construir(tmp_path / "sitio", 6, date(2026, 11, 25))
    d = json.loads((tmp_path / "sitio" / "datos.json").read_text(encoding="utf-8"))
    assert (tmp_path / "sitio" / "index.html").exists() and (tmp_path / "sitio" / ".nojekyll").exists()
    assert "2026-11-22" in d["semanas"] and "2026-12-27" in d["semanas"]
    assert all(len(h["dias"]) == 6 for h in d["semanas"].values())
    assert d["cantos"] and "table.hoja" in d["css"]


def test_respeta_semanas_revisadas(tmp_path):
    construir(tmp_path / "sitio", 3, date(2026, 11, 25))
    d = json.loads((tmp_path / "sitio" / "datos.json").read_text(encoding="utf-8"))
    real = (__import__("yaml").safe_load(open("semanas/2026-11-22.yaml", encoding="utf-8")))
    assert d["semanas"]["2026-11-22"] == real
