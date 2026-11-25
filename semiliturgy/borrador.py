"""Reglas de la hoja de liturgia y generación del borrador semanal (YAML editable)."""
from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date, timedelta
from itertools import cycle
from pathlib import Path

import yaml

from .calendario import (DATA, MESES, DiaLiturgico, dia_liturgico, domingo_de, romano, semana)
from .cantos import Sugeridor, usados_recientemente

RAIZ = DATA.parent
CLAVES_DIA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
NOMBRE_DIA = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
TIEMPO_HOJA = {"adviento": "Adviento", "navidad": "Navidad", "ordinario": "Ordinario",
               "cuaresma": "Cuaresma", "semana_santa": "Semana Santa", "triduo": "Triduo Pascual",
               "pascua": "Pascua"}

PREFACIO_COMUN = {
    "virgen": ["Santa María Virgen I", "Santa María Virgen II"],
    "martires": ["Mártires I", "Mártires II"],
    "pastores": ["Santos pastores"],
    "doctores": ["Santos pastores"],
    "virgenes": ["Santas vírgenes y santos religiosos"],
    "santos": ["Santos I", "Santos II"],
    "apostoles": ["Apóstoles I", "Apóstoles II"],
}


def cargar_config(path: Path | None = None) -> dict:
    path = path or RAIZ / "config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def cargar_himnos() -> list[dict]:
    p = DATA / "himnos.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) or [] if p.exists() else []


class Rotador:
    """Reparte opciones de una lista sin repetir hasta agotarla."""

    def __init__(self, semilla: int = 0):
        self._ciclos: dict[tuple, cycle] = {}
        self.semilla = semilla

    def siguiente(self, opciones: list[str]) -> str:
        clave = tuple(opciones)
        if clave not in self._ciclos:
            desfase = self.semilla % len(opciones)
            self._ciclos[clave] = cycle(opciones[desfase:] + opciones[:desfase])
        return next(self._ciclos[clave])


# ---------------------------------------------------------------- reglas por campo

def es_grande(d: DiaLiturgico) -> bool:
    return d.grado in ("solemnidad", "fiesta", "triduo")


def salmodia(d: DiaLiturgico, hora: str) -> str:
    if d.grado == "triduo" or (d.tiempo.nombre == "pascua" and d.tiempo.semana == 1):
        return "Propia"
    if d.grado == "solemnidad":
        return "Domingo I" if hora == "laudes" else "Propia"
    if d.grado == "fiesta":
        return "Domingo I" if hora == "laudes" else "Del común"
    if d.es_domingo:
        return f"Domingo {romano(d.tiempo.salterio)}"
    return "Feria"


def antifona_evangelica(d: DiaLiturgico, cfg: dict) -> str:
    if es_grande(d) or d.es_domingo:
        return "Propia"
    if d.grado in ("memoria", "memoria_libre"):
        return cfg.get("antifonas_memoria", "Feria")
    if d.fecha.month == 12 and 17 <= d.fecha.day <= 24:
        return f"Propia del {d.fecha.day} de diciembre"
    if d.tiempo.nombre != "ordinario":
        return "Del tiempo"
    return "Feria"


def himno(d: DiaLiturgico, hora: str, himnos: list[dict], usados: set[str]) -> str:
    if es_grande(d):
        return "Propio"
    if d.tiempo.nombre in ("adviento", "navidad", "cuaresma", "semana_santa", "pascua") and not himnos:
        return "Del tiempo"
    etiquetas = {d.celebracion.comun} if d.grado in ("memoria", "memoria_libre") and d.celebracion.comun else set()
    tiempo = d.tiempo.nombre

    def encaja(h: dict, repetir: bool = False) -> bool:
        if hora not in h.get("horas", [hora]) or (h["titulo"] in usados and not repetir):
            return False
        if etiquetas:
            return bool(etiquetas & set(h.get("etiquetas", [])))
        return tiempo in h.get("tiempos", []) and not h.get("etiquetas")

    candidatos = [h for h in himnos if encaja(h)]
    if not candidatos and etiquetas:           # memoria sin himno propio en el catálogo: el del tiempo
        etiquetas = set()
        candidatos = [h for h in himnos if encaja(h)]
    if not candidatos:                         # catálogo agotado esta semana: se permite repetir
        candidatos = [h for h in himnos if encaja(h, repetir=True)]
    if not candidatos:
        return "Del tiempo" if tiempo != "ordinario" else ""
    elegido = candidatos[d.fecha.toordinal() % len(candidatos)]
    usados.add(elegido["titulo"])
    return elegido["titulo"]


