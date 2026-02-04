"""
Generador de PDFs para el sistema de pagos
Basado en el formato del voucher de depósito proporcionado
"""

from django.http import HttpResponse
from django.template.loader import get_template
from django.template import Context
from django.utils import timezone
from io import BytesIO
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white


def generate_deposit_pdf(deposit_order):
    """
    Genera el PDF del voucher de depósito basado en la imagen proporcionada
    """
    buffer = BytesIO()
    
    # Configurar el documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para el título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    # Estilo para texto en negrita
    bold_style = ParagraphStyle(
        'CustomBold',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    # Contenido del PDF
    story = []
    
    # Encabezado
    story.append(Paragraph(f"A-002 OF, {deposit_order.subsidiary.name.upper()}", title_style))
    story.append(Paragraph("REIMPRESION DE DEPÓSITO", subtitle_style))
    story.append(Paragraph(f"DEP-{deposit_order.deposit_number}", subtitle_style))
    story.append(Spacer(1, 12))
    
    # Información del cajero y fechas
    cajero_info = f"Cajero(a): {deposit_order.user.first_name.upper()}{deposit_order.user.last_name.upper()}"
    story.append(Paragraph(cajero_info, normal_style))
    
    fecha_original = deposit_order.created_at.strftime("%d/%m/%Y %H:%M:%S")
    story.append(Paragraph(f"Fecha: {fecha_original}", normal_style))
    
    fecha_reimpresion = timezone.now().strftime("%d/%m/%Y %H:%M:%S")
    story.append(Paragraph(f"Reimpresion: Fecha: {fecha_reimpresion}", normal_style))
    
    story.append(Paragraph("Usuario: agente", normal_style))
    story.append(Paragraph(f"Ent. Destino: {deposit_order.bank or 'BCP (BANCO DE CREDITO)'}", normal_style))
    story.append(Paragraph(f"Suc. Origen: N-017 FILIAL {deposit_order.subsidiary.name.upper()}", normal_style))
    story.append(Spacer(1, 12))
    
    # Información del depósito
    story.append(Paragraph("Depositante: " + deposit_order.depositor_name.upper(), bold_style))
    if deposit_order.depositor_document:
        story.append(Paragraph(f"Documento: {deposit_order.depositor_document}", normal_style))
    
    nacionalidad = deposit_order.get_nationality_display() if deposit_order.nationality else ""
    story.append(Paragraph(f"Nacionalidad: {nacionalidad}", normal_style))
    
    story.append(Paragraph("Titular: " + deposit_order.account_holder.upper(), bold_style))
    story.append(Paragraph(f"Nro. de Cuenta: {deposit_order.account_number}", normal_style))
    story.append(Paragraph(f"Observación: {deposit_order.observation}", normal_style))
    story.append(Paragraph(f"Suc. Encargada: A-002 OF. {deposit_order.subsidiary.name.upper()}", normal_style))
    story.append(Spacer(1, 12))
    
    # Monto
    story.append(Paragraph(f"Monto_: {deposit_order.amount}", bold_style))
    story.append(Paragraph(f"SON: {deposit_order.amount_in_words}", bold_style))
    story.append(Spacer(1, 20))
    
    # Pie de página
    story.append(Paragraph("ENTREGADO RECIBIDO", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("***OF. PRINCIPAL: 997-376-015***", normal_style))
    story.append(Paragraph("www.peru-lider.com", normal_style))
    
    # Construir el PDF
    doc.build(story)
    
    # Obtener el contenido del buffer
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content


