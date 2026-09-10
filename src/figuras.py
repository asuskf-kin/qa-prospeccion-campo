# -*- coding: utf-8 -*-
"""Los graficos del reporte. Cada funcion guarda un PNG en output/figs/."""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from shapely.geometry import box

from . import config as cfg
from .analisis import Resultados, limpiar_nombre

K = cfg.KIN

ETIQUETA_VISIBLE = {"SE APERTURARA EL CLIENTE": "SE APERTURARÁ EL CLIENTE"}


def estilo() -> None:
    plt.rcParams.update({
        "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
        "font.size": 9,
        "axes.edgecolor": K["mid"], "axes.labelcolor": K["dark"],
        "text.color": K["dark"], "xtick.color": K["dark"], "ytick.color": K["dark"],
        "axes.spines.top": False, "axes.spines.right": False,
    })


def _guardar(fig, destino: Path, nombre: str) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"{nombre}.png"
    fig.savefig(ruta, facecolor="white")
    plt.close(fig)
    print(f"  -> {ruta.name}")
    return ruta


# ------------------------------------------------------------------ 01 y 02
def resultado_visitas(res: Resultados, destino: Path) -> Path:
    d = res["distribucion"].sort_values("Cantidad")
    colores = [K["lime"] if i == "SE APERTURARA EL CLIENTE"
               else K["alert"] if i == "NO EXISTE EL ESTABLECIMIENTO"
               else K["gray"] for i in d.index]

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    b = ax.barh([ETIQUETA_VISIBLE.get(i, i) for i in d.index], d["Cantidad"],
                color=colores, edgecolor=K["dark"], linewidth=0.7)
    ax.bar_label(b, labels=[f" {int(n)}  ({p:.0f}%)"
                            for n, p in zip(d["Cantidad"], d["Porcentaje (%)"])],
                 fontsize=8.5)
    ax.set_xlim(0, d["Cantidad"].max() * 1.28)
    ax.set_xlabel("Puntos visitados")
    ax.set_title(f"Resultado de las {res.metrics['visitas_unicas']} visitas de campo",
                 loc="left", fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(axis="y", length=0)
    return _guardar(fig, destino, "01_resultado_visitas")


def canales(res: Resultados, destino: Path) -> Path:
    c = res.fuentes.respuestas["Canal"].value_counts().head(8).sort_values()
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    b = ax.barh(c.index, c.values, color=K["dark"], edgecolor=K["dark"])
    ax.bar_label(b, padding=3, fontsize=8.5)
    ax.set_xlim(0, c.max() * 1.18)
    ax.set_xlabel("Puntos visitados")
    ax.set_title("Canales cubiertos por la prueba (top 8)", loc="left",
                 fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(axis="y", length=0)
    return _guardar(fig, destino, "02_canales")


# ---------------------------------------------------------------------- 03
def validity_score(res: Resultados, destino: Path) -> Path:
    caso, control = res["caso"], res["control"]
    auc = res.metrics["validity"]["auc"]

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2),
                             gridspec_kw={"width_ratios": [1.55, 1]})
    ax = axes[0]
    bins = np.linspace(0.25, 1.0, 34)
    ax.hist(control, bins=bins, density=True, color=K["gray"], edgecolor="white",
            linewidth=0.4, label=f"Resto de la base (n={len(control):,})".replace(",", "."))
    ax.hist(caso, bins=bins, density=True, histtype="step", linewidth=2.1,
            color=K["alert"], label=f"NO EXISTE (n={len(caso)})")
    ax.set_xlabel("validity_score de la base de prospección")
    ax.set_ylabel("densidad")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Los POI inexistentes tienen el score MÁS alto", loc="left",
                 fontsize=10.5, fontweight="bold", pad=8)

    ax = axes[1]
    bp = ax.boxplot([control, caso], vert=True, widths=0.55, patch_artist=True,
                    tick_labels=["Resto\nde la base", "NO\nEXISTE"], showfliers=False)
    for patch, c in zip(bp["boxes"], [K["gray"], K["alert"]]):
        patch.set_facecolor(c)
        patch.set_edgecolor(K["dark"])
    for el in ("medians", "whiskers", "caps"):
        for it in bp[el]:
            it.set_color(K["dark"])
    ax.set_ylabel("validity_score")
    ax.set_title(f"AUC = {auc:.2f}".replace(".", ","), loc="left",
                 fontsize=10.5, fontweight="bold", pad=8)
    return _guardar(fig, destino, "03_validity_score")


