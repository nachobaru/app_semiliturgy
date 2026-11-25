"""Catálogo del cantoral y sugerencia de cantos para la misa."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from .calendario import DATA, DiaLiturgico


@dataclass
class Canto:
    n: int
    titulo: str
    pagina: int
    subseccion: str
    momentos: list[str]
    etiquetas: list[str]
    peso: float = 1.0
    excluir: bool = False
    solo_si: str | None = None

    def etiqueta_hoja(self) -> str:
        return f"{self.n} · {self.titulo}"


@lru_cache(maxsize=1)
def catalogo() -> dict[int, Canto]:
    datos = json.loads((DATA / "cantoral.json").read_text(encoding="utf-8"))
    ajustes_path = DATA / "etiquetas_cantos.yaml"
    ajustes = yaml.safe_load(ajustes_path.read_text(encoding="utf-8")) if ajustes_path.exists() else {}
    out = {}
    for c in datos:
        a = (ajustes or {}).get(c["n"], {}) or {}
        out[c["n"]] = Canto(
            n=c["n"], titulo=c["titulo"], pagina=c["pagina"], subseccion=c["subseccion"],
            momentos=a.get("momentos", c["momentos"]),
            etiquetas=list(dict.fromkeys(c["etiquetas"] + a.get("etiquetas", []))),
            peso=float(a.get("peso", 1.0)), excluir=bool(a.get("excluir", False)),
            solo_si=a.get("solo_si"),
        )
    return out


NUM_CANTO = re.compile(r"^\s*(\d{1,3})\s*·")


def numero_de(texto: str | None) -> int | None:
    m = NUM_CANTO.match(texto or "")
    return int(m.group(1)) if m else None


def usados_recientemente(carpeta: Path, antes_de: date, semanas: int) -> set[int]:
    """Números de canto que aparecen en las hojas de las últimas `semanas` semanas."""
    usados: set[int] = set()
    if not carpeta.exists():
        return usados
    for f in sorted(carpeta.glob("*.yaml")):
        try:
            inicio = date.fromisoformat(f.stem[:10])
        except ValueError:
            continue
        if not (0 < (antes_de - inicio).days <= semanas * 7):
            continue
        hoja = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for dia in hoja.get("dias", []):
            for v in (dia.get("cantos") or {}).values():
                n = numero_de(v)
                if n:
                    usados.add(n)
    return usados


def etiquetas_preferidas(dia: DiaLiturgico) -> list[str]:
    """Etiquetas de canto que encajan con el día, de más a menos específica."""
    c = dia.celebracion
    nombre = c.nombre.lower()
    prefs: list[str] = []
    if "covadonga" in nombre:
        prefs.append("covadonga")
    if c.comun == "virgen" or ("virgen maría" in nombre and c.grado != "feria"):
        prefs.append("virgen")
    if "corazón de jesús" in nombre:
        prefs.append("sagrado_corazon")
    if "cuerpo y sangre" in nombre or "sacerdote" in nombre:
        prefs.append("santisimo")
    if "pentecostés" in nombre:
        prefs.append("espiritu_santo")
    if "san josé" in nombre:
        prefs.append("san_jose")
    if "difuntos" in nombre:
        prefs.append("difuntos")
    if c.comun in ("apostoles", "martires", "virgenes", "santos", "pastores"):
        prefs += [c.comun, "santos"]
    t = dia.tiempo.nombre
    tag_tiempo = {"semana_santa": "cuaresma", "triduo": "cuaresma"}.get(t, t)
    if tag_tiempo != "ordinario":
        prefs.append(tag_tiempo)
    prefs.append("general")
    return prefs


# Etiquetas de tiempo: un canto con una de estas solo vale en su tiempo.
ETIQUETAS_TIEMPO = {"adviento", "navidad", "cuaresma", "pascua"}


@dataclass
class Sugeridor:
    excluidos: set[int] = field(default_factory=set)

    def sugerir(self, dia: DiaLiturgico, momento: str) -> Canto | None:
        prefs = etiquetas_preferidas(dia)
        tiempo = {"semana_santa": "cuaresma", "triduo": "cuaresma"}.get(dia.tiempo.nombre, dia.tiempo.nombre)
        rng = random.Random(f"{dia.fecha.isoformat()}-{momento}")
        propios = [c for c in catalogo().values()
                   if c.solo_si and c.solo_si.lower() in dia.celebracion.nombre.lower()
                   and momento in c.momentos and not c.excluir and c.n not in self.excluidos]
        if propios:
            self.excluidos.add(propios[0].n)
            return propios[0]
        for tag in prefs:
            candidatos = [
                c for c in catalogo().values()
                if momento in c.momentos and tag in c.etiquetas and not c.excluir and not c.solo_si
                and c.n not in self.excluidos
                and not ((set(c.etiquetas) & ETIQUETAS_TIEMPO) and tiempo not in c.etiquetas)
            ]
            if candidatos:
                elegido = rng.choices(candidatos, weights=[c.peso for c in candidatos])[0]
                self.excluidos.add(elegido.n)
                return elegido
        return None
