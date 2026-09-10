# -*- coding: utf-8 -*-
"""Carga de fuentes y exportacion de hallazgos.

La regla del modulo: todo archivo de puntos que salga a `findings/` lleva
`longitud` y `latitud`. La garantia vive en `exportar()`, no repartida por el
codigo de analisis.
"""
from __future__ import annotations

import re
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

from .config import Pais

# --------------------------------------------------------------- normalizar
def norm_key(texto) -> str:
    """Clave sin tildes, en minusculas y sin puntuacion."""
    if pd.isna(texto):
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def col(df: pd.DataFrame, *fragmentos: str) -> str:
    """Resuelve el nombre real de una columna a partir de fragmentos.

    Protege el pipeline de los encabezados con tilde del formulario, que
    cambian de codificacion segun quien exporte el Excel.
    """
    claves = [norm_key(f) for f in fragmentos]
    for c in df.columns:
        if all(k in norm_key(c) for k in claves):
            return c
    raise KeyError(f"sin columna que contenga {fragmentos}")


# ------------------------------------------------------------------- carga
MAPA_RESULTADO = {
    "NO EXISTE EL ESTABLECIMIENTO": "NO EXISTE EL ESTABLECIMIENTO",
    "EXISTE COMO CLIENTE": "EXISTE COMO CLIENTE",
    "FUERA DE COBERTURA": "FUERA DE COBERTURA",
    "SE APERTURARA EL CLIENTE": "SE APERTURARA EL CLIENTE",
    "COMPRA A MAYORISTA": "COMPRA A MAYORISTA",
    "OTROS RUBROS": "OTROS RUBROS",
    "CLIENTE CADENA": "CLIENTE CADENA",
}


class Fuentes:
    """Las tres entradas del QA, ya cargadas y con las columnas resueltas."""

    def __init__(self, p: Pais):
        self.pais = p
        self.respuestas_raw = pd.read_excel(p.buscar(p.patron_respuestas))
        self.universo = pd.read_csv(p.buscar(p.patron_universo), low_memory=False)
        self.clientes = pd.read_csv(p.buscar(p.patron_clientes), low_memory=False)

        r = self.respuestas_raw
        self.C_NOMBRE = col(r, "codigo de cliente", "nombre")
        self.C_NOMBRE_OK = col(r, "es correcto el nombre")
        self.C_DIRECCION = col(r, "direccion")
        self.C_EXISTE_BD = col(r, "existe dentro de nuestra base")
        self.C_VISITA = col(r, "datos de visita")

        # la maestra mezcla activos e inactivos
        self.clientes["activo"] = self.clientes["pos_fecha_baja"].isna()

        # una fila por POI: se conserva la primera respuesta de cada uno
        vis = r.drop_duplicates(subset=["dataplor_id"], keep="first").copy()
        vis["resultado"] = vis[self.C_VISITA].map(norm_key).str.upper()
        sin_mapear = set(vis["resultado"]) - set(MAPA_RESULTADO)
        if sin_mapear:
            raise ValueError(f"categorias no contempladas: {sin_mapear}")
        vis["resultado"] = vis["resultado"].map(MAPA_RESULTADO)
        self.respuestas = vis

    def __repr__(self) -> str:
        return (f"<Fuentes {self.pais.nombre}: {len(self.respuestas_raw)} respuestas, "
                f"{len(self.respuestas)} POI unicos, {len(self.universo):,} universo, "
                f"{len(self.clientes):,} maestra>")


def limites(p: Pais) -> tuple:
    """Contorno nacional y divisiones administrativas (geoBoundaries gbOpen)."""
    import json
    from shapely.geometry import shape

    p.geo.mkdir(parents=True, exist_ok=True)
    for nombre, url in p.url_geo.items():
        destino = p.geo / nombre
        if not destino.exists():
            print(f"  descargando {nombre}")
            urllib.request.urlretrieve(url, destino)

    def leer(nombre):
        return json.loads((p.geo / nombre).read_text(encoding="utf-8"))

    adm0 = shape(leer(f"{p.iso3.lower()}_adm0.geojson")["features"][0]["geometry"])
    adm1 = {f["properties"]["shapeName"]: shape(f["geometry"])
            for f in leer(f"{p.iso3.lower()}_adm1.geojson")["features"]}
    return adm0, adm1


# ------------------------------------------------------------- exportacion
COL_LON, COL_LAT = "longitud", "latitud"

# Pares que representan la coordenada DEL PROPIO PUNTO, en orden de preferencia.
# `pos_longitude`/`pos_latitude` (maestra) y `top_1_*` (vecino) quedan fuera a
# proposito: describen otro lugar, y usarlas pondria el punto donde no va.
PARES_COORD = [
    ("Longitud", "Latitud"),          # capturada en campo
    ("Longitud_pto", "Latitud_pto"),  # ya renombrada en el consolidado
    ("longitude", "latitude"),        # POI de la base de prospeccion
]


class Exportador:
    """Escribe los hallazgos garantizando que se puedan mapear."""

    def __init__(self, destino: Path):
        self.destino = destino
        self.destino.mkdir(parents=True, exist_ok=True)
        self.fuentes_geo: list[tuple] = []

    def registrar_geo(self, id_col: str, df: pd.DataFrame, lon: str, lat: str) -> None:
        """Declara de donde sacar lon/lat para un identificador dado."""
        f = (df[[id_col, lon, lat]].dropna(subset=[id_col])
             .drop_duplicates(subset=[id_col]))
        self.fuentes_geo.append((id_col, f, lon, lat))

    def _con_coordenadas(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        for lon, lat in PARES_COORD:              # ya vienen en el propio df
            if lon in out.columns and lat in out.columns:
                x = pd.to_numeric(out[lon], errors="coerce")
                y = pd.to_numeric(out[lat], errors="coerce")
                if x.notna().any() and y.notna().any():
                    out[COL_LON], out[COL_LAT] = x, y
                    break

        if COL_LON not in out.columns:            # recuperarlas por identificador
            for id_col, fuente, lon, lat in self.fuentes_geo:
                if id_col in out.columns:
                    m = out[[id_col]].merge(fuente, on=id_col, how="left")
                    out[COL_LON] = pd.to_numeric(m[lon], errors="coerce").values
                    out[COL_LAT] = pd.to_numeric(m[lat], errors="coerce").values
                    break

        if COL_LON in out.columns:                # lon/lat al frente
            resto = [c for c in out.columns if c not in (COL_LON, COL_LAT)]
            out = out[[COL_LON, COL_LAT] + resto]
        return out

    def __call__(self, df: pd.DataFrame, nombre: str, geo: bool = True) -> Path:
        """Guarda `df` como findings/<nombre>.csv.

        Con `geo=True` (por defecto) el archivo sale con `longitud` y `latitud`
        al inicio. Si no hay forma de resolverlas la exportacion falla, en vez
        de dejar un archivo que despues no se puede mapear. `geo=False` es para
        tablas agregadas que no representan puntos.
        """
        faltan = 0
        if geo:
            df = self._con_coordenadas(df)
            if COL_LON not in df.columns:
                raise ValueError(
                    f"'{nombre}': sin coordenadas y sin identificador para "
                    f"recuperarlas. Usa geo=False si no son puntos.")
            faltan = int(df[[COL_LON, COL_LAT]].isna().any(axis=1).sum())

        ruta = self.destino / f"{nombre}.csv"
        df.to_csv(ruta, index=False, encoding="utf-8-sig")
        aviso = "" if not faltan else f"  [!] {faltan} sin coordenada"
        print(f"  -> {ruta.name}  ({len(df)} filas){aviso}")
        return ruta
