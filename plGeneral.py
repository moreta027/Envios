# plGeneral.py
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm
from datetime import date
import sys, os
import re
import pandas as pd
import connection
import base64
import json
import unicodedata
from reportlab.pdfbase import pdfmetrics


# --- NUEVO: función para cargar configuración de Graph desde archivo externo ---
def load_graph_config(path="graph_config.json"):
    """Carga la configuración de Microsoft Graph desde un archivo JSON."""
    # Si la ruta no es absoluta, buscar en la carpeta del ejecutable
    if not os.path.isabs(path):
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(app_dir, path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# requests se usa para Graph API (si no está instalado, se debe instalar: pip install requests)
import requests

# Salida PDF (nombre por defecto si quieres generar un único archivo)
pdf_file = "Reporte_generado.pdf"
styles = getSampleStyleSheet()

def build_header(elements, title="REPORTE GENERAL"):
    logo_path = "logo.png"
    # 1 cm ≈ 28.35 px, así que 10px ≈ 0.353 cm
    logo = Image(logo_path, width=(4.4+0.353)*cm, height=(2.2+0.353)*cm) if os.path.exists(logo_path) else Spacer((4.4+0.353)*cm, (2.2+0.353)*cm)
    titulo = Paragraph(f"<b>{title}</b>", ParagraphStyle('title', alignment=1, fontSize=16, leading=18))
    hoy = date.today()
    info = [
        ["Fecha", hoy.strftime("%d/%m/%Y")],
        ["Día", str(hoy.day)],
        ["Mes", str(hoy.month)]
    ]
    tabla_info = Table(info, colWidths=[2.2*cm, 3.0*cm])
    tabla_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#00A3B4")),  # color de la fecha
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey)
    ]))

    header_table = Table([[logo, titulo, tabla_info]], colWidths=[5.2*cm, 17.4*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*cm))

def df_to_table_data(df: pd.DataFrame, header_labels=None):
    if df is None or df.empty:
        return [["RUTA", "Region", "Presupuesto", "Ventas", "% CUMP"], ["Sin datos", "", "", "", ""]]

    if header_labels is None:
        cols = list(df.columns[:8])
    else:
        cols = header_labels

    rows = [cols]
    for _, r in df.iterrows():
        row = []
        for c in cols:
            val = r[c] if c in df.columns else ""
            if pd.notna(val) and isinstance(val, (int, float)):
                if "PPTO" in str(c).upper() or "VTS" in str(c).upper() or "PRESUP" in str(c).upper():
                    row.append(f"${val:,.0f}")
                else:
                    row.append(f"{val}")
            else:
                row.append("" if pd.isna(val) else str(val))
        rows.append(row)
    return rows

