# Los hallazgos

Cifras de la ola de **Guatemala, septiembre 2026**: 104 respuestas sobre 100 POI
únicos, contra 34.915 POI del universo y 229.077 registros de la maestra
(152.816 activos).

Todo lo de aquí sale de `data/guatemala/output/deck_metrics.json`. Si se corre
otra ola, los números cambian y este documento hay que actualizarlo.

## El reparto de las 100 visitas

No se solapa y suma 100. Es la tesis del reporte.

| | Visitas | Qué es |
|---|---|---|
| **FALLO NUESTRO** | 24 | 22 ya eran clientes + 2 cadenas no detectadas |
| **DATO DESACTUALIZADO** | 35 | POI que ya no existen en terreno |
| **RECUPERABLE** | 16 | mal etiquetados «fuera de cobertura» |
| **RIESGO ASUMIDO** | 14 | 10 mayorista + 4 otros rubros |
| **RESULTADO ÚTIL** | 11 | aperturas conseguidas |

La tasa de apertura real es **11%**. El techo no lo pone el mercado: lo pone la
calidad de los datos de entrada.

## Hallazgo 1 — El universo está desactualizado, y su score no lo anticipa

**35 de 100** POI visitados ya no operaban.

Lo grave no es eso, es que el `validity_score` del proveedor **apunta al revés**:

| | |
|---|---|
| AUC (Mann-Whitney) | **0,724** — p < 0,001 |
| AUC controlando por departamento | 0,741 (no es sesgo geográfico) |
| Mediana de los inexistentes | 0,949 |
| Mediana del resto de la base | 0,754 |
| Casos bajo el percentil 25 | **0 de 35** |

Los POI que no existen tienen el score **más alto**. Ningún punto de corte sirve
como filtro: el *lift* nunca supera 1,00, es decir, filtrar por score no mejora
en nada la elección al azar. Con un corte en 0,95 se descartaría el 75% del
universo comprado y aun así se dejaría pasar la mitad de los inexistentes.

Las columnas de estado (`open_closed_status`, `dataplor_status`) llegan
constantes, así que tampoco aportan señal de cierre.

## Hallazgo 2 — Nuestro motor no reconoce clientes que ya existen

De las **22** propuestas que el campo marcó como «ya es cliente», solo **16**
traen un `pos_id` verificable:

```
22 propuestas  =  16 con pos_id  +  4 que el campo rechaza  +  2 texto libre
16 verificables =  3 confirmados  +  9 probables  +  2 sin registro  +  2 a revisar
```

- **3 DUPLICADO CONFIRMADO** — coincide nombre **y** ubicación
- **9 DUPLICADO PROBABLE** — coincide nombre **o** ubicación, no ambos
- **2 POS_ID AUSENTE EN EL CORTE** — clientes válidos del embotellador que no
  están en la copia de maestra que recibimos: el corte está viejo
- **2 REQUIERE REVISION MANUAL** — el veredicto automático no alcanza

El caso documentado a mano: **«Kyro's» y «KAIROS MARKET» son el mismo cliente.**
Nuestro motor le dio 36,6/100 de similitud de nombre y lo dejó salir a campo
como prospecto, así que se gastó una visita en alguien que ya era cliente. El
GPS tampoco lo salvó, porque la maestra ubica a ese cliente **15,4 km** de donde
realmente está.

Es un **falso negativo**, no un duplicado falso — más grave, porque consume
visita y deja el cliente contado dos veces.

### La causa raíz

Nuestro universo identifica por **rótulo comercial**; la maestra, por
**titular**. El encuestador tuvo que reescribir el nombre en **10 de 14** casos
para que coincidiera, y **50,8%** de la maestra (116.477 registros) responde al
patrón de nombre de persona, contra solo **28,2%** que lleva un descriptor
comercial.

El 50,8% es una **estimación por reglas de texto** (tres o más palabras sin
descriptor comercial), no un conteo exacto. Está etiquetada como tal en el deck.
Para llevarla como cifra dura habría que validar una muestra revisada a mano;
con 200 registros basta.

## Hallazgo 3 — «Fuera de cobertura» no están fuera de cobertura

Los **16** puntos así marcados tienen un cliente de la maestra al lado:

| | |
|---|---|
| Distancia máxima al cliente más cercano | **198,6 m** |
| Distancia mediana | 66,2 m |
| Con un cliente a menos de 500 m | **16 de 16** |

No es una limitación logística: es **asignación de ruta de preventa**. Son
recuperables sin ningún cambio de cobertura.

## Hallazgo 4 — Qué parte del descarte era evitable

De las 16 visitas que no convirtieron por segmentación, **solo 2 eran
evitables**:

- **10 COMPRA A MAYORISTA** — riesgo asumido. Hay demanda; la abastece un
  tercero. Solo se descubre visitando, y además es una oportunidad de conversión
  de canal.
- **4 OTROS RUBROS** — riesgo asumido. Ninguna fuente clasifica el rubro con
  precisión suficiente para descartarlo sin ir al punto.
- **2 CLIENTE CADENA** — **error nuestro**. Ninguna venía marcada como cadena en
  el universo; el detector no las identificó.

Presentar los 16 como fallo era inflar el problema. El coste evitable real es
2%.

## Hallazgo 5 — Integridad del formulario

- **4 POI encuestados dos veces** (104 respuestas para 100 puntos), aceptadas
  sin aviso
- **6 respuestas** en texto libre o contradictorias en el campo de referencia a
  la maestra (4 dicen «no existe» contradiciendo la propuesta, 2 texto libre)
- **0 IDs huérfanos**: la trazabilidad del `dataplor_id` sí funciona

> **Pendiente.** Este hallazgo no tiene acción asignada en ningún bloque de
> próximos pasos, y no aparece en la versión ejecutiva. Quedó así tras quitar el
> punto de mayorista del lado del cliente. Hay que decidir si va al cliente,
> vuelve a nuestro lado, o se saca del reporte.

## Dónde ocurrió

Las 100 visitas caen dentro de Guatemala, concentradas en 7 departamentos:

| Departamento | Visitas |
|---|---|
| Jutiapa | 59 |
| Retalhuleu | 24 |
| Quetzaltenango | 8 |
| Santa Rosa | 6 |
| Guatemala · Jalapa · Escuintla | 1 cada uno |

5 puntos quedan 23–49 m fuera del polígono oficial: es Champerico, sobre la
costa de Retalhuleu. Artefacto de la línea de costa generalizada, **no un error
del dato**.

En ambos focos los puntos visitados caen dentro de zonas ya densamente cubiertas
por la maestra: la prospección no está explorando territorio nuevo.
