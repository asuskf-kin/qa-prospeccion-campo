# El dominio

Qué es cada cosa. Sin esto, el código parece arbitrario.

## El negocio

Un **embotellador** quiere abrir puntos de venta nuevos. Nosotros le entregamos
una lista de candidatos (**prospectos**) sacada de un universo de POI comprado a
**Dataplor**, filtrando los que ya son sus clientes. Su fuerza de ventas los
visita y llena un **formulario de visita** diciendo qué encontró.

Este repositorio audita esa ronda: **cuántos de los puntos que mandamos a
visitar no debieron haber salido de la lista, y de quién es cada fallo.**

## Las tres fuentes

Van en `data/{pais}/raw/`. Los nombres exactos varían por entrega; se resuelven
por patrón en `config.Pais`.

### 1. Formulario de visita — `Respuestas*.xlsx`

Una fila por respuesta enviada. **Puede haber más filas que puntos**: un mismo
POI se encuesta dos veces y llegan dos filas (en Guatemala, 104 respuestas para
100 puntos).

| Columna | Qué es |
|---|---|
| `dataplor_id` | el POI del universo que se mandó a visitar. Es la llave. |
| `Código de Cliente interno y Nombre de Establecimiento` | `2368.Chicharrones y Carnitas Don NICHO` — código interno + **rótulo comercial** |
| `¿Es correcto el nombre de Establecimiento ?` | `Si`, `No`, **o el nombre corregido escrito a mano** |
| `Dirección`, `Barrio/Colonia`, `Longitud`, `Latitud` | lo que capturó el vendedor en el punto |
| `Region`, `Ruta de preventa`, `Canal` | la operación a la que pertenece |
| `EXISTE DENTRO DE NUESTRA BASE DE DATOS` | el `pos_id` de la maestra, o texto libre |
| `DATOS DE VISITA` | **el resultado de la visita.** Ver la taxonomía abajo. |
| `Conteo` | `Único` / `Duplicado`, ya marcado en origen |
| `Comentario` | texto libre del vendedor; se conserva siempre |

Los encabezados llevan tilde y cambian de codificación según quién exporte el
Excel. Nunca se escriben literales: se resuelven con `datos.col(df, "datos de
visita")`, que compara sin tildes ni puntuación.

### 2. Universo de prospección — `Dataplor_*.csv`

~35.000 POI comprados. Lo relevante:

| Columna | Qué es |
|---|---|
| `dataplor_id` | la llave contra el formulario |
| `name`, `address`, `city`, `state` | el POI según el proveedor |
| `latitude`, `longitude` | **la coordenada del POI** |
| `validity_score` | la confianza que el proveedor dice tener en el registro |
| `channel_cat`, `identified_as_chain`, `chain_name` | clasificación de canal y detección de cadena |
| `open_closed_status`, `dataplor_status` | estado del punto. **Llegan constantes: no aportan nada.** |

### 3. Maestra de clientes — `Clientes_*.csv`

~229.000 registros del embotellador, activos e inactivos.

| Columna | Qué es |
|---|---|
| `pos_id` | la llave del cliente |
| `pos_name` | **el TITULAR o razón social, no el nombre del local.** Ver más abajo. |
| `pos_addres`, `pos_city` | dirección según el embotellador |
| `pos_longitude`, `pos_latitude` | **la ubicación que la maestra le asigna**, que es justo lo que el QA pone en duda |
| `pos_fecha_baja` | nulo = activo. De aquí sale la columna derivada `activo`. |
| `pos_channel`, `pos_subchannel`, `pos_consumer_type` | segmentación comercial |

## La taxonomía del formulario

`DATOS DE VISITA` tiene siete valores. Cada uno cae en **exactamente una**
categoría de responsabilidad (`config.CLASIFICACION`), y las categorías no se
solapan y suman el total de visitas.

| Resultado | Significa | Responsabilidad |
|---|---|---|
| `SE APERTURARA EL CLIENTE` | se abre el punto | **RESULTADO ÚTIL** |
| `EXISTE COMO CLIENTE` | ya era cliente | **FALLO NUESTRO** — nuestro filtro no lo excluyó |
| `CLIENTE CADENA` | se negocia centralizado | **FALLO NUESTRO** — el detector de cadenas no lo vio |
| `NO EXISTE EL ESTABLECIMIENTO` | el local ya no opera | **DATO DESACTUALIZADO** — el universo está viejo |
| `FUERA DE COBERTURA` | el vendedor lo marca inalcanzable | **RECUPERABLE** — casi siempre es asignación de ruta |
| `COMPRA A MAYORISTA` | hay demanda, la abastece un tercero | **RIESGO ASUMIDO** |
| `OTROS RUBROS` | no pertenece al universo bebible | **RIESGO ASUMIDO** |

Esa distinción entre **fallo** y **riesgo asumido** es la tesis del reporte, y
la pidió el cliente explícitamente: mayorista y otros rubros solo se descubren
visitando, así que contarlos como errores infla el problema y quita credibilidad
a lo que sí es error nuestro.

Si una entrega trae un valor nuevo en `DATOS DE VISITA`, el pipeline **falla** en
`Fuentes.__init__` hasta que se le asigne categoría. Es deliberado: un resultado
sin clasificar rompería la aritmética del resumen sin avisar.

## Los dos nombres que no son el mismo nombre

La causa raíz de casi todos los fallos de emparejamiento:

| Nuestro universo guarda el rótulo | La maestra guarda el titular |
|---|---|
| Smoothies Lios | EDVIN OSWALDO TUN CAHUEC |
| Restaurante La Mariscada | DEBORA LITBETH |
| Casa Mía Café | DAVID EDUARDO ALVARADO ESCOBAR |
| Apoxab | MARTA CHANCHAVAC |

Son **campos semánticamente distintos**. Emparejar por nombre entre las dos
fuentes está condenado a fallar, y el 50,8% de la maestra responde al patrón de
nombre de persona. Por eso el emparejamiento debe apoyarse en geolocalización y
dirección, con el nombre solo como desempate.

Ojo con una consecuencia sutil: en los cruces validados, `score_nombre` sale
alto (90–100) porque compara contra **el nombre que el encuestador reescribió a
mano**, no contra el rótulo. Visto suelto, parece que el cruce funcionó bien.

## Vocabulario

| Término | Qué es |
|---|---|
| POI | punto de interés del universo comprado; candidato a prospectar |
| POS | punto de venta; un cliente del embotellador |
| maestra | la base de clientes del embotellador |
| corte | la copia de la maestra que nos entregan, con su fecha |
| rótulo | el nombre comercial visible del local |
| titular | la persona o razón social a nombre de quien está el cliente |
| ruta de preventa | la ruta del vendedor que atiende una zona |
| ola | una ronda de visitas de campo |
