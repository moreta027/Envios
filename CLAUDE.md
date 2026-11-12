# CLAUDE.md — Criterios para trabajar en este proyecto

Guía para cualquier persona o agente que modifique el código. Visión general en [README.md](README.md);
reglas de negocio en [docs/REPORTES.md](docs/REPORTES.md); deuda conocida en [docs/PROBLEMAS_CONOCIDOS.md](docs/PROBLEMAS_CONOCIDOS.md).

## Reglas críticas

1. **Nunca enviar correos reales durante pruebas.** Los bloques `if __name__ == "__main__"` usan `dry_run=False`.
   Para probar, importar las funciones y llamar `send_reports_from_mapping(..., dry_run=True)`, o solo `build_report()`.
   Los scripts de inventario no tienen modo dry-run: probar solo `build_report_*` y no llamar `send_inventario_report_via_graph`.
2. **No ejecutar `pl*.py` ni los `.exe` de `dist/`** sin confirmación explícita: envían correo a vendedores, visitadores y buzones corporativos.
3. **Secretos:** no escribir contraseñas, `client_secret` ni cadenas de conexión en código, documentación, commits o logs.
   Leerlos de variables de entorno o de `graph_config.json` (que no debe versionarse).
4. **Solo lectura en la base de datos.** Las consultas son `SELECT`; no agregar `INSERT/UPDATE/DELETE` sobre `SAPPRODUCCION`.
5. **Consultas parametrizadas** (`?` de pyodbc). Nunca concatenar valores en el SQL.

## Arquitectura y dónde va cada cosa

- **SQL** → solo en `connection.py`, una función `get_dataframe*()` por reporte que devuelve un `pandas.DataFrame`.
  Año/mes por defecto = fecha actual; no dejar valores fijos (ej. `(2026, 9, ...)`).
- **PDF y envío** → en el `pl*.py` correspondiente. Flujo de cada script: consultar → construir PDF → buscar PDF por código → enviar → enviar resumen.
- **Destinatarios** → en los CSV `RelacionCorreos*.csv` (columnas `Vendedor,Correo` y `CodigoRuta,Correo`).
  No poner correos de vendedores en el código.
- **Nombres de archivo** → `Reporte_{sanitize_filename(nombre)}.pdf`. Si cambias el formato, actualiza también
  `find_report_by_vendor_code`, que depende de él para emparejar código ↔ archivo.

## Convenciones

- Código, comentarios, mensajes y textos de PDF/correo en **español**.
- Archivos `.py` en **UTF-8 sin BOM** y con saltos de línea consistentes; revisar que tildes y ñ no se corrompan (`envÃ­o`).
- Estilo visual de los PDF (mantener al crear reportes nuevos):
  - Encabezado: logo + título centrado + tabla Fecha/Día/Mes (fondo `#00A3B4`).
  - Tablas: cabecera `#198A99` texto blanco, rejilla `#35BDEE`, filas alternas whitesmoke/lightgrey, fila TOTAL `#82A1B0` en negrita.
  - Pie gris: "@Todos los derechos reservados por laboratorios alfa S.R.L. Creado por Inteligencia de Negocios".
  - Ventas: A4 horizontal. Inventario: A4 vertical.
- Montos con separador de miles y sin decimales (`f"{v:,.0f}"`); porcentajes con 2 decimales y `%`.
- Recursos (`logo.png`, `graph_config.json`, CSV) deben resolverse tanto en script como en `.exe` (`sys.frozen` / `sys._MEIPASS`).
- Si agregas una dependencia o archivo de datos, actualizar el `.spec` (`hiddenimports` / `datas`) y el README.

## Checklist antes de dar un cambio por terminado

- [ ] `python -c "import plGeneral, plGeneralVisita, plInventarioCambios, plInventarioVencimiento"` importa sin errores.
- [ ] Se generó al menos un PDF de prueba y se revisó visualmente (columnas, totales, que nada se salga de la página).
- [ ] Los totales del PDF cuadran con la consulta SQL (ver fórmulas en [docs/REPORTES.md](docs/REPORTES.md)).
- [ ] Prueba de envío con `dry_run=True`: el resumen no muestra `missing_file` inesperados.
- [ ] Ningún secreto nuevo en el diff (`git diff` revisado).
- [ ] Si cambió algo empaquetado, se recompiló el `.exe` con su `.spec`.

## Git

- No versionar: `venv*/`, `build/`, `dist/`, `__pycache__/`, instaladores `python-*.exe`, PDFs generados, `graph_config.json`, `*.log`.
- Mensajes de commit en español, describiendo el reporte afectado (ej. `plGeneralVisita: corrige año fijo en consulta`).
