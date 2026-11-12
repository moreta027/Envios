# Envíos — Reportes automáticos por correo

Automatización de **Inteligencia de Negocios — Laboratorios Alfa S.R.L.** que consulta SQL Server (SAP),
genera reportes PDF con ReportLab y los envía por correo con Microsoft Graph (Outlook / Microsoft 365).

## Procesos

| Script | Qué genera | Carpeta de salida | Destinatarios |
|---|---|---|---|
| `plGeneral.py` | Un PDF de ventas por **vendedor** (PPTO, VTS, % cumplimiento, proyección, devoluciones, GAP por tipo de producto) | `VENTAS/` | `RelacionCorreosVendedores.csv` + resumen a Business Intelligence |
| `plGeneralVisita.py` | Un PDF de ventas por **ruta de visita médica**, desglosado por grupo de visita | ` VENTAS VISITA/` (ver [problemas conocidos](docs/PROBLEMAS_CONOCIDOS.md)) | `RelacionCorreosVisitadores.csv` + resumen a Business Intelligence |
| `plInventarioCambios.py` | Productos que pasaron de stock 0 a disponible (por nicho: Farmacia e Institucional / Veterinaria) | `INVENTARIO/` | buzón de notificaciones de inventario |
| `plInventarioVencimiento.py` | Lotes con stock que vencen en los próximos 6 meses (centro 5503, almacén 1001) | `INVENTARIO/` | buzón de vencimiento de inventario |

Las reglas de negocio (fórmulas, filtros, formato) están en [docs/REPORTES.md](docs/REPORTES.md).

## Estructura

```
connection.py                  # Todas las consultas SQL (una función get_dataframe* por reporte)
plGeneral.py                   # Reporte de ventas por vendedor + envío
plGeneralVisita.py             # Reporte de visita médica por ruta + envío
plInventarioCambios.py         # Reporte de cambios de inventario + envío
plInventarioVencimiento.py     # Reporte de vencimientos + envío
*.spec                         # Configuración de PyInstaller (un .exe por script)
run_build_all.py               # Solo genera los PDF de VENTAS (sin enviar)
crear_tarea_workdir.ps1        # Crea la tarea programada de Windows para plGeneral.exe
graph_config.json              # Credenciales de Microsoft Graph (SECRETO, no versionado)
db_config.json                 # Credenciales de SQL Server (SECRETO, no versionado)
RelacionCorreos*.csv           # Mapeo código → correo
logo.png                       # Logo del encabezado de los PDF
VENTAS/, VENTAS VISITA/, INVENTARIO/   # PDFs generados (salida)
build/, dist/                  # Salida de PyInstaller
Envios/venv310, Envios/venv311 # Entornos virtuales locales
```

## Requisitos

- Windows con **ODBC Driver 17 for SQL Server**.
- Acceso de red al servidor SQL `10.0.0.198` (base `SAPPRODUCCION` y servidor enlazado `MBSAP`).
- Python 3.10 o 3.11.
- Paquetes: `pandas`, `pyodbc`, `reportlab`, `requests`, `pyinstaller` (para compilar).
- Una app registrada en Azure AD con permiso de aplicación `Mail.Send` sobre los buzones remitentes.

## Instalación

```bash
python -m venv Envios/venv311
```

```bash
Envios/venv311/Scripts/pip install pandas pyodbc reportlab requests pyinstaller
```

Crear `graph_config.json` junto al script o al `.exe`:

```json
{
  "tenant_id": "<tenant>",
  "client_id": "<client>",
  "client_secret": "<secreto>",
  "sender": "<buzón remitente>"
}
```

Configurar SQL Server con **una** de estas dos opciones:

- Variables de entorno `SQL_SERVER`, `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD` (y opcional `SQL_DRIVER`), o
- un archivo `db_config.json` junto al script o al `.exe`:

```json
{
  "driver": "ODBC Driver 17 for SQL Server",
  "server": "<servidor>",
  "database": "SAPPRODUCCION",
  "username": "<usuario>",
  "password": "<contraseña>"
}
```

Ninguno de los dos archivos JSON se sube a git (ver `.gitignore`).

## Ejecución

> ⚠️ Ejecutar cualquiera de los `pl*.py` directamente **envía correos reales** (`dry_run=False`).
> Para probar, usa las funciones con `dry_run=True` (ver [CLAUDE.md](CLAUDE.md)).

Solo generar los PDF de ventas, sin enviar:

```bash
python run_build_all.py
```

Generar y enviar (producción):

```bash
python plGeneral.py
```

Los scripts usan rutas relativas (`VENTAS/`, `logo.png`), así que deben ejecutarse **desde la carpeta del proyecto**
(o con ese directorio de trabajo en la tarea programada).

## Compilación a .exe

```bash
pyinstaller plGeneral.spec
```

El `.exe` queda en `dist/`. `plGeneral` y `plGeneralVisita` leen `graph_config.json` y los CSV **de la carpeta del .exe**;
los de inventario los empaquetan dentro del ejecutable (`datas` en el `.spec`), por lo que hay que recompilarlos si cambia el secreto.
Todos los `.exe` leen `db_config.json` de **su propia carpeta** (copiarlo a `dist/` junto a ellos) o de las variables de entorno.

## Programación

`crear_tarea_workdir.ps1` registra la tarea `plGeneral_Automatica` (diaria, 9:00 a. m.). Las rutas del script apuntan a
otro equipo (`C:\Users\mmore\...`) y deben ajustarse antes de usarlo.
