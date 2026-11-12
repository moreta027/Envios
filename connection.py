
import json
import os
import sys

import pyodbc
import pandas as pd
from datetime import date


def _app_dir() -> str:
    """Carpeta del .exe (PyInstaller) o del script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_db_config(path: str = "db_config.json") -> dict:
    """Configuración de SQL Server.

    Prioridad: variables de entorno SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD (y SQL_DRIVER opcional);
    si no están todas, se lee `db_config.json` de la carpeta del script/.exe. Ese archivo NO se versiona.
    """
    env = {
        "server": os.getenv("SQL_SERVER"),
        "database": os.getenv("SQL_DATABASE"),
        "username": os.getenv("SQL_USER"),
        "password": os.getenv("SQL_PASSWORD"),
    }
    if all(env.values()):
        env["driver"] = os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
        return env

    if not os.path.isabs(path):
        path = os.path.join(_app_dir(), path)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"No se encontró {path} ni las variables de entorno SQL_SERVER/SQL_DATABASE/SQL_USER/SQL_PASSWORD."
        )
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("driver", "ODBC Driver 17 for SQL Server")
    return cfg


def get_connection():
    """Abre una conexión a SQL Server con la configuración externa."""
    cfg = load_db_config()
    cadena = (
        f"DRIVER={{{cfg['driver']}}};SERVER={cfg['server']};DATABASE={cfg['database']};"
        f"UID={cfg['username']};PWD={cfg['password']}"
    )
    return pyodbc.connect(cadena)

def get_dataframe(ano: int = None, mes: int = None):
    """
    Ejecuta la consulta y devuelve un DataFrame con los resultados.
    """

    hoy = date.today()
    if ano is None:
        ano = hoy.year
    if mes is None:
        mes = hoy.month
    
        
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    WITH dias AS (
        SELECT trabajado, cantidad
        FROM [MBSAP].MovilBusiness5STD.[dbo].DiasTrabajos
        WHERE ANO = ? AND MES = ?
    ),
    fuente_agg AS (
        SELECT
            VENDEDOR,
            ISNULL(Categoria, '') AS Categoria,
            SUM(CASE WHEN IndicadorTabla = 'PPTO' THEN Monto ELSE 0 END) AS PPTO,
            SUM(CASE WHEN IndicadorTabla = 'VTS' THEN Monto ELSE 0 END) AS VTS,
            SUM(CASE WHEN IndicadorTabla = 'PSL' THEN Monto ELSE 0 END) AS PSL,
			SUM(CASE WHEN IndicadorTabla = 'VTS' AND Monto < 0 THEN Monto ELSE 0 END) AS DEV
        FROM [vwEnviosVentas]
        WHERE ANO = ? AND MES = ?
        GROUP BY VENDEDOR, ISNULL(Categoria, '')
    )
    SELECT
        fa.VENDEDOR AS Vendedor,
        fa.Categoria AS TipoProducto,
        ROUND(ISNULL(fa.PPTO,0),2) AS PPTO,
        ROUND(ISNULL(fa.VTS,0),2) AS VTS,
        CASE WHEN ROUND(ISNULL(fa.PPTO,0),2) = 0
             THEN '0 %'
             ELSE CONVERT(VARCHAR(20), ROUND(fa.VTS/NULLIF(fa.PPTO,0)*100,2)) + ' %'
        END AS CUMP,
        ROUND(ISNULL(fa.PSL,0),2) AS PSL,
        CASE WHEN (dias.trabajado * dias.cantidad) = 0 OR (ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) = 0
             THEN NULL
             ELSE ((ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) / (dias.trabajado)) * dias.cantidad
        END AS PROYECCION,
        CASE WHEN (dias.trabajado * dias.cantidad) = 0 OR ROUND(ISNULL(fa.PPTO,0),2) = 0 OR (ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) = 0
             THEN NULL
             ELSE (((ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) / (dias.trabajado)) * dias.cantidad) / NULLIF(ROUND(ISNULL(fa.PPTO,0),2),0)
        END AS [%_PROY],
		ROUND(ISNULL(fa.DEV,0),2) AS DEV,
		IIF((ROUND(ISNULL(fa.VTS,0),2)  + ABS(ROUND(ISNULL(fa.DEV,0),2)))  = 0,0,
			ABS(ROUND(ISNULL(fa.DEV,0),2))/
		   (ROUND(ISNULL(fa.VTS,0),2)  + ABS(ROUND(ISNULL(fa.DEV,0),2)))) AS [%_DEV],
		ROUND(ISNULL(fa.PPTO,0),2) - ROUND(ISNULL(fa.VTS,0),2) AS GAP
    FROM fuente_agg fa
    CROSS JOIN dias
        
    """
    # parámetros: (ano, mes) para la CTE y (ano, mes) para la agregación de fuente
    # cursor.execute(query, (2026, 8, 2026, 8))
    cursor.execute(query,(ano,mes,ano,mes))
    data = cursor.fetchall()
    df = pd.DataFrame.from_records(data, columns=[column[0] for column in cursor.description])
    conn.close()
    return df

