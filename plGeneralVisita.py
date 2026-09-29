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


# --- NUEVO: funciÃ³n para cargar configuraciÃ³n de Graph desde archivo externo ---
def load_graph_config(path="graph_config.json"):
    """Carga la configuraciÃ³n de Microsoft Graph desde un archivo JSON."""
    # Si la ruta no es absoluta, buscar en la carpeta del ejecutable
    if not os.path.isabs(path):
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(app_dir, path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No se encontrÃ³ el archivo de configuraciÃ³n: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# requests se usa para Graph API (si no estÃ¡ instalado, se debe instalar: pip install requests)
import requests

# Salida PDF (nombre por defecto si quieres generar un Ãºnico archivo)
pdf_file = "Reporte_generado.pdf"
styles = getSampleStyleSheet()

def build_header(elements, title="REPORTE GENERAL"):
    logo_path = "logo.png"
    # 1 cm â‰ˆ 28.35 px, asÃ­ que 10px â‰ˆ 0.353 cm
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
    # Agregar nota solo si el tÃ­tulo es 'EQUIPO DE VISITA MEDICA'
    if titulo.strip().upper() == 'EQUIPO DE VISITA MEDICA':
        nota = 'NOTA: La distribución del presupuesto se realiza con fines de focalización estratégica en su zona, manteniéndose como meta principal el logro del 100% del presupuesto total.'
        from reportlab.lib.styles import ParagraphStyle
        nota_style = ParagraphStyle('nota', fontSize=9, textColor='#444444', leftIndent=6, rightIndent=6, spaceAfter=6)
        elements.append(Paragraph(nota, nota_style))

    ncols = len(data[0])
    page_width, _ = landscape(A4)
    available_width = page_width - (2 * cm)  # margen aproximado

    # Ajuste de ancho: distribuir el ancho disponible entre todas las columnas
    if ncols > 1:
        first_col_w = 110
        other_col_w = (available_width - first_col_w) / (ncols - 1)
        colWidths = [first_col_w] + [other_col_w] * (ncols - 1)
    else:
        colWidths = [available_width]

    # Eliminar fila TOTAL extra: ahora la fila TOTAL solo se agrega desde build_report_for_vendor, no aquÃ­

    tabla = Table(data, colWidths=colWidths, repeatRows=1)

    header_size = 9  # Definir tamaño de fuente para el encabezado
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

    # Color de texto NEGRO para la primera columna (RUTA, vendedor) en filas de datos, excepto filas TOTAL*
    nrows = len(data)
    for i in range(1, nrows):
        if str(data[i][0]).strip().upper().startswith('TOTAL'):
            styles_list.append(('TEXTCOLOR', (0,i), (0,i), colors.white))
        else:
            styles_list.append(('TEXTCOLOR', (0,i), (0,i), colors.HexColor("#23282B")))

    # alineaciones por columna: primeras 2 columnas a la izquierda, resto a la derecha
        #styles_list.append(('ALIGN', (0,1), (1,-1), 'LEFT'))
        #styles_list.append(('ALIGN', (2,1), (-2,-1), 'RIGHT'))
    # Padding personalizado: mÃ¡s para RUTA, menos para las demÃ¡s
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

    # detectar filas TOTAL* y aplicar estilo destacado (negrita + fondo)
    total_rows = [i for i, row in enumerate(data) if i > 0 and len(row) > 1 and str(row[0]).strip().upper().startswith('TOTAL')]
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
    # eliminar caracteres no vÃ¡lidos para archivos
    return re.sub(r'[^A-Za-z0-9_\-\.]', '', name)


def build_report_for_vendor(vendedor_value: str, df_vendor: pd.DataFrame, out_dir: str = "VENTAS VISITA"):
    elements = []
    # Renombrar columnas para que sean consistentes y sin espacios/case
    rename_map = {
        'codigo ruta': 'CodigoRuta',
        'codigoruta': 'CodigoRuta',
        'categoria': 'Categoria',
        'tipoproducto': 'Categoria',
        'grupo visita': 'gprVisita',
        'gprvisita': 'gprVisita',
        'ppto': 'PPTO',
        'vts': 'VTS',
        'cump': 'CUMP',
        'psl': 'PSL',
        'proyeccion': 'PROYECCION',
        '%_proy': '%_PROY',
        '%_proyeccion': '%_PROY',
        'dev': 'DEV',
        '%_dev': '%_DEV',
        'gap': 'GAP',
    }
    df_vendor = df_vendor.rename(columns={c: rename_map.get(c.strip().lower(), c) for c in df_vendor.columns})

    # Detect route code column
    vendor_col = None
    for cand in ("CodigoRuta", "CODIGORUTA", "Codigo Ruta", "RUTA", "Vendedor", "VENDEDOR"):
        if cand in df_vendor.columns:
            vendor_col = cand
            break
    if vendor_col is None:
        vendor_col = df_vendor.columns[0]

    display_name = str(vendedor_value)
    if vendor_col in df_vendor.columns:
        vals = df_vendor[vendor_col].dropna().astype(str).unique()
        for v in vals:
            if str(v).strip().startswith(str(vendedor_value).strip()):
                display_name = v
                break
        else:
            if len(vals):
                display_name = vals[0]

    title = f"REPORTE - {display_name}"
    build_header(elements, title=title)

    # Expected dataset columns: CodigoRuta, Categoria, gprVisita, PPTO, VTS, PSL
    ruta_col = vendor_col if vendor_col in df_vendor.columns else None
    cat_col = None
    gpr_col = None
    # Eliminar referencia a Categoria
    cat_col = None
    for cand in ("gprVisita", "GprVisita", "GPRVISITA", "Grupo Visita"):
        if cand in df_vendor.columns:
            gpr_col = cand
            break

    pres_col = "PPTO" if "PPTO" in df_vendor.columns else None
    ven_col = "VTS" if "VTS" in df_vendor.columns else None
    psl_col = "PSL" if "PSL" in df_vendor.columns else None
    dev_col = "DEV" if "DEV" in df_vendor.columns else None
    gap_col = "GAP" if "GAP" in df_vendor.columns else None

    # Detect columns for PROYECCION, %_PROY, DEV, %_DEV and GAP
    proy_col = None
    pct_proy_col = None
    # Buscar columnas con nombres exactos (como en la consulta SQL)
    for cand in ("PROYECCION", "Proyeccion", "PROY", "PROYEC"):
        if cand in df_vendor.columns:
            proy_col = cand
            break
    for cand in ("%_PROY", "%_PROYECCION"):
        if cand in df_vendor.columns:
            pct_proy_col = cand
            break

    header = ["CodigoRuta", "gprVisita", "PPTO", "VTS", "CUMP", "PSL", "PROYECCION", "%_PROY", "DEV", "%_DEV", "GAP"]
    
    # --- DATA GROUPING AND TABLE GENERATION ---
    if ruta_col is None or gpr_col is None or pres_col is None or ven_col is None or psl_col is None:
        vacio = ["Sin datos"] + ["" for _ in header[1:]]
        crear_tabla_estandar(elements, "EQUIPO DE VISITA MEDICA", [header, vacio])
    else:
        # Pre-aggregate data to have clean rows for grouping
        agg_dict = {pres_col: "sum", ven_col: "sum", psl_col: "sum"}
        if proy_col:
            agg_dict[proy_col] = "sum"
        if pct_proy_col:
            agg_dict[pct_proy_col] = "mean"
        if dev_col:
            agg_dict[dev_col] = "sum"
        if gap_col:
            agg_dict[gap_col] = "sum"
        agg_base = (
            df_vendor
            .groupby([ruta_col, gpr_col], dropna=False)
            .agg(agg_dict)
            .reset_index()
            .sort_values(by=[ruta_col, pres_col], ascending=[True, False])
        )

        # Unique routes in this vendor's data
        unique_routes = agg_base[ruta_col].dropna().unique()
        first_table = True
        for route in unique_routes:
            route_data = agg_base[agg_base[ruta_col] == route]
            if route_data.empty:
                continue

            rows = [header]
            route_pres_total = 0.0
            route_ven_total = 0.0
            route_psl_total = 0.0
            route_proy_total = 0.0
            route_dev_total = 0.0
            route_gap_total = 0.0
            route_pct_proy_total = 0.0
            proy_count = 0
            pct_proy_count = 0

            for _, r in route_data.iterrows():
                ruta_value = str(r[ruta_col]) if pd.notna(r[ruta_col]) else ""
                gpr_value = str(r[gpr_col]) if pd.notna(r[gpr_col]) else ""
                pres_val = float(r[pres_col]) if pd.notna(r[pres_col]) else 0.0
                ven_val = float(r[ven_col]) if pd.notna(r[ven_col]) else 0.0
                psl_val = float(r[psl_col]) if pd.notna(r[psl_col]) else 0.0
                cump_val = (ven_val / pres_val * 100) if pres_val else 0.0
                proy_val = r[proy_col] if proy_col and proy_col in r and pd.notna(r[proy_col]) else None
                pct_proy_val = r[pct_proy_col] if pct_proy_col and pct_proy_col in r and pd.notna(r[pct_proy_col]) else None
                dev_val = float(r[dev_col]) if dev_col and dev_col in r and pd.notna(r[dev_col]) else 0.0
                gap_val = float(r[gap_col]) if gap_col and gap_col in r and pd.notna(r[gap_col]) else (pres_val - ven_val)
                pct_dev_val = (abs(dev_val) / (ven_val + abs(dev_val)) * 100) if (ven_val + abs(dev_val)) else 0.0

                route_pres_total += pres_val
                route_ven_total += ven_val
                route_psl_total += psl_val
                route_dev_total += dev_val
                route_gap_total += gap_val
                if proy_val is not None:
                    try:
                        route_proy_total += float(proy_val)
                        proy_count += 1
                    except Exception:
                        pass
                if pct_proy_val is not None:
                    try:
                        route_pct_proy_total += float(pct_proy_val)
                        pct_proy_count += 1
                    except Exception:
                        pass

                row = [
                    ruta_value,
                    gpr_value,
                    f"{pres_val:,.0f}",
                    f"{ven_val:,.0f}",
                    f"{cump_val:.2f}%",
                    f"{psl_val:,.0f}",
                ]
                row.append(f"{float(proy_val):,.0f}" if proy_val is not None else "")
                if pct_proy_val is not None:
                    try:
                        pct_val = float(pct_proy_val) * 100 if float(pct_proy_val) < 2 else float(pct_proy_val)
                        row.append(f"{pct_val:.2f}%")
                    except Exception:
                        row.append(str(pct_proy_val))
                else:
                    row.append("")
                row.extend([
                    f"{dev_val:,.0f}",
                    f"{pct_dev_val:.2f}%",
                    f"{gap_val:,.0f}",
                ])
                rows.append(row)

            # Add TOTAL row for this route
            route_total_cump = (route_ven_total / route_pres_total * 100) if route_pres_total else 0.0
            route_total_pct_dev = (abs(route_dev_total) / (route_ven_total + abs(route_dev_total)) * 100) if (route_ven_total + abs(route_dev_total)) else 0.0
            route_norm = str(route).upper().replace(r"[^A-Z0-9]", "")
            if "RUTACADENAS" in route_norm:
                total_label = "TOTAL RUTA CADENAS"
            else:
                total_label = "TOTAL RUTA"

            total_row = [
                total_label,
                "",
                f"{route_pres_total:,.0f}",
                f"{route_ven_total:,.0f}",
                f"{int(route_total_cump)}%",
                f"{route_psl_total:,.0f}",
            ]
            total_row.append(f"{route_proy_total:,.0f}" if proy_count > 0 else "")
            avg_pct = (route_pct_proy_total / pct_proy_count * 100) if pct_proy_count > 0 else 0.0
            total_row.append(f"{avg_pct:.2f}%" if pct_proy_count > 0 else "")
            total_row.extend([
                f"{route_dev_total:,.0f}",
                f"{route_total_pct_dev:.2f}%",
                f"{route_gap_total:,.0f}",
            ])
            rows.append(total_row)

            table_title = "EQUIPO DE VISITA MEDICA" if first_table else ""
            crear_tabla_estandar(elements, table_title, rows)
            first_table = False

    safe = sanitize_filename(str(display_name))
    filename = os.path.join(out_dir, f"Reporte_{safe}.pdf")
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.2*cm, bottomMargin=1*cm)

    def footer(canvas, doc):
        canvas.saveState()
        width, height = landscape(A4)
        footer_text = "@Todos los derechos reservados por laboratorios alfa S.R.L. Creado por Inteligencia de Negocios"
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        canvas.rect(0, 0, width, 18, fill=1, stroke=0)
        canvas.setFillColorRGB(1, 1, 1)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(width/2, 6, footer_text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    print(f"Generado: {filename}")


def build_report(ano: int = None, mes: int = None, dia: int = None, out_dir: str = " VENTAS VISITA"):
    # obtener datos frescos cada ejecuciÃ³n
    df = connection.get_dataframeVisita(ano=ano, mes=mes)

    if df is None or df.empty:
        print("No hay datos para generar reportes.")
        return

    # No renaming required: get_dataframeVisita returns columns: CodigoRuta, Categoria, gprVisita, PPTO, VTS, PSL
    # We'll use the source column names directly.

    # detectar columna de vendedor
    vendor_col = None
    for cand in ("CodigoRuta", "CODIGORUTA", "Codigo Ruta", "RUTA", "Vendedor", "VENDEDOR", "RutaVisita"):
        if cand in df.columns:
            vendor_col = cand
            break
    if vendor_col is None:
        # si no existe columna de vendedor, usar la primera columna como agrupador
        vendor_col = df.columns[0]

    # detectar columna gpr para aplicar el cruce con RUTA CADENAS
    gpr_col = None
    for cand in ("gprVisita", "GprVisita", "GPRVISITA", "Grupo Visita"):
        if cand in df.columns:
            gpr_col = cand
            break
    # Columna de linea para hacer match exacto junto con gprVisita
    line_col = None
    for cand in ("line_VM", "LINE_VM", "Line_VM", "Linea_VM", "linea_vm"):
        if cand in df.columns:
            line_col = cand
            break
    # fallback si line_VM no viene en el dataset
    if line_col is None:
        for cand in ("Categoria", "CATEGORIA", "TipoProducto"):
            if cand in df.columns:
                line_col = cand
                break

    # crear directorio de salida si no existe
    os.makedirs(out_dir, exist_ok=True)

    # separar RUTA CADENAS para usarla como alimentador de otras rutas
    route_norm = (
        df[vendor_col]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.replace(r"[^A-Z0-9]", "", regex=True)
    )
    is_ruta_cadenas = route_norm.eq("RUTACADENAS")
    df_cadenas = df[is_ruta_cadenas].copy()
    df_main = df[~is_ruta_cadenas].copy()

    # generar un PDF por ruta (sin generar PDF propio para RUTA CADENAS)
    for vendedor_value, group in df_main.groupby(vendor_col):
        group_aug = group.copy()

        # agregar filas de RUTA CADENAS con match exacto por gprVisita + line_VM
        if gpr_col and not df_cadenas.empty and gpr_col in group.columns and gpr_col in df_cadenas.columns:
            if line_col and line_col in group.columns and line_col in df_cadenas.columns:
                group_pairs = set(
                    zip(
                        group[gpr_col].fillna("").astype(str).str.strip().str.upper(),
                        group[line_col].fillna("").astype(str).str.strip().str.upper(),
                    )
                )
                cadenas_mask = [
                    (gpr_v, line_v) in group_pairs
                    for gpr_v, line_v in zip(
                        df_cadenas[gpr_col].fillna("").astype(str).str.strip().str.upper(),
                        df_cadenas[line_col].fillna("").astype(str).str.strip().str.upper(),
                    )
                ]
                cadenas_match = df_cadenas[cadenas_mask]
            else:
                gpr_vals = (
                    group[gpr_col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .unique()
                )
                cadenas_match = df_cadenas[
                    df_cadenas[gpr_col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .isin(gpr_vals)
                ] if len(gpr_vals) > 0 else df_cadenas.iloc[0:0]

            if not cadenas_match.empty:
                group_aug = pd.concat([group_aug, cadenas_match], ignore_index=True)

        build_report_for_vendor(vendedor_value, group_aug, out_dir=out_dir)


def find_report_by_vendor_code(vendor_code: str, out_dir: str = "VENTAS VISITA") -> list:
    """Busca archivos `Reporte_{vendor_code}*.pdf` en `out_dir` y devuelve la lista de rutas encontradas.
    
    Busca normalizando espacios a guiones bajos para coincidir con cómo se guardan los archivos.
    """
    if not os.path.isdir(out_dir):
        return []
    
    # Normalizar el código de vendedor: reemplazar espacios con guiones bajos
    normalized_code = vendor_code.strip().replace(' ', '_').upper()
    
    matches = []
    for fname in os.listdir(out_dir):
        if not fname.lower().endswith('.pdf'):
            continue
        
        base = os.path.basename(fname)
        # El archivo tiene formato: Reporte_{CODIGO_NORMALIZADO}.pdf
        # Extraer la parte entre "Reporte_" y ".pdf"
        if base.startswith('Reporte_') and base.endswith('.pdf'):
            # Remover "Reporte_" al inicio y ".pdf" al final
            code_part = base[8:-4]  # 8 = len('Reporte_'), 4 = len('.pdf')
            
            # Comparar después de normalizar (espacios a guiones bajos)
            if code_part.upper() == normalized_code:
                matches.append(os.path.join(out_dir, fname))
    
    return sorted(matches)


def get_graph_token(graph_config: dict) -> str:
    """Obtiene un token OAuth2 (client_credentials) para Microsoft Graph.

    graph_config debe contener: tenant_id, client_id, client_secret
    Devuelve access_token en caso de Ã©xito o lanza excepciÃ³n si falla.
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


def send_report_via_graph(to_email: str, vendor_code: str, out_dir: str = "VENTAS VISITA", subject_template: str = None, body_template: str = None, dry_run: bool = True, graph_config: dict = None) -> bool:
    """EnvÃ­a (o simula) el primer PDF encontrado para `vendor_code` usando Microsoft Graph (app-only).

    graph_config debe incluir: tenant_id, client_id, client_secret, sender (email address used as from)
    """
    files = find_report_by_vendor_code(vendor_code, out_dir)
    subject = subject_template or f"Reporte para vendedor {vendor_code}"
    body = body_template or f"Adjunto encontrarás el reporte para el vendedor {vendor_code}."

    # Si no hay archivo, enviar solo el correo sin adjunto (Ãºtil para resumen)
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
        print("DRY RUN (graph): se enviará correo a:", to_email)
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


def send_report_to(email_address: str, vendor_code: str, out_dir: str = "VENTAS VISITA", subject_template: str = None, body_template: str = None, dry_run: bool = True, smtp_config: dict = None) -> bool:
    """Envía (o simula el envío) del primer PDF encontrado para `vendor_code` al `email_address`.

    Si `dry_run=True` sólo imprime lo que se enviará (recomendado para pruebas).
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
        print("DRY RUN: se enviará correo a:", email_address)
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


def send_reports_from_mapping(mapping_path: str, out_dir: str = "VENTAS VISITA", dry_run: bool = True, method: str = 'smtp', smtp_config: dict = None, graph_config: dict = None) -> dict:
    """Procesa un CSV/Excel con columnas Vendedor y Correo y envÃ­a (o hace dry-run) los reportes.

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
    vendedor_col = cols.get('codigoruta') or cols.get('vendedor') or cols.get('vendor') or cols.get('codigo') or mp.columns[0]
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
        body = f'Adjunto le enviamos las ventas correspondientes al día "{today_str}".\n\nSaludos cordiales'

        try:
            if method == 'smtp':
                ok = send_report_to(email, vendor_code, out_dir=out_dir, subject_template=subject, body_template=body, dry_run=dry_run, smtp_config=smtp_config)
            elif method == 'graph':
                ok = send_report_via_graph(email, vendor_code, out_dir=out_dir, subject_template=subject, body_template=body, dry_run=dry_run, graph_config=graph_config)
            else:
                print('MÃ©todo desconocido:', method)
                ok = False
        except Exception as e:
            print('ExcepciÃ³n enviando', vendor_code, email, type(e).__name__, e)
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
    build_report(out_dir=" VENTAS VISITA")

    # 2. Cargar configuraciÃ³n de Graph
    graph_config = load_graph_config()

    # 3. Enviar reportes a cada vendedor segÃºn el CSV
    import sys
    def get_app_root():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    mapping_path = os.path.join(get_app_root(), "RelacionCorreosVisitadores.csv")
    resumen = send_reports_from_mapping(
        mapping_path=mapping_path,
        out_dir=" VENTAS VISITA",
        dry_run=False,
        method='graph',
        graph_config=graph_config
    )

    # 4. Enviar correo de resumen a businessintelligence@laboratoriosalfa.com
    resumen_txt = "RESUMEN DE ENVIOS DE REPORTES\n\n"
    resumen_txt += f"Enviados correctamente: {len(resumen['sent'])}\n"
    for v, e in resumen['sent']:
        resumen_txt += f"  - {v}: {e}\n"
    resumen_txt += f"\nErrores de envÃ­o: {len(resumen['failed'])}\n"
    for v, e in resumen['failed']:
        resumen_txt += f"  - {v}: {e}\n"
    resumen_txt += f"\nArchivos no encontrados: {len(resumen['missing_file'])}\n"
    for v in resumen['missing_file']:
        resumen_txt += f"  - {v}\n"
    resumen_txt += f"\nCorreos invÃ¡lidos: {len(resumen['invalid_email'])}\n"
    for v, e in resumen['invalid_email']:
        resumen_txt += f"  - {v}: {e}\n"

    # Si hubo errores de envÃ­o, enviar un reporte detallado a businessintelligence@laboratoriosalfa.com
    if resumen['failed']:
        detalle_errores = "REPORTE DE ERRORES DE ENVIO DE CORREOS\n\n"
        detalle_errores += f"Total errores de envÃ­o: {len(resumen['failed'])}\n"
        for v, e in resumen['failed']:
            detalle_errores += f"  - Vendedor: {v} | Correo: {e}\n"
        detalle_errores += "\nPor favor, revisar estos correos y reenviar manualmente si es necesario.\n"
        send_report_via_graph(
            to_email="businessintelligence@laboratoriosalfa.com",
            vendor_code="ERRORES_ENVIO",
            out_dir=" VENTAS VISITA",
            subject_template="Errores de envio de reportes de ventas",
            body_template=detalle_errores,
            dry_run=False,
            graph_config=graph_config
        )

    # Enviar correo de resumen general
    send_report_via_graph(
        to_email="businessintelligence@laboratoriosalfa.com",
        vendor_code="RESUMEN",
        out_dir=" VENTAS VISITA",
        subject_template="Resumen de envio de reporte de ventas visita medica",
        body_template=resumen_txt,
        dry_run=False,
        graph_config=graph_config
    )


