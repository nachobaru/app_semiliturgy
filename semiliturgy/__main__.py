"""Línea de órdenes.

    python -m semiliturgy dia 2026-11-21
    python -m semiliturgy borrador 2026-11-23        # cualquier fecha de la semana
    python -m semiliturgy hoja semanas/2026-11-22.yaml
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .borrador import RAIZ, generar_borrador, guardar_borrador
from .calendario import dia_liturgico, domingo_de, romano
from .hoja import exportar


def cmd_dia(a):
    d = dia_liturgico(date.fromisoformat(a.fecha))
    t = d.tiempo
    print(f"{d.fecha}  {d.celebracion.nombre}  [{d.celebracion.grado}, {d.celebracion.color}]")
    print(f"  Tiempo: {t.nombre}, semana {t.semana}, salterio {romano(t.salterio)}"
          f" · ciclo {d.ciclo_dominical} / año {d.ciclo_ferial}")
    for c in d.memorias_libres:
        print(f"  Memoria libre: {c.nombre}")
    for c in d.conmemoraciones:
        print(f"  Conmemoración: {c.nombre}")
    for x in d.avisos:
        print(f"  ⚠ {x}")


def cmd_borrador(a):
    f = date.fromisoformat(a.fecha)
    ruta = Path(a.salida) if a.salida else RAIZ / "semanas" / f"{domingo_de(f).isoformat()}.yaml"
    if ruta.exists() and not a.forzar:
        raise SystemExit(f"{ruta} ya existe (usa --forzar para sobrescribir tus cambios).")
    hoja = generar_borrador(f)
    guardar_borrador(hoja, ruta)
    print(f"Borrador: {ruta}")
    for n in hoja["notas"]:
        print(f"  · {n}")


def cmd_hoja(a):
    for p in exportar(Path(a.yaml), pdf=not a.sin_pdf):
        print(p)


def main():
    p = argparse.ArgumentParser(prog="semiliturgy", description="Hoja de liturgia del Seminario")
    sub = p.add_subparsers(required=True)
    s = sub.add_parser("dia", help="Muestra la celebración de un día")
    s.add_argument("fecha")
    s.set_defaults(func=cmd_dia)
    s = sub.add_parser("borrador", help="Genera el borrador YAML de la semana")
    s.add_argument("fecha", help="cualquier fecha de la semana (AAAA-MM-DD)")
    s.add_argument("-o", "--salida")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(func=cmd_borrador)
    s = sub.add_parser("hoja", help="Genera la hoja (HTML y PDF) a partir del YAML")
    s.add_argument("yaml")
    s.add_argument("--sin-pdf", action="store_true")
    s.set_defaults(func=cmd_hoja)
    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