def crear_tabla_estandar(elements, titulo, data):

    elements.append(Paragraph(titulo, styles['Heading4']))
    # Agregar nota solo si el título es 'EQUIPO DE VENTAS'
    if titulo.strip().upper() == 'EQUIPO DE VENTAS':
        nota = 'NOTA: La distribución del presupuesto se realiza con fines de focalización estratégica en su zona, manteniéndose como meta principal el logro del 100% del presupuesto total.'
        from reportlab.lib.styles import ParagraphStyle
        nota_style = ParagraphStyle('nota', fontSize=9, textColor='#444444', leftIndent=6, rightIndent=6, spaceAfter=6)
        elements.append(Paragraph(nota, nota_style))

    ncols = len(data[0])
    page_width, _ = landscape(A4)
    available_width = page_width - (2 * cm)  # margen aproximado

    # Ajuste más preciso: padding visual y fuente exacta por celda
    header_font = 'Helvetica-Bold'
    header_size = 9
    body_font = 'Helvetica'
    body_size = 8
    min_col_w = 1.2 * cm  # más pequeño para columnas cortas
    padding_pts = 14  # padding visual más generoso

    # Distribuir el ancho disponible para que tablas con más columnas no se salgan de la página.
    first_col_w = 110
    other_col_w = (available_width - first_col_w) / (ncols - 1) if ncols > 1 else available_width
    colWidths = [first_col_w] + [other_col_w] * (ncols - 1) if ncols > 1 else [available_width]

    # Eliminar fila TOTAL extra: ahora la fila TOTAL solo se agrega desde build_report_for_vendor, no aquí

    tabla = Table(data, colWidths=colWidths, repeatRows=1)

    styles_list = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#198A99")),  # principal
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), header_size),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor("#35BDEE")),  # secundario
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]

    # Color de texto NEGRO para la primera columna (RUTA, vendedor) en filas de datos, excepto la fila TOTAL
    nrows = len(data)
    for i in range(1, nrows):
        if str(data[i][0]).strip().upper() == 'TOTAL':
            styles_list.append(('TEXTCOLOR', (0,i), (0,i), colors.white))
        else:
            styles_list.append(('TEXTCOLOR', (0,i), (0,i), colors.HexColor("#23282B")))

    # alineaciones por columna: primeras 2 columnas a la izquierda, resto a la derecha
        #styles_list.append(('ALIGN', (0,1), (1,-1), 'LEFT'))
        #styles_list.append(('ALIGN', (2,1), (-2,-1), 'RIGHT'))
    # Padding personalizado: más para RUTA, menos para las demás
    for col in range(ncols):
        h = str(data[0][col]) if col < len(data[0]) else ''
        if '%_PROY' in h.upper() or '%_DEV' in h.upper():
            styles_list.append(('ALIGN', (col,0), (col,-1), 'CENTER'))
            styles_list.append(('LEFTPADDING', (col,0), (col,-1), 0))
            styles_list.append(('RIGHTPADDING', (col,0), (col,-1), 0))
        elif 'RUTA' in h.upper():
            styles_list.append(('LEFTPADDING', (col,0), (col,-1), 16))
            styles_list.append(('RIGHTPADDING', (col,0), (col,-1), 16))
        else:
            styles_list.append(('LEFTPADDING', (col,0), (col,-1), 2))
            styles_list.append(('RIGHTPADDING', (col,0), (col,-1), 2))

    # detectar filas "TOTAL" y aplicar estilo destacado (negrita + fondo)
    total_rows = [i for i, row in enumerate(data) if i > 0 and len(row) > 1 and str(row[0]).strip().upper() == 'TOTAL']
    for r in total_rows:
        styles_list.append(('FONTNAME', (0,r), (-1,r), 'Helvetica-Bold'))
        styles_list.append(('BACKGROUND', (0,r), (-1,r), colors.HexColor("#82A1B0")))  # Color solicitado
        styles_list.append(('TEXTCOLOR', (0,r), (-1,r), colors.white))

    tabla.setStyle(TableStyle(styles_list))
    elements.append(tabla)
    elements.append(Spacer(1, 0.4*cm))

def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = name.replace(" ", "_")
    # eliminar caracteres no válidos para archivos
    return re.sub(r'[^A-Za-z0-9_\-\.]', '', name)


