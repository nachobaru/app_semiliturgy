"""Motor del calendario litúrgico (rito romano, calendario de España).

Calcula para cualquier fecha: tiempo litúrgico, semana, semana del salterio,
ciclos de lecturas y la celebración que corresponde según la tabla de
precedencias de las Normas Universales del Año Litúrgico (NUALC 59-61),
en versión simplificada (ver `RANGOS`).

Particularidades de España que se aplican:
  * Epifanía siempre el 6 de enero; Bautismo del Señor el domingo siguiente.
  * Ascensión trasladada al domingo VII de Pascua.
  * Corpus Christi trasladado al domingo siguiente a la Santísima Trinidad.
  * Jesucristo, Sumo y Eterno Sacerdote: jueves después de Pentecostés (fiesta).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Rango de precedencia: cuanto más bajo, más importante (NUALC 59, simplificado).
RANGOS = {
    "triduo": 1,
    "privilegiado": 2,         # Navidad, Epifanía, Ascensión, Pentecostés, domingos de Adv/Cua/Pas, Ceniza, Semana Santa, octava de Pascua
    "solemnidad": 3,
    "solemnidad_propia": 4,
    "fiesta_señor": 5,
    "domingo": 6,              # domingos de Navidad y del T.O.
    "fiesta": 7,
    "fiesta_propia": 8,
    "feria_privilegiada": 9,   # Adviento 17-24, octava de Navidad, ferias de Cuaresma
    "memoria": 10,
    "memoria_propia": 11,
    "memoria_libre": 12,
    "feria": 13,
}


def romano(n: int) -> str:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


# ---------------------------------------------------------------- fechas base

@lru_cache(maxsize=None)
def pascua(año: int) -> date:
    """Domingo de Pascua (algoritmo anónimo gregoriano / Meeus)."""
    a = año % 19
    b, c = divmod(año, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(año, mes, dia + 1)


def domingo_de(d: date) -> date:
    """Domingo con el que empieza la semana de `d` (el mismo día si es domingo)."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


@lru_cache(maxsize=None)
def adviento1(año: int) -> date:
    navidad = date(año, 12, 25)
    adv4 = navidad - timedelta(days=(navidad.weekday() + 1) % 7 or 7)
    return adv4 - timedelta(weeks=3)


@lru_cache(maxsize=None)
def bautismo(año: int) -> date:
    """Domingo después del 6 de enero (en España la Epifanía no se traslada)."""
    epi = date(año, 1, 6)
    return epi + timedelta(days=(6 - epi.weekday()) or 7)


@lru_cache(maxsize=None)
def sagrada_familia(año: int) -> date:
    """Domingo dentro de la octava de Navidad; si no lo hay, 30 de diciembre."""
    for dia in range(26, 32):
        d = date(año, 12, dia)
        if d.weekday() == 6:
            return d
    return date(año, 12, 30)


def año_liturgico(d: date) -> int:
    """Año litúrgico que *termina* en el año civil devuelto (el que empieza en Adviento del anterior)."""
    return d.year + 1 if d >= adviento1(d.year) else d.year


def ciclo_dominical(d: date) -> str:
    return {1: "A", 2: "B", 0: "C"}[año_liturgico(d) % 3]


def ciclo_ferial(d: date) -> str:
    return "I" if año_liturgico(d) % 2 else "II"


# ---------------------------------------------------------------- tiempos

@dataclass
class Tiempo:
    nombre: str        # adviento | navidad | ordinario | cuaresma | semana_santa | triduo | pascua
    semana: int        # semana dentro del tiempo (0 = días después de Ceniza)
    salterio: int      # 1..4


