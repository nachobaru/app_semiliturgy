from datetime import date

import pytest

from semiliturgy.calendario import (adviento1, bautismo, ciclo_dominical, ciclo_ferial,
                                    dia_liturgico, pascua, tiempo_de)


@pytest.mark.parametrize("año,esperado", [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)),
                                          (2026, date(2026, 4, 5)), (2027, date(2027, 3, 28)),
                                          (2028, date(2028, 4, 16))])
def test_pascua(año, esperado):
    assert pascua(año) == esperado


def test_adviento_y_bautismo():
    assert adviento1(2025) == date(2025, 11, 30)
    assert adviento1(2026) == date(2026, 11, 29)
    assert bautismo(2026) == date(2026, 1, 11)


@pytest.mark.parametrize("fecha,tiempo,semana,salterio", [
    ("2026-11-18", "ordinario", 33, 1),     # hoja real de la semana XXXIII: salterio I
    ("2026-11-23", "ordinario", 34, 2),
    ("2026-11-29", "adviento", 1, 1),
    ("2026-01-12", "ordinario", 1, 1),
    ("2026-02-19", "cuaresma", 0, 4),
    ("2026-02-23", "cuaresma", 1, 1),
    ("2026-04-13", "pascua", 2, 2),
    ("2026-05-25", "ordinario", 8, 4),
])
def test_tiempos(fecha, tiempo, semana, salterio):
    t = tiempo_de(date.fromisoformat(fecha))
    assert (t.nombre, t.semana, t.salterio) == (tiempo, semana, salterio)


def test_ciclos():
    assert ciclo_dominical(date(2026, 11, 22)) == "A"
    assert ciclo_ferial(date(2026, 11, 22)) == "II"
    assert ciclo_dominical(date(2026, 11, 29)) == "B"
    assert ciclo_ferial(date(2026, 11, 29)) == "I"


@pytest.mark.parametrize("fecha,nombre,grado", [
    ("2026-11-18", "Miércoles de la XXXIII semana del tiempo ordinario", "feria"),
    ("2026-11-21", "Presentación de la Bienaventurada Virgen María", "memoria"),
    ("2026-11-22", "Jesucristo, Rey del Universo", "solemnidad"),
    ("2026-12-08", "Inmaculada Concepción de la Virgen María", "solemnidad"),
    ("2026-02-18", "Miércoles de Ceniza", "feria"),
    ("2026-05-17", "Ascensión del Señor", "solemnidad"),          # trasladada al domingo en España
    ("2026-05-28", "Jesucristo, Sumo y Eterno Sacerdote", "fiesta"),
    ("2026-06-07", "Santísimo Cuerpo y Sangre de Cristo", "solemnidad"),
    ("2026-08-06", "Transfiguración del Señor", "fiesta"),         # fiesta del Señor en día de semana
    ("2026-11-09", "Dedicación de la basílica de Letrán", "fiesta"),
])
def test_celebraciones(fecha, nombre, grado):
    c = dia_liturgico(date.fromisoformat(fecha)).celebracion
    assert (c.nombre, c.grado) == (nombre, grado)


def test_domingo_to_prevalece_sobre_fiesta_de_santo():
    # 2026-10-18 (San Lucas) cae en domingo: gana el domingo XXIX
    assert dia_liturgico(date(2026, 10, 18)).celebracion.grado == "domingo"


def test_memoria_libre_no_sustituye_a_la_feria():
    d = dia_liturgico(date(2026, 11, 25))
    assert d.celebracion.grado == "feria"
    assert "Catalina" in d.memorias_libres[0].nombre


def test_memoria_en_cuaresma_es_conmemoracion():
    d = dia_liturgico(date(2027, 3, 7))   # Perpetua y Felicidad, domingo III de Cuaresma 2027
    assert d.celebracion.grado == "domingo"
    d = dia_liturgico(date(2026, 3, 7))   # sábado de la II semana de Cuaresma
    assert d.celebracion.grado == "feria"
    assert d.conmemoraciones and "Perpetua" in d.conmemoraciones[0].nombre


def test_memorias_libres_de_juan_diego_y_raimundo():
    from datetime import date
    from semiliturgy.calendario import dia_liturgico
    for f, nombre in [(date(2026, 12, 9), "San Juan Diego"), (date(2027, 1, 7), "San Raimundo de Peñafort")]:
        d = dia_liturgico(f)
        assert d.celebracion.grado == "feria"                       # la feria sigue siendo lo del día
        assert any(c.nombre.startswith(nombre) for c in d.memorias_libres)


def test_santa_maria_en_sabado():
    from datetime import date
    from semiliturgy.calendario import dia_liturgico
    nombres = lambda f: [c.nombre for c in dia_liturgico(f).memorias_libres]
    assert "Santa María en sábado" in nombres(date(2026, 11, 28))        # sábado del T. O., feria
    assert "Santa María en sábado" not in nombres(date(2026, 11, 21))    # Presentación: memoria obligatoria
    assert "Santa María en sábado" not in nombres(date(2026, 12, 5))     # Adviento
    assert "Santa María en sábado" not in nombres(date(2026, 11, 27))    # viernes
    assert dia_liturgico(date(2026, 11, 28)).celebracion.grado == "feria"  # sigue siendo opción, no lo del día
