# -*- coding: utf-8 -*-
"""Punto de entrada del QA de prospección.

    python run.py guatemala              # análisis + figuras + deck
    python run.py guatemala --solo-datos # sin figuras ni PowerPoint
    python run.py --paises               # qué países hay configurados
"""
from __future__ import annotations

import argparse
import json
import sys

from src import config, deck, figuras
from src.analisis import ejecutar


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pais", nargs="?", help="slug del país, p. ej. guatemala")
    ap.add_argument("--solo-datos", action="store_true",
                    help="solo el análisis y los CSV, sin figuras ni deck")
    ap.add_argument("--sin-deck", action="store_true",
                    help="análisis y figuras, pero sin generar el PowerPoint")
    ap.add_argument("--paises", action="store_true",
                    help="lista los países configurados y termina")
    args = ap.parse_args(argv)

    if args.paises or not args.pais:
        print("Países configurados:")
        for slug, p in config.PAISES.items():
            print(f"  {slug:12} {p.nombre} ({p.iso3})  ->  {p.dir}")
        return 0

    p = config.pais(args.pais)
    print(f"\n=== QA de prospección · {p.nombre} ===\n")

    print("[1/4] análisis")
    res = ejecutar(p)

    print("\n[2/4] métricas")
    p.metrics.write_text(json.dumps(res.metrics, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    print(f"  -> {p.metrics.name}")

    if args.solo_datos:
        print("\nlisto (solo datos)")
        return 0

    print("\n[3/4] figuras")
    figuras.generar(res, p.figs)

    if args.sin_deck:
        print("\nlisto (sin deck)")
        return 0

    print("\n[4/4] reporte")
    deck.construir(p)

    agg = res.metrics["cuenta_agregada"]
    print(f"\nlisto · {res.metrics['visitas_unicas']} visitas: "
          + " · ".join(f"{k} {v}" for k, v in agg.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