def tiene_primeras_visperas(hoy: DiaLiturgico, mañana: DiaLiturgico) -> bool:
    """Las vísperas de hoy son I Vísperas de mañana (domingos y solemnidades), si mañana prevalece."""
    if not (mañana.es_domingo or mañana.grado == "solemnidad"):
        return False
    return mañana.celebracion.rango < hoy.celebracion.rango


def primeras_visperas(m: DiaLiturgico) -> dict:
    if m.grado == "solemnidad" or m.celebracion.señor:
        sal = "Propia (I Vísperas)"
        himno_ = "Propio"
    else:
        sal = f"I Vísperas del domingo (semana {romano(m.tiempo.salterio)})"
        himno_ = "Del tiempo" if m.tiempo.nombre != "ordinario" else "Del domingo"
    return {"de": m.celebracion.nombre, "himno": himno_, "salmodia": sal, "magnificat": "Propia"}


def formulario(d: DiaLiturgico) -> str:
    c = d.celebracion
    if c.grado != "feria":
        return c.nombre
    if d.tiempo.nombre == "ordinario":
        return f"Domingo {romano(d.tiempo.semana)} del tiempo ordinario"
    return c.nombre


def prefacio(d: DiaLiturgico, cfg: dict, rot: Rotador) -> str:
    c = d.celebracion
    t, s = d.tiempo.nombre, d.tiempo.semana
    if c.prefacio:
        return c.prefacio
    if c.comun and c.grado != "feria":
        return rot.siguiente(PREFACIO_COMUN.get(c.comun, ["Santos I", "Santos II"]))
    if t == "adviento":
        return "Adviento II" if (d.fecha.month == 12 and d.fecha.day >= 17) else "Adviento I"
    if t == "navidad":
        if d.fecha.month == 1 and d.fecha.day > 6:
            return "Epifanía o Navidad I-III"
        return rot.siguiente(["Navidad I", "Navidad II", "Navidad III"])
    if t == "cuaresma":
        if d.es_domingo:
            return "Propio del domingo"
        if s == 5:
            return "Pasión del Señor I"
        return rot.siguiente(["Cuaresma I", "Cuaresma II", "Cuaresma III", "Cuaresma IV"])
    if t == "semana_santa":
        return "Pasión del Señor II"
    if t == "triduo":
        return "Propio"
    if t == "pascua":
        if s == 1:
            return "Pascual I"
        if s == 7 and not d.es_domingo:
            return rot.siguiente(["Ascensión I", "Ascensión II"])
        return rot.siguiente(["Pascual I", "Pascual II", "Pascual III", "Pascual IV", "Pascual V"])
    if d.es_domingo:
        return f"Dominical {romano((s - 1) % 8 + 1)}"
    return rot.siguiente(cfg["prefacios_comunes"])


def etiqueta_celebracion(d: DiaLiturgico) -> str:
    c = d.celebracion
    if c.grado == "feria":
        return "FERIA"
    if c.grado == "domingo":
        return c.nombre.upper()
    grado = {"solemnidad": "Solemnidad", "fiesta": "Fiesta", "memoria": "Memoria",
             "triduo": "Triduo Pascual"}.get(c.grado, "")
    return f"{c.nombre.upper()}" + (f" ({grado})" if grado and c.grado != "memoria" else "")


# ---------------------------------------------------------------- borrador

def campos_dia(d: DiaLiturgico, horario: dict, cfg: dict, himnos: list[dict],
               himnos_usados: set[str], rot: Rotador, sug: Sugeridor) -> dict:
    """Todo lo que la hoja dice de un día según su celebración (el orden de las claves es el de la hoja)."""
    horas = horario.get("horas", [])
    dia: dict = {"celebracion": etiqueta_celebracion(d), "color": d.celebracion.color}
    if horario.get("laudes_con_eucaristia"):
        dia["laudes_con_eucaristia"] = True
    if "laudes" in horas:
        dia["laudes"] = {"himno": himno(d, "laudes", himnos, himnos_usados),
                         "salmodia": salmodia(d, "laudes"),
                         "benedictus": antifona_evangelica(d, cfg)}
    if "eucaristia" in horas:
        dia["eucaristia"] = {"formulario": formulario(d), "prefacio": prefacio(d, cfg, rot)}
        cantos = {}
        for momento in ("entrada", "ofertorio", "comunion"):
            c = sug.sugerir(d, momento)
            cantos[momento] = c.etiqueta_hoja() if c else ""
        dia["cantos"] = cantos
    if "visperas" in horas:
        sig = dia_liturgico(d.fecha + timedelta(days=1))
        if tiene_primeras_visperas(d, sig):
            dia["visperas"] = primeras_visperas(sig)
        else:
            dia["visperas"] = {"himno": himno(d, "visperas", himnos, himnos_usados),
                               "salmodia": salmodia(d, "visperas"),
                               "magnificat": antifona_evangelica(d, cfg)}
    return dia


