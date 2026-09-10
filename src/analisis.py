# -*- coding: utf-8 -*-
"""El QA: comparacion de textos, geografia y las cuatro ramas del formulario.

Cada funcion `rama_*` recibe las fuentes y devuelve sus tablas; `ejecutar()`
las encadena y deja todo en un `Resultados`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from scipy.stats import ks_2samp, mannwhitneyu
from shapely.geometry import Point
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import BallTree
from unidecode import unidecode

from . import config as cfg
from .datos import MAPA_RESULTADO, Exportador, Fuentes, limites, norm_key


# =========================================================== texto y geografia
def limpiar_nombre(texto) -> str:
    """'2105.Smoothies Lios' -> 'smoothies lios' (quita el codigo interno)."""
    if pd.isna(texto) or not str(texto).strip():
        return ""
    texto = re.sub(r"^\d+[\.\-\s]*", "", str(texto))
    texto = unidecode(texto).lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", texto)).strip()


ABREVIATURAS = {
    r"\bcol\b|\bcolonia\b": "colonia",
    r"\bave?\b|\bavenida\b": "avenida",
    r"\bcll?\b|\bcalle\b": "calle",
    r"\bz\b|\bzn\b|\bzona\b": "zona",
    r"\bkm\b|\bkilometro\b": "km",
    r"\bblvd?\b|\bbulevar\b": "bulevar",
    r"\bno\b|\bnum\b|\bnumero\b": "",
}


def limpiar_direccion(texto) -> str:
    if pd.isna(texto) or not str(texto).strip():
        return ""
    texto = unidecode(str(texto)).lower().strip()
    for patron, reemplazo in ABREVIATURAS.items():
        texto = re.sub(patron, reemplazo, texto)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", texto)).strip()


def sim_tfidf(a: str, b: str) -> float:
    """Similitud de subpalabras via n-gramas de caracteres (0-100)."""
    if not a or not b:
        return 0.0
    try:
        m = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)).fit_transform([a, b])
        return float(cosine_similarity(m[0:1], m[1:2])[0][0]) * 100
    except ValueError:
        return 0.0


def score_ponderado(a: str, b: str, pesos=(0.45, 0.30, 0.25)) -> float:
    """Combina token_set (robusto al orden), TF-IDF y Levenshtein."""
    w_tok, w_tfidf, w_ratio = pesos
    return round(fuzz.token_set_ratio(a, b) * w_tok
                 + sim_tfidf(a, b) * w_tfidf
                 + fuzz.ratio(a, b) * w_ratio, 2)


def clasificar(score: float, umbrales: dict, etiquetas: tuple) -> str:
    if score >= umbrales["exacto"]:
        return etiquetas[0]
    if score >= umbrales["similar"]:
        return etiquetas[1]
    if score >= umbrales["revisar"]:
        return etiquetas[2]
    return etiquetas[3]


def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia geografica en metros entre pares de coordenadas."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return cfg.RADIO_TIERRA_M * 2 * np.arcsin(np.sqrt(a))


def resumen_categoria(serie: pd.Series, titulo: str = "") -> pd.DataFrame:
    out = pd.DataFrame({
        "Cantidad": serie.value_counts(dropna=False),
        "Porcentaje (%)": (serie.value_counts(dropna=False, normalize=True) * 100).round(1),
    })
    out.index.name = titulo or serie.name
    return out


# ===================================================================== salida
@dataclass
class Resultados:
    """Todo lo que produce el analisis, listo para figuras y reporte."""

    fuentes: Fuentes
    metrics: dict = field(default_factory=dict)
    tablas: dict = field(default_factory=dict)

    def __getitem__(self, k):
        return self.tablas[k]


# ============================================================ 1. integridad
def qa_integridad(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    r, m = f.respuestas_raw, res.metrics

    huerfanos = set(r["dataplor_id"]) - set(f.universo["dataplor_id"])
    conteo = r["dataplor_id"].value_counts()
    dups = conteo[conteo > 1]
    errores_id = (r[r["dataplor_id"].isin(dups.index)]
                  .sort_values(["dataplor_id", "Timestamp"]))

    coords_ok = (pd.to_numeric(f.respuestas["Latitud"], errors="coerce").notna()
                 & pd.to_numeric(f.respuestas["Longitud"], errors="coerce").notna())

    exportar(errores_id, "errores_id")
    res.tablas["errores_id"] = errores_id

    m.update(
        universo_dataplor=len(f.universo),
        maestra_total=len(f.clientes),
        maestra_activos=int(f.clientes["activo"].sum()),
        respuestas_crudas=len(r),
        visitas_unicas=len(f.respuestas),
        ids_duplicados=len(dups),
        ids_huerfanos=len(huerfanos),
        coords_validas=int(coords_ok.sum()),
    )


# ============================================================= 2. panorama
def panorama(f: Fuentes, res: Resultados) -> None:
    v, m = f.respuestas, res.metrics

    dist = resumen_categoria(v["resultado"], "DATOS DE VISITA")
    m["distribucion_resultado"] = {
        k: {"n": int(x["Cantidad"]), "pct": float(x["Porcentaje (%)"])}
        for k, x in dist.to_dict("index").items()}

    v["macro_resultado"] = np.select(
        [v["resultado"].isin(cfg.APERTURA),
         v["resultado"].isin(cfg.YA_ATENDIDO),
         v["resultado"].isin(cfg.DESCARTE)],
        ["OPORTUNIDAD", "YA ATENDIDO / COBERTURA EXISTENTE", "DESCARTE"],
        default="OTRO")

    m["macro_resultado"] = {k: int(x) for k, x in v["macro_resultado"].value_counts().items()}
    m["tasa_apertura"] = round(float(v["resultado"].isin(cfg.APERTURA).mean()) * 100, 1)
    m["canales_top"] = {str(k): int(x) for k, x in v["Canal"].value_counts().head(5).items()}
    m["regiones"] = {str(k): int(x) for k, x in v["Region"].value_counts().items()}
    res.tablas["distribucion"] = dist


# ================================================ 3. rama A: existe como cliente
NOMBRE_OK = {"VALIDO_EXACTO", "VALIDO_SIMILAR"}
GEO_OK = {"CORRECTA_EXACTA", "CORRECTA_TOLERANCIA"}

COLS_VAL = ["dataplor_id", "pos_id_norm", "pos_name", "score_nombre",
            "estatus_nombre", "score_direccion", "estatus_direccion",
            "distancia_metros", "estatus_coordenadas",
            "pos_longitude", "pos_latitude"]


def _validar_fila(r, f: Fuentes) -> dict:
    correccion = limpiar_nombre(r[f.C_NOMBRE_OK])
    nombre_campo = (correccion if correccion and correccion not in {"si", "no"}
                    else limpiar_nombre(r[f.C_NOMBRE]))
    nombre_maestra = limpiar_nombre(r["pos_name"])

    if nombre_campo and nombre_maestra:
        sn = score_ponderado(nombre_campo, nombre_maestra)
        estado_nombre = clasificar(sn, cfg.UMBRAL_NOMBRE,
                                   ("VALIDO_EXACTO", "VALIDO_SIMILAR",
                                    "REVISAR_MANUAL", "NO_COINCIDE"))
    else:
        sn, estado_nombre = 0.0, "SIN_DATOS_PARA_COMPARAR"

    dir_campo = limpiar_direccion(r[f.C_DIRECCION])
    dir_maestra = limpiar_direccion(r["pos_addres"])
    if dir_campo and dir_maestra:
        sd = score_ponderado(dir_campo, dir_maestra, pesos=(0.50, 0.30, 0.20))
        estado_dir = clasificar(sd, cfg.UMBRAL_DIRECCION,
                                ("CORRECTA_EXACTA", "CORRECTA_SIMILAR",
                                 "REVISAR_MANUAL", "DESCARTAR_DIFERENTE"))
    else:
        sd, estado_dir = 0.0, "DIRECCION_VACIA"

    d = haversine_m(pd.to_numeric(r["Latitud"], errors="coerce"),
                    pd.to_numeric(r["Longitud"], errors="coerce"),
                    pd.to_numeric(r["pos_latitude"], errors="coerce"),
                    pd.to_numeric(r["pos_longitude"], errors="coerce"))
    if pd.isna(d):
        estado_geo = "COORDENADA_VACIA"
    elif d <= 20:
        estado_geo = "CORRECTA_EXACTA"
    elif d <= cfg.TOLERANCIA_GPS_M:
        estado_geo = "CORRECTA_TOLERANCIA"
    elif d <= cfg.TOLERANCIA_GPS_M * 5:
        estado_geo = "REVISAR_MANUAL"
    else:
        estado_geo = "DESCARTAR_DIFERENTE"

    return {
        "nombre_campo": nombre_campo, "nombre_maestra": nombre_maestra,
        "score_nombre": sn, "estatus_nombre": estado_nombre,
        "dir_campo": dir_campo, "dir_maestra": dir_maestra,
        "score_direccion": sd, "estatus_direccion": estado_dir,
        "distancia_metros": None if pd.isna(d) else round(float(d), 2),
        "estatus_coordenadas": estado_geo,
    }


def rama_existe_cliente(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    m = res.metrics
    ec = f.respuestas[f.respuestas["resultado"] == "EXISTE COMO CLIENTE"].copy()
    ec["ref_bd"] = ec[f.C_EXISTE_BD].astype(str).str.strip()

    es_id = ec["ref_bd"].str.replace(r"\.0$", "", regex=True).str.fullmatch(r"\d{6,}")
    dice_no = ec["ref_bd"].map(norm_key).str.contains(r"\bno\b", na=False)
    ec["tipo_referencia"] = np.select(
        [es_id, dice_no],
        ["POS_ID DECLARADO", "CONTRADICCION (dice 'no existe')"],
        default="TEXTO LIBRE (no verificable)")

    con_id = ec[es_id].copy()
    con_id["pos_id_norm"] = con_id["ref_bd"].str.replace(r"\.0$", "", regex=True)

    maestra = f.clientes.copy()
    maestra["pos_id_norm"] = (maestra["pos_id"].astype(str).str.strip()
                              .str.replace(r"\.0$", "", regex=True))
    cruce = con_id.merge(maestra, on="pos_id_norm", how="left", validate="m:1")

    filas = [_validar_fila(r, f) for _, r in cruce.iterrows()]
    validado = pd.concat([cruce.reset_index(drop=True), pd.DataFrame(filas)], axis=1)

    # pos_name nunca viene vacio en la maestra: un nulo aqui significa que el
    # pos_id no esta en el corte recibido, no que al registro le falte el nombre.
    validado["veredicto"] = np.select(
        [validado["pos_name"].isna(),
         validado["estatus_nombre"].isin(NOMBRE_OK) & validado["estatus_coordenadas"].isin(GEO_OK),
         validado["estatus_nombre"].isin(NOMBRE_OK) | validado["estatus_coordenadas"].isin(GEO_OK)],
        ["POS_ID AUSENTE EN EL CORTE DE LA MAESTRA", "DUPLICADO CONFIRMADO",
         "DUPLICADO PROBABLE"],
        default="REQUIERE REVISION MANUAL")

    cols = [f.C_NOMBRE] + COLS_VAL
    exportar(validado[cols], "existe_como_cliente_validado")
    exportar(validado[validado["pos_name"].isna()][cols], "pos_id_ausente_en_corte")
    exportar(validado[validado["veredicto"] == "REQUIERE REVISION MANUAL"][cols],
             "cruces_a_revisar")

    res.tablas["validado"] = validado
    m["existe_como_cliente"] = {
        "total": len(ec),
        "detalle": {k: int(v) for k, v in ec["tipo_referencia"].value_counts().items()},
    }
    m["veredicto_cruce"] = {k: int(v) for k, v in validado["veredicto"].value_counts().items()}
    m["cruce_pos_id_declarados"] = len(con_id)


# ======================================== 3b. causa raiz: titular vs rotulo
DESCRIPTOR_COMERCIAL = (
    r"\b(?:restaurant\w*|comedor|cafeteria|cafe|tienda|abarrot\w*|super\w*|mercad\w*|"
    r"deposito|licorer\w*|carnicer\w*|panader\w*|tortiller\w*|farmacia|gasolinera|"
    r"estacion|hotel|bar|disco|pizzer\w*|heladeria|kiosco|pulperia|venta|distribuidora|"
    r"comercial|minisuper|market|sala|salon|club|gym|gimnasio|libreria|ferreteria|sa|s a|"
    r"sociedad|anonima|cia|ltda|empresa|corporacion|grupo|centro|almacen|bodega|agencia|"
    r"servicio|autoservicio|refresqueria|fonda|soda|churrasqueria|marisqueria)\b"
)


def causa_raiz_titular(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    """La maestra identifica al titular; el universo, al rotulo comercial."""
    validado = res["validado"]
    comp = validado[validado["pos_name"].notna()].copy()
    comp["nombre_rotulo"] = comp[f.C_NOMBRE].map(limpiar_nombre)
    comp["nombre_tecleado"] = comp[f.C_NOMBRE_OK].map(limpiar_nombre)
    comp["nombre_maestra"] = comp["pos_name"].map(limpiar_nombre)
    comp["sim_rotulo_vs_maestra"] = [
        fuzz.token_set_ratio(r.nombre_rotulo, r.nombre_maestra) for r in comp.itertuples()]
    comp["sim_tecleado_vs_maestra"] = [
        fuzz.token_set_ratio(r.nombre_tecleado, r.nombre_maestra)
        if r.nombre_tecleado not in ("si", "no", "") else np.nan
        for r in comp.itertuples()]

    # prevalencia estimada en toda la maestra: sin descriptor comercial y con
    # tres o mas palabras responde al patron de un nombre de persona
    nombres = f.clientes["pos_name"].astype(str).map(
        lambda t: re.sub(r"[^a-z0-9\s]", " ", unidecode(t).lower()))
    tiene_desc = nombres.str.contains(DESCRIPTOR_COMERCIAL, regex=True, na=False)
    patron_persona = (~tiene_desc) & (nombres.str.split().str.len() >= 3)

    exportar(comp[["dataplor_id", "pos_id_norm", f.C_NOMBRE, "pos_name",
                   "nombre_tecleado", "sim_rotulo_vs_maestra",
                   "sim_tecleado_vs_maestra", "pos_longitude", "pos_latitude"]],
             "titular_vs_nombre_comercial")

    res.tablas["comp"] = comp
    res.metrics["titular"] = {
        "reescritos": int(comp["sim_tecleado_vs_maestra"].notna().sum()),
        "evaluados": len(comp),
        "exactos": int((comp["sim_tecleado_vs_maestra"] == 100).sum()),
        "pct_patron_persona": round(float(patron_persona.mean()) * 100, 1),
        "n_patron_persona": int(patron_persona.sum()),
        "pct_descriptor_comercial": round(float(tiene_desc.mean()) * 100, 1),
        "ejemplos": [{"rotulo": r.nombre_rotulo.title(), "maestra": r.pos_name}
                     for r in comp[comp["sim_rotulo_vs_maestra"] < 60].head(5).itertuples()],
    }


def fichas_ejemplos(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    """Los tres modos de fallo del cruce, con los dos lados y sus coordenadas."""
    validado, comp = res["validado"], res["comp"]
    rev = validado[validado["veredicto"] == "REQUIERE REVISION MANUAL"]
    aus = validado[validado["veredicto"] == "POS_ID AUSENTE EN EL CORTE DE LA MAESTRA"]

    seleccion = [
        ("Falso negativo",
         "Ya era cliente y no lo reconocimos: salió a campo como prospecto.",
         rev.sort_values("distancia_metros", ascending=False).iloc[0]),
        ("Convención de nombre",
         "El cruce solo funcionó porque el encuestador reescribió el titular.",
         comp.sort_values("sim_rotulo_vs_maestra").iloc[0]),
        ("Corte desactualizado",
         "El pos_id es válido en el sistema del embotellador, pero no está en el corte.",
         aus.iloc[0]),
    ]

    def ficha(modo, glosa, r):
        hay = not pd.isna(r["pos_name"])
        d = r["distancia_metros"]
        return {
            "modo": modo, "glosa": glosa,
            "campo_nombre": re.sub(r"^\d+\.", "", str(r[f.C_NOMBRE])).strip(),
            "campo_ctx": f"{r['Region']} · ruta {r['Ruta de preventa']} · {r['Canal']}",
            "campo_lon": round(float(r["Longitud"]), 6),
            "campo_lat": round(float(r["Latitud"]), 6),
            "maestra_nombre": r["pos_name"] if hay else "SIN REGISTRO EN EL CORTE",
            "maestra_id": str(r["pos_id_norm"]),
            "maestra_ctx": f"{r['pos_city']} · {r['pos_channel']}" if hay else "",
            "maestra_lon": round(float(r["pos_longitude"]), 6) if hay else None,
            "maestra_lat": round(float(r["pos_latitude"]), 6) if hay else None,
            "score": None if pd.isna(r["score_nombre"]) else round(float(r["score_nombre"]), 1),
            "distancia_m": None if pd.isna(d) else int(round(d)),
        }

    res.metrics["ejemplos_h3"] = [ficha(m, g, r) for m, g, r in seleccion]

    lado_a = ["dataplor_id", f.C_NOMBRE, "Region", "Ruta de preventa", "Canal",
              f.C_DIRECCION, "Longitud", "Latitud"]
    lado_b = ["pos_id_norm", "pos_name", "pos_city", "pos_addres", "pos_channel",
              "pos_longitude", "pos_latitude"]
    juicio = ["score_nombre", "estatus_nombre", "distancia_metros",
              "estatus_coordenadas", "veredicto"]

    partes = []
    for etiqueta, df in [("1. Falso negativo / revisión manual", rev),
                         ("2. pos_id ausente en el corte", aus),
                         ("3. La maestra guarda al titular",
                          comp.sort_values("sim_rotulo_vs_maestra").head(3))]:
        d = df[lado_a + lado_b + juicio].copy()
        d.insert(0, "modo_de_fallo", etiqueta)
        partes.append(d)

    exportar(pd.concat(partes, ignore_index=True), "ejemplos_hallazgo3")


# ================================================== 4. rama B: no existe
def rama_no_existe(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    ids = set(f.respuestas.loc[f.respuestas["resultado"] == "NO EXISTE EL ESTABLECIMIENTO",
                               "dataplor_id"].dropna())
    dp = f.universo.copy()
    dp["validity_score"] = pd.to_numeric(dp["validity_score"], errors="coerce")
    dp["NO_EXISTE"] = dp["dataplor_id"].isin(ids)

    caso = dp.loc[dp["NO_EXISTE"], "validity_score"].dropna()
    control = dp.loc[~dp["NO_EXISTE"], "validity_score"].dropna()

    u, p_mw = mannwhitneyu(caso, control, alternative="two-sided")
    auc = u / (len(caso) * len(control))
    ks, p_ks = ks_2samp(caso, control)
    pct = caso.apply(lambda v: (control < v).mean())

    prev = dp["NO_EXISTE"].mean()
    curva = []
    for thr in (0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99):
        mk = (dp["validity_score"] < thr).fillna(False)
        prec = dp["NO_EXISTE"][mk].mean() if mk.sum() else np.nan
        curva.append({
            "umbral": thr,
            "recall (% de fallos capturados)": round(mk[dp["NO_EXISTE"]].mean() * 100, 1),
            "% de la base descartada": round(mk.mean() * 100, 1),
            "lift": round(prec / prev, 2) if mk.sum() else np.nan,
        })

    # control del sesgo geografico: solo los departamentos visitados
    deptos = sorted(set(dp.loc[dp["NO_EXISTE"], "state"].dropna()))
    sub = dp[dp["state"].isin(deptos)]
    a = sub.loc[sub["NO_EXISTE"], "validity_score"].dropna()
    b = sub.loc[~sub["NO_EXISTE"], "validity_score"].dropna()
    u2, _ = mannwhitneyu(a, b, alternative="two-sided")

    exportar(dp.loc[dp["NO_EXISTE"],
                    ["dataplor_id", "name", "state", "city", "validity_score",
                     "data_quality_confidence_score", "open_closed_status",
                     "number_of_reviews", "latitude", "longitude"]]
               .assign(percentil_en_base=pct.values)
               .sort_values("validity_score", ascending=False),
             "poi_inexistentes")

    ej = (dp.loc[dp["NO_EXISTE"], ["name", "city", "validity_score", "number_of_reviews"]]
            .sort_values("validity_score", ascending=False).head(5))
    ej.columns = ["POI Dataplor", "Ciudad", "validity_score", "Reseñas"]

    res.tablas["universo"] = dp
    res.tablas["caso"], res.tablas["control"] = caso, control
    res.metrics["validity"] = {
        "auc": round(float(auc), 3), "p_mw": float(p_mw),
        "ks": round(float(ks), 3), "p_ks": float(p_ks),
        "mediana_caso": round(float(caso.median()), 4),
        "mediana_control": round(float(control.median()), 4),
        "media_caso": round(float(caso.mean()), 4),
        "media_control": round(float(control.mean()), 4),
        "percentil_mediano_casos": round(float(pct.median()), 3),
        "casos_bajo_p25": int((pct < 0.25).sum()),
        "n_casos": len(caso),
        "auc_controlado": round(float(u2 / (len(a) * len(b))), 3),
        "departamentos": deptos,
    }
    res.metrics["curva_umbral"] = curva
    res.metrics["ejemplos_no_existe"] = ej.to_dict("records")


# ============================================ 5. rama C: fuera de cobertura
def rama_fuera_cobertura(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    maestra = f.clientes.dropna(subset=["pos_latitude", "pos_longitude"]).copy()
    for c in ("pos_latitude", "pos_longitude"):
        maestra[c] = pd.to_numeric(maestra[c], errors="coerce")
    maestra = maestra.dropna(subset=["pos_latitude", "pos_longitude"])

    fc = f.respuestas[f.respuestas["resultado"] == "FUERA DE COBERTURA"].copy()
    ooc = fc.copy()
    ooc["Latitud"] = pd.to_numeric(ooc["Latitud"], errors="coerce")
    ooc["Longitud"] = pd.to_numeric(ooc["Longitud"], errors="coerce")
    ooc = ooc.dropna(subset=["Latitud", "Longitud"])

    tree = BallTree(np.radians(maestra[["pos_latitude", "pos_longitude"]].values),
                    metric="haversine")
    dist_rad, idx = tree.query(np.radians(ooc[["Latitud", "Longitud"]].values), k=3)
    dist_m = dist_rad * cfg.RADIO_TIERRA_M

    ooc["dist_cliente_1_m"] = np.round(dist_m[:, 0], 1)
    ooc["dist_cliente_3_m"] = np.round(dist_m[:, 2], 1)
    ooc["dist_promedio_top3_m"] = np.round(dist_m.mean(axis=1), 1)
    for k in range(3):
        ooc[f"top_{k+1}_pos_id"] = maestra["pos_id"].values[idx[:, k]]
        ooc[f"top_{k+1}_pos_name"] = maestra["pos_name"].values[idx[:, k]]
        ooc[f"top_{k+1}_activo"] = maestra["activo"].values[idx[:, k]]
        # las coordenadas del vecino permiten dibujar el par en el mapa
        ooc[f"top_{k+1}_longitud"] = maestra["pos_longitude"].values[idx[:, k]]
        ooc[f"top_{k+1}_latitud"] = maestra["pos_latitude"].values[idx[:, k]]

    dentro = ooc["dist_cliente_1_m"] <= cfg.RADIO_COBERTURA_M
    exportar(ooc[[f.C_NOMBRE, "dataplor_id", "Region", "Ruta de preventa", "Canal",
                  "Longitud", "Latitud", "dist_cliente_1_m", "dist_cliente_3_m",
                  "dist_promedio_top3_m", "top_1_pos_id", "top_1_pos_name",
                  "top_1_activo", "top_1_longitud", "top_1_latitud"]],
             "fuera_de_cobertura")

    res.tablas["ooc"] = ooc
    res.tablas["maestra_geo"] = maestra
    res.metrics["fuera_cobertura"] = {
        "n": len(fc), "con_coordenadas": len(ooc),
        "dist_min_m": float(ooc["dist_cliente_1_m"].min()),
        "dist_mediana_m": float(ooc["dist_cliente_1_m"].median()),
        "dist_max_m": float(ooc["dist_cliente_1_m"].max()),
        "dist_prom_top3_max_m": float(ooc["dist_promedio_top3_m"].max()),
        "dentro_radio_n": int(dentro.sum()),
        "radio_m": cfg.RADIO_COBERTURA_M,
    }


# ================================================== 6. rama D: segmentacion
def rama_segmentacion(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    rd = f.respuestas[f.respuestas["resultado"].isin(
        ["COMPRA A MAYORISTA", "OTROS RUBROS", "CLIENTE CADENA"])].copy()

    cadena = rd[rd["resultado"] == "CLIENTE CADENA"]
    info = f.universo[f.universo["dataplor_id"].isin(cadena["dataplor_id"])]

    exportar(rd[[f.C_NOMBRE, "dataplor_id", "resultado", "Region", "Canal",
                 "Ruta de preventa", "Latitud", "Longitud"]], "errores_segmentacion")

    res.tablas["rama_d"] = rd
    res.metrics["rama_d"] = {k: int(v) for k, v in rd["resultado"].value_counts().items()}
    res.metrics["cadenas_marcadas_en_dataplor"] = int(
        info["identified_as_chain"].fillna(False).astype(bool).sum())


# ========================================= 7. geografia y cuenta consolidada
def geografia(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    p = f.pais
    adm0, deptos = limites(p)

    def asignar(lat, lon, tol_m=cfg.TOLERANCIA_COSTA_M):
        """Departamento que contiene el punto.

        La linea de costa oficial esta generalizada, asi que los puntos de playa
        caen unas decenas de metros fuera del poligono. Se asignan al mas cercano
        mientras no superen `tol_m`; mas alla de eso se marcan fuera del pais.
        """
        if pd.isna(lat) or pd.isna(lon):
            return pd.Series({"departamento": None, "dist_borde_m": np.nan})
        punto = Point(lon, lat)
        for nombre, poly in deptos.items():
            if poly.covers(punto):
                return pd.Series({"departamento": nombre, "dist_borde_m": 0.0})
        nombre, d = min(((n, poly.distance(punto) * 111_320) for n, poly in deptos.items()),
                        key=lambda t: t[1])
        return pd.Series({"departamento": nombre if d <= tol_m else "FUERA DEL PAIS",
                          "dist_borde_m": round(d, 1)})

    geo = f.respuestas.copy()
    geo["lat"] = pd.to_numeric(geo["Latitud"], errors="coerce")
    geo["lon"] = pd.to_numeric(geo["Longitud"], errors="coerce")
    geo = geo.dropna(subset=["lat", "lon"])
    geo[["departamento", "dist_borde_m"]] = geo.apply(
        lambda r: asignar(r["lat"], r["lon"]), axis=1)

    res.tablas["geo"] = geo
    res.tablas["deptos"] = deptos
    res.tablas["adm0"] = adm0
    res.metrics["departamentos"] = {
        str(k): int(v) for k, v in geo["departamento"].value_counts().items()}
    res.metrics["puntos_fuera_del_pais"] = int((geo["departamento"] == "FUERA DEL PAIS").sum())
    res.metrics["puntos_en_costa"] = int(((geo["dist_borde_m"] > 0)
                                          & (geo["departamento"] != "FUERA DEL PAIS")).sum())


def cuenta_visitas(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    """Reparte las visitas por responsabilidad, sin solapes y sumando el total."""
    D = {k: v["n"] for k, v in res.metrics["distribucion_resultado"].items()}

    filas = []
    for resultado, (hallazgo, responsabilidad) in cfg.CLASIFICACION.items():
        if resultado in D:
            filas.append({"Concepto": hallazgo, "Visitas": D[resultado],
                          "Responsabilidad": responsabilidad,
                          "Nota": cfg.DETALLE_CAUSA[resultado]})
    cuenta = pd.DataFrame(filas)

    total = res.metrics["visitas_unicas"]
    if cuenta["Visitas"].sum() != total:
        raise AssertionError(f"la cuenta da {cuenta['Visitas'].sum()}, no {total}")

    agg = cuenta.groupby("Responsabilidad", sort=False)["Visitas"].sum()
    exportar(cuenta, "cuenta_de_las_visitas", geo=False)

    res.tablas["cuenta"] = cuenta
    res.metrics["cuenta"] = cuenta.to_dict("records")
    res.metrics["cuenta_agregada"] = {k: int(v) for k, v in agg.items()}


def consolidado_geo(f: Fuentes, exportar: Exportador, res: Resultados) -> None:
    """Un archivo con todos los puntos, su hallazgo y sus coordenadas."""
    hg = res["geo"].copy()
    hg["hallazgo"] = hg["resultado"].map(lambda r: cfg.CLASIFICACION[r][0])
    hg["responsabilidad"] = hg["resultado"].map(lambda r: cfg.CLASIFICACION[r][1])
    hg = hg.rename(columns={"lon": "Longitud_pto", "lat": "Latitud_pto"})

    dp = res["universo"]
    hg = hg.merge(dp.loc[dp["NO_EXISTE"], ["dataplor_id", "validity_score"]],
                  on="dataplor_id", how="left")
    hg = hg.merge(res["ooc"][["dataplor_id", "dist_cliente_1_m", "top_1_pos_id",
                              "top_1_pos_name", "top_1_longitud", "top_1_latitud"]],
                  on="dataplor_id", how="left")
    hg = hg.merge(res["validado"][["dataplor_id", "pos_id_norm", "pos_name", "veredicto",
                                   "score_nombre", "distancia_metros",
                                   "pos_longitude", "pos_latitude"]],
                  on="dataplor_id", how="left")

    cols = ["dataplor_id", f.C_NOMBRE, "resultado", "hallazgo", "responsabilidad",
            "departamento", "Region", "Canal", "Ruta de preventa",
            "Longitud_pto", "Latitud_pto",
            "pos_id_norm", "pos_name", "veredicto", "score_nombre", "distancia_metros",
            "pos_longitude", "pos_latitude",
            "dist_cliente_1_m", "top_1_pos_id", "top_1_pos_name",
            "top_1_longitud", "top_1_latitud", "validity_score"]
    salida = hg[cols].sort_values(["responsabilidad", "hallazgo"])

    if len(salida) != res.metrics["visitas_unicas"]:
        raise AssertionError("faltan puntos en la exportacion geografica")

    exportar(salida, "hallazgos_geo")
    res.tablas["hallazgos_geo"] = salida


def formulario_con_causa(f: Fuentes, res: Resultados) -> Path:
    """Devuelve el formulario original con la causa escrita en `Comentario`."""
    m = res.metrics
    d = f.respuestas_raw.copy()
    d["_resultado"] = d[f.C_VISITA].map(norm_key).str.upper().map(MAPA_RESULTADO)

    d["responsabilidad"] = d["_resultado"].map(lambda r: cfg.CLASIFICACION[r][1])
    d["hallazgo"] = d["_resultado"].map(lambda r: cfg.CLASIFICACION[r][0])
    d = d.merge(res["ooc"][["dataplor_id", "dist_cliente_1_m"]],
                on="dataplor_id", how="left")
    d["_dup"] = d.groupby("dataplor_id")["dataplor_id"].transform("size") > 1

    def redactar(r):
        partes = [f"{r['responsabilidad']} · {cfg.DETALLE_CAUSA[r['_resultado']]}"]
        if pd.notna(r["dist_cliente_1_m"]):
            partes.append(f"Cliente más cercano de la maestra a {r['dist_cliente_1_m']:.0f} m.")
        if r["_dup"]:
            partes.append("Respuesta duplicada: este punto se encuestó más de una vez.")
        previo = r.get("Comentario")
        if pd.notna(previo) and str(previo).strip():
            partes.append(f"[comentario original: {str(previo).strip()}]")
        return "  ".join(partes)

    d["Comentario"] = d.apply(redactar, axis=1)
    salida = d[list(f.respuestas_raw.columns) + ["responsabilidad", "hallazgo"]]

    ruta = f.pais.out / f"Respuestas {f.pais.nombre} - con causa.xlsx"
    salida.to_excel(ruta, index=False)
    print(f"  -> {ruta.name}  ({len(salida)} filas)")
    res.tablas["con_causa"] = salida
    return ruta


# ================================================================ resumen
def resumen_hallazgos(exportar: Exportador, res: Resultados) -> None:
    m = res.metrics
    v = m["veredicto_cruce"]
    filas = [
        ("Integridad del formulario",
         f"{m['ids_duplicados']} POI encuestados dos veces "
         f"({m['respuestas_crudas']} respuestas para {m['visitas_unicas']} puntos)."),
        ("Tasa de apertura",
         f"solo {m['tasa_apertura']}% de las visitas termina en apertura."),
        ("Vigencia del universo",
         f"{m['distribucion_resultado']['NO EXISTE EL ESTABLECIMIENTO']['pct']}% de los "
         f"POI visitados no existe en terreno."),
        ("validity_score no anticipa el fallo",
         f"AUC={m['validity']['auc']}: los POI inexistentes tienen score MAS alto "
         f"({m['validity']['mediana_caso']} vs {m['validity']['mediana_control']})."),
        ("'Fuera de cobertura' mal etiquetado",
         f"{m['fuera_cobertura']['dentro_radio_n']}/{m['fuera_cobertura']['con_coordenadas']} "
         f"con un cliente a menos de {cfg.RADIO_COBERTURA_M} m."),
        ("Emparejamiento contra la maestra",
         f"de {m['cruce_pos_id_declarados']} pos_id, "
         f"{v.get('REQUIERE REVISION MANUAL', 0)} requieren revision y "
         f"{v.get('POS_ID AUSENTE EN EL CORTE DE LA MAESTRA', 0)} no estan en el corte."),
        ("Causa raiz del cruce",
         f"{m['titular']['pct_patron_persona']}% de la maestra identifica al titular, "
         f"no al local."),
        ("Errores de segmentacion",
         f"{sum(m['rama_d'].values())} visitas en mayoristas, otros rubros o cadenas."),
    ]
    tabla = pd.DataFrame(filas, columns=["Hallazgo", "Evidencia"])
    exportar(tabla, "hallazgos_resumen", geo=False)
    res.tablas["hallazgos"] = tabla


# ================================================================ pipeline
def ejecutar(p, con_formulario: bool = True) -> Resultados:
    """Corre el QA completo y deja todo en `output/`."""
    p.crear_carpetas()
    f = Fuentes(p)
    print(f)

    exportar = Exportador(p.findings)
    exportar.registrar_geo("dataplor_id", f.respuestas_raw, "Longitud", "Latitud")
    exportar.registrar_geo("dataplor_id", f.universo, "longitude", "latitude")
    exportar.registrar_geo("pos_id", f.clientes, "pos_longitude", "pos_latitude")

    res = Resultados(fuentes=f)
    qa_integridad(f, exportar, res)
    panorama(f, res)
    rama_existe_cliente(f, exportar, res)
    causa_raiz_titular(f, exportar, res)
    fichas_ejemplos(f, exportar, res)
    rama_no_existe(f, exportar, res)
    rama_fuera_cobertura(f, exportar, res)
    rama_segmentacion(f, exportar, res)
    geografia(f, exportar, res)
    cuenta_visitas(f, exportar, res)
    consolidado_geo(f, exportar, res)
    resumen_hallazgos(exportar, res)
    if con_formulario:
        formulario_con_causa(f, res)
    return res
