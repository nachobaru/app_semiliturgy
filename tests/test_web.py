"""Interfaz web: crear, editar, vista previa y protección de rutas."""
import pytest

pytest.importorskip("flask")

from semiliturgy.hoja import cargar_hoja
from semiliturgy.web import crear_app


@pytest.fixture
def cliente(tmp_path):
    app = crear_app(tmp_path)
    return app.test_client(), tmp_path


def test_crear_editar_y_vista_previa(cliente):
    c, carpeta = cliente
    r = c.post("/crear", data={"fecha": "2026-11-18"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/semana/2026-11-15")
    assert (carpeta / "2026-11-15.yaml").exists()

    r = c.post("/semana/2026-11-15", data={
        "titulo": "Semana de prueba", "avisos": "Retiro el sábado",
        "d0.cantos.entrada": "17 · Juntos como hermanos", "d0.laudes.himno": "Eres la luz"})
    assert "Guardado" in r.get_data(as_text=True)
    hoja = cargar_hoja(carpeta / "2026-11-15.yaml")
    assert hoja["titulo"] == "Semana de prueba"
    assert hoja["avisos"] == "Retiro el sábado"
    assert hoja["dias"][0]["cantos"]["entrada"] == "17 · Juntos como hermanos"
    assert hoja["dias"][0]["laudes"]["himno"] == "Eres la luz"
    assert hoja["dias"][1]["eucaristia"]["prefacio"]  # lo no enviado se conserva

    r = c.get("/semana/2026-11-15/hoja")
    assert r.status_code == 200 and "Retiro el sábado" in r.get_data(as_text=True)


def test_abrir_semana_existente_no_pisa_cambios(cliente):
    c, carpeta = cliente
    c.post("/crear", data={"fecha": "2026-11-18"})
    c.post("/semana/2026-11-15", data={"avisos": "Mis avisos"})
    c.post("/crear", data={"fecha": "2026-11-18"})
    assert cargar_hoja(carpeta / "2026-11-15.yaml")["avisos"] == "Mis avisos"


def test_regenerar_deja_copia(cliente):
    c, carpeta = cliente
    c.post("/crear", data={"fecha": "2026-11-18"})
    c.post("/semana/2026-11-15", data={"avisos": "Mis avisos"})
    c.post("/crear", data={"fecha": "2026-11-15", "forzar": "1"})
    assert cargar_hoja(carpeta / "2026-11-15.yaml")["avisos"] != "Mis avisos"
    assert "Mis avisos" in (carpeta / "2026-11-15.yaml.bak").read_text(encoding="utf-8")


@pytest.mark.parametrize("ruta", ["/semana/..%2Fconfig/hoja", "/semana/abc", "/semana/2026-11-15"])
def test_rutas_invalidas_o_inexistentes(cliente, ruta):
    assert cliente[0].get(ruta).status_code == 404


def test_fecha_invalida(cliente):
    r = cliente[0].post("/crear", data={"fecha": "no"})
    assert r.status_code == 302 and "error=" in r.headers["Location"]
