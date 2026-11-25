"""Comprobaciones contra la hoja real de la semana XXXIII (15-21 nov 2026)."""
from datetime import date

from semiliturgy.borrador import cargar_config, generar_borrador
from semiliturgy.hoja import render_html


def _hoja(fecha, tmp_path):
    return generar_borrador(fecha, cargar_config(), carpeta_semanas=tmp_path)


def _dia(hoja, iso):
    return next(d for d in hoja["dias"] if d["fecha"] == iso)


def test_cabecera_semana_xxxiii(tmp_path):
    h = _hoja(date(2026, 11, 18), tmp_path)
    assert h["titulo"] == "Semana del 15 al 21 de noviembre"
    assert h["salterio"] == "I"
    assert h["tiempo"] == "Ordinario"


def test_feria_como_en_la_hoja_real(tmp_path):
    d = _dia(_hoja(date(2026, 11, 18), tmp_path), "2026-11-19")   # jueves
    assert d["celebracion"] == "FERIA"
    assert d["laudes"]["salmodia"] == "Feria"
    assert d["laudes"]["benedictus"] == "Feria"
    assert d["eucaristia"]["formulario"] == "Domingo XXXIII del tiempo ordinario"
    assert d["eucaristia"]["prefacio"].startswith("Común")
    assert d["visperas"]["magnificat"] == "Feria"


def test_memoria_de_la_virgen(tmp_path):
    d = _dia(_hoja(date(2026, 11, 18), tmp_path), "2026-11-21")   # sábado
    assert d["celebracion"] == "PRESENTACIÓN DE LA BIENAVENTURADA VIRGEN MARÍA"
    assert d["laudes"]["salmodia"] == "Feria"
    assert d["laudes"]["benedictus"] == "Feria"
    assert d["eucaristia"]["prefacio"].startswith("Santa María Virgen")


def test_sabado_tiene_primeras_visperas_del_domingo(tmp_path):
    d = _dia(_hoja(date(2026, 11, 23), tmp_path), "2026-11-28")
    assert d["visperas"]["de"] == "Domingo I de Adviento"


def test_prefacios_comunes_no_se_repiten_en_la_semana(tmp_path):
    h = _hoja(date(2026, 11, 23), tmp_path)
    comunes = [d["eucaristia"]["prefacio"] for d in h["dias"] if d["eucaristia"]["prefacio"].startswith("Común")]
    assert len(comunes) == len(set(comunes))


def test_cantos_no_se_repiten_y_existen(tmp_path):
    h = _hoja(date(2026, 11, 23), tmp_path)
    cantos = [c for d in h["dias"] for c in d["cantos"].values()]
    assert all(cantos)
    assert len(cantos) == len(set(cantos))


def test_render_html(tmp_path):
    html = render_html(_hoja(date(2026, 11, 18), tmp_path))
    assert "HOJA LITURGIA" in html and "SEMANA DE SALTERIO: I" in html


def test_himno_sin_titulo_segun_la_celebracion(tmp_path):
    h = _hoja(date(2026, 11, 18), tmp_path)
    jueves = _dia(h, "2026-11-19")                         # feria
    assert jueves["laudes"]["himno"] == jueves["visperas"]["himno"] == "Feria"
    sabado = _dia(h, "2026-11-21")                         # memoria de la Virgen
    assert sabado["laudes"]["himno"] == "Del común de santa María Virgen"


def test_himno_de_fiestas_y_solemnidades(tmp_path):
    fiesta = _dia(generar_borrador(date(2027, 1, 25), cargar_config(), carpeta_semanas=tmp_path), "2027-01-25")
    assert fiesta["laudes"]["himno"] == "Del común de apóstoles"       # Conversión de san Pablo
    solemne = _dia(generar_borrador(date(2026, 12, 8), cargar_config(), carpeta_semanas=tmp_path), "2026-12-08")
    assert solemne["laudes"]["himno"] == "Propio"                      # Inmaculada
