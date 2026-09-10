---
description: Corre el QA completo de un país y verifica que las salidas cuadren
argument-hint: [pais]
---

Corre el pipeline para el país `$1` (si no se indica, `guatemala`):

```bash
python run.py $1
```

Después verifica y reporta:

1. **La aritmética cierra.** El resumen final debe sumar el total de visitas. Si
   `cuenta_visitas()` hubiera fallado, habría lanzado `AssertionError`; confírmalo
   en la salida.
2. **Todas las exportaciones de puntos llevan coordenadas.** Recorre
   `data/$1/output/findings/*.csv` y comprueba que tienen `longitud` y `latitud`
   sin nulos. Las dos tablas agregadas (`hallazgos_resumen`,
   `cuenta_de_las_visitas`) van sin ellas a propósito.
3. **Los dos decks se generaron** con el número de diapositivas esperado: 26 el
   completo, 16 el ejecutivo.
4. **Las cifras clave no se movieron** respecto a `.claude/docs/hallazgos.md`. Si
   alguna cambió, dilo explícitamente: puede ser una entrega nueva de datos o una
   regresión.

No sobrescribas ningún archivo con sufijo `_EDITADO`.
