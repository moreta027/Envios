import base64
import json
import requests
# plInventarioCambios.py
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm
from datetime import date
import sys, os
import pandas as pd
import connection

styles = getSampleStyleSheet()

def resource_path(relative_path):
	base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
	return os.path.join(base_path, relative_path)


def build_header(elements, title="ACTUALIZACIÓN DE PRODUCTOS CON STOCK CERO"):
	logo_path = resource_path("logo.png")
	logo = Image(logo_path, width=5*cm, height=2.6*cm) if os.path.exists(logo_path) else Spacer(5*cm, 2.6*cm)
	titulo = Paragraph(f"<b>{title}</b>", ParagraphStyle('title', alignment=1, fontSize=16, leading=18))
	hoy = date.today()
	info = [
		["Fecha", hoy.strftime("%d/%m/%Y")],
		["Día", str(hoy.day)],
		["Mes", str(hoy.month)],
		["Centro", str('5503')],
		["Almacén", str('1001')],
	]
	tabla_info = Table(info, colWidths=[2.2*cm, 3.0*cm])
	tabla_info.setStyle(TableStyle([
		('BACKGROUND', (0,0), (-1,0), colors.HexColor("#00A3B4")),
		('TEXTCOLOR', (0,0), (-1,0), colors.white),
		('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
		('FONTSIZE', (0,0), (-1,-1), 8),
		('ALIGN', (0,0), (-1,-1), 'LEFT'),
		('GRID', (0,0), (-1,-1), 0.25, colors.grey)
	]))
	header_table = Table([[logo, titulo, tabla_info]], colWidths=[5.2*cm, 7.4*cm, 5*cm])
	header_table.setStyle(TableStyle([
		('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
		('LEFTPADDING', (0,0), (-1,-1), 6),
		('RIGHTPADDING', (0,0), (-1,-1), 6),
	]))
	elements.append(header_table)
	elements.append(Spacer(1, 0.3*cm))

def crear_tabla_inventario(elements, data):
	
	ncols = len(data[0])
	# Ahora hay 4 columnas: Producto, Stock, FechaRegistro, Tipo
	colWidths = [10*cm, 2.5*cm, 4*cm, 2.5*cm]
	def truncate(text, maxlen):
		text = str(text)
		return text if len(text) <= maxlen else text[:maxlen-3] + '...'

	# Limitar caracteres: Producto 40, Stock 10, Fecha de entrada 20, Tipo 20
	new_header = data[0][:]  # copia
	# Cambiar encabezado 'FechaRegistro' por 'Fecha de entrada'
	if "FechaRegistro" in new_header:
		idx = new_header.index("FechaRegistro")
		new_header[idx] = "Fecha de entrada"
	new_data = [new_header]
	for row in data[1:]:
		new_row = [
			truncate(row[0], 60),
			f"{float(row[1]):,.2f}" if row[1] not in (None, "", "nan") else "",
			truncate(row[2], 20),
			truncate(row[3], 20)
		]
		new_data.append(new_row)

	tabla = Table(new_data, colWidths=colWidths, repeatRows=1)
	tabla.setStyle(TableStyle([
		('BACKGROUND', (0,0), (-1,0), colors.HexColor("#198A99")),
		('TEXTCOLOR', (0,0), (-1,0), colors.white),
		('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
		('FONTSIZE', (0,0), (-1,0), 10),
		('ALIGN', (0,0), (-1,0), 'CENTER'),
		('GRID', (0,0), (-1,-1), 0.25, colors.HexColor("#35BDEE")),
		('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
		('LEFTPADDING', (0,0), (-1,-1), 4),
		('RIGHTPADDING', (0,0), (-1,-1), 4),
		('ALIGN', (1,1), (3,-1), 'CENTER'),
		('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
		('FONTSIZE', (0,1), (-1,-1), 9),
	]))
	elements.append(tabla)
	elements.append(Spacer(1, 0.4*cm))

def build_report_inventario(out_file="INVENTARIO/Reporte_CambiosInventario.pdf"):
	os.makedirs(os.path.dirname(out_file), exist_ok=True)
	df = connection.get_dataframeInventarioCambios()
	if df is None or df.empty:
		print("No hay cambios de inventario para reportar.")
		return
	# Renombrar columnas si es necesario
	cols = list(df.columns)
	# Forzar nombres correctos si los nombres no coinciden exactamente
	expected_cols = ["Producto", "Stock", "FechaRegistro", "Tipo", "NICHO"]
	if cols != expected_cols:
		if len(cols) >= 5:
			df = df.iloc[:, :5]
			df.columns = expected_cols
	print("Columnas del DataFrame antes de filtrar por NICHO:", list(df.columns))
	elements = []
	build_header(elements, title="ACTUALIZACIÓN DE PRODUCTOS CON STOCK CERO")

	elements.append(Paragraph("NOTA: El listado incluye productos que pasaron de stock 0 a disponible, así como aquellos reincorporados " \
	"por devoluciones en buen estado." \
	" ", styles['Heading4']))

	for nicho in ["FARMACIA E INSTITUCIONAL", "VETERINARIA"]:
		sub_df = df[df["NICHO"] == nicho]
		if not sub_df.empty:
			elements.append(Paragraph(f"<b>{nicho}</b>", styles['Heading3']))
			elements.append(Spacer(1, 0.2*cm))
			# Encabezados: Producto, Stock, FechaRegistro, Tipo
			data = [sub_df.columns[:4].tolist()] + sub_df.iloc[:, :4].values.tolist()
			crear_tabla_inventario(elements, data)

	doc = SimpleDocTemplate(out_file, pagesize=A4,
							leftMargin=1*cm, rightMargin=1*cm,
							topMargin=1.2*cm, bottomMargin=1*cm)
	def footer(canvas, doc):
		canvas.saveState()
		width, height = A4
		footer_text = "@Todos los derechos reservados por laboratorios alfa S.R.L. Creado por Inteligencia de Negocios"
		canvas.setFillColorRGB(0.5, 0.5, 0.5)
		canvas.rect(0, 0, width, 18, fill=1, stroke=0)
		canvas.setFillColorRGB(1, 1, 1)
		canvas.setFont("Helvetica", 9)
		canvas.drawCentredString(width/2, 6, footer_text)
		canvas.restoreState()
	doc.build(elements, onFirstPage=footer, onLaterPages=footer)
	print(f"Generado: {out_file}")


def send_inventario_report_via_graph(pdf_path, fecha=None, graph_config_path="graph_config.json"):
	"""
	Envía el PDF de inventario a notificaciones_inventario@laboratoriosalfa.com usando Graph API.
	"""
	# Cargar configuración
	with open(resource_path(graph_config_path), "r", encoding="utf-8") as f:
		graph_config = json.load(f)
	tenant_id = graph_config["tenant_id"]
	client_id = graph_config["client_id"]
	client_secret = graph_config["client_secret"]
	sender = "notificaciones@laboratoriosalfa.com"  # Remitente fijo
	to_email = "notificaciones_inventario@laboratoriosalfa.com"

	# Obtener token
	token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
	data = {
		'grant_type': 'client_credentials',
		'client_id': client_id,
		'client_secret': client_secret,
		'scope': 'https://graph.microsoft.com/.default'
	}
	r = requests.post(token_url, data=data, timeout=10)
	r.raise_for_status()
	access_token = r.json()['access_token']

	# Preparar correo
	if fecha is None:
		fecha = date.today().strftime("%d/%m/%Y")
	subject = f"Cambio de inventario ({fecha})"
	body =  """
Este reporte ha sido generado automáticamente.
Adjunto se envía los productos terminados que pasan de inventario cero a tener stock.

Sistema desarrollado por Inteligencia de Negocios - Laboratorios Alfa S.R.L.
"""

	with open(pdf_path, 'rb') as f:
		b = f.read()
	b64 = base64.b64encode(b).decode('ascii')
	attach = {
		"@odata.type": "#microsoft.graph.fileAttachment",
		"name": os.path.basename(pdf_path),
		"contentType": "application/pdf",
		"contentBytes": b64
	}

	message = {
		"message": {
			"subject": subject,
			"body": {
				"contentType": "Text",
				"content": body
			},
			"toRecipients": [
				{"emailAddress": {"address": to_email}}
			],
			"from": {"emailAddress": {"address": sender}},
			"attachments": [attach]
		}
	}

	url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
	headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
	r = requests.post(url, headers=headers, data=json.dumps(message), timeout=20)
	if r.status_code in (200, 202):
		print('Enviado via Graph:', to_email)
		return True
	else:
		print('Error Graph:', r.status_code, r.text)
		return False

if __name__ == "__main__":
	pdf_path = "INVENTARIO/Reporte_CambiosInventario.pdf"
	# Validar si hay cambios antes de enviar
	import connection

	df = connection.get_dataframeInventarioCambios()
	if df is None or df.empty:
		print("No hay cambios de inventario. No se enviará el archivo.")
	else:
		build_report_inventario(out_file=pdf_path)
		send_inventario_report_via_graph(pdf_path)