def tiempo_de(d: date) -> Tiempo:
    y = d.year
    p = pascua(y)
    ceniza = p - timedelta(days=46)
    ramos = p - timedelta(days=7)
    jueves_santo = p - timedelta(days=3)
    pentecostes = p + timedelta(days=49)
    adv1 = adviento1(y)

    def sal(n: int) -> int:
        return (n - 1) % 4 + 1

    if adv1 <= d < date(y, 12, 25):
        s = (d - adv1).days // 7 + 1
        return Tiempo("adviento", s, sal(s))
    if d >= date(y, 12, 25) or d <= bautismo(y):
        anio_nav = y if d.month == 12 else y - 1
        inicio = domingo_de(sagrada_familia(anio_nav))
        s = max(0, (domingo_de(d) - inicio).days // 7)
        return Tiempo("navidad", s + 1, s % 4 + 1)
    if d < ceniza:
        s = (domingo_de(d) - bautismo(y)).days // 7 + 1
        return Tiempo("ordinario", s, sal(s))
    if d < ramos:
        if d < ceniza + timedelta(days=4):
            return Tiempo("cuaresma", 0, 4)
        s = (domingo_de(d) - (ceniza + timedelta(days=4))).days // 7 + 1
        return Tiempo("cuaresma", s, sal(s))
    if d < jueves_santo:
        return Tiempo("semana_santa", 6, 2)
    if d < p:
        return Tiempo("triduo", 6, 2)
    if d <= pentecostes:
        s = (domingo_de(d) - p).days // 7 + 1
        return Tiempo("pascua", s, sal(s))
    s = 34 - (adv1 - domingo_de(d)).days // 7 + 1
    return Tiempo("ordinario", s, sal(s))


# ---------------------------------------------------------------- celebraciones

@dataclass
class Celebracion:
    nombre: str
    grado: str                    # solemnidad | fiesta | memoria | memoria_libre | domingo | feria
    rango: int
    color: str
    prefacio: str | None = None   # prefacio propio, si lo hay
    comun: str | None = None
    ambito: str = "universal"
    verificar: bool = False
    señor: bool = False


@dataclass
class DiaLiturgico:
    fecha: date
    tiempo: Tiempo
    celebracion: Celebracion
    feria: Celebracion                         # la celebración temporal del día (domingo o feria)
    conmemoraciones: list[Celebracion] = field(default_factory=list)
    memorias_libres: list[Celebracion] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def ciclo_dominical(self) -> str:
        return ciclo_dominical(self.fecha)

    @property
    def ciclo_ferial(self) -> str:
        return ciclo_ferial(self.fecha)

    @property
    def es_domingo(self) -> bool:
        return self.fecha.weekday() == 6

    @property
    def grado(self) -> str:
        return self.celebracion.grado


COLOR_TIEMPO = {"adviento": "morado", "navidad": "blanco", "ordinario": "verde",
                "cuaresma": "morado", "semana_santa": "morado", "triduo": "blanco",
                "pascua": "blanco"}

NOMBRE_TIEMPO = {"adviento": "de Adviento", "navidad": "de Navidad",
                 "ordinario": "del tiempo ordinario", "cuaresma": "de Cuaresma",
                 "pascua": "de Pascua"}


def _temporal(d: date, t: Tiempo) -> Celebracion:
    """Domingo o feria del tiempo, sin santoral ni fiestas movibles."""
    dia = DIAS[d.weekday()]
    color = COLOR_TIEMPO[t.nombre]
    if t.nombre == "semana_santa":
        nombre = "Domingo de Ramos en la Pasión del Señor" if d.weekday() == 6 else f"{dia} Santo"
        return Celebracion(nombre, "domingo" if d.weekday() == 6 else "feria", RANGOS["privilegiado"],
                           "rojo" if d.weekday() == 6 else "morado")
    if t.nombre == "triduo":
        nombre = {3: "Jueves Santo de la Cena del Señor", 4: "Viernes Santo de la Pasión del Señor",
                  5: "Sábado Santo"}[d.weekday()]
        return Celebracion(nombre, "triduo", RANGOS["triduo"], "rojo" if d.weekday() == 4 else "blanco")
    if t.nombre == "navidad":
        if d.month == 12 and 25 < d.day <= 31:
            return Celebracion(f"Día {d.day - 24}.º de la Octava de Navidad", "feria",
                               RANGOS["feria_privilegiada"], color)
        if d.weekday() == 6:
            return Celebracion("Domingo II después de Navidad", "domingo", RANGOS["domingo"], color)
        return Celebracion(f"{d.day} de {MESES[d.month - 1]} (tiempo de Navidad)", "feria", RANGOS["feria"], color)

    nt = NOMBRE_TIEMPO[t.nombre]
    if d.weekday() == 6:
        rango = RANGOS["domingo"] if t.nombre == "ordinario" else RANGOS["privilegiado"]
        return Celebracion(f"Domingo {romano(t.semana)} {nt}", "domingo", rango,
                           "rosa" if (t.nombre, t.semana) in {("adviento", 3), ("cuaresma", 4)} else color)

    if t.nombre == "adviento" and d.month == 12 and d.day >= 17:
        return Celebracion(f"Feria privilegiada de Adviento: {d.day} de diciembre", "feria",
                           RANGOS["feria_privilegiada"], color)
    if t.nombre == "cuaresma":
        if t.semana == 0:
            if d.weekday() == 2:
                return Celebracion("Miércoles de Ceniza", "feria", RANGOS["privilegiado"], color)
            return Celebracion(f"{dia} después de Ceniza", "feria", RANGOS["feria_privilegiada"], color)
        return Celebracion(f"{dia} de la {romano(t.semana)} semana de Cuaresma", "feria",
                           RANGOS["feria_privilegiada"], color)
    if t.nombre == "pascua" and t.semana == 1:
        return Celebracion(f"{dia} de la Octava de Pascua", "feria", RANGOS["privilegiado"], color)
    return Celebracion(f"{dia} de la {romano(t.semana)} semana {nt}", "feria", RANGOS["feria"], color)


def _movibles(año: int) -> dict[date, Celebracion]:
    p = pascua(año)
    td = timedelta
    R = RANGOS
    m = {
        p: Celebracion("Domingo de Pascua de la Resurrección del Señor", "solemnidad", R["triduo"], "blanco", "Pascual I"),
        p + td(42): Celebracion("Ascensión del Señor", "solemnidad", R["privilegiado"], "blanco", "Ascensión I-II", señor=True),
        p + td(49): Celebracion("Domingo de Pentecostés", "solemnidad", R["privilegiado"], "rojo", "Propio"),
        p + td(50): Celebracion("Bienaventurada Virgen María, Madre de la Iglesia", "memoria", R["memoria"], "blanco", comun="virgen"),
        p + td(53): Celebracion("Jesucristo, Sumo y Eterno Sacerdote", "fiesta", R["fiesta_señor"], "blanco", "Propio", ambito="españa", señor=True),
        p + td(56): Celebracion("Santísima Trinidad", "solemnidad", R["solemnidad"], "blanco", "Propio", señor=True),
        p + td(63): Celebracion("Santísimo Cuerpo y Sangre de Cristo", "solemnidad", R["solemnidad"], "blanco", "Santísima Eucaristía I-II", señor=True),
        p + td(68): Celebracion("Sagrado Corazón de Jesús", "solemnidad", R["solemnidad"], "blanco", "Propio", señor=True),
        p + td(69): Celebracion("Inmaculado Corazón de la Virgen María", "memoria", R["memoria"], "blanco", comun="virgen"),
        adviento1(año) - td(7): Celebracion("Jesucristo, Rey del Universo", "solemnidad", R["solemnidad"], "blanco", "Propio", señor=True),
        bautismo(año): Celebracion("Bautismo del Señor", "fiesta", R["fiesta_señor"], "blanco", "Propio", señor=True),
        sagrada_familia(año): Celebracion("Sagrada Familia de Jesús, María y José", "fiesta", R["fiesta_señor"], "blanco", "Navidad I-III", señor=True),
    }
    return m


@lru_cache(maxsize=1)
def _santoral() -> dict[str, dict]:
    general = yaml.safe_load((DATA / "santoral.yaml").read_text(encoding="utf-8")) or {}
    propio_path = DATA / "calendario_propio.yaml"
    propio = yaml.safe_load(propio_path.read_text(encoding="utf-8")) if propio_path.exists() else {}
    general.update(propio or {})
    return general


def _celebracion_santoral(d: date) -> Celebracion | None:
    e = _santoral().get(d.strftime("%m-%d"))
    if not e:
        return None
    propia = e.get("ambito") == "oviedo"
    grado = e["grado"]
    clave = grado
    if grado == "solemnidad":
        clave = "solemnidad_propia" if propia else "solemnidad"
        if d.strftime("%m-%d") in {"12-25", "01-06"}:
            clave = "privilegiado"
    elif grado == "fiesta":
        clave = "fiesta_señor" if e.get("señor") else ("fiesta_propia" if propia else "fiesta")
    elif grado == "memoria" and propia:
        clave = "memoria_propia"
    return Celebracion(e["nombre"], grado, RANGOS[clave], e.get("color", "blanco"),
                       e.get("prefacio"), e.get("comun"), e.get("ambito", "universal"),
                       bool(e.get("verificar")), bool(e.get("señor")))


def dia_liturgico(d: date) -> DiaLiturgico:
    t = tiempo_de(d)
    feria = _temporal(d, t)
    candidatos = [feria]
    mov = _movibles(d.year).get(d)
    if mov:
        candidatos.append(mov)
    santo = _celebracion_santoral(d)
    if santo:
        candidatos.append(santo)

    candidatos.sort(key=lambda c: (c.rango, c is feria))
    ganador = candidatos[0]
    dia = DiaLiturgico(d, t, ganador, feria)

    for c in candidatos[1:]:
        if c.grado == "memoria_libre":
            if ganador.grado in ("feria",) and ganador.rango == RANGOS["feria"]:
                dia.memorias_libres.append(c)
            elif ganador.rango == RANGOS["feria_privilegiada"]:
                dia.conmemoraciones.append(c)
        elif c.grado == "memoria":
            if ganador.rango == RANGOS["feria_privilegiada"]:
                dia.conmemoraciones.append(c)
        elif c.grado == "solemnidad" and c is not feria:
            dia.avisos.append(f"La solemnidad «{c.nombre}» queda impedida: revisar traslado en la Epacta.")

    # Una memoria libre nunca sustituye sola a la feria: queda como opción.
    if ganador.grado == "memoria_libre":
        dia.celebracion = feria
        dia.memorias_libres.insert(0, ganador)
    # En ferias privilegiadas las memorias pasan a conmemoración.
    if ganador.grado in ("memoria",) and feria.rango == RANGOS["feria_privilegiada"]:
        dia.celebracion = feria
        dia.conmemoraciones.insert(0, ganador)

    if dia.celebracion.verificar:
        dia.avisos.append(f"«{dia.celebracion.nombre}» está pendiente de verificar con la Epacta.")
    return dia


def semana(domingo: date) -> list[DiaLiturgico]:
    """Los siete días (domingo a sábado) que empiezan en `domingo`."""
    inicio = domingo_de(domingo)
    return [dia_liturgico(inicio + timedelta(days=i)) for i in range(7)]
