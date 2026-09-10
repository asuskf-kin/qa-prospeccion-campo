# -*- coding: utf-8 -*-
"""Genera el reporte ejecutivo en PowerPoint con la identidad de Kin Analytics.

    from src import config, deck
    deck.construir(config.pais("guatemala"))

Lee `deck_metrics.json` y las figuras que dejo el analisis, y escribe el .pptx
en `output/deck/`. El archivo generado tiene un nombre propio para no pisar la
version que el equipo edita a mano (mapas pegados, ajustes de texto).
"""
from __future__ import annotations

import json
from math import ceil
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from .config import ASSETS, Pais


def construir(p: Pais, salida: Path | None = None) -> Path:
    """Arma el deck del pais y devuelve la ruta del archivo escrito."""
    FIGS = p.figs
    OUT = salida or (p.deck / f"Reporte_QA_{p.nombre}_generado.pptx")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    M = json.loads(p.metrics.read_text(encoding="utf-8"))

    # --------------------------------------------------------------------- marca
    DARK = RGBColor(0x20, 0x24, 0x27)
    LIME = RGBColor(0xE6, 0xFD, 0x01)
    GRAY = RGBColor(0xD8, 0xD9, 0xD4)
    LIGHT = RGBColor(0xEF, 0xF0, 0xEB)
    MID = RGBColor(0x8A, 0x8D, 0x88)
    ALERT = RGBColor(0xE5, 0x32, 0x6A)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)

    FONT = "Segoe UI"
    FONT_BOLD = "Segoe UI Semibold"

    SLIDE_W, SLIDE_H = 13.333, 7.5
    FOOTER_TOP, FOOTER_H = 6.832, 0.668
    TITLE_TOP = 0.62
    RULE_TOP = 1.10
    BODY_TOP = 1.55
    MARGIN = 0.62

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    BLANK = prs.slide_layouts[6]


    # ------------------------------------------------------------------ formato
    def mil(n) -> str:
        """Separador de miles al estilo local: 34915 -> '34.915'."""
        return f"{int(n):,}".replace(",", ".")


    def dec(x, nd: int = 3) -> str:
        """Coma decimal: 0.724 -> '0,724'."""
        return f"{float(x):.{nd}f}".replace(".", ",")


    def sin_sombra(shp):
        """Elimina la sombra heredada del tema (PowerPoint y LibreOffice)."""
        sp_pr = shp._element.spPr
        for tag in ("effectLst", "effectDag"):
            for e in sp_pr.findall(f"{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag}"):
                sp_pr.remove(e)
        sp_pr.append(sp_pr.makeelement(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst", {}))
        style = shp._element.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}style")
        if style is not None:
            shp._element.remove(style)
        return shp


    # ----------------------------------------------------------------- primitivas
    def new_slide(dark: bool = False):
        s = prs.slides.add_slide(BLANK)
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                Inches(SLIDE_W), Inches(SLIDE_H))
        bg.fill.solid()
        bg.fill.fore_color.rgb = DARK if dark else WHITE
        bg.line.fill.background()
        sin_sombra(bg)
        return s


    def footer(s, dark: bool = False):
        s.shapes.add_picture(str(ASSETS / ("footer_dark.png" if dark else "footer_light.png")),
                             0, Inches(FOOTER_TOP), Inches(SLIDE_W), Inches(FOOTER_H))


    def tb(s, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
        box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        tf.paragraphs[0].alignment = align
        return tf


    def write(tf, runs, size=12, color=DARK, bold=False, font=FONT,
              space_after=6, line=1.25, first=True, align=None):
        """Escribe un parrafo. `runs` puede ser str o lista de (texto, dict)."""
        p = tf.paragraphs[0] if first and not tf.paragraphs[0].runs else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = line
        if align is not None:
            p.alignment = align
        for txt, ov in ([(runs, {})] if isinstance(runs, str) else runs):
            r = p.add_run()
            r.text = txt
            f = r.font
            f.size = Pt(ov.get("size", size))
            f.bold = ov.get("bold", bold)
            f.name = ov.get("font", FONT_BOLD if ov.get("bold", bold) else font)
            f.color.rgb = ov.get("color", color)
        return p


    def title(s, text, dark=False, rule=True):
        tf = tb(s, MARGIN, TITLE_TOP, SLIDE_W - 2 * MARGIN, 0.55)
        write(tf, text, size=25, bold=True, color=WHITE if dark else DARK, space_after=0)
        if rule:
            bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(MARGIN - 0.48),
                                     Inches(RULE_TOP), Inches(SLIDE_W - 2 * (MARGIN - 0.48)),
                                     Inches(0.035))
            bar.fill.solid()
            bar.fill.fore_color.rgb = LIME
            bar.line.fill.background()
            sin_sombra(bar)
        return s


    def hexagon(s, cx, cy, w, fill=None, line=None, lw=1.0):
        """Hexagono de punta arriba centrado en (cx, cy) con ancho `w` pulgadas."""
        h = w * 1.1547
        shp = s.shapes.add_shape(MSO_SHAPE.HEXAGON, Inches(cx - h / 2), Inches(cy - w / 2),
                                 Inches(h), Inches(w))
        shp.rotation = 90
        if fill is None:
            shp.fill.background()
        else:
            shp.fill.solid()
            shp.fill.fore_color.rgb = fill
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = line
            shp.line.width = Pt(lw)
        sin_sombra(shp)
        return shp


    def rect(s, x, y, w, h, fill=None, line=None, lw=1.0, dash=None, radius=None):
        shape = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if radius:
            shp.adjustments[0] = radius
        if fill is None:
            shp.fill.background()
        else:
            shp.fill.solid()
            shp.fill.fore_color.rgb = fill
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = line
            shp.line.width = Pt(lw)
            if dash:
                from pptx.enum.dml import MSO_LINE_DASH_STYLE
                shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        sin_sombra(shp)
        shp.text_frame.word_wrap = True
        return shp


    def picture(s, path, x, y, w, h, align="center"):
        """Inserta una imagen ajustada dentro del rectangulo (x, y, w, h)."""
        iw, ih = Image.open(path).size
        k = min(w / iw, h / ih)
        pw, ph = iw * k, ih * k
        px = x if align == "left" else x + (w - pw) / 2
        py = y + (h - ph) / 2
        return s.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(pw), Inches(ph))


    def n_lineas(texto, w_in, size_pt) -> int:
        """Estima cuantas lineas ocupa `texto` en un ancho dado (Segoe UI)."""
        cpl = max(8, w_in * 96 / (size_pt * 0.70))
        return max(1, ceil(len(_plain(texto)) / cpl))


    def kpi(s, x, y, w, h, valor, etiqueta, acento=LIME, oscuro=False, v_size=28):
        """Tarjeta de indicador: cifra grande + etiqueta, siempre dentro del marco."""
        card = rect(s, x, y, w, h, fill=DARK if oscuro else LIGHT)
        rect(s, x, y, w, 0.075, fill=acento)
        tf = tb(s, x + 0.26, y + 0.26, w - 0.52, v_size * 1.3 / 72)
        write(tf, valor, size=v_size, bold=True, color=WHITE if oscuro else DARK,
              space_after=0, line=1.0)
        tf = tb(s, x + 0.26, y + 0.30 + v_size * 1.25 / 72, w - 0.52, h - 0.6)
        write(tf, etiqueta, size=10, color=GRAY if oscuro else MID, space_after=0, line=1.2)
        return card


    def bullets(s, x, y, w, items, size=12.5, dark=False, gap=11, bullet=LIME):
        """Lista con vinetas hexagonales; el alto de cada item se estima al vuelo."""
        yy = y
        for texto in items:
            hexagon(s, x + 0.075, yy + 0.115, 0.10, fill=bullet)
            n = n_lineas(texto, w - 0.30, size)
            tf = tb(s, x + 0.30, yy - 0.03, w - 0.30, 0.24 * n + 0.12)
            write(tf, texto, size=size, color=WHITE if dark else DARK,
                  space_after=0, line=1.3)
            yy += (size * 1.3 / 72) * n + gap / 72
        return yy


    def _plain(runs):
        return runs if isinstance(runs, str) else "".join(t for t, _ in runs)


    def divisor(s, texto):
        s.shapes.add_picture(str(ASSETS / "section_bg.png"), 0, 0,
                             Inches(SLIDE_W), Inches(SLIDE_H))
        cy = 3.915
        hexagon(s, 7.032, cy, 3.369, fill=GRAY)
        hexagon(s, 10.400, cy, 3.369, fill=DARK)
        tf = tb(s, 9.05, cy - 0.85, 2.75, 1.7, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        for i, linea in enumerate(texto.split("\n")):
            write(tf, linea, size=25, bold=True, color=LIME, space_after=0,
                  first=(i == 0), align=PP_ALIGN.CENTER)


    def placeholder_mapa(s, x, y, w, h, titulo, ayuda):
        """Marco vacio listo para pegar una captura de mapa."""
        rect(s, x, y, w, h, fill=RGBColor(0xFA, 0xFA, 0xF8), line=MID, lw=1.25, dash=True)
        hexagon(s, x + w / 2, y + h / 2 - 0.42, 0.62, fill=None, line=MID, lw=1.5)
        hexagon(s, x + w / 2, y + h / 2 - 0.42, 0.24, fill=LIME)
        tf = tb(s, x + 0.4, y + h / 2 + 0.16, w - 0.8, 1.0, align=PP_ALIGN.CENTER)
        write(tf, titulo, size=13, bold=True, color=DARK, space_after=4,
              align=PP_ALIGN.CENTER)
        write(tf, ayuda, size=10, color=MID, first=False, align=PP_ALIGN.CENTER, line=1.3)


    def nota(s, texto, dark=False, y=6.42):
        """Pie de pagina con la fuente del dato."""
        tf = tb(s, MARGIN, y, SLIDE_W - 2 * MARGIN, 0.3)
        write(tf, texto, size=8.5, color=MID if not dark else GRAY, space_after=0)


    def notas_orador(s, texto):
        s.notes_slide.notes_text_frame.text = texto


    # ===========================================================================
    # 1 — PORTADA
    # ===========================================================================
    s = new_slide(dark=True)
    s.shapes.add_picture(str(ASSETS / "title_hex.png"), Inches(5.871), Inches(0.687),
                         Inches(4.988), Inches(5.740))
    wedge = s.shapes.add_shape(MSO_SHAPE.HEXAGON, Inches(10.55), Inches(1.35),
                               Inches(5.4), Inches(4.7))
    wedge.rotation = 90
    wedge.fill.solid()
    wedge.fill.fore_color.rgb = RGBColor(0x16, 0x19, 0x1B)
    wedge.line.fill.background()
    sin_sombra(wedge)

    tf = tb(s, 0.62, 0.72, 3.0, 0.8)
    write(tf, "Kin Analytics\n©2026", size=9, color=MID, space_after=8, line=1.25)
    write(tf, "CONFIDENCIAL", size=9, color=MID, first=False)

    tf = tb(s, 0.62, 2.55, 5.3, 1.5)
    write(tf, "Prospección Digital", size=31, color=WHITE, bold=False, space_after=2, line=1.15)
    write(tf, "Guatemala", size=31, color=WHITE, first=False, space_after=0, line=1.15)

    tf = tb(s, 0.62, 4.25, 5.3, 1.3)
    write(tf, "Revisión de Hallazgos", size=24, bold=True, color=LIME, space_after=3)
    write(tf, "Prueba de campo · Ultrasegmentación", size=13, color=WHITE,
          first=False, space_after=3)
    write(tf, "Septiembre 2026", size=15, bold=True, color=LIME, first=False)

    footer(s, dark=True)
    notas_orador(s, "Revisión QA de la prueba de campo de prospección digital en Guatemala: "
                    "104 respuestas sobre 100 POI únicos, contrastadas contra los 34.915 POI de "
                    "la base interna de prospección y 229.077 registros de la maestra.")

    # ===========================================================================
    # 2 — AGENDA
    # ===========================================================================
    s = new_slide()
    title(s, "Contenido")
    AGENDA = [
        ("01", "Introducción", "Objetivo, alcance y fuentes de la revisión"),
        ("02", "Panorama general", "Cómo se repartieron las 100 visitas de campo"),
        ("03", "Hallazgos clave", "Los cinco problemas que explican el resultado"),
        ("04", "Próximos pasos", "Acciones para mejorar la calidad del entregable"),
    ]
    y = 1.75
    for num, tit, sub in AGENDA:
        hexagon(s, 1.05, y + 0.42, 0.78, fill=LIGHT)
        tf = tb(s, 0.68, y + 0.19, 0.75, 0.5, align=PP_ALIGN.CENTER)
        write(tf, num, size=17, bold=True, color=DARK, space_after=0, align=PP_ALIGN.CENTER)
        tf = tb(s, 1.85, y + 0.10, 9.5, 0.9)
        write(tf, tit, size=17, bold=True, color=DARK, space_after=3)
        write(tf, sub, size=11.5, color=MID, first=False)
        y += 1.14
    footer(s)

    # ===========================================================================
    # 3 — DIVISOR: INTRODUCCIÓN
    # ===========================================================================
    divisor(new_slide(), "Introducción")

    # ===========================================================================
    # 4 — INTRODUCCIÓN
    # ===========================================================================
    s = new_slide()
    title(s, "Introducción")
    tf = tb(s, MARGIN, BODY_TOP, 11.2, 1.0)
    write(tf, [("Esta revisión audita la prueba de campo compartida por el equipo "
                "embotellador y ordena los resultados observados en los puntos visitados. "
                "Cada respuesta se contrastó contra nuestra base interna de prospección "
                "y contra la maestra de clientes.", {})], size=13, line=1.4)

    y = 2.55
    for cab, cuerpo in [
        ("Objetivo",
         "Entender por qué fallan o aciertan los intentos de apertura de nuevos POS, "
         "identificar patrones consistentes por canal y aislar los factores que "
         "explican el comportamiento de los puntos visitados."),
        ("Alcance",
         f"{M['respuestas_crudas']} respuestas de formulario sobre "
         f"{M['visitas_unicas']} POI únicos · {mil(M['universo_dataplor'])} POI de la base "
         f"interna de prospección · {mil(M['maestra_total'])} registros de la maestra "
         f"({mil(M['maestra_activos'])} activos)."),
        ("Impacto",
         "Priorizar mejor los prospectos, dejar de gastar visitas en puntos inviables y "
         "corregir las reglas de cruce contra la base de clientes."),
    ]:
        tf = tb(s, MARGIN, y, 11.2, 1.1)
        write(tf, cab, size=14, bold=True, color=DARK, space_after=4)
        write(tf, cuerpo, size=12.5, color=DARK, first=False, line=1.4)
        y += 1.28
    footer(s)

    # ===========================================================================
    # 5 — DIVISOR: PANORAMA GENERAL
    # ===========================================================================
    divisor(new_slide(), "Panorama\nGeneral")

    # ===========================================================================
    # 6 — PUNTO DE PARTIDA
    # ===========================================================================
    s = new_slide()
    title(s, "Punto de partida")

    # ---------------------------------------------- bloque A: de donde salen
    tf = tb(s, MARGIN, 1.52, 11.9, 0.3)
    write(tf, "De dónde salen los 100 puntos visitados", size=13, bold=True,
          color=DARK, space_after=0)

    PASOS = [
        ("1", "Base de prospección", mil(M["universo_dataplor"]),
         "POI en el universo interno", GRAY),
        ("2", "Maestra de clientes", mil(M["maestra_activos"]),
         "clientes activos", MID),
        ("3", "Prueba de campo", f"{M['visitas_unicas']}", "POI visitados", LIME),
    ]
    x = 0.72
    for num, cab, valor, sub, color in PASOS:
        rect(s, x, 1.94, 3.55, 1.92, fill=LIGHT)
        rect(s, x, 1.94, 3.55, 0.085, fill=color)
        hexagon(s, x + 0.58, 2.46, 0.54, fill=DARK)
        tf = tb(s, x + 0.31, 2.30, 0.54, 0.4, align=PP_ALIGN.CENTER)
        write(tf, num, size=13, bold=True, color=LIME, space_after=0, align=PP_ALIGN.CENTER)
        tf = tb(s, x + 1.06, 2.32, 2.3, 0.4)
        write(tf, cab, size=11.5, bold=True, color=DARK, space_after=0)
        tf = tb(s, x + 0.31, 2.92, 3.0, 0.85)
        write(tf, valor, size=26, bold=True, color=DARK, space_after=1)
        write(tf, sub, size=10.5, color=MID, first=False)
        if num != "3":
            ar = s.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(x + 3.62), Inches(2.70),
                                    Inches(0.40), Inches(0.40))
            ar.fill.solid(); ar.fill.fore_color.rgb = GRAY
            ar.line.fill.background(); sin_sombra(ar)
        x += 4.03

    # ------------------------------------ separador entre los dos bloques
    ln = s.shapes.add_connector(1, Inches(0.72), Inches(4.24),
                                Inches(12.62), Inches(4.24))
    ln.line.color.rgb = GRAY
    ln.line.width = Pt(1.0)

    # ------------------------------------------- bloque B: en que terminaron
    tf = tb(s, MARGIN, 4.44, 11.9, 0.3)
    write(tf, [("En qué terminaron esas ", {"bold": True}),
               (f"{M['visitas_unicas']} visitas", {"bold": True}),
               ("   ·   11 + 34 + 55 = 100", {"size": 10, "bold": False, "color": MID})],
          size=13, color=DARK, space_after=0)

    SEG = [
        (M["macro_resultado"]["OPORTUNIDAD"], "Apertura", LIME, DARK),
        (M["macro_resultado"]["YA ATENDIDO / COBERTURA EXISTENTE"], "Ya atendidos", MID, WHITE),
        (M["macro_resultado"]["DESCARTE"], "Descartados en terreno", ALERT, WHITE),
    ]
    BAR_X, BAR_W, BAR_Y, BAR_H = 0.72, 11.90, 4.88, 0.72
    xx = BAR_X
    for n, etiqueta, color, tinta in SEG:
        w = BAR_W * n / M["visitas_unicas"]
        rect(s, xx, BAR_Y, w, BAR_H, fill=color)
        tf = tb(s, xx + 0.14, BAR_Y + 0.20, w - 0.28, 0.34)
        write(tf, f"{n}", size=17, bold=True, color=tinta, space_after=0)
        xx += w

    xx = BAR_X
    for n, etiqueta, color, tinta in SEG:
        w = BAR_W * n / M["visitas_unicas"]
        tf = tb(s, xx, BAR_Y + BAR_H + 0.12, max(w, 1.6), 0.3)
        write(tf, etiqueta, size=10.5, color=DARK, space_after=0)
        xx += w

    nota(s, "El primer bloque muestra de qué fuentes sale la muestra; el segundo, "
            "cómo se repartieron las 100 visitas. No son pasos consecutivos.", y=6.36)
    footer(s)

    # ===========================================================================
    # 7 — RESULTADO DE LAS VISITAS
    # ===========================================================================
    d = M["distribucion_resultado"]
    s = new_slide()
    title(s, "Panorama general — Resultado de las visitas")
    picture(s, FIGS / "01_resultado_visitas.png", 0.55, 1.55, 8.35, 4.55)

    rect(s, 9.20, 1.72, 3.55, 4.20, fill=LIGHT)
    rect(s, 9.20, 1.72, 3.55, 0.075, fill=LIME)
    tf = tb(s, 9.50, 2.05, 3.0, 3.7)
    write(tf, "Lectura", size=11, bold=True, color=MID, space_after=10)
    write(tf, [(f"{d['NO EXISTE EL ESTABLECIMIENTO']['pct']:.0f}%", {"size": 26, "bold": True}),
               (" de los POI entregados no existe en terreno.", {"size": 12})],
          first=False, space_after=14, line=1.3)
    write(tf, [(f"{d['EXISTE COMO CLIENTE']['pct']:.0f}%", {"size": 26, "bold": True}),
               (" ya figuraba como cliente de la operación.", {"size": 12})],
          first=False, space_after=14, line=1.3)
    write(tf, [(f"{M['tasa_apertura']:.0f}%", {"size": 26, "bold": True, "color": DARK}),
               (" es la tasa real de apertura de la prueba.", {"size": 12})],
          first=False, space_after=0, line=1.3)
    nota(s, f"Fuente: formulario de visita — {M['visitas_unicas']} POI únicos "
            f"({M['respuestas_crudas']} respuestas recibidas).")
    footer(s)

    # ===========================================================================
    # 8 — EMBUDO
    # ===========================================================================
    s = new_slide()
    title(s, "Panorama general — Embudo de la prueba de campo")

    def caja(x, y, w, h, texto, sub, fill, color=DARK, size=11.5):
        rect(s, x, y, w, h, fill=fill)
        tf = tb(s, x + 0.12, y + 0.13, w - 0.24, h - 0.26, align=PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE)
        write(tf, texto, size=size, bold=True, color=color, space_after=2,
              align=PP_ALIGN.CENTER, line=1.2)
        if sub:
            write(tf, sub, size=size - 1.5, color=color, first=False,
                  align=PP_ALIGN.CENTER, line=1.2)

    def conector(x1, y1, x2, y2):
        ln = s.shapes.add_connector(2, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        ln.line.color.rgb = GRAY
        ln.line.width = Pt(1.5)

    caja(5.05, 1.62, 3.25, 0.68, f"{M['respuestas_crudas']} respuestas recibidas",
         f"{M['visitas_unicas']} POI únicos · {M['ids_duplicados']} encuestados dos veces",
         LIME, DARK, 12)
    conector(6.67, 2.30, 6.67, 2.62)
    conector(2.25, 2.62, 11.10, 2.62)

    RAMAS = [
        (0.72, "DESCARTE", M["macro_resultado"]["DESCARTE"], ALERT, WHITE,
         [("No existe el establecimiento", d["NO EXISTE EL ESTABLECIMIENTO"]["n"]),
          ("Fuera de cobertura", d["FUERA DE COBERTURA"]["n"]),
          ("Otros rubros", d["OTROS RUBROS"]["n"])]),
        (5.05, "YA ATENDIDO", M["macro_resultado"]["YA ATENDIDO / COBERTURA EXISTENTE"],
         GRAY, DARK,
         [("Existe como cliente", d["EXISTE COMO CLIENTE"]["n"]),
          ("Compra a mayorista", d["COMPRA A MAYORISTA"]["n"]),
          ("Cliente cadena", d["CLIENTE CADENA"]["n"])]),
        (9.38, "OPORTUNIDAD", M["macro_resultado"]["OPORTUNIDAD"], LIME, DARK,
         [("Se aperturará el cliente", d["SE APERTURARA EL CLIENTE"]["n"])]),
    ]
    for x, etiqueta, total, fill, color, detalle in RAMAS:
        conector(x + 1.62, 2.62, x + 1.62, 2.95)
        caja(x, 2.95, 3.25, 0.72, f"{etiqueta} — {total} POI",
             f"{total}% de las visitas", fill, color, 12)
        yy = 3.95
        for nombre, n in detalle:
            rect(s, x, yy, 3.25, 0.58, fill=LIGHT)
            rect(s, x, yy, 0.06, 0.58, fill=fill)
            tf = tb(s, x + 0.24, yy + 0.15, 2.4, 0.3)
            write(tf, nombre, size=10.5, color=DARK, space_after=0)
            tf = tb(s, x + 2.55, yy + 0.11, 0.55, 0.35, align=PP_ALIGN.RIGHT)
            write(tf, str(n), size=14, bold=True, color=DARK, space_after=0,
                  align=PP_ALIGN.RIGHT)
            yy += 0.70

    rect(s, 0.72, 6.05, 11.90, 0.50, fill=DARK)
    tf = tb(s, 0.98, 6.16, 11.4, 0.32)
    write(tf, [("89 de cada 100 visitas ", {"bold": True, "color": LIME}),
               ("no generan un cliente nuevo: más de la mitad se pierde en información "
                "desactualizada o mal etiquetada, no en rechazo comercial.",
                {"color": WHITE})], size=11.5, space_after=0)
    footer(s)

    # ===========================================================================
    # 9 — MAPA GENERADO
    # ===========================================================================
    s = new_slide()
    title(s, "Panorama general — Dónde se concentró la prueba")
    picture(s, FIGS / "05_mapa_visitas.png", 0.55, 1.48, 12.2, 3.75)
    tf = tb(s, MARGIN, 5.42, 11.9, 1.0)
    write(tf, [("La prueba se concentró en dos focos: ", {}),
               (f"GAF ({M['regiones']['GAF']} POI)", {"bold": True}),
               (" en el suroriente y ", {}),
               (f"LITORAL ({M['regiones']['LITORAL']} POI)", {"bold": True}),
               (" en la costa occidental. En ambos focos los puntos visitados caen "
                "dentro de zonas ya densamente cubiertas por la maestra de clientes: "
                "la prospección no está explorando territorio nuevo.", {})],
          size=12.5, line=1.4)
    nota(s, "Fuente: coordenadas del formulario sobre la maestra de clientes (contexto en gris).")
    footer(s)

    # ===========================================================================
    # 10 — PLACEHOLDER MAPA 1
    # ===========================================================================
    s = new_slide()
    title(s, "Panorama general — Mapa de cobertura")
    placeholder_mapa(s, 0.62, 1.55, 12.1, 4.05,
                     "Espacio reservado para el mapa de cobertura",
                     "Pegar aquí la captura de Kepler / QGIS / Power BI · "
                     "sugerido: POI visitados sobre rutas de preventa, coloreados por resultado")
    tf = tb(s, MARGIN, 5.78, 11.9, 0.55)
    write(tf, [("Datos listos en ", {"color": MID}),
               ("findings/hallazgos_geo.csv", {"font": "Consolas", "color": DARK}),
               (": los 100 puntos con coordenadas, hallazgo y responsabilidad. "
                "Mensaje sugerido: ver si los resultados negativos se agrupan en rutas "
                "o territorios concretos.", {"color": MID})], size=11.5, line=1.35)
    footer(s)

    # ===========================================================================
    # 11 — DIVISOR: HALLAZGOS
    # ===========================================================================
    divisor(new_slide(), "Hallazgos\nClave")

    # ===========================================================================
    # 12 — HALLAZGO 1
    # ===========================================================================
    v = M["validity"]
    s = new_slide()
    title(s, "Hallazgo 1 — Nuestra base de prospección está desactualizada")
    picture(s, FIGS / "03_validity_score.png", 0.55, 1.62, 8.35, 3.05)

    rect(s, 9.20, 1.72, 3.55, 4.20, fill=LIGHT)
    rect(s, 9.20, 1.72, 3.55, 0.075, fill=ALERT)
    tf = tb(s, 9.50, 2.02, 3.0, 3.75)
    write(tf, "El score apunta al revés", size=12, bold=True, color=DARK, space_after=10)
    write(tf, [("Los POI que no existen en terreno tienen un ", {}),
               ("validity_score más alto", {"bold": True}),
               (" que el resto de la base.", {})], size=11.5, first=False,
          space_after=12, line=1.35)
    write(tf, [(f"AUC {dec(v['auc'])}", {"size": 22, "bold": True, "color": ALERT}),
               (f"   (p < 0,001)", {"size": 10, "color": MID})],
          first=False, space_after=8)
    write(tf, [("Mediana NO EXISTE:  ", {}), (dec(v["mediana_caso"]), {"bold": True})],
          size=11.5, first=False, space_after=3, line=1.35)
    write(tf, [("Mediana de la base:  ", {}), (dec(v["mediana_control"]), {"bold": True})],
          size=11.5, first=False, space_after=12, line=1.35)
    write(tf, [("0 de 35", {"bold": True}),
               (" casos cae por debajo del percentil 25 de la base.", {})],
          size=11.5, first=False, space_after=0, line=1.35)

    y = bullets(s, 0.62, 4.95, 8.3, [
        [(f"{d['NO EXISTE EL ESTABLECIMIENTO']['n']} de {M['visitas_unicas']} POI visitados "
          f"({d['NO EXISTE EL ESTABLECIMIENTO']['pct']:.0f}%)", {"bold": True}),
         (" ya no operaban al momento de la visita.", {})],
        [("El efecto se mantiene al controlar por departamento visitado ", {}),
         (f"(AUC {dec(v['auc_controlado'])})", {"bold": True}),
         (": no es un sesgo geográfico.", {})],
        [("Los campos de estado del punto (abierto/cerrado) llegan ", {}),
         ("constantes en toda la base", {"bold": True}),
         (": tampoco aportan señal de cierre.", {})],
    ], size=11.5, gap=6)
    nota(s, f"Mann-Whitney sobre {mil(M['universo_dataplor'])} POI · "
            f"KS = {dec(v['ks'])} (p < 0,001).")
    footer(s)

    # ===========================================================================
    # 13 — HALLAZGO 1B: CURVA DE UMBRAL + EJEMPLOS
    # ===========================================================================
    s = new_slide()
    title(s, "Hallazgo 1 — Filtrar por validity_score no sirve")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.6)
    write(tf, [("Ningún punto de corte del ", {}), ("validity_score", {"font": "Consolas"}),
               (" separa los POI inexistentes: el ", {}), ("lift nunca supera 1,00", {"bold": True}),
               (", es decir, filtrar por score no mejora en nada la elección al azar.", {})],
          size=12.5, line=1.4)

    FILAS = [c for c in M["curva_umbral"] if c["umbral"] in (0.50, 0.70, 0.85, 0.90, 0.95, 0.99)]
    cab = ["Umbral", "% de la base descartada", "% de fallos capturados", "Lift"]
    anchos = [1.35, 2.55, 2.55, 1.15]
    x0, y0 = 0.72, 2.42
    x = x0
    for txt, w in zip(cab, anchos):
        rect(s, x, y0, w, 0.46, fill=DARK)
        tf = tb(s, x + 0.10, y0 + 0.12, w - 0.2, 0.3, align=PP_ALIGN.CENTER)
        write(tf, txt, size=9.5, bold=True, color=WHITE, space_after=0, align=PP_ALIGN.CENTER)
        x += w
    yy = y0 + 0.46
    for i, f in enumerate(FILAS):
        x = x0
        marca = f["lift"] >= 0.9
        vals = [dec(f["umbral"], 2),
                dec(f["% de la base descartada"], 1) + "%",
                dec(f["recall (% de fallos capturados)"], 1) + "%",
                dec(f["lift"], 2)]
        for val, w in zip(vals, anchos):
            rect(s, x, yy, w, 0.42, fill=LIGHT if i % 2 == 0 else WHITE)
            tf = tb(s, x + 0.10, yy + 0.10, w - 0.2, 0.28, align=PP_ALIGN.CENTER)
            write(tf, val, size=10.5, bold=marca, color=ALERT if marca else DARK,
                  space_after=0, align=PP_ALIGN.CENTER)
            x += w
        yy += 0.42
    tf = tb(s, x0, yy + 0.16, 7.6, 0.6)
    write(tf, "Con un corte en 0,95 se descartaría el 75% del universo comprado y aun así "
              "se dejarían pasar la mitad de los POI inexistentes.", size=10.5, color=MID, line=1.35)

    rect(s, 8.55, 2.42, 4.10, 3.45, fill=LIGHT)
    rect(s, 8.55, 2.42, 4.10, 0.075, fill=ALERT)
    tf = tb(s, 8.85, 2.72, 3.55, 0.4)
    write(tf, "Ejemplos: score casi perfecto, local inexistente", size=11, bold=True,
          color=DARK, space_after=0, line=1.25)
    yy = 3.42
    for e in M["ejemplos_no_existe"][:4]:
        tf = tb(s, 8.85, yy, 3.55, 0.55)
        write(tf, e["POI Dataplor"], size=11, bold=True, color=DARK, space_after=1)  # nombre del POI
        write(tf, [(f"{e['Ciudad']}  ·  ", {"color": MID}),
                   (f"score {dec(e['validity_score'])}",
                    {"bold": True, "color": ALERT}),
                   (f"  ·  {int(e['Reseñas'])} reseñas", {"color": MID})],
              size=9.5, first=False, space_after=0)
        yy += 0.60
    nota(s, f"Prevalencia de la base = {M['validity']['n_casos']}/{mil(M['universo_dataplor'])} POI · "
            f"lift 1,00 = el umbral no aporta nada.")
    footer(s)

    # ===========================================================================
    # 14 — PLACEHOLDER MAPA 2
    # ===========================================================================
    s = new_slide()
    title(s, "Hallazgo 1 — Dónde están los POI inexistentes")
    placeholder_mapa(s, 0.62, 1.55, 7.85, 4.05,
                     "Espacio reservado para el mapa de POI inexistentes",
                     "Sugerido: los 35 POI 'no existe' sobre la base de prospección,\n"
                     "dimensionados por validity_score")
    rect(s, 8.78, 1.55, 3.95, 4.05, fill=LIGHT)
    rect(s, 8.78, 1.55, 3.95, 0.075, fill=LIME)
    tf = tb(s, 9.08, 1.88, 3.4, 3.5)
    write(tf, "Qué buscar en el mapa", size=12, bold=True, color=DARK, space_after=12)
    bullets(s, 9.08, 2.35, 3.4, [
        "¿Se agrupan en ciudades concretas o están repartidos?",
        "¿Coinciden con zonas de alta densidad de la maestra?",
        "¿Hay rutas de preventa que concentran el problema?",
    ], size=10.5, gap=8)
    tf = tb(s, 9.08, 4.60, 3.4, 0.9)
    write(tf, [("Coordenadas listas en ", {"color": MID}),
               ("findings/poi_inexistentes.csv", {"font": "Consolas", "color": DARK}),
               (" y en el consolidado ", {"color": MID}),
               ("hallazgos_geo.csv", {"font": "Consolas", "color": DARK}),
               (".", {"color": MID})], size=10, line=1.35)
    footer(s)

    # ===========================================================================
    # 15 — HALLAZGO 2
    # ===========================================================================
    fc = M["fuera_cobertura"]
    s = new_slide()
    title(s, "Hallazgo 2 — «Fuera de cobertura» está mal etiquetado")
    picture(s, FIGS / "04_fuera_cobertura.png", 0.55, 1.58, 8.35, 3.55)

    rect(s, 9.20, 1.72, 3.55, 4.20, fill=LIGHT)
    rect(s, 9.20, 1.72, 3.55, 0.075, fill=LIME)
    tf = tb(s, 9.50, 2.02, 3.0, 3.7)
    write(tf, "No es cobertura, es ruta", size=12, bold=True, color=DARK, space_after=14)
    for cifra, glosa in [
        (f"{fc['dist_max_m']:.0f} m", "es la distancia máxima a un cliente de la maestra."),
        (f"{fc['dist_mediana_m']:.0f} m", "es la distancia mediana."),
        (f"{fc['dentro_radio_n']}/{fc['con_coordenadas']}",
         f"puntos tienen un cliente a menos de {fc['radio_m']} m."),
    ]:
        write(tf, cifra, size=25, bold=True, color=DARK, first=False, space_after=1, line=1.05)
        write(tf, glosa, size=11.5, color=DARK, first=False, space_after=15, line=1.3)

    tf = tb(s, MARGIN, 5.40, 8.3, 0.9)
    write(tf, [("Los ", {}), (f"{fc['n']} puntos", {"bold": True}),
               (" marcados como fuera de cobertura tienen un cliente ya atendido "
                "a menos de 200 metros. La etiqueta no describe una limitación logística: "
                "describe un ", {}),
               ("problema de asignación de ruta de preventa", {"bold": True}), (".", {})],
          size=12, line=1.4)
    nota(s, "Distancia haversine al vecino más cercano de la maestra (BallTree, k=3).")
    footer(s)

    # ===========================================================================
    # 16 — PLACEHOLDER MAPA 3 / EJEMPLOS
    # ===========================================================================
    s = new_slide()
    title(s, "Hallazgo 2 — Ejemplo de punto «fuera de cobertura»")
    placeholder_mapa(s, 0.62, 1.55, 6.05, 4.05,
                     "Espacio para captura del caso",
                     "Sugerido: acercamiento a un punto marcado fuera de cobertura\n"
                     "con el cliente activo más cercano visible")
    placeholder_mapa(s, 6.95, 1.55, 5.78, 4.05,
                     "Espacio para segundo caso",
                     "Sugerido: ficha del POI y del cliente de la maestra\n"
                     "que lo tiene al lado")
    tf = tb(s, MARGIN, 5.78, 11.9, 0.55)
    write(tf, [("Casos con detalle y coordenadas en ", {"color": MID}),
               ("findings/fuera_de_cobertura.csv", {"font": "Consolas", "color": DARK}),
               (" — incluye el pos_id, el nombre y las coordenadas de los tres clientes "
                "más cercanos, para trazar el par en el mapa.", {"color": MID})],
          size=11, line=1.35)
    footer(s)

    # ===========================================================================
    # 17 — HALLAZGO 3
    # ===========================================================================
    ec = M["existe_como_cliente"]
    vc = M["veredicto_cruce"]
    n_verif = ec["detalle"]["POS_ID DECLARADO"]

    s = new_slide()
    title(s, "Hallazgo 3 — Nuestro motor no reconoce clientes que ya existen")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.55)
    write(tf, [("El cruce POI ↔ maestra lo propone ", {}),
               ("nuestro motor de emparejamiento", {"bold": True}),
               (f". De las {ec['total']} propuestas marcadas en campo como «ya es cliente», "
                f"solo {n_verif} traen un pos_id verificable — y al validarlas aparecen "
                "fallos en las dos direcciones.", {})], size=12.5, line=1.4)


    def bloque(x, w, encabezado, filas, total_txt):
        """Desglose vertical con la suma explicita en el encabezado."""
        tf = tb(s, x, 2.22, w, 0.3)
        write(tf, encabezado, size=11, bold=True, color=DARK, space_after=0)
        tf = tb(s, x, 2.48, w, 0.24)
        write(tf, total_txt, size=9, color=MID, space_after=0)
        yy = 2.82
        for n, etiqueta, color in filas:
            rect(s, x, yy, w, 0.50, fill=LIGHT)
            rect(s, x, yy, 0.07, 0.50, fill=color)
            t = tb(s, x + 0.26, yy + 0.13, 0.62, 0.3)
            write(t, str(n), size=16, bold=True, color=DARK, space_after=0)
            t = tb(s, x + 0.95, yy + 0.15, w - 1.15, 0.3)
            write(t, etiqueta, size=10.5, color=DARK, space_after=0)
            yy += 0.56
        return yy


    n_contra = ec["detalle"].get("CONTRADICCION (dice 'no existe')", 0)
    n_libre = ec["detalle"].get("TEXTO LIBRE (no verificable)", 0)
    n_conf = vc.get("DUPLICADO CONFIRMADO", 0)
    n_prob = vc.get("DUPLICADO PROBABLE", 0)
    n_aus = vc.get("POS_ID AUSENTE EN EL CORTE DE LA MAESTRA", 0)
    n_rev = vc.get("REQUIERE REVISION MANUAL", 0)

    bloque(0.72, 5.45,
           f"Las {ec['total']} propuestas, por tipo de referencia",
           [(n_verif, "con pos_id verificable", LIME),
            (n_contra, "el campo las rechaza: «no existe»", ALERT),
            (n_libre, "texto libre, no verificable", MID)],
           f"{n_verif} + {n_contra} + {n_libre} = {ec['total']}")

    bloque(6.90, 5.72,
           f"Los {n_verif} verificables, contrastados contra la maestra",
           [(n_conf, "confirmado por nombre Y ubicación", LIME),
            (n_prob, "probable: coincide nombre O ubicación", MID),
            (n_aus, "el pos_id no está en el corte recibido", ALERT),
            (n_rev, "requieren revisión manual", ALERT)],
           f"{n_conf} + {n_prob} + {n_aus} + {n_rev} = {n_verif}")

    # ------------------------------------------------- el caso revisado a mano
    rect(s, 0.72, 5.02, 11.90, 1.28, fill=DARK)
    rect(s, 0.72, 5.02, 0.09, 1.28, fill=ALERT)
    tf = tb(s, 1.08, 5.20, 11.2, 0.34)
    write(tf, [("Fallo nuestro · falso negativo:  ", {"bold": True, "color": ALERT}),
               ("«Kyro's» y «KAIROS MARKET» son el mismo cliente.", {"bold": True,
                                                                     "color": WHITE})],
          size=12.5, space_after=0)
    tf = tb(s, 1.08, 5.58, 11.2, 0.62)
    write(tf, [("Nuestro motor le dio ", {"color": GRAY}),
               ("36,6 de similitud de nombre", {"bold": True, "color": WHITE}),
               (" y lo dejó salir a campo como prospecto: se gastó una visita en un punto "
                "que ya era cliente. El GPS tampoco lo detectó porque la maestra ubica a ese "
                "cliente ", {"color": GRAY}),
               ("15,4 km de donde realmente está", {"bold": True, "color": WHITE}),
               (".", {"color": GRAY})], size=10.5, line=1.35, space_after=0)
    nota(s, "Validación de tres capas: nombre (token-set + TF-IDF + Levenshtein), dirección y "
            "distancia haversine. El veredicto automático solo señala los casos a revisar; "
            "el de Kyro's se confirmó a mano.", y=6.44)
    footer(s)

    # ===========================================================================
    # 18 — HALLAZGO 3: EJEMPLOS DE CRUCE
    # ===========================================================================
    s = new_slide()
    title(s, "Hallazgo 3 — Ejemplos de cruce")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.4)
    write(tf, "Los tres modos de fallo, con los dos lados del emparejamiento y sus "
              "coordenadas reales.", size=12, color=DARK, space_after=0)

    X_CAMPO, W_CAMPO = 0.72, 5.05
    X_CHIP, W_CHIP = 5.92, 1.34
    X_MAE, W_MAE = 7.42, 5.20
    ALTO, ETIQ, HUECO = 0.94, 0.26, 0.20


    def lado(x, w, y, titulo, color_tit, nombre, ctx, lon, lat, apagado=False):
        tf = tb(s, x + 0.22, y + 0.09, w - 0.44, 0.20)
        write(tf, titulo, size=7.5, bold=True, color=color_tit, space_after=0)
        tf = tb(s, x + 0.22, y + 0.27, w - 0.44, 0.24)
        write(tf, nombre, size=11.5, bold=True,
              color=MID if apagado else DARK, space_after=0)
        tf = tb(s, x + 0.22, y + 0.51, w - 0.44, 0.36)
        if ctx:
            write(tf, ctx, size=8.5, color=MID, space_after=2, line=1.1)
        if lon is not None:
            write(tf, f"lon {dec(lon, 6)}    lat {dec(lat, 6)}", size=8,
                  color=DARK, font="Consolas", first=bool(not ctx), space_after=0)


    yy = 2.06
    for e in M["ejemplos_h3"]:
        rect(s, 0.72, yy, 11.90, ETIQ, fill=DARK)
        tf = tb(s, 0.96, yy + 0.045, 11.4, 0.20)
        write(tf, [(e["modo"].upper(), {"bold": True, "color": LIME}),
                   ("   ·   " + e["glosa"], {"color": WHITE})], size=8.5, space_after=0)

        y = yy + ETIQ
        rect(s, X_CAMPO, y, W_CAMPO, ALTO, fill=LIGHT)
        lado(X_CAMPO, W_CAMPO, y, "LO QUE CAPTURÓ EL CAMPO", MID,
             e["campo_nombre"], e["campo_ctx"], e["campo_lon"], e["campo_lat"])

        hay = e["maestra_lon"] is not None
        rect(s, X_MAE, y, W_MAE, ALTO, fill=LIGHT if hay else WHITE,
             line=None if hay else ALERT, lw=1.2, dash=not hay)
        lado(X_MAE, W_MAE, y, f"MAESTRA · pos_id {e['maestra_id']}",
             MID if hay else ALERT, e["maestra_nombre"], e["maestra_ctx"],
             e["maestra_lon"], e["maestra_lat"], apagado=not hay)

        lejos = (e["distancia_m"] or 0) > 500
        rect(s, X_CHIP, y + 0.13, W_CHIP, ALTO - 0.26,
             fill=ALERT if (lejos or not hay) else GRAY)
        tinta = WHITE if (lejos or not hay) else DARK
        tf = tb(s, X_CHIP, y + 0.24, W_CHIP, 0.5, align=PP_ALIGN.CENTER)
        if e["distancia_m"] is None:
            write(tf, "sin registro", size=9.5, bold=True, color=tinta,
                  space_after=0, align=PP_ALIGN.CENTER)
        else:
            write(tf, f"{mil(e['distancia_m'])} m", size=12.5, bold=True, color=tinta,
                  space_after=1, align=PP_ALIGN.CENTER)
            write(tf, f"nombre {dec(e['score'], 1)}", size=7.5, color=tinta,
                  first=False, align=PP_ALIGN.CENTER, space_after=0)
        yy += ETIQ + ALTO + HUECO

    tf = tb(s, MARGIN, 6.28, 11.9, 0.3)
    write(tf, [("Los 7 casos con todos sus campos en ", {"color": MID}),
               ("findings/ejemplos_hallazgo3.csv", {"font": "Consolas", "color": DARK}),
               (".", {"color": MID})], size=9, space_after=0)
    footer(s)

    # ===========================================================================
    # 18 bis — HALLAZGO 3: CAUSA RAÍZ
    # ===========================================================================
    t = M["titular"]
    s = new_slide()
    title(s, "Hallazgo 3 · causa raíz — Dos convenciones de nombre distintas")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.6)
    write(tf, [("Nuestra base de prospección identifica cada punto por su ", {}),
               ("rótulo comercial", {"bold": True}),
               (" («Smoothies Lios»); la maestra del cliente lo identifica por su ", {}),
               ("titular", {"bold": True}),
               (" («Edvin Oswaldo Tun Cahuec»). Nuestro motor comparaba un campo "
                "contra el otro.", {})], size=12.5, line=1.4)

    # ------------------- los casos hablan mejor que cualquier metrica agregada
    rect(s, 0.72, 2.28, 11.90, 0.44, fill=DARK)
    tf = tb(s, 1.02, 2.38, 5.0, 0.28)
    write(tf, "Lo que dice el rótulo  ·  NUESTRA base de prospección", size=10,
          bold=True, color=WHITE, space_after=0)
    tf = tb(s, 7.05, 2.38, 5.4, 0.28)
    write(tf, "A quién identifica la maestra del cliente", size=10,
          bold=True, color=LIME, space_after=0)

    yy = 2.72
    for i, e in enumerate(t["ejemplos"][:5]):
        rect(s, 0.72, yy, 11.90, 0.50, fill=LIGHT if i % 2 == 0 else WHITE)
        tf = tb(s, 1.02, yy + 0.13, 5.6, 0.3)
        write(tf, e["rotulo"], size=11.5, bold=True, color=DARK, space_after=0)
        tf = tb(s, 6.62, yy + 0.14, 0.4, 0.3)
        write(tf, "→", size=11, color=MID, space_after=0)
        tf = tb(s, 7.05, yy + 0.13, 5.4, 0.3)
        write(tf, e["maestra"].title(), size=11.5, color=ALERT, space_after=0)
        yy += 0.50

    bullets(s, MARGIN, yy + 0.26, 12.0, [
        [(f"El encuestador tuvo que reescribir el nombre en {t['reescritos']} de "
          f"{t['evaluados']} casos", {"bold": True}),
         (" para que coincidiera con la maestra: tecleó el titular, no el rótulo.", {})],
        [(f"{t['pct_patron_persona']}% de la maestra ({mil(t['n_patron_persona'])} registros) "
          f"responde al patrón de nombre de persona", {"bold": True}),
         (f"; solo {t['pct_descriptor_comercial']}% lleva un descriptor comercial "
          f"(estimación por reglas de texto).", {})],
    ], size=11.5, gap=8)
    nota(s, "Prevalencia estimada por ausencia de descriptor comercial en el nombre; "
            "los cinco casos provienen de los cruces validados a mano.", y=6.52)
    footer(s)

    # ===========================================================================
    # 19 — HALLAZGO 4
    # ===========================================================================
    rd = M["rama_d"]
    total_rd = sum(rd.values())
    s = new_slide()
    title(s, "Hallazgo 4 — Qué parte del descarte era realmente evitable")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.55)
    write(tf, [(f"{total_rd} visitas no convirtieron por segmentación, pero solo ", {}),
               (f"{rd['CLIENTE CADENA']} eran evitables", {"bold": True}),
               (f". Las otras {total_rd - rd['CLIENTE CADENA']} son ", {}),
               ("riesgo asumido de prospectar", {"bold": True}),
               (": no se pueden anticipar en gabinete.", {})], size=12.5, line=1.4)

    CASOS = [
        ("COMPRA A MAYORISTA  ·  riesgo asumido", rd["COMPRA A MAYORISTA"],
         "Hay demanda, pero la abastece un tercero.",
         "No es un fallo: solo se descubre visitando. Es además una oportunidad de "
         "conversión de canal que debe enrutarse al equipo de mayoristas.", MID),
        ("OTROS RUBROS  ·  riesgo asumido", rd["OTROS RUBROS"],
         "El POI no pertenece al universo bebible.",
         "Ninguna fuente clasifica el rubro con precisión suficiente para descartarlo "
         "sin ir al punto. Es parte del costo de explorar.", MID),
        ("CLIENTE CADENA  ·  error nuestro", rd["CLIENTE CADENA"],
         "El punto se negocia de forma centralizada.",
         f"Estas sí eran evitables: ninguna de las {rd['CLIENTE CADENA']} venía marcada "
         f"como cadena en nuestra base. El detector de cadenas no las identificó.", ALERT),
    ]
    x = 0.72
    for etiqueta, n, resumen, detalle, color in CASOS:
        rect(s, x, 2.42, 3.85, 3.45, fill=LIGHT)
        rect(s, x, 2.42, 3.85, 0.085, fill=color)
        tf = tb(s, x + 0.30, 2.75, 3.25, 0.5)
        write(tf, etiqueta, size=10.5, bold=True, color=MID, space_after=6)
        write(tf, f"{n}", size=34, bold=True, color=DARK, first=False, space_after=8)
        tf = tb(s, x + 0.30, 4.20, 3.25, 1.5)
        write(tf, resumen, size=12, bold=True, color=DARK, space_after=8, line=1.3)
        write(tf, detalle, size=10.5, color=MID, first=False, line=1.35)
        x += 4.02

    rect(s, 0.72, 6.02, 11.90, 0.50, fill=DARK)
    tf = tb(s, 0.98, 6.13, 11.4, 0.32)
    write(tf, [("Coste evitable real: ", {"bold": True, "color": LIME}),
               (f"{rd['CLIENTE CADENA']}% del esfuerzo de campo. El resto es el precio "
                "normal de prospectar, y conviene decirlo así en lugar de contarlo "
                "como fallo.", {"color": WHITE})], size=11.5, space_after=0)
    footer(s)

    # ===========================================================================
    # 20 — HALLAZGO 5
    # ===========================================================================
    s = new_slide()
    title(s, "Hallazgo 5 — Integridad del formulario de captura")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.55)
    write(tf, "El instrumento de captura admite entradas que no se pueden validar de forma "
              "automática, lo que degrada cualquier análisis posterior.", size=12.5, line=1.4)

    kpi(s, 0.72, 2.35, 3.85, 1.52, f"{M['respuestas_crudas']} → {M['visitas_unicas']}",
        f"{M['ids_duplicados']} POI fueron encuestados dos veces", ALERT)
    kpi(s, 4.74, 2.35, 3.85, 1.52,
        f"{M['existe_como_cliente']['detalle'].get('TEXTO LIBRE (no verificable)', 0)} + "
        f"{M['existe_como_cliente']['detalle'].get('CONTRADICCION (dice \'no existe\')', 0)}",
        "respuestas en texto libre o contradictorias en el campo de referencia a la maestra",
        ALERT)
    kpi(s, 8.76, 2.35, 3.85, 1.52, f"{M['ids_huerfanos']}",
        "IDs del formulario ausentes en la base de prospección — la trazabilidad del ID "
        "sí funciona", LIME)

    tf = tb(s, MARGIN, 4.12, 11.9, 0.4)
    write(tf, "Qué corregir en el formulario", size=14, bold=True, color=DARK, space_after=0)
    bullets(s, MARGIN, 4.62, 11.7, [
        [("Bloquear el reenvío del mismo ", {}), ("ID de punto", {"bold": True}),
         (": hoy se aceptan respuestas duplicadas sin aviso.", {})],
        [("Convertir «EXISTE DENTRO DE NUESTRA BASE DE DATOS» en un campo validado contra la "
          "maestra", {"bold": True}),
         (", en lugar de texto libre que admite «Si existe», «No existe» o «Ya se cerró negocio».", {})],
        [("Hacer obligatorio el ", {}), ("pos_id", {"font": "Consolas"}),
         (" cuando el resultado sea «existe como cliente»: sin él el hallazgo no es auditable.", {})],
        [("Registrar la fecha de corte de la base de prospección usada en cada ola de visitas.", {})],
    ], size=11.5, gap=8)
    footer(s)

    # ===========================================================================
    # 21 — RESUMEN
    # ===========================================================================
    agg = M["cuenta_agregada"]
    s = new_slide()
    title(s, "Resumen — a qué corresponde cada una de las 100 visitas")
    tf = tb(s, MARGIN, BODY_TOP, 11.9, 0.55)
    write(tf, [(f"{agg['FALLO NUESTRO']} visitas eran evitables por nosotros", {"bold": True}),
               (f" y {agg['DATO DESACTUALIZADO']} más con la base al día. Solo ", {}),
               (f"{agg['RIESGO ASUMIDO']} son costo inevitable", {"bold": True}),
               (" de prospectar. Los grupos no se solapan y suman 100.", {})],
          size=12.5, line=1.4)

    FILAS = [
        ("FALLO NUESTRO", agg["FALLO NUESTRO"], ALERT,
         "22 puntos ya eran clientes y 2 eran cadenas: nuestro filtro no los excluyó."),
        ("DATO DESACTUALIZADO", agg["DATO DESACTUALIZADO"], ALERT,
         "POI que ya no existen en terreno. Se evita refrescando la base de prospección."),
        ("RECUPERABLE", agg["RECUPERABLE"], LIME,
         "Mal etiquetados «fuera de cobertura»: tienen un cliente a menos de 200 m."),
        ("RIESGO ASUMIDO", agg["RIESGO ASUMIDO"], MID,
         "Mayorista y otros rubros: solo se descubren visitando. No son fallos."),
        ("RESULTADO ÚTIL", agg["RESULTADO ÚTIL"], LIME,
         "Aperturas conseguidas: el objetivo de la prueba."),
    ]
    ESCALA = 2.55 / max(v for _, v, _, _ in FILAS)

    yy = 2.30
    for etiqueta, n, color, glosa in FILAS:
        tf = tb(s, 0.72, yy + 0.06, 2.35, 0.3)
        write(tf, etiqueta, size=10, bold=True, color=DARK, space_after=0)
        rect(s, 3.15, yy, max(n * ESCALA, 0.30), 0.42, fill=color)
        tf = tb(s, 3.15 + max(n * ESCALA, 0.30) + 0.14, yy + 0.05, 0.7, 0.32)
        write(tf, str(n), size=15, bold=True, color=DARK, space_after=0)
        tf = tb(s, 6.55, yy + 0.09, 6.1, 0.36)
        write(tf, glosa, size=10.5, color=MID, space_after=0, line=1.2)
        yy += 0.62

    # ------------------------------------- falsos negativos / falsos positivos
    rect(s, 0.72, 5.52, 11.90, 0.92, fill=LIGHT)
    rect(s, 0.72, 5.52, 0.09, 0.92, fill=DARK)
    tf = tb(s, 1.06, 5.70, 5.4, 0.6)
    write(tf, [("Falso negativo", {"bold": True, "color": ALERT}),
               ("  ·  no reconocimos clientes que ya existían", {"size": 10, "color": MID})],
          size=11, space_after=3)
    write(tf, "22 puntos salieron a visitar siendo ya clientes. Caso documentado: Kyro's.",
          size=10, color=DARK, first=False, space_after=0, line=1.2)
    tf = tb(s, 6.95, 5.70, 5.5, 0.6)
    write(tf, [("Falso positivo", {"bold": True, "color": DARK}),
               ("  ·  emparejar dos locales distintos", {"size": 10, "color": MID})],
          size=11, space_after=3)
    write(tf, "2 casos quedaron en revisión manual; ninguno se confirmó como error.",
          size=10, color=DARK, first=False, space_after=0, line=1.2)
    footer(s)

    # ===========================================================================
    # 22 — DIVISOR: PRÓXIMOS PASOS
    # ===========================================================================
    divisor(new_slide(), "Próximos\nPasos")

    # ===========================================================================
    # 23 — PRÓXIMOS PASOS (CLIENTE)
    # ===========================================================================
    PANEL = RGBColor(0x2A, 0x2E, 0x31)


    def slide_pasos(titulo, subtitulo, pasos, acento=LIME, s_cab=12.5, s_det=10.5, gap=0.16):
        """Diapositiva oscura con una lista numerada de acciones."""
        sl = new_slide(dark=True)
        title(sl, titulo, dark=True, rule=False)
        bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(MARGIN - 0.48),
                                  Inches(RULE_TOP), Inches(6.6), Inches(0.035))
        bar.fill.solid(); bar.fill.fore_color.rgb = acento
        bar.line.fill.background(); sin_sombra(bar)

        hexagon(sl, 12.35, 2.26, 1.50, fill=PANEL)
        hexagon(sl, 13.65, 3.13, 1.50, fill=PANEL)
        hexagon(sl, 12.35, 4.00, 1.50, fill=PANEL)
        hexagon(sl, 13.65, 4.87, 1.50, fill=acento)
        hexagon(sl, 12.35, 5.74, 1.50, fill=PANEL)

        tf = tb(sl, MARGIN, 1.32, 9.6, 0.32)
        write(tf, subtitulo, size=11.5, color=GRAY, space_after=0)

        ancho = 9.35
        y = 1.90
        for i, (cab, det) in enumerate(pasos, 1):
            hexagon(sl, 0.88, y + 0.24, 0.44, fill=acento)
            t = tb(sl, 0.64, y + 0.09, 0.48, 0.3, align=PP_ALIGN.CENTER)
            write(t, str(i), size=11, bold=True, color=DARK, space_after=0,
                  align=PP_ALIGN.CENTER)
            n = n_lineas(det, ancho, s_det)
            t = tb(sl, 1.40, y, ancho, 0.34 + 0.22 * n)
            write(t, cab, size=s_cab, bold=True, color=acento, space_after=2)
            write(t, det, size=s_det, color=WHITE, first=False, line=1.3)
            y += (s_cab * 1.25 / 72) + (s_det * 1.3 / 72) * n + gap
        footer(sl, dark=True)
        return sl


    slide_pasos(
        "Próximos pasos — Cliente",
        "Acciones que dependen de la operación y de la maestra de clientes.",
        [
            ("Reasignar los puntos «fuera de cobertura»",
             f"Los {fc['n']} puntos tienen un cliente atendido a menos de 200 m: es un ajuste "
             "de ruta de preventa, no una limitación de cobertura."),
            ("Incorporar el nombre comercial a la maestra",
             f"Hoy pos_name guarda al titular: {M['titular']['pct_patron_persona']:.0f}% de los "
             "registros es un nombre de persona. Añadir el nombre del rótulo permitiría cruzar "
             "de forma automática y fiable."),
            ("Entregar cortes de la maestra al día",
             f"{vc.get('POS_ID AUSENTE EN EL CORTE DE LA MAESTRA', 0)} pos_id válidos del sistema "
             "del embotellador no aparecen en el corte que recibimos. Con una entrega periódica "
             "el cruce trabaja sobre datos vigentes."),
            ("Validar la siguiente ola en campo",
             "Ejecutar la próxima prueba sobre la lista ya depurada y con el formulario "
             "corregido, para medir cuánto sube la tasa de apertura."),
        ])

    # ===========================================================================
    # 24 — PRÓXIMOS PASOS (KIN ANALYTICS)
    # ===========================================================================
    slide_pasos(
        "Próximos pasos — Nuestro proceso",
        "Lo que vamos a corregir en Kin Analytics antes de la próxima entrega.",
        s_cab=12.5, s_det=10.5, gap=0.16, pasos=[
            ("Robustecer el motor de emparejamiento",
             f"Reforzar la comparación de nombres para que reconozca variantes de escritura y "
             f"equivalencias fonéticas — «Kyro's» ↔ «KAIROS MARKET» puntuó apenas 36,6 — y sumar "
             f"geolocalización y dirección como criterios de decisión, no solo el nombre."),
            ("Reprocesar y reentregar el cruce",
             f"Volver a correr el emparejamiento con las reglas corregidas y entregar la lista "
             f"de duplicados depurada; hoy solo {vc.get('DUPLICADO CONFIRMADO', 0)} de "
             f"{ec['total']} propuestas resisten la validación."),
            ("Retirar el validity_score de la priorización",
             f"No discrimina (AUC {dec(v['auc'])}, en dirección contraria). Lo sustituimos por "
             "señales de actividad reciente y lo validamos contra esta prueba antes de volver "
             "a publicarlo."),
            ("Actualizar y vigilar la base de prospección",
             f"Refrescar el universo interno y monitorear la tasa de POI inexistentes por ola: "
             f"hoy es {d['NO EXISTE EL ESTABLECIMIENTO']['pct']:.0f}%."),
            ("Robustecer la detección de cadenas",
             f"El filtro ya existe, pero no identificó ninguna de las {rd['CLIENTE CADENA']} "
             f"cadenas visitadas. Reforzarlo cruzando el marcador de cadena con el nombre de la "
             f"enseña antes de generar la lista de visita."),
        ])

    # ===========================================================================
    # 24 — CIERRE
    # ===========================================================================
    s = new_slide(dark=True)
    hexagon(s, 11.2, 3.6, 4.6, fill=RGBColor(0x16, 0x19, 0x1B))
    tf = tb(s, 0.90, 2.60, 8.5, 1.6)
    write(tf, "Gracias", size=40, bold=True, color=WHITE, space_after=10)
    write(tf, "Let knowledge in.", size=17, color=LIME, first=False, space_after=0)
    tf = tb(s, 0.90, 4.55, 8.5, 1.0)
    write(tf, "Revisión QA · Prospección Digital Guatemala · Septiembre 2026",
          size=11.5, color=GRAY, space_after=4)
    write(tf, "Tablas de respaldo en findings/ · métricas en deck_metrics.json",
          size=10.5, color=MID, first=False)
    footer(s, dark=True)


    prs.save(OUT)
    print(f"  -> {OUT.name}  ({len(prs.slides._sldIdLst)} diapositivas)")
    return OUT
