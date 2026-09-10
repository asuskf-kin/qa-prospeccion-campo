---
description: Da de alta un país nuevo en el pipeline y lo corre por primera vez
argument-hint: <pais> <ISO3>
---

Da de alta el país `$1` (código `$2`) siguiendo
[`.claude/docs/replicar.md`](../docs/replicar.md).

1. Lee `.claude/docs/dominio.md` antes de tocar nada: los nombres de columna y la
   taxonomía del formulario son el contrato del pipeline.
2. Añade la entrada a `PAISES` en `src/config.py`. Necesitas `lat_centro` y
   `bbox` (lon_min, lon_max, lat_min, lat_max) reales del país; búscalos, no los
   inventes.
3. Comprueba que los tres insumos estén en `data/$1/raw/` y que casen con los
   patrones. Inspecciónalos con `python -c` — **no** los abras con Read, son
   archivos de decenas de MB.
4. Corre `python run.py $1`.

Los fallos esperables, en orden de probabilidad, están listados en
`replicar.md#añadir-un-país`: encabezados distintos en el formulario, un valor
nuevo en `DATOS DE VISITA`, otro esquema de maestra, o `state` ausente en el
universo.

Cuando termine, reporta el reparto de responsabilidades y compáralo con
Guatemala: si un país sale con un perfil muy distinto, dilo — puede ser un
hallazgo real o un problema de mapeo de columnas.
