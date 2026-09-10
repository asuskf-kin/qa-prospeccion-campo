# -*- coding: utf-8 -*-
"""Rutas, umbrales y paleta. Un pais = una entrada en PAISES."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"


# --------------------------------------------------------------------- pais
@dataclass(frozen=True)
class Pais:
    """Todo lo que cambia de un pais a otro."""

    slug: str                  # carpeta bajo data/
    nombre: str                # como se escribe en el reporte
    iso3: str                  # para descargar los limites administrativos
    patron_clientes: str       # glob del csv de la maestra
    patron_universo: str       # glob del csv de la base de prospeccion
    patron_respuestas: str     # glob del excel del formulario
    lat_centro: float          # para la relacion de aspecto de los mapas
    bbox: tuple                # (lon_min, lon_max, lat_min, lat_max)
    divisiones: str = "departamentos"

    @property
    def dir(self) -> Path:
        return RAIZ / "data" / self.slug

    @property
    def raw(self) -> Path:
        return self.dir / "raw"

    @property
    def geo(self) -> Path:
        return self.dir / "geo"

    @property
    def out(self) -> Path:
        return self.dir / "output"

    @property
    def findings(self) -> Path:
        return self.out / "findings"

    @property
    def figs(self) -> Path:
        return self.out / "figs"

    @property
    def deck(self) -> Path:
        return self.out / "deck"

    @property
    def metrics(self) -> Path:
        return self.out / "deck_metrics.json"

    def crear_carpetas(self) -> None:
        for d in (self.raw, self.geo, self.findings, self.figs, self.deck):
            d.mkdir(parents=True, exist_ok=True)

    def buscar(self, patron: str) -> Path:
        """Primer archivo de raw/ que coincide con el patron."""
        encontrados = sorted(self.raw.glob(patron))
        if not encontrados:
            raise FileNotFoundError(
                f"{self.nombre}: no hay ningun archivo '{patron}' en {self.raw}")
        return encontrados[0]

    @property
    def url_geo(self) -> dict:
        base = ("https://github.com/wmgeolab/geoBoundaries/raw/9469f09/"
                f"releaseData/gbOpen/{self.iso3}")
        return {
            f"{self.iso3.lower()}_adm0.geojson":
                f"{base}/ADM0/geoBoundaries-{self.iso3}-ADM0.geojson",
            f"{self.iso3.lower()}_adm1.geojson":
                f"{base}/ADM1/geoBoundaries-{self.iso3}-ADM1.geojson",
        }


PAISES = {
    "guatemala": Pais(
        slug="guatemala",
        nombre="Guatemala",
        iso3="GTM",
        patron_clientes="Clientes_*.csv",
        patron_universo="Dataplor_*.csv",
        patron_respuestas="Respuestas*.xlsx",
        lat_centro=15.5,
        bbox=(-92.4, -88.1, 13.5, 18.0),
    ),
}


def pais(slug: str) -> Pais:
    try:
        return PAISES[slug.lower()]
    except KeyError:
        raise SystemExit(
            f"pais desconocido: '{slug}'. Disponibles: {', '.join(PAISES)}")


# ----------------------------------------------------------------- umbrales
UMBRAL_NOMBRE = {"exacto": 88, "similar": 70, "revisar": 50}
UMBRAL_DIRECCION = {"exacto": 85, "similar": 65, "revisar": 45}
TOLERANCIA_GPS_M = 100        # margen normal de antena GPS
RADIO_COBERTURA_M = 500       # a partir de aqui se considera "lejos"
TOLERANCIA_COSTA_M = 200      # la linea de costa oficial esta generalizada
RADIO_TIERRA_M = 6_371_000.0


# -------------------------------------------------------------------- marca
KIN = {
    "dark": "#202427",
    "lime": "#E6FD01",
    "gray": "#D8D9D4",
    "light": "#EFF0EB",
    "mid": "#8A8D88",
    "alert": "#E5326A",
    "white": "#FFFFFF",
}

FUENTE = "Segoe UI"
FUENTE_BOLD = "Segoe UI Semibold"


# ------------------------------------------- taxonomia de responsabilidades
# Cada resultado del formulario cae en exactamente una categoria. No se solapan
# y suman el total de visitas: es la base del resumen ejecutivo.
CLASIFICACION = {
    "SE APERTURARA EL CLIENTE":     ("Apertura conseguida", "RESULTADO ÚTIL"),
    "EXISTE COMO CLIENTE":          ("Ya era cliente", "FALLO NUESTRO"),
    "CLIENTE CADENA":               ("Cadena no detectada", "FALLO NUESTRO"),
    "NO EXISTE EL ESTABLECIMIENTO": ("POI que ya no existe", "DATO DESACTUALIZADO"),
    "FUERA DE COBERTURA":           ("Mal etiquetado «fuera de cobertura»", "RECUPERABLE"),
    "COMPRA A MAYORISTA":           ("Compra a mayorista", "RIESGO ASUMIDO"),
    "OTROS RUBROS":                 ("Otros rubros", "RIESGO ASUMIDO"),
}

DETALLE_CAUSA = {
    "SE APERTURARA EL CLIENTE":
        "Apertura conseguida: el objetivo de la prueba.",
    "EXISTE COMO CLIENTE":
        "Ya era cliente y nuestro filtro no lo excluyó de la lista de prospección.",
    "CLIENTE CADENA":
        "Cadena no detectada por nuestro filtro: se negocia de forma centralizada.",
    "NO EXISTE EL ESTABLECIMIENTO":
        "El POI ya no existe en terreno: la base de prospección está desactualizada.",
    "FUERA DE COBERTURA":
        "Mal etiquetado: tiene un cliente de la maestra a menos de 200 m. "
        "Es asignación de ruta de preventa, no falta de cobertura.",
    "COMPRA A MAYORISTA":
        "Hay demanda pero la abastece un tercero: solo se descubre visitando.",
    "OTROS RUBROS":
        "El punto no pertenece al universo bebible: solo se descubre visitando.",
}

# Como se agrupan los resultados en el embudo.
APERTURA = ["SE APERTURARA EL CLIENTE"]
YA_ATENDIDO = ["EXISTE COMO CLIENTE", "CLIENTE CADENA", "COMPRA A MAYORISTA"]
DESCARTE = ["NO EXISTE EL ESTABLECIMIENTO", "OTROS RUBROS", "FUERA DE COBERTURA"]