def build_report_for_vendor(vendedor_value: str, df_vendor: pd.DataFrame, out_dir: str = "VENTAS"):
    elements = []
    # Determinar nombre mostrado del vendedor: usar el valor pasado pero preferir el nombre completo
    # presente en el DataFrame (ej. '01 - LEIDY PERALTA').
    # Esto cubre el caso en que se llama con código '01' pero df_vendor tiene '01 - NAME'.
    # Detectar la columna que contiene el vendedor
    vendor_col = None
    for cand in ("RUTA", "Vendedor", "VENDEDOR"):
        if cand in df_vendor.columns:
            vendor_col = cand
            break
    if vendor_col is None:
        vendor_col = df_vendor.columns[0]

    display_name = str(vendedor_value)
    if vendor_col in df_vendor.columns:
        vals = df_vendor[vendor_col].dropna().astype(str).unique()
        # primero buscar valores que empiecen con el code pasado
        for v in vals:
            if str(v).strip().startswith(str(vendedor_value).strip()):
                display_name = v
                break
        else:
            if len(vals):
                display_name = vals[0]

    title = f"REPORTE - {display_name}"
    build_header(elements, title=title)

    def fmt_pct_display(val, decimals: int = 2):
        """Convierte un valor numérico en un porcentaje legible.
        - val puede ser un número (por ejemplo 0.32 para 32%) o una cadena ya formateada.
        - Si val es numérico y está entre -1 y 1, lo multiplica por 100.
        - Formatea con `decimals` decimales y elimina ceros/trailing dot innecesarios.
        - Devuelve una cadena con el signo '%' al final."""
        try:
            num = float(val)
        except Exception:
            # si ya es string, devolver limpio
            return str(val).strip()
        if abs(num) <= 1:
            num = num * 100
        fmt = f"{{num:.{decimals}f}}".replace('{num}', '{num}')
        # usar formateo directo para evitar que f-strings confundan la plantilla
        s = (f"{num:.{decimals}f}")
        # eliminar ceros finales y punto si es necesario
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return f"{s}%"

    # column set to show exact source columns: RUTA (if present), PPTO, VTS, CUMP, PSL, PROY, %_PROY, DEV, %_DEV, GAP
    # Columnas principales
    pres_col = "PPTO" if "PPTO" in df_vendor.columns else ("Presupuesto" if "Presupuesto" in df_vendor.columns else None)
    ven_col = "VTS" if "VTS" in df_vendor.columns else ("Ventas" if "Ventas" in df_vendor.columns else None)
    ps_col = "PSL" if "PSL" in df_vendor.columns else None
    proy_col = "PROY" if "PROY" in df_vendor.columns else ("PROYECCION" if "PROYECCION" in df_vendor.columns else ("PROYECTADO" if "PROYECTADO" in df_vendor.columns else None))
    pct_proy_col = "%_PROY" if "%_PROY" in df_vendor.columns else None
    dev_col = "DEV" if "DEV" in df_vendor.columns else None
    gap_col = "GAP" if "GAP" in df_vendor.columns else None

    cat_col = None
    if pres_col is None or ven_col is None:
        crear_tabla_estandar(elements, "EQUIPO DE VENTAS", [["RUTA", "PPTO", "VTS", "CUMP", "PSL", "PROY", "%_PROY", "DEV", "%_DEV", "GAP"], ["Sin datos", "", "", "", "", "", "", "", "", ""]])
    # Ordenar por PPTO descendente si existe la columna
    df_sorted = df_vendor.copy()
    if pres_col and pres_col in df_sorted.columns:
        df_sorted = df_sorted.sort_values(by=pres_col, ascending=False)
    else:
        df_sorted = df_vendor
    for cand in ("TipoProducto", "Categoria", "CATEGORIA", "CATEGORÍA", "Category", "CAT"):
        if cand in df_sorted.columns:
            cat_col = cand
            break
    if cat_col is None:
        for c in df_sorted.columns:
            # normalizar cadena para eliminar acentos y comparar en minúsculas
            c_norm = unicodedata.normalize('NFD', str(c)).encode('ascii','ignore').decode().lower()
            if c_norm in ("tipoproducto", "categoria", "category", "cat"):
                cat_col = c
                break

    header = ["Tipo Producto", "PPTO", "VTS", "CUMP", "PSL", "PROY", "%_PROY", "DEV", "%_DEV", "GAP"]

    # Construir filas solo con las columnas requeridas, sin RUTA
    if pres_col is None or ven_col is None:
        crear_tabla_estandar(elements, "EQUIPO DE VENTAS", [["Categoria", "PPTO", "VTS", "CUMP", "PSL", "PROY", "%_PROY", "DEV", "%_DEV", "GAP"], ["Sin datos", "", "", "", "", "", "", "", "", ""]])
    else:
        rows = [header]
        # Agrupar solo por categoria si existe
        group_keys = []
        if cat_col:
            group_keys.append(cat_col)
        if group_keys:
            agg_cols = {pres_col: 'sum', ven_col: 'sum'}
            if ps_col:
                agg_cols[ps_col] = 'sum'
            if proy_col:
                agg_cols[proy_col] = 'sum'
            if dev_col:
                agg_cols[dev_col] = 'sum'
            if gap_col:
                agg_cols[gap_col] = 'sum'
            agg = df_sorted.groupby(group_keys).agg(agg_cols).reset_index()
            # Ordenar por PPTO descendente si existe
            if pres_col in agg.columns:
                agg = agg.sort_values(by=pres_col, ascending=False)
            for _, r in agg.iterrows():
                category_value = r[cat_col] if (cat_col and cat_col in r.index) else ""
                pres_val = r.get(pres_col, 0)
                ven_val = r.get(ven_col, 0)
                psl_val = r.get(ps_col, None) if ps_col else None
                proy_val = r.get(proy_col, None) if proy_col else None
                dev_val = r.get(dev_col, 0) if dev_col else 0
                gap_val = r.get(gap_col, None) if gap_col else (pres_val - ven_val)
                pct_proy_val = (proy_val / pres_val * 100) if pres_val else 0
                pct_dev_val = (abs(dev_val) / (ven_val + abs(dev_val)) * 100) if (ven_val + abs(dev_val)) else 0
                cump_val = (ven_val / pres_val * 100) if pres_val else 0
                pres_str = f"{pres_val:,.0f}" if pres_val is not None else "0"
                ven_str = f"{ven_val:,.0f}" if ven_val is not None else "0"
                psl_str = f"{psl_val:,.0f}" if (psl_val is not None and pd.notna(psl_val)) else ""
                proy_str = f"{proy_val:,.0f}" if (proy_val is not None and pd.notna(proy_val)) else ""
                dev_str = f"{dev_val:,.0f}" if pd.notna(dev_val) else "0"
                gap_str = f"{gap_val:,.0f}" if (gap_val is not None and pd.notna(gap_val)) else ""
                cump_str = f"{cump_val:.2f}%" if pres_val else ""
                pct_proy = f"{pct_proy_val:.2f}%" if pres_val else ""
                pct_dev = f"{pct_dev_val:.2f}%"
                rows.append([category_value, pres_str, ven_str, cump_str, psl_str, proy_str, pct_proy, dev_str, pct_dev, gap_str])
        else:
            # Si no hay agrupación, usar todo el DataFrame como una sola fila
            pres_val = df_sorted[pres_col].sum(min_count=1)
            ven_val = df_sorted[ven_col].sum(min_count=1)
            psl_val = df_sorted[ps_col].sum(min_count=1) if ps_col else None
            proy_val = df_sorted[proy_col].sum(min_count=1) if proy_col else None
            dev_val = df_sorted[dev_col].sum(min_count=1) if dev_col else 0
            gap_val = df_sorted[gap_col].sum(min_count=1) if gap_col else (pres_val - ven_val)
            pct_proy_val = (proy_val / pres_val * 100) if pres_val else 0
            pct_dev_val = (abs(dev_val) / (ven_val + abs(dev_val)) * 100) if (ven_val + abs(dev_val)) else 0
            cump_val = (ven_val / pres_val * 100) if pres_val else 0
            pres_str = f"{pres_val:,.0f}" if pres_val is not None else "0"
            ven_str = f"{ven_val:,.0f}" if ven_val is not None else "0"
            psl_str = f"{psl_val:,.0f}" if (psl_val is not None and pd.notna(psl_val)) else ""
            proy_str = f"{proy_val:,.0f}" if (proy_val is not None and pd.notna(proy_val)) else ""
            dev_str = f"{dev_val:,.0f}" if pd.notna(dev_val) else "0"
            gap_str = f"{gap_val:,.0f}" if (gap_val is not None and pd.notna(gap_val)) else ""
            cump_str = f"{cump_val:.2f}%" if pres_val else ""
            pct_proy = f"{pct_proy_val:.2f}%" if pres_val else ""
            pct_dev = f"{pct_dev_val:.2f}%"
            rows.append([display_name, pres_str, ven_str, cump_str, psl_str, proy_str, pct_proy, dev_str, pct_dev, gap_str])

        # Fila TOTAL al final, sumando columnas numéricas y calculando %_PROY total
        total_pres = sum(float(row[1].replace(',','')) if row[1] else 0 for row in rows[1:])
        total_ven = sum(float(row[2].replace(',','')) if row[2] else 0 for row in rows[1:])
        total_psl = sum(float(row[4].replace(',','')) if row[4] else 0 for row in rows[1:])
        total_proy = sum(float(row[5].replace(',','')) if row[5] else 0 for row in rows[1:])
        total_dev = sum(float(row[7].replace(',','')) if row[7] else 0 for row in rows[1:])
        total_gap = sum(float(row[9].replace(',','')) if row[9] else 0 for row in rows[1:])
        total_cump = (total_ven/total_pres*100) if total_pres else 0
        total_pct_proy = (total_proy/total_pres*100) if total_pres else 0
        total_pct_dev = (abs(total_dev)/(total_ven + abs(total_dev))*100) if (total_ven + abs(total_dev)) else 0
        total_row = ["TOTAL", f"{total_pres:,.0f}", f"{total_ven:,.0f}", f"{total_cump:.2f}%", f"{total_psl:,.0f}", f"{total_proy:,.0f}", f"{total_pct_proy:.2f}%", f"{total_dev:,.0f}", f"{total_pct_dev:.2f}%", f"{total_gap:,.0f}"]
        rows.append(total_row)
        crear_tabla_estandar(elements, "EQUIPO DE VENTAS", rows)

    # DETALLE POR PRODUCTO eliminado: no se incluye en este reporte
    # (se removió la tabla por producto por petición del usuario)


    # nombre de archivo — usar display_name (si fue resuelto) para que incluya código y nombre
    safe = sanitize_filename(str(display_name))
    filename = os.path.join(out_dir, f"Reporte_{safe}.pdf")
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.2*cm, bottomMargin=1*cm)

    def footer(canvas, doc):
        canvas.saveState()
        width, height = landscape(A4)
        footer_text = "@Todos los derechos reservados por laboratorios alfa S.R.L. Creado por Inteligencia de Negocios"
        canvas.setFillColorRGB(0.5, 0.5, 0.5)  # gris
        canvas.rect(0, 0, width, 18, fill=1, stroke=0)
        canvas.setFillColorRGB(1, 1, 1)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(width/2, 6, footer_text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    print(f"Generado: {filename}")


def build_report(ano: int = None, mes: int = None, dia: int = None, out_dir: str = "VENTAS"):
    # obtener datos frescos cada ejecución
    df = connection.get_dataframe(ano=ano, mes=mes)

    if df is None or df.empty:
        print("No hay datos para generar reportes.")
        return

    # No renaming required: get_dataframe returns columns: Vendedor, PPTO, VTS, CUMP, PSL, PROY, %_PROY
    # We'll use the source column names directly.

    # detectar columna de vendedor
    vendor_col = None
    for cand in ("RUTA", "Vendedor", "VENDEDOR"):
        if cand in df.columns:
            vendor_col = cand
            break
    if vendor_col is None:
        # si no existe columna de vendedor, usar la primera columna como agrupador
        vendor_col = df.columns[0]

    # crear directorio de salida si no existe
    os.makedirs(out_dir, exist_ok=True)

    # generar un PDF por vendedor
    for vendedor_value, group in df.groupby(vendor_col):
        build_report_for_vendor(vendedor_value, group, out_dir=out_dir)


def find_report_by_vendor_code(vendor_code: str, out_dir: str = "VENTAS") -> list:
    """Busca archivos `Reporte_{vendor_code}*.pdf` en `out_dir` y devuelve la lista de rutas encontradas."""
    if not os.path.isdir(out_dir):
        return []
    # Convertir vendor_code a entero para comparación robusta
    try:
        vendor_code_int = int(vendor_code)
    except Exception:
        vendor_code_int = str(vendor_code).lstrip('0')  # fallback: quitar ceros a la izquierda

    matches = []
    for fname in os.listdir(out_dir):
        if not fname.lower().endswith('.pdf'):
            continue
        # Extraer el código del nombre del archivo: Reporte_{codigo}_...
        base = os.path.basename(fname)
        parts = base.split('_')
        if len(parts) < 2:
            continue
        code_part = parts[1]
        # Limpiar posibles guiones y espacios
        code_part = code_part.strip().replace('-', '').replace(' ', '')
        try:
            code_int = int(code_part)
        except Exception:
            code_int = code_part.lstrip('0')
        if code_int == vendor_code_int:
            matches.append(os.path.join(out_dir, fname))
    return sorted(matches)


def get_graph_token(graph_config: dict) -> str:
    """Obtiene un token OAuth2 (client_credentials) para Microsoft Graph.

    graph_config debe contener: tenant_id, client_id, client_secret
    Devuelve access_token en caso de éxito o lanza excepción si falla.
    """
    tenant_id = graph_config.get('tenant_id')
    client_id = graph_config.get('client_id')
    client_secret = graph_config.get('client_secret')
    if not tenant_id or not client_id or not client_secret:
        raise ValueError('graph_config debe contener tenant_id, client_id y client_secret')

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    r = requests.post(token_url, data=data, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f'Error obteniendo token: {r.status_code} {r.text}')
    return r.json()['access_token']


def send_report_via_graph(to_email: str, vendor_code: str, out_dir: str = "VENTAS", subject_template: str = None, body_template: str = None, dry_run: bool = True, graph_config: dict = None) -> bool:
    """Envía (o simula) el primer PDF encontrado para `vendor_code` usando Microsoft Graph (app-only).

    graph_config debe incluir: tenant_id, client_id, client_secret, sender (email address used as from)
    """
    files = find_report_by_vendor_code(vendor_code, out_dir)
    subject = subject_template or f"Reporte para vendedor {vendor_code}"
    body = body_template or f"Adjunto encontrarás el reporte para el vendedor {vendor_code}."

    # Si no hay archivo, enviar solo el correo sin adjunto (útil para resumen)
    attach = None
    if files:
        file_path = files[0]
        with open(file_path, 'rb') as f:
            b = f.read()
        b64 = base64.b64encode(b).decode('ascii')
        attach = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": os.path.basename(file_path),
            "contentType": "application/pdf",
            "contentBytes": b64
        }

    if dry_run:
        print("DRY RUN (graph): se enviaría correo a:", to_email)
        print(" Asunto:", subject)
        print(" Cuerpo:", body)
        if attach:
            print(" Archivo adjunto:", attach["name"])
        else:
            print(" Sin archivo adjunto")
        return True

    if graph_config is None:
        raise ValueError('graph_config requerido para envío por Graph')

    access_token = get_graph_token(graph_config)
    sender = graph_config.get('sender')
    if not sender:
        raise ValueError('graph_config debe incluir la cuenta remitente en la clave "sender"')

    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": to_email}}
            ]
        }
    }
    if attach:
        message["message"]["attachments"] = [attach]

    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    r = requests.post(url, headers=headers, data=json.dumps(message), timeout=20)
    if r.status_code in (200, 202):
        print('Enviado via Graph:', to_email)
        return True
    else:
        print('Error Graph:', r.status_code, r.text)
        return False