# ---------------------------------------------------------------------- 04
def fuera_cobertura(res: Resultados, destino: Path) -> Path:
    d = res["ooc"].sort_values("dist_cliente_1_m")
    etiquetas = [limpiar_nombre(n)[:26].title() for n in d[res.fuentes.C_NOMBRE]]

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    b = ax.barh(etiquetas, d["dist_cliente_1_m"], color=K["lime"],
                edgecolor=K["dark"], linewidth=0.7)
    ax.bar_label(b, fmt=" %.0f m", fontsize=8)
    ax.axvline(cfg.RADIO_COBERTURA_M, color=K["alert"], linestyle="--", linewidth=1.4)
    ax.text(cfg.RADIO_COBERTURA_M, len(d) - 0.3, f" radio de {cfg.RADIO_COBERTURA_M} m",
            color=K["alert"], fontsize=8, va="top")
    ax.set_xlim(0, cfg.RADIO_COBERTURA_M * 1.12)
    ax.set_xlabel("Distancia al cliente más cercano de la maestra (m)")
    ax.set_title("Todos los puntos 'fuera de cobertura' tienen un cliente al lado",
                 loc="left", fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(axis="y", length=0, labelsize=8)
    return _guardar(fig, destino, "04_fuera_cobertura")


# ---------------------------------------------------------------------- 05
def mapa_visitas(res: Resultados, destino: Path) -> Path:
    p = res.fuentes.pais
    geo, deptos, maestra = res["geo"], res["deptos"], res["maestra_geo"]
    visitados = {d for d in geo["departamento"].unique() if d and d != "FUERA DEL PAIS"}

    estilos = {
        "NO EXISTE EL ESTABLECIMIENTO": (K["alert"], "o"),
        "EXISTE COMO CLIENTE": (K["dark"], "s"),
        "FUERA DE COBERTURA": ("#4F8FF0", "^"),
        "SE APERTURARA EL CLIENTE": (K["lime"], "*"),
    }

    def dibujar(ax, lw=0.45):
        for nombre, poly in deptos.items():
            partes = poly.geoms if poly.geom_type == "MultiPolygon" else [poly]
            for parte in partes:
                xs, ys = parte.exterior.xy
                ax.fill(xs, ys, zorder=1, linewidth=lw, edgecolor=K["mid"],
                        facecolor="#FAFDDF" if nombre in visitados else "white")

    aspecto = 1 / np.cos(np.radians(p.lat_centro))
    pad = 0.14
    zx0, zx1 = geo["lon"].min() - pad, geo["lon"].max() + pad
    zy0, zy1 = geo["lat"].min() - pad, geo["lat"].max() + pad

    fig, (axN, axZ) = plt.subplots(1, 2, figsize=(10.2, 4.3),
                                   gridspec_kw={"width_ratios": [1, 1.42]})

    dibujar(axN)
    axN.scatter(geo["lon"], geo["lat"], s=11, c=K["alert"], linewidths=0, zorder=4)
    axN.add_patch(Rectangle((zx0, zy0), zx1 - zx0, zy1 - zy0, fill=False,
                            edgecolor=K["dark"], linewidth=1.3, zorder=5))
    axN.set_xlim(p.bbox[0], p.bbox[1])
    axN.set_ylim(p.bbox[2], p.bbox[3])
    axN.set_aspect(aspecto)
    axN.axis("off")
    axN.set_title(f"{p.nombre} · {len(deptos)} {p.divisiones}\n"
                  f"la prueba toca {len(visitados)}",
                  loc="left", fontsize=10, fontweight="bold", pad=6)

    ctx = maestra[maestra["pos_longitude"].between(zx0, zx1)
                  & maestra["pos_latitude"].between(zy0, zy1)]
    dibujar(axZ, lw=0.8)
    axZ.scatter(ctx["pos_longitude"], ctx["pos_latitude"], s=0.9, c=K["mid"],
                alpha=0.30, linewidths=0, zorder=2,
                label=f"Maestra de clientes ({len(ctx):,})".replace(",", "."))
    for etiqueta, (c, mk) in estilos.items():
        sel = geo[geo["resultado"] == etiqueta]
        axZ.scatter(sel["lon"], sel["lat"], marker=mk, c=c, zorder=4,
                    s=150 if mk == "*" else 44, edgecolors=K["dark"], linewidths=0.6,
                    label=f"{ETIQUETA_VISIBLE.get(etiqueta, etiqueta)} ({len(sel)})")
    resto = geo[~geo["resultado"].isin(estilos)]
    axZ.scatter(resto["lon"], resto["lat"], marker="o", c="white", zorder=4, s=34,
                edgecolors=K["dark"], linewidths=0.7, label=f"Otros ({len(resto)})")

    recorte = box(zx0, zy0, zx1, zy1)
    for nombre in visitados:
        visible = deptos[nombre].intersection(recorte)
        if visible.is_empty:
            continue
        c = visible.representative_point()
        axZ.annotate(nombre.upper(), (c.x, c.y), fontsize=6.8, color=K["dark"],
                     ha="center", va="center", zorder=6, fontweight="bold",
                     path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])

    axZ.set_xlim(zx0, zx1)
    axZ.set_ylim(zy0, zy1)
    axZ.set_aspect(aspecto)
    axZ.axis("off")
    axZ.set_title("Detalle del área visitada", loc="left",
                  fontsize=10, fontweight="bold", pad=6)
    axZ.legend(frameon=False, fontsize=7, loc="upper left",
               bbox_to_anchor=(1.01, 1.0), markerscale=1.1)
    return _guardar(fig, destino, "05_mapa_visitas")


TODAS = [resultado_visitas, canales, validity_score, fuera_cobertura, mapa_visitas]


def generar(res: Resultados, destino: Path) -> None:
    estilo()
    for fn in TODAS:
        fn(res, destino)
