# qa-prospeccion-campo

Auditoría de las pruebas de campo de prospección: contrasta las respuestas del
formulario de visita contra la base interna de prospección y contra la maestra
de clientes del embotellador, y produce los hallazgos, las figuras y el reporte
ejecutivo.

Responde tres preguntas: **cuántas visitas se pudieron evitar**, **cuáles son
fallos nuestros** y **cuáles son costo inevitable de prospectar**.

---

## Uso

```bash
pip install -r requirements.txt
python run.py guatemala
```

Eso deja en `data/guatemala/output/` los CSV de hallazgos, las figuras, el
`deck_metrics.json` y el PowerPoint.

```bash
python run.py --paises              # países configurados
python run.py guatemala --solo-datos  # sin figuras ni deck
python run.py guatemala --sin-deck    # análisis y figuras
```

El recorrido comentado de los hallazgos está en
[`notebooks/qa_prospection.ipynb`](notebooks/qa_prospection.ipynb), que importa
`src/` en vez de duplicar la lógica.

---

## Estructura

```
├── run.py                  punto de entrada
├── src/
│   ├── config.py           países, rutas, umbrales, paleta y taxonomía
│   ├── datos.py            carga de fuentes y exportación con coordenadas
│   ├── analisis.py         las cuatro ramas del QA
│   ├── figuras.py          los gráficos
│   └── deck.py             el PowerPoint
├── notebooks/              narrativa sobre src/
├── assets/                 identidad gráfica (footer, portada, divisores)
└── data/
    └── {pais}/
        ├── raw/            insumos, tal como llegan
        ├── geo/            límites administrativos (se descargan solos)
        └── output/
            ├── findings/   un CSV por hallazgo
            ├── figs/       gráficos del reporte
            ├── deck/       PowerPoint
            └── deck_metrics.json
```

## Añadir un país

Una entrada en `PAISES` (`src/config.py`) y los tres archivos en
`data/{pais}/raw/`:

```python
"honduras": Pais(
    slug="honduras", nombre="Honduras", iso3="HND",
    patron_clientes="Clientes_*.csv",
    patron_universo="Dataplor_*.csv",
    patron_respuestas="Respuestas*.xlsx",
    lat_centro=14.8, bbox=(-89.4, -83.1, 12.9, 16.6),
),
```

Los límites administrativos se descargan de geoBoundaries la primera vez y
quedan en `data/{pais}/geo/`.

---

## Decisiones que conviene conocer antes de tocar el código

**Toda exportación de puntos lleva coordenadas.** La garantía vive en
`Exportador.__call__`, no repetida en cada llamada: si un DataFrame no trae
`longitud`/`latitud`, se recuperan por identificador, y si no hay forma de
resolverlas la exportación falla en vez de dejar un archivo que no se puede
mapear. Las tablas agregadas se marcan con `geo=False`.

**`pos_longitude`/`pos_latitude` no son la coordenada del punto.** Son la
ubicación que la maestra le asigna, que es justamente lo que el QA pone en duda.
Están excluidas de `PARES_COORD` a propósito.

**Los encabezados del formulario se resuelven por fragmento** (`datos.col`).
Los nombres con tilde cambian de codificación según quién exporte el Excel.

**La taxonomía de responsabilidades no se solapa y suma el total de visitas.**
Está en `config.CLASIFICACION` y hay un `assert` que lo verifica: si se añade un
resultado nuevo al formulario, el pipeline falla hasta que se le asigne
categoría.

**El deck generado nunca pisa el editado.** `deck.construir()` escribe
`Reporte_QA_{Pais}_generado.pptx`; la versión con mapas pegados y ajustes
manuales vive aparte en la misma carpeta.

**Las tildes de la línea de costa.** Los límites oficiales están generalizados,
así que los puntos de playa caen unas decenas de metros fuera del polígono. Se
asignan al departamento más cercano dentro de `TOLERANCIA_COSTA_M`; más allá se
marcan como fuera del país.

---

## Salidas

| Archivo | Qué contiene |
|---|---|
| `hallazgos_geo.csv` | **una fila por punto visitado** con su hallazgo, responsabilidad y coordenadas — el insumo para el mapa |
| `cuenta_de_las_visitas.csv` | el reparto por responsabilidad que sostiene el resumen |
| `existe_como_cliente_validado.csv` | el cruce contra la maestra, validado en tres capas |
| `ejemplos_hallazgo3.csv` | los dos lados de cada emparejamiento fallido |
| `titular_vs_nombre_comercial.csv` | evidencia de la causa raíz del cruce |
| `poi_inexistentes.csv` | los POI que ya no operan, con su `validity_score` |
| `fuera_de_cobertura.csv` | distancia al cliente más cercano y sus coordenadas |
| `cruces_a_revisar.csv` · `pos_id_ausente_en_corte.csv` | los casos que no resisten la validación |
| `errores_id.csv` · `errores_segmentacion.csv` | integridad del formulario y filtros previos |
| `Respuestas {Pais} - con causa.xlsx` | el formulario original con la causa escrita en `Comentario` |

## Requisitos

Python 3.11+. Para regenerar el PowerPoint hace falta la tipografía **Segoe UI**
(en otro sistema, cambiar `FUENTE` en `src/config.py`).
