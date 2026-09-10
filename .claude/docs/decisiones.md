# Decisiones y trampas

Por qué el código es así. Varias de estas salieron de un error real; están
documentadas para no repetirlo.

## Trampas del dominio

### `pos_longitude`/`pos_latitude` no son la coordenada del punto

Son la ubicación que **la maestra** le asigna al cliente, que es exactamente lo
que el QA pone en duda (en el caso Kyro's, difiere 15,4 km de la realidad).
Están excluidas de `PARES_COORD` en `datos.py` a propósito.

**Ya nos costó un error:** al centralizar el manejo de coordenadas, el
exportador las tomó como coordenada del punto y dejó `existe_como_cliente_validado.csv`
con 14 de 16 filas geolocalizadas y las otras en el lugar equivocado. Si se
añade un par de columnas a `PARES_COORD`, verificar que describe **la ubicación
de la fila**, no de otro registro. Lo mismo aplica a `top_1_longitud/latitud`
(el vecino más cercano).

### `pos_name` nunca viene vacío en la maestra

Así que un `pos_name` nulo después del `merge` **no** significa que al registro
le falte el nombre: significa que **el `pos_id` no está en el corte que
recibimos**. Son clientes reales del embotellador; lo que está viejo es la copia.

**Ya nos costó un error:** el veredicto se llamaba `MAESTRA INCOMPLETA (sin
nombre)` y decía lo contrario de lo que pasaba. Hoy es
`POS_ID AUSENTE EN EL CORTE DE LA MAESTRA`.

### El veredicto automático no decide, solo señala

`REQUIERE REVISION MANUAL` es literal: la clasificación por nombre + GPS no
alcanza para esos casos. Al revisar Kyro's a mano resultó ser el **mismo
cliente**, algo que el algoritmo no podía saber. No presentar el veredicto
automático como conclusión.

### La línea de costa oficial está generalizada

Los puntos de playa caen unas decenas de metros fuera del polígono. Se asignan
al departamento más cercano mientras no superen `TOLERANCIA_COSTA_M` (200 m);
más allá se marcan `FUERA DEL PAIS`. Sin esa tolerancia, 5 puntos de Champerico
aparecían como coordenadas inválidas.

### Los encabezados del formulario cambian de codificación

`Dirección`, `¿Es correcto el nombre...?`, `Código de Cliente...` vienen con
tilde y se transforman según quién exporte el Excel. Se resuelven con
`datos.col(df, "fragmento")`, que compara sin tildes ni puntuación. **No escribir
nombres de columna literales.**

### Las categorías del formulario se normalizan antes de mapear

`SE APERTURARÁ EL CLIENTE` llega con tilde o sin ella. Se pasa por `norm_key` y
se mapea contra `MAPA_RESULTADO`, con un `assert` que revienta si aparece un
valor nuevo.

## Decisiones de diseño

### La garantía de coordenadas vive en el exportador

`Exportador.__call__` adjunta `longitud`/`latitud` al inicio de todo CSV de
puntos: las toma del DataFrame o las recupera por identificador contra las
fuentes registradas. Si no puede resolverlas, **falla** en vez de dejar un
archivo que después no se puede mapear. Las tablas agregadas se marcan
`geo=False`.

Antes esto se hacía a mano en cada llamada y se olvidaba. La regla es: *si el
requisito aplica a todas las salidas, va en la función que escribe*.

### La taxonomía es un contrato con `assert`

`config.CLASIFICACION` reparte los siete resultados del formulario en cinco
responsabilidades sin solapes. `cuenta_visitas()` verifica que sumen el total de
visitas y falla si no. Un resultado nuevo sin clasificar rompería la aritmética
del resumen sin avisar.

### Cada diapositiva es una función; cada versión, una lista

`deck.py` registra las diapositivas en `SLIDES` y publica dos guiones,
`COMPLETO` (26) y `EJECUTIVO` (16). Las diapositivas son las mismas funciones en
ambos, así que un cambio de contenido llega a las dos versiones y mover una es
editar la lista.

El orden del guion manda sobre la numeración de los títulos: si se reordenan los
hallazgos hay que renumerar los `title(...)`. No está automatizado a propósito,
porque los títulos también llevan el nombre del hallazgo.

### Las cifras nunca se escriben a mano en el deck

Todo sale de `deck_metrics.json`. Un número literal en `deck.py` es un error:
se desincroniza en la siguiente ola sin que nadie lo note.

### Los entregables editados a mano son intocables

El equipo pega mapas y ajusta textos en PowerPoint. El generador escribe
`_completo` y `_ejecutivo`; las versiones editadas llevan `_EDITADO`.
Regenerar encima de una edición manual destruye trabajo que no está en git.

### El notebook importa, no repite

Antes la lógica estaba duplicada entre el script que generaba el notebook y el
que armaba el deck, y se desincronizaron. Hoy `notebooks/` importa `src/`.

### Formato numérico local

`mil()` y `dec()` en `deck.py`: separador de miles con punto, decimal con coma
(`34.915`, `0,724`). Aplicar a todo número que salga al deck.

### Promedios sobre muestras chicas: mejor no mostrarlos

Se quitó un gráfico que comparaba similitud media de nombres (47,7 vs 98,7 sobre
14 cruces). Un promedio compuesto sobre tan poco invita a preguntas que
distraen; los cinco casos concretos convencen más. **Preferir el caso a la
media cuando n es pequeño.**

## Nomenclatura del proveedor

El cliente pidió primero llamar a Dataplor «base interna de prospección», y
después reescribió a mano los títulos poniendo «Dataplor». Hoy el deck lo nombra.

**Si el reporte se comparte con el embotellador y no debe verse el proveedor**,
hay que neutralizarlo otra vez en `src/deck.py` y en el eje de
`figuras.validity_score`. Conviene confirmarlo antes de cada entrega.
