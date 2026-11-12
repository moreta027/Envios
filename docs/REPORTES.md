# Reglas de negocio de los reportes

Criterios que debe cumplir cada reporte. Si el código y este documento no coinciden, hay que corregir uno de los dos
y dejar constancia del motivo.

## Indicadores comunes (ventas y visita médica)

Origen: `IndicadorTabla` en las vistas `vwEnviosVentas` / `vwEnviosVisitaMedica`, filtradas por `ANO` y `MES`.
Días laborables: `[MBSAP].MovilBusiness5STD.dbo.DiasTrabajos` (`trabajado` = días transcurridos, `cantidad` = días del mes).

| Columna | Significado | Fórmula |
|---|---|---|
| **PPTO** | Presupuesto del mes | `SUM(Monto)` donde `IndicadorTabla = 'PPTO'` |
| **VTS** | Ventas netas (incluye devoluciones) | `SUM(Monto)` donde `IndicadorTabla = 'VTS'` |
| **CUMP** | % de cumplimiento | `VTS / PPTO × 100` (0 si PPTO = 0) |
| **PSL** | Pedidos sin liquidar / pendientes | `SUM(Monto)` donde `IndicadorTabla = 'PSL'` |
| **PROY** | Proyección al cierre del mes | `(VTS + PSL) / trabajado × cantidad` (vacío si no hay días o VTS+PSL = 0) |
| **%_PROY** | Proyección vs presupuesto | `PROY / PPTO × 100` |
| **DEV** | Devoluciones | `SUM(Monto)` de `VTS` con `Monto < 0` (valor negativo) |
| **%_DEV** | % devoluciones sobre venta bruta | `|DEV| / (VTS + |DEV|) × 100` |
| **GAP** | Lo que falta para la meta | `PPTO − VTS` |

Criterios:
- Los montos se redondean a 2 decimales en SQL y se muestran sin decimales con separador de miles.
- Toda división debe proteger el denominador 0 (mostrar 0 % o vacío, nunca error).
- La fila **TOTAL** se recalcula a partir de los totales (CUMP, %_PROY y %_DEV del total), **no** promediando porcentajes.
  Excepción actual: el %_PROY del total en visita médica es un promedio (ver [problemas conocidos](PROBLEMAS_CONOCIDOS.md)).

## 1. Ventas por vendedor — `plGeneral.py`

- **Datos:** `connection.get_dataframe(ano, mes)` → columnas `Vendedor, TipoProducto, PPTO, VTS, CUMP, PSL, PROYECCION, %_PROY, DEV, %_DEV, GAP`.
- **Agrupación:** un PDF por valor de `Vendedor` (formato `"NN - NOMBRE"`); dentro, una fila por `TipoProducto`, ordenadas por PPTO descendente, más fila TOTAL.
- **Título:** `REPORTE - {Vendedor}`; tabla `EQUIPO DE VENTAS` con la nota de focalización estratégica del presupuesto.
- **Archivo:** `VENTAS/Reporte_{NN_-_NOMBRE}.pdf`.
- **Envío:** por cada fila de `RelacionCorreosVendedores.csv` (`Vendedor` = código numérico). El emparejamiento compara el código numérico
  (sin ceros a la izquierda) con el número tras `Reporte_`. Si hay varios PDF con el mismo código, **se envía solo el primero**.
- **Asunto:** `Ventas diarias "{nombre}", "{dd/mm/aaaa}"`.
- **Resumen:** siempre se envía a Business Intelligence (enviados, fallidos, sin archivo, correo inválido); si hubo fallos, además un correo de errores.

## 2. Ventas visita médica por ruta — `plGeneralVisita.py`

- **Datos:** `connection.get_dataframeVisita(ano, mes)`; excluye rutas `ESP-INST%`. `gprVisita` nulo se muestra como `GENERICOS`.
- **RUTA CADENAS:** no genera PDF propio. Sus filas se añaden a cada ruta que tenga el mismo par (`Grupo Visita`, `Categoría/línea`).
  Se muestra como bloque aparte con fila `TOTAL RUTA CADENAS`.
- **Agrupación:** un PDF por `Codigo Ruta`; una tabla por ruta (la propia y la de cadenas) con filas por grupo de visita y fila `TOTAL RUTA`.
- **Archivo:** `VENTAS VISITA/Reporte_{CODIGO_RUTA}.pdf` (espacios → `_`).
- **Envío:** `RelacionCorreosVisitadores.csv` (`CodigoRuta,Correo`). El código del CSV debe coincidir **exactamente** (ignorando mayúsculas
  y con espacios → `_`) con el nombre del archivo.

## 3. Cambios de inventario — `plInventarioCambios.py`

- **Datos:** tabla `InventarioCambios`, registros del día actual; antes de las 12:00 también incluye el día anterior.
- **Contenido:** productos que pasaron de stock 0 a disponible o reingresaron por devolución en buen estado, ordenados por stock descendente.
- **Secciones:** `FARMACIA E INSTITUCIONAL` y `VETERINARIA` (según `Tipo`).
- **Archivo:** `INVENTARIO/Reporte_CambiosInventario.pdf`. **No se envía** si no hay registros.
- **Asunto:** `Cambio de inventario ({dd/mm/aaaa})`.

## 4. Próximos vencimientos — `plInventarioVencimiento.py`

- **Datos:** `vwInventarioLotesFechaVencimiento`, centro `5503`, almacén `1001`, `STOCK > 0`, vencimiento entre 0 y 6 meses.
- **Columnas:** Código, Descripción, Lote, Cantidad, FCH VENC, DIAS VENC; orden por días para vencer ascendente.
- **Archivo:** `INVENTARIO/Reporte_VencimientoInventario.pdf`. **No se envía** si no hay lotes.
- **Asunto:** `Proximos Vencimientos ({dd/mm/aaaa})`.

## Criterios para un reporte nuevo

1. Consulta nueva en `connection.py` (parametrizada, sin fechas fijas).
2. Script `plNombre.py` con el mismo flujo y estilo visual (ver [CLAUDE.md](../CLAUDE.md)).
3. Destinatarios en CSV o configuración, no en código.
4. No enviar nada si no hay datos; siempre registrar en consola qué se generó y qué se envió.
5. Su `.spec`, su entrada en el README y su sección en este documento.