def opciones_dia(d: DiaLiturgico, dia: dict, horario: dict, cfg: dict, himnos: list[dict],
                 himnos_usados: set[str], rot: Rotador, sug: Sugeridor) -> list[dict]:
    """Variantes de un día con memorias libres: la feria (la que ya está en `dia`) y cada memoria.

    Las variantes se calculan con copia del estado (rotadores, himnos y cantos usados) para no alterar
    lo que se propone en los demás días: solo una de ellas acabará en la hoja.
    """
    base = {k: copy.deepcopy(v) for k, v in dia.items() if k not in ("fecha", "dia")}
    feria = d.celebracion.grado == "feria"
    opciones = [{"etiqueta": "Feria" if feria else d.celebracion.nombre,
                 "tipo": "Del día", **base}]
    for c in d.memorias_libres:
        variante = replace(d, celebracion=c, memorias_libres=[], conmemoraciones=[], avisos=[])
        campos = campos_dia(variante, horario, cfg, himnos, set(himnos_usados),
                            Rotador(semilla=rot.semilla), Sugeridor(excluidos=set(sug.excluidos)))
        opciones.append({"etiqueta": c.nombre, "tipo": "Memoria libre", **campos})
    return opciones


def generar_borrador(fecha: date, cfg: dict | None = None, carpeta_semanas: Path | None = None,
                     con_opciones: bool = False) -> dict:
    """`con_opciones`: añade a cada día con memorias libres la lista `opciones` (para la web)."""
    cfg = cfg or cargar_config()
    carpeta_semanas = carpeta_semanas or RAIZ / "semanas"
    inicio = domingo_de(fecha)
    dias = semana(inicio)
    rot = Rotador(semilla=dias[1].tiempo.semana)
    himnos = cargar_himnos()
    himnos_usados: set[str] = set()
    sug = Sugeridor(excluidos=usados_recientemente(carpeta_semanas, inicio, cfg.get("semanas_sin_repetir_cantos", 3)))

    fin = inicio + timedelta(days=6)
    if inicio.month == fin.month:
        titulo = f"Semana del {inicio.day} al {fin.day} de {MESES[fin.month - 1]}"
    else:
        titulo = f"Semana del {inicio.day} de {MESES[inicio.month - 1]} al {fin.day} de {MESES[fin.month - 1]}"

    ref = dias[1]  # el lunes marca la semana y el salterio
    hoja = {
        "semana": inicio.isoformat(),
        "titulo": titulo,
        "salterio": romano(ref.tiempo.salterio),
        "tiempo": TIEMPO_HOJA[ref.tiempo.nombre],
        "dias": [],
        "avisos": "",
        "notas": [],
    }

    for d in dias:
        clave = CLAVES_DIA[d.fecha.weekday()]
        if clave not in cfg["dias_en_hoja"]:
            continue
        horario = cfg["horario"].get(clave, {})
        dia: dict = {"fecha": d.fecha.isoformat(), "dia": NOMBRE_DIA[d.fecha.weekday()]}
        dia.update(campos_dia(d, horario, cfg, himnos, himnos_usados, rot, sug))
        if con_opciones and d.memorias_libres:
            dia["opciones"] = opciones_dia(d, dia, horario, cfg, himnos, himnos_usados, rot, sug)
            dia["opcion"] = 0
        for c in d.memorias_libres:
            if not con_opciones:
                hoja["notas"].append(f"{dia['dia']} {d.fecha.day}: memoria libre opcional — {c.nombre}.")
        for c in d.conmemoraciones:
            hoja["notas"].append(f"{dia['dia']} {d.fecha.day}: conmemoración — {c.nombre}.")
        for a in d.avisos:
            hoja["notas"].append(f"{dia['dia']} {d.fecha.day}: {a}")
        hoja["dias"].append(dia)
    return hoja


CABECERA_YAML = """\
# Borrador de la hoja de liturgia. Generado automáticamente: revísalo y edítalo.
# - Cambia lo que quieras (himnos, prefacios, cantos, avisos...).
# - Los cantos van como "número · título": el número sirve para no repetirlos
#   en las semanas siguientes.
# - Las "notas" son avisos de la app y NO salen en la hoja.
# Después: python -m semiliturgy hoja {ruta}
"""


def guardar_borrador(hoja: dict, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = yaml.safe_dump(hoja, allow_unicode=True, sort_keys=False, width=120)
    ruta.write_text(CABECERA_YAML.format(ruta=ruta) + texto, encoding="utf-8")