def get_dataframeVisita(ano: int = None, mes: int = None):
    """
    Ejecuta la consulta y devuelve un DataFrame con los resultados.
    """

    hoy = date.today()
    if ano is None:
        ano = hoy.year
    if mes is None:
        mes = hoy.month
    
        
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        
    WITH dias AS (
        SELECT trabajado, cantidad
        FROM [MBSAP].MovilBusiness5STD.[dbo].DiasTrabajos
        WHERE ANO = ? AND MES = ?
    ),
    fuente_agg AS (
        SELECT
            CodigoRuta,
            ISNULL(Categoria, '') AS Categoria,
			gprVisita,
            SUM(CASE WHEN IndicadorTabla = 'PPTO' THEN Monto ELSE 0 END) AS PPTO,
            SUM(CASE WHEN IndicadorTabla = 'VTS' THEN Monto ELSE 0 END) AS VTS,
            SUM(CASE WHEN IndicadorTabla = 'PSL' THEN Monto ELSE 0 END) AS PSL,
			SUM(CASE WHEN IndicadorTabla = 'VTS' AND Monto < 0 THEN Monto ELSE 0 END) AS DEV
        FROM [vwEnviosVisitaMedica]
        WHERE ANO = ? AND MES = ? and CodigoRuta not like 'ESP-INST%'
        GROUP BY CodigoRuta, ISNULL(Categoria, ''),gprVisita 
    )
    SELECT
        fa.CodigoRuta AS [Codigo Ruta],
        fa.Categoria AS TipoProducto,
		isnull(fa.gprVisita,'GENERICOS') as [Grupo Visita],
        ROUND(ISNULL(fa.PPTO,0),2) AS PPTO,
        ROUND(ISNULL(fa.VTS,0),2) AS VTS,
        CASE WHEN ROUND(ISNULL(fa.PPTO,0),2) = 0
             THEN '0 %'
             ELSE CONVERT(VARCHAR(20), ROUND(fa.VTS/NULLIF(fa.PPTO,0)*100,2)) + ' %'
        END AS CUMP,
        ROUND(ISNULL(fa.PSL,0),2) AS PSL,
        CASE WHEN (dias.trabajado * dias.cantidad) = 0 OR (ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) = 0
             THEN NULL
             ELSE ((ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) / (dias.trabajado)) * dias.cantidad
        END AS PROYECCION,
        CASE WHEN (dias.trabajado * dias.cantidad) = 0 OR ROUND(ISNULL(fa.PPTO,0),2) = 0 OR (ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) = 0
             THEN NULL
             ELSE (((ROUND(ISNULL(fa.VTS,0),2) + ROUND(ISNULL(fa.PSL,0),2)) / (dias.trabajado)) * dias.cantidad) / NULLIF(ROUND(ISNULL(fa.PPTO,0),2),0)
        END AS [%_PROY],
		ROUND(ISNULL(fa.DEV,0),2) AS DEV,
		IIF((ROUND(ISNULL(fa.VTS,0),2)  + ABS(ROUND(ISNULL(fa.DEV,0),2)))  = 0,0,
			ABS(ROUND(ISNULL(fa.DEV,0),2))/
		   (ROUND(ISNULL(fa.VTS,0),2)  + ABS(ROUND(ISNULL(fa.DEV,0),2)))) AS [%_DEV],
		ROUND(ISNULL(fa.PPTO,0),2) - ROUND(ISNULL(fa.VTS,0),2) AS GAP
    FROM fuente_agg fa
    CROSS JOIN dias


    """
    # parámetros: (ano, mes) para la CTE y (ano, mes) para la agregación de fuente
    # cursor.execute(query, (2026, 8, 2026, 8))
    cursor.execute(query, (ano, mes, ano, mes))
    data = cursor.fetchall()
    df = pd.DataFrame.from_records(data, columns=[column[0] for column in cursor.description])
    conn.close()
    return df

def get_dataframeInventarioCambios(ano: int = None, mes: int = None , day: int = None):
    """
    Ejecuta la consulta y devuelve un DataFrame con los resultados.
    """

    hoy = date.today()
    if ano is None:
        ano = hoy.year
    if mes is None:
        mes = hoy.month
    if day is None:
        day = hoy.day
        
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT TRY_CONVERT(VARCHAR,CodigoProducto)+' - ' +Descripcion Producto
        , Stock
        , FechaRegistro
        , Tipo
        , CASE WHEN TIPO = 'VETERINARIA' THEN 'VETERINARIA' ELSE 'FARMACIA E INSTITUCIONAL' END AS NICHO
        FROM InventarioCambios
        WHERE YEAR(FechaRegistro) = ? AND MONTH(FechaRegistro) = ? AND DAY(FechaRegistro) in (?,IIF(GETDATE()<CONVERT(VARCHAR,CONVERT(DATE,GETDATE()))+' 12:00:00.000',?-1,0)) --DAY(FechaRegistro) = ?
        order by Stock desc
    """
    # parámetros: (ano, mes, day) para la CTE y (ano, mes, day) para la agregación de fuente
    cursor.execute(query,(ano,mes,day,day))
    data = cursor.fetchall()
    df = pd.DataFrame.from_records(data, columns=[column[0] for column in cursor.description])
    conn.close()
    return df