def send_report_to(email_address: str, vendor_code: str, out_dir: str = "VENTAS", subject_template: str = None, body_template: str = None, dry_run: bool = True, smtp_config: dict = None) -> bool:
    """Envía (o simula el envío) del primer PDF encontrado para `vendor_code` al `email_address`.

    Si `dry_run=True` sólo imprime lo que se enviaría (recomendado para pruebas).
    Para envío real, pasar `smtp_config` con: host, port, username, password, from_addr, use_tls (bool).
    """
    files = find_report_by_vendor_code(vendor_code, out_dir)
    if not files:
        print(f"No se encontró archivo para vendedor '{vendor_code}' en {out_dir}")
        return False

    file_path = files[0]
    subject = subject_template or f"Reporte para vendedor {vendor_code}"
    body = body_template or f"Adjunto encontrarás el reporte para el vendedor {vendor_code}."

    if dry_run:
        print("DRY RUN: se enviaría correo a:", email_address)
        print(" Asunto:", subject)
        print(" Cuerpo:", body)
        print(" Archivo adjunto:", file_path)
        return True

    # envío real
    if smtp_config is None:
        raise ValueError("smtp_config requerido para envíos reales")

    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_config.get('from_addr', smtp_config.get('username'))
    msg["To"] = email_address
    msg.set_content(body)

    with open(file_path, 'rb') as f:
        data = f.read()
    msg.add_attachment(data, maintype='application', subtype='pdf', filename=os.path.basename(file_path))

    host = smtp_config.get('host')
    port = smtp_config.get('port', 587)
    username = smtp_config.get('username')
    password = smtp_config.get('password')
    use_tls = smtp_config.get('use_tls', True)

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=smtp_config.get('timeout', 10))
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=smtp_config.get('timeout', 10))

        if username and password:
            server.login(username, password)

        server.send_message(msg)
        server.quit()
        print("Enviado:", file_path, "->", email_address)
        return True
    except Exception as e:
        print("Error enviando correo a", email_address, "para vendedor", vendor_code)
        print(type(e).__name__, e)
        return False


