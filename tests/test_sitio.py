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
    sitio = d["semanas"]["2026-11-22"]
    for dia in sitio["dias"]:   # salvo las opciones añadidas, la hoja revisada queda intacta
        dia.pop("opciones", None), dia.pop("opcion", None)
    sitio["notas"] = real["notas"]
    assert sitio == real


def test_semana_revisada_recibe_opciones(tmp_path):
    construir(tmp_path / "sitio", 3, date(2026, 11, 25))
    d = json.loads((tmp_path / "sitio" / "datos.json").read_text(encoding="utf-8"))
    lunes = next(x for x in d["semanas"]["2026-11-22"]["dias"] if x["dia"] == "LUNES")
    assert [o["tipo"] for o in lunes["opciones"]] == ["Del día", "Memoria libre"] and lunes["opcion"] == 0
    assert lunes["opciones"][0]["cantos"] == lunes["cantos"]      # la variante activa es lo revisado a mano


def test_dias_con_memoria_libre_traen_opciones(tmp_path):
    from semiliturgy.borrador import generar_borrador
    h = generar_borrador(date(2026, 11, 22), carpeta_semanas=tmp_path, con_opciones=True)
    lunes = next(d for d in h["dias"] if d["dia"] == "LUNES")
    assert [o["tipo"] for o in lunes["opciones"]] == ["Del día", "Memoria libre"]
    feria, memoria = lunes["opciones"]
    assert lunes["opcion"] == 0 and lunes["celebracion"] == feria["celebracion"] == "FERIA"
    assert memoria["etiqueta"].startswith("San Clemente") and memoria["color"] == "rojo"
    assert memoria["eucaristia"]["formulario"] != feria["eucaristia"]["formulario"]
    assert memoria["eucaristia"]["prefacio"].startswith("Mártires")
    assert "opciones" not in next(d for d in h["dias"] if d["dia"] == "MARTES")


def test_sin_opciones_el_borrador_no_cambia(tmp_path):
    from semiliturgy.borrador import generar_borrador
    base = generar_borrador(date(2026, 11, 22), carpeta_semanas=tmp_path)
    con = generar_borrador(date(2026, 11, 22), carpeta_semanas=tmp_path, con_opciones=True)
    for a, b in zip(base["dias"], con["dias"]):
        assert a == {k: v for k, v in b.items() if k not in ("opciones", "opcion")}
    assert any("memoria libre" in n for n in base["notas"]) and not con["notas"]
