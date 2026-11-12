# Problemas conocidos y pendientes

Detectados al analizar el proyecto (12/11/2026). Ordenados por prioridad.

## 🔴 Seguridad (urgente)

1. ✅ *Corregido en código (12/11/2026)* — **Contraseña de SQL Server en el código.** `connection.py` ahora usa `get_connection()`,
   que lee variables de entorno o `db_config.json` (no versionado).
   - ⚠️ **Pendiente:** la contraseña sigue en el historial de git (commit inicial). Hay que **cambiarla** en SQL Server y actualizar `db_config.json`.
2. ✅ *Sacado del repositorio (12/11/2026)* — **`graph_config.json` (con `client_secret`)** ya no se sigue en git y está en `.gitignore`.
   - ⚠️ **Pendiente:** sigue en el historial y dentro de los `.exe` de inventario. Hay que **renovar el secreto** en Azure AD, actualizar el archivo y recompilar.
     Si el repo se sube a un remoto, limpiar el historial antes (`git filter-repo`) o empezar un repo nuevo.
3. ✅ *Corregido (12/11/2026)* — **`.gitignore` creado.** Venvs, `build/`, `dist/`, instaladores, `__pycache__/` y PDF generados se quitaron
   del índice (siguen en disco). Quedan 15 archivos versionados. El historial anterior conserva su tamaño hasta que se reescriba.

## 🟠 Errores funcionales

4. ✅ *Corregido (12/11/2026)* — **Año/mes fijos en visita médica.** `get_dataframeVisita` usa ahora `(ano, mes, ano, mes)`.
5. **Carpeta con espacio inicial.** `plGeneralVisita.py` escribe en `" VENTAS VISITA"` (con espacio delante) en `build_report` y en `__main__`,
   pero los valores por defecto usan `"VENTAS VISITA"`. Por eso existen dos carpetas y git muestra la versión con espacio como borrada.
   - Acción: unificar en una constante `OUT_DIR = "VENTAS VISITA"`.
6. **Texto con codificación corrupta** en `plGeneralVisita.py` (`envÃ­o`, `configuraciÃ³n`): aparece así en los correos de resumen.
   - Acción: corregir los literales y guardar el archivo en UTF-8 sin BOM.
7. **Códigos de vendedor duplicados.** En `VENTAS/` hay varios PDF con el mismo código (ej. `Reporte_02_-_...` con dos nombres) porque se
   acumulan de ejecuciones anteriores; `find_report_by_vendor_code` envía el primero en orden alfabético, que puede ser un reporte viejo o de otra persona.
   - Acción: limpiar la carpeta de salida al inicio de cada ejecución y/o avisar si hay más de una coincidencia.
8. **%_PROY del TOTAL en visita médica** se calcula como promedio de porcentajes por fila, no como `PROY total / PPTO total`
   (como sí hace el reporte de ventas). Además usa la heurística "si es < 2 multiplicar por 100".
9. **Rutas relativas.** `plGeneral.py` busca `logo.png` y `VENTAS/` en el directorio de trabajo; ejecutado desde otra carpeta, genera el PDF sin logo
   o en otro lugar. `crear_tarea_workdir.ps1` además apunta a rutas de otro equipo y redirige la salida mediante `Arguments`, lo que no funciona en un `.exe`.

## 🟡 Mantenibilidad

10. **Código duplicado:** `plGeneral.py` y `plGeneralVisita.py` comparten ~60 % del código (Graph, SMTP, resumen, encabezado, pie);
    los dos de inventario son casi idénticos. Conviene extraer un módulo común (`comun/pdf.py`, `comun/correo.py`).
11. **Código muerto:** `send_report_to` / `test_smtp_connection` (SMTP no se usa), `df_to_table_data`, `pdf_file`, `fmt_pct_display`.
12. **Destinatarios fijos en código:** buzón de Business Intelligence y buzones de inventario. Moverlos a configuración.
13. **Sin dependencias declaradas** (`requirements.txt`) ni pruebas automáticas. Mínimo recomendado: prueba de las fórmulas de totales y del
    emparejamiento código ↔ archivo.
14. **Sin registro (logging):** solo `print`. Si la tarea programada falla, no queda rastro. Usar `logging` hacia un archivo con fecha.