def test_smtp_connection(smtp_config: dict) -> tuple:
    """Prueba conectar y (opcionalmente) logearse en SMTP. Devuelve (True, None) si ok, o (False, error) en caso contrario.

    smtp_config keys: host, port, username (opt), password (opt), use_tls (bool)
    """
    import smtplib
    host = smtp_config.get('host')
    port = smtp_config.get('port', 587)
    username = smtp_config.get('username')
    password = smtp_config.get('password')
    use_tls = smtp_config.get('use_tls', True)
    timeout = smtp_config.get('timeout', 10)

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=timeout)

        if username and password:
            server.login(username, password)
        server.quit()
        return (True, None)
    except Exception as e:
        return (False, e)


def send_reports_from_mapping(mapping_path: str, out_dir: str = "VENTAS", dry_run: bool = True, method: str = 'smtp', smtp_config: dict = None, graph_config: dict = None) -> dict:
    """Procesa un CSV/Excel con columnas Vendedor y Correo y envía (o hace dry-run) los reportes.

    method: 'smtp' (por defecto) o 'graph'
    Retorna un dict con listas: sent, failed, missing_file, invalid_email
    """
    import pandas as pd
    if mapping_path.lower().endswith('.csv'):
        mp = pd.read_csv(mapping_path, dtype=str)
    else:
        mp = pd.read_excel(mapping_path, dtype=str)

    # normalizar nombres de columna
    cols = {c.lower(): c for c in mp.columns}
    vendedor_col = cols.get('vendedor') or cols.get('vendor') or cols.get('codigo') or mp.columns[0]
    correo_col = cols.get('correo') or cols.get('email') or cols.get('mail') or mp.columns[1] if len(mp.columns) > 1 else None

    sent = []
    failed = []
    missing_file = []
    invalid_email = []


    from datetime import date
    today_str = date.today().strftime("%d/%m/%Y")

    for _, row in mp.iterrows():
        vendor_code = str(row[vendedor_col]).strip()
        email = str(row[correo_col]).strip() if correo_col else ''
        if not email or email.lower() in ('nan', 'none'):
            invalid_email.append((vendor_code, email))
            continue

        files = find_report_by_vendor_code(vendor_code, out_dir)
        if not files:
            missing_file.append(vendor_code)
            continue

        # Obtener nombre del vendedor del archivo PDF (ejemplo: Reporte_01_-_LEIDY_PERALTA.pdf)
        vendedor_nombre = vendor_code
        if files:
            fname = files[0]
            # Extraer nombre entre primer guion bajo y .pdf
            import os
            base = os.path.basename(fname)
            partes = base.split('_', 2)
            if len(partes) == 3:
                vendedor_nombre = partes[2].replace('.pdf','').replace('_',' ').strip()
            else:
                vendedor_nombre = vendor_code

        subject = f'Ventas diarias "{vendedor_nombre}", "{today_str}"'
        body = f'Adjunto le envío las ventas correspondientes al día "{today_str}".\n\nSaludos cordiales'

        try:
            if method == 'smtp':
                ok = send_report_to(email, vendor_code, out_dir=out_dir, subject_template=subject, body_template=body, dry_run=dry_run, smtp_config=smtp_config)
            elif method == 'graph':
                ok = send_report_via_graph(email, vendor_code, out_dir=out_dir, subject_template=subject, body_template=body, dry_run=dry_run, graph_config=graph_config)
            else:
                print('Método desconocido:', method)
                ok = False
        except Exception as e:
            print('Excepción enviando', vendor_code, email, type(e).__name__, e)
            ok = False

        if ok:
            sent.append((vendor_code, email))
        else:
            failed.append((vendor_code, email))

    summary = {
        'sent': sent,
        'failed': failed,
        'missing_file': missing_file,
        'invalid_email': invalid_email,
    }
    print('Resumen envio:', summary)
    return summary


