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
    assert d["cantos"] and ".cuerpo-hoja" in d["css"]


def test_respeta_semanas_revisadas(tmp_path):
    construir(tmp_path / "sitio", 3, date(2026, 11, 25))
    d = json.loads((tmp_path / "sitio" / "datos.json").read_text(encoding="utf-8"))
    real = (__import__("yaml").safe_load(open("semanas/2026-11-22.yaml", encoding="utf-8")))
    sitio = d["semanas"]["2026-11-22"]
    for dia in sitio["dias"]:   # salvo las opciones añadidas, la hoja revisada queda intacta
        dia.pop("opciones", None), dia.pop("opcion", None), dia.pop("adecuados", None)
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
    h = generar_borrador(date(2026, 11, 22), carpeta_semanas=tmp_path, para_web=True)
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
    con = generar_borrador(date(2026, 11, 22), carpeta_semanas=tmp_path, para_web=True)
    for a, b in zip(base["dias"], con["dias"]):
        assert a == {k: v for k, v in b.items() if k not in ("opciones", "opcion", "adecuados")}
    assert any("memoria libre" in n for n in base["notas"]) and not con["notas"]


def _web(fecha, tmp_path):
    from semiliturgy.borrador import generar_borrador
    return generar_borrador(fecha, carpeta_semanas=tmp_path, para_web=True)


def test_adecuados_por_momento_y_tiempo(tmp_path):
    from semiliturgy.cantos import catalogo, numero_de
    cat = catalogo()
    h = _web(date(2026, 12, 1), tmp_path)                       # I semana de Adviento
    for dia in h["dias"]:
        for momento, nums in dia["adecuados"].items():
            assert nums, f"{dia['dia']} {momento} sin adecuados"
            assert all(momento in cat[n].momentos for n in nums)
            assert not any("pascua" in cat[n].etiquetas or "cuaresma" in cat[n].etiquetas for n in nums)
            propuesto = numero_de(dia["cantos"][momento])
            assert propuesto is None or propuesto in nums          # lo propuesto está entre los adecuados


def test_adecuados_de_una_memoria_son_otros(tmp_path):
    from semiliturgy.cantos import catalogo
    sabado = next(d for d in _web(date(2026, 12, 12), tmp_path)["dias"] if d["fecha"] == "2026-12-12")
    feria, guadalupe = sabado["opciones"]
    assert feria["adecuados"] == sabado["adecuados"]
    primero = guadalupe["adecuados"]["entrada"][0]                     # los marianos, delante
    assert "virgen" in catalogo()[primero].etiquetas
    assert guadalupe["adecuados"]["entrada"] != feria["adecuados"]["entrada"]


def test_adecuados_excluyen_los_recientes(tmp_path):
    from semiliturgy.borrador import guardar_borrador
    from semiliturgy.cantos import numero_de
    anterior = _web(date(2026, 11, 22), tmp_path)
    guardar_borrador(anterior, tmp_path / "2026-11-22.yaml")
    usados = {numero_de(v) for d in anterior["dias"] for v in d["cantos"].values()} - {None}
    h = _web(date(2026, 11, 29), tmp_path)
    assert not usados & {n for d in h["dias"] for ns in d["adecuados"].values() for n in ns}


def test_sitio_publica_el_catalogo_con_pagina(tmp_path):
    construir(tmp_path / "sitio", 2, date(2026, 11, 25))
    d = json.loads((tmp_path / "sitio" / "datos.json").read_text(encoding="utf-8"))
    c = d["cantos"][0]
    assert set(c) == {"n", "titulo", "pagina", "subseccion", "momentos", "etiqueta"}
    lunes = next(x for x in d["semanas"]["2026-11-22"]["dias"] if x["dia"] == "LUNES")
    assert lunes["adecuados"]["entrada"] and "adecuados" in lunes["opciones"][1]


def test_sitio_exporta_css_y_ajuste_de_la_hoja(tmp_path):
    construir(tmp_path / "sitio", 1, date(2026, 11, 25))
    d = json.loads((tmp_path / "sitio" / "datos.json").read_text(encoding="utf-8"))
    assert "@page" in d["css"] and "data-color" in d["css"]
    assert "scrollHeight" in d["ajuste"] and "<script>" not in d["ajuste"]
    assert (tmp_path / "sitio" / "hoja.js").exists()