def get_dataframeInventarioVencimiento():
    """
    Ejecuta la consulta y devuelve un DataFrame con los resultados.
    """
        
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
        CODIGO Codigo,
        DESCRIPCION Descripcion,
        LOTE Lote,
        STOCK Cantidad,
        FECHA_LOTE_VENCIMIENTO Fecha_Venc_Lote,
        DATEDIFF(DD,GETDATE(),FECHA_LOTE_VENCIMIENTO) Dias_para_Venc
        FROM 
        [vwInventarioLotesFechaVencimiento] I
        where ALMACEN = '1001' AND CENTRO = '5503' AND STOCK > 0 
        AND DATEDIFF(MM,GETDATE(),FECHA_LOTE_VENCIMIENTO) <= 6 
        AND DATEDIFF(MM,GETDATE(),FECHA_LOTE_VENCIMIENTO) >= 0
        ORDER BY Dias_para_Venc ASC
    """
    # parámetros: (ano, mes, day) para la CTE y (ano, mes, day) para la agregación de fuente
    cursor.execute(query)
    data = cursor.fetchall()
    df = pd.DataFrame.from_records(data, columns=[column[0] for column in cursor.description])
    conn.close()
    return df


if __name__ == "__main__":
    # comportamiento de script (opcional)
    print("Ejecutando consulta desde connection.py...")
    df = get_dataframeInventarioVencimiento()
    print(df.head())
