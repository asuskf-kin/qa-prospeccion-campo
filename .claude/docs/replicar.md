# Replicar el proyecto

## Desde cero

```bash
git clone <repo> && cd qa-prospeccion-campo
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Los datos **no están en git** (los dos CSV pesan 97 MB). Hay que colocarlos:

```
data/guatemala/raw/
├── Clientes_*.csv        maestra de clientes del embotellador
├── Dataplor_*.csv        universo de POI comprado
└── Respuestas*.xlsx      formulario de visita
```

Los nombres exactos no importan, solo que casen con los patrones de
`config.PAISES[...]`. Los límites administrativos se descargan solos de
geoBoundaries la primera vez.

```bash
python run.py guatemala
```

Deja en `data/guatemala/output/`:

```
findings/     12 CSV, uno por hallazgo — todos con longitud/latitud
figs/         5 PNG
deck/         Reporte_QA_Guatemala_{completo,ejecutivo}.pptx
deck_metrics.json
Respuestas Guatemala - con causa.xlsx
```

Tarda unos 3 minutos, casi todo en leer los CSV grandes y en el
punto-en-polígono de los departamentos.

### Verificar que salió bien

El resumen final debe cuadrar en el total de visitas:

```
listo · 100 visitas: RESULTADO ÚTIL 11 · FALLO NUESTRO 24 ·
        DATO DESACTUALIZADO 35 · RECUPERABLE 16 · RIESGO ASUMIDO 14
```

Si la suma no da el total, `cuenta_visitas()` habría fallado antes con un
`AssertionError`. Y la última celda del notebook lista los CSV con cuántas filas
llevan coordenadas: deben ir todas, salvo las dos tablas agregadas marcadas
`n/a`.

## Añadir un país

Una entrada en `PAISES` (`src/config.py`):

```python
"honduras": Pais(
    slug="honduras", nombre="Honduras", iso3="HND",
    patron_clientes="Clientes_*.csv",
    patron_universo="Dataplor_*.csv",
    patron_respuestas="Respuestas*.xlsx",
    lat_centro=14.8,                      # para la relación de aspecto del mapa
    bbox=(-89.4, -83.1, 12.9, 16.6),      # lon_min, lon_max, lat_min, lat_max
),
```

Los tres archivos en `data/honduras/raw/` y:

```bash
python run.py honduras
```

Qué esperar que rompa, en orden de probabilidad:

1. **Encabezados distintos en el formulario.** `Fuentes.__init__` falla con
   `KeyError`. Se ajusta el fragmento en la llamada a `col()`, no el nombre
   completo.
2. **Un valor nuevo en `DATOS DE VISITA`.** Falla con `categorias no
   contempladas: {...}`. Hay que añadirlo a `MAPA_RESULTADO`, a
   `CLASIFICACION` y a `DETALLE_CAUSA`.
3. **La maestra con otro esquema.** `rama_existe_cliente` y
   `rama_fuera_cobertura` asumen `pos_id`, `pos_name`, `pos_addres`,
   `pos_city`, `pos_channel`, `pos_fecha_baja`, `pos_longitude`,
   `pos_latitude`.
4. **`state` ausente en el universo.** Se usa para el control geográfico del
   `validity_score`.

## Qué hacer con cada salida

| Archivo | Para qué |
|---|---|
| `hallazgos_geo.csv` | cargar en Kepler / QGIS / Power BI. Una fila por punto con hallazgo, responsabilidad y coordenadas |
| `deck/*_completo.pptx` | la revisión entera |
| `deck/*_ejecutivo.pptx` | la reunión con dirección |
| `Respuestas ... - con causa.xlsx` | devolver al equipo de campo: su formulario con la causa escrita en `Comentario` |
| `findings/ejemplos_hallazgo3.csv` | los dos lados de cada emparejamiento fallido, para ir a buscarlos en el mapa |
| `deck_metrics.json` | la fuente de todas las cifras del deck |

Los marcos punteados del deck son **espacios reservados** para capturas de mapa.
Se pegan a mano y el archivo resultante se guarda con sufijo `_EDITADO`, que el
generador nunca sobrescribe.

## Ejecutar el notebook

```bash
cd notebooks && jupyter lab qa_prospection.ipynb
```

Importa `src/` y muestra las tablas intermedias. Sirve para explorar un hallazgo
o mostrar el razonamiento; **no** para cambiar la lógica: eso va en `src/`.

## Dependencias con nota

| | |
|---|---|
| `shapely` | punto-en-polígono contra los departamentos |
| `scikit-learn` | `BallTree` para el vecino más cercano, TF-IDF para nombres |
| `rapidfuzz` | similitud de nombres y direcciones |
| `python-pptx` | el deck |
| `openpyxl` | leer y escribir los Excel |

**Tipografía.** El deck usa Segoe UI. En un sistema sin ella, cambiar `FUENTE` y
`FUENTE_BOLD` en `src/config.py`; el layout está calibrado para sus métricas, así
que otra fuente puede desbordar algún bloque de texto.

**Para revisar el deck sin PowerPoint**, en un equipo con LibreOffice:

```bash
soffice --headless --convert-to pdf --outdir /tmp <archivo>.pptx
```