if __name__ == "__main__":
    # 1. Generar los reportes (opcional, descomentar si es necesario)
    build_report()

    # 2. Cargar configuración de Graph
    graph_config = load_graph_config()

    # 3. Enviar reportes a cada vendedor según el CSV
    import sys
    def get_app_root():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    mapping_path = os.path.join(get_app_root(), "RelacionCorreosVendedores.csv")
    resumen = send_reports_from_mapping(
        mapping_path=mapping_path,
        out_dir="VENTAS",
        dry_run=False,
        method='graph',
        graph_config=graph_config
    )

    # 4. Enviar correo de resumen a businessintelligence@laboratoriosalfa.com
    resumen_txt = "RESUMEN DE ENVÍO DE REPORTES\n\n"
    resumen_txt += f"Enviados correctamente: {len(resumen['sent'])}\n"
    for v, e in resumen['sent']:
        resumen_txt += f"  - {v}: {e}\n"
    resumen_txt += f"\nErrores de envío: {len(resumen['failed'])}\n"
    for v, e in resumen['failed']:
        resumen_txt += f"  - {v}: {e}\n"
    resumen_txt += f"\nArchivos no encontrados: {len(resumen['missing_file'])}\n"
    for v in resumen['missing_file']:
        resumen_txt += f"  - {v}\n"
    resumen_txt += f"\nCorreos inválidos: {len(resumen['invalid_email'])}\n"
    for v, e in resumen['invalid_email']:
        resumen_txt += f"  - {v}: {e}\n"

    # Si hubo errores de envío, enviar un reporte detallado a businessintelligence@laboratoriosalfa.com
    if resumen['failed']:
        detalle_errores = "REPORTE DE ERRORES DE ENVÍO DE CORREOS\n\n"
        detalle_errores += f"Total errores de envío: {len(resumen['failed'])}\n"
        for v, e in resumen['failed']:
            detalle_errores += f"  - Vendedor: {v} | Correo: {e}\n"
        detalle_errores += "\nPor favor, revisar estos correos y reenviar manualmente si es necesario.\n"
        send_report_via_graph(
            to_email="businessintelligence@laboratoriosalfa.com",
            vendor_code="ERRORES_ENVIO",
            out_dir="VENTAS",
            subject_template="Errores de envío de reportes de ventas",
            body_template=detalle_errores,
            dry_run=False,
            graph_config=graph_config
        )

    # Enviar correo de resumen general
    send_report_via_graph(
        to_email="businessintelligence@laboratoriosalfa.com",
        vendor_code="RESUMEN",
        out_dir="VENTAS",
        subject_template="Resumen de envío de reportes de ventas",
        body_template=resumen_txt,
        dry_run=False,
        graph_config=graph_config
    )

