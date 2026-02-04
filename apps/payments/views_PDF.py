import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, Image, Flowable, HRFlowable, \
    PageTemplate, Frame, BaseDocTemplate
from reportlab.platypus import Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
import decimal
import io
from django.conf import settings

from .number_to_letters import numero_a_moneda
from ..users.models import CustomUser

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=14))
styles.add(ParagraphStyle(name='Center-Blue', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=14,
                          textColor=colors.cornflowerblue))
styles.add(ParagraphStyle(name='Center_White', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=14,
                          textColor=colors.white))
styles.add(ParagraphStyle(name='Left_Square', alignment=TA_LEFT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Left_Newgot', alignment=TA_LEFT, leading=12, fontName='Newgot', fontSize=10))
styles.add(ParagraphStyle(name='Center_Newgot', alignment=TA_CENTER, leading=12, fontName='Newgot', fontSize=10))
styles.add(
    ParagraphStyle(name='Justify_Newgot_title', alignment=TA_JUSTIFY, leading=14, fontName='Newgot', fontSize=14))
styles.add(
    ParagraphStyle(name='Justify_Newgot_text', alignment=TA_JUSTIFY, leading=10, fontName='Newgot', fontSize=12))
styles.add(
    ParagraphStyle(name='Justify_Newgot_text_red', alignment=TA_CENTER, leading=14, fontName='Newgot', fontSize=14,
                   textColor=colors.darkred))
styles.add(ParagraphStyle(name='Center_Newgot_title', alignment=TA_CENTER, leading=15, fontName='Newgot', fontSize=15))
styles.add(ParagraphStyle(name='Center_Newgot_title_blue', alignment=TA_CENTER, leading=15, fontName='Newgot',
                          fontSize=15, textColor=colors.dodgerblue))
styles.add(
    ParagraphStyle(name='Center_Newgot_title_f12', alignment=TA_CENTER, leading=15, fontName='Newgot', fontSize=12))
styles.add(
    ParagraphStyle(name='Center_Newgot_sub_title', alignment=TA_CENTER, leading=10, fontName='Newgot', fontSize=10,
                   textColor=colors.lightslategrey))
styles.add(
    ParagraphStyle(name='Center_Newgot_sub_title_2', alignment=TA_CENTER, leading=10, fontName='Newgot', fontSize=8))
styles.add(
    ParagraphStyle(name='Center_Newgot_sub_title_3', alignment=TA_CENTER, leading=10, fontName='Newgot', fontSize=10))
styles.add(ParagraphStyle(name='Justify_Square', alignment=TA_JUSTIFY, leading=12, fontName='Square', fontSize=11))
styles.add(ParagraphStyle(name='Justify_Square_Blue', alignment=TA_JUSTIFY, leading=10, fontName='Square', fontSize=10,
                          textColor=colors.dodgerblue))
styles.add(
    ParagraphStyle(name='Justify_Square_bold', alignment=TA_JUSTIFY, leading=10, fontName='Square-Bold', fontSize=10))

reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))
pdfmetrics.registerFont(TTFont('Square-Bold', 'sqr721bc.ttf'))
pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

logo = "static/assets/img/logo_disa_nobg.png"

ml = 0.25 * inch
mr = 0.25 * inch
ms = 0.25 * inch
mi = 0.25 * inch


def generate_deposit_pdf(deposit_id):
    try:
        from .models import DepositOrder
        from ..hrm.models import Subsidiary
        from ..users.models import CustomUser
        
        # Obtener el depósito
        deposit = DepositOrder.objects.select_related(
            'depositor_client', 'cashier', 'origin_subsidiary', 
            'subsidiary_encargada', 'destination_entity', 'confirmed_by'
        ).get(id=deposit_id)
        
        # Crear el buffer para el PDF
        buffer = io.BytesIO()
        
        # Configurar el documento con el ancho especificado para tickets
        _wt = 2.93 * inch - 4 * 0.05 * inch
        
        # Tamaño del documento (formato ticket)
        pz_thermal = (2.93 * inch, 11.6 * inch)

        ml = 0.05 * inch
        mr = 0.05 * inch
        ms = 0.039 * inch
        mi = 0.039 * inch

        doc = SimpleDocTemplate(
            buffer,
            pagesize=pz_thermal,
            rightMargin=mr,
            leftMargin=ml,
            topMargin=ms,
            bottomMargin=mi,
            title='IMPRESIÓN DE TRANSACCIÓN'
        )
        
        # Lista de elementos del PDF
        elements = []
        
        # Agregar logo centrado en la parte superior
        logo_image = Image(logo)
        logo_image.drawHeight = 1.1 * inch
        logo_image.drawWidth = 1.1 * inch
        elements.append(Spacer(1, -10))
        # Crear tabla para centrar la imagen
        logo_table = Table([[logo_image]], colWidths=[_wt])
        logo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(logo_table)
        elements.append(Spacer(1, -5))
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='DepositHeader',
            alignment=TA_CENTER,
            leading=12,
            fontName='Helvetica-Bold',
            fontSize=12
        ))
        styles.add(ParagraphStyle(
            name='DepositTitle',
            alignment=TA_CENTER,
            leading=7,
            fontName='Helvetica-Bold',
            fontSize=8
        ))
        styles.add(ParagraphStyle(
            name='DepositSubtitle',
            alignment=TA_CENTER,
            leading=7,
            fontName='Helvetica',
            fontSize=6
        ))
        styles.add(ParagraphStyle(
            name='DepositText',
            alignment=TA_LEFT,
            leading=9,
            fontName='Helvetica',
            fontSize=8
        ))
        styles.add(ParagraphStyle(
            name='DepositTextBold',
            alignment=TA_LEFT,
            leading=8,
            fontName='Helvetica-Bold',
            fontSize=8
        ))
        styles.add(ParagraphStyle(
            name='DepositTextRight',
            alignment=TA_RIGHT,
            leading=8,
            fontName='Helvetica',
            fontSize=8
        ))
        styles.add(ParagraphStyle(
            name='DepositTextRightBold',
            alignment=TA_RIGHT,
            leading=8,
            fontName='Helvetica-Bold',
            fontSize=8
        ))
        styles.add(ParagraphStyle(
            name='DepositSeparator',
            alignment=TA_LEFT,
            leading=6,
            fontName='Helvetica',
            fontSize=6,
            textColor=colors.grey
        ))
        
        # Encabezado del documento
        # Sucursal encargada
        # if deposit.subsidiary_encargada:
        #     elements.append(Paragraph(deposit.subsidiary_encargada.name.upper(), styles['DepositHeader']))
        # elements.append(Spacer(2, 2))
        
        # Título del documento
        elements.append(Paragraph(f"{deposit.subsidiary.serial} - {deposit.subsidiary.name}", styles['DepositTitle']))
        elements.append(Spacer(2, 2))
        elements.append(Paragraph(f"IMPRESION DE {deposit.get_type_deposit_display()}", styles['DepositTitle']))
        elements.append(Spacer(2, 2))

        # Número del depósito

        elements.append(Paragraph(deposit.deposit_number, styles['DepositHeader']))

        elements.append(Spacer(3, 3))
        elements.append(DashedLine(width=500, dash_pattern=[3, 3]))
        elements.append(Spacer(3, 3))
        
        # Crear tabla con información en dos columnas
        info_data = []
        
        # Información del cajero
        if deposit.cashier:
            info_data.append([
                Paragraph("Cajero(a):", styles['DepositText']),
                Paragraph(deposit.cashier.first_name.upper(), styles['DepositText'])
            ])

        # Fecha de reimpresión (fecha actual)
        from datetime import datetime
        current_time = datetime.now()
        info_data.append([
            Paragraph("Fecha Reimpresion:", styles['DepositText']),
            Paragraph(current_time.strftime('%d/%m/%Y %H:%M:%S'), styles['DepositText'])
        ])

        # Fecha original (fecha de creación del depósito)
        if deposit.creation_date:
            info_data.append([
                Paragraph("Fecha:", styles['DepositText']),
                Paragraph(deposit.creation_date.strftime('%d/%m/%Y %H:%M:%S'), styles['DepositText'])
            ])

        # Sucursal origen
        if deposit.origin_subsidiary:
            info_data.append([
                Paragraph("Suc. Origen:", styles['DepositText']),
                Paragraph(deposit.origin_subsidiary.name.upper(), styles['DepositText'])
            ])

        # Usuario
        if deposit.origin_subsidiary:
            info_data.append([
                Paragraph("Usuario:", styles['DepositText']),
                Paragraph(deposit.cashier.first_name.upper(), styles['DepositText'])
            ])
        
        # Entidad destino
        if deposit.destination_entity:
            info_data.append([
                Paragraph("Ent. Destino:", styles['DepositText']),
                Paragraph(deposit.destination_entity.name.upper(), styles['DepositText'])
            ])
        
        # DNI del titular
        if deposit.depositor_client and deposit.depositor_client.number:
            info_data.append([
                Paragraph("DNI Titular:", styles['DepositText']),
                Paragraph(deposit.depositor_client.number, styles['DepositText'])
            ])
        
        # Nombre del titular
        if deposit.depositor_client:
            info_data.append([
                Paragraph("Titular:", styles['DepositText']),
                Paragraph(deposit.depositor_client.full_name.upper(), styles['DepositText'])
            ])
        
        # Teléfono del titular
        if deposit.depositor_client and deposit.depositor_client.phone1:
            info_data.append([
                Paragraph("Teléfono:", styles['DepositText']),
                Paragraph(f"CEL - {deposit.depositor_client.phone1}", styles['DepositText'])
            ])
        
        # Código de letra (usar el número del cliente)
        if deposit.depositor_client and deposit.depositor_client.number:
            info_data.append([
                Paragraph("Código Letra:", styles['DepositText']),
                Paragraph(deposit.account_number, styles['DepositText'])
            ])

        # Recepetor
        if deposit.depositor_client and deposit.depositor_client.number:
            info_data.append([
                Paragraph("Titular Receptor:", styles['DepositText']),
                Paragraph(deposit.account_holder.upper(), styles['DepositText'])
            ])

        # Observación
        if deposit.observation:
            info_data.append([
                Paragraph("Observación:", styles['DepositText']),
                Paragraph(deposit.observation.upper(), styles['DepositText'])
            ])
        
        # Sucursal encargada
        if deposit.subsidiary_encargada:
            info_data.append([
                Paragraph("Suc. Encargada:", styles['DepositText']),
                Paragraph(deposit.subsidiary_encargada.name.upper(), styles['DepositText'])
            ])

        # Crear tabla con dos columnas
        info_table = Table(info_data, colWidths=[_wt * 0.4, _wt * 0.6])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),   # Primera columna (etiquetas) a la izquierda
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),   # Segunda columna (valores) a la izquierda
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Sin negrita
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8),
            ('TOPPADDING', (0, 0), (-1, -1), 1.8),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        elements.append(info_table)
        elements.append(Spacer(2, 2))

        # Línea separadora
        elements.append(DashedLine(width=500, dash_pattern=[3, 3]))
        elements.append(Spacer(2, 2))

        # Monto en tabla separada
        monto_data = [[
            Paragraph("Monto:", styles['DepositText']),
            Paragraph(str(decimal.Decimal(deposit.amount)), styles['DepositTextBold'])
        ]]
        monto_table = Table(monto_data, colWidths=[_wt * 0.4, _wt * 0.6])
        monto_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),   # Primera columna (etiquetas) a la izquierda
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),   # Segunda columna (valores) a la izquierda
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Sin negrita
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(monto_table)
        elements.append(Spacer(10, 10))

        
        # Monto en letras
        if deposit.amount_in_words:
            elements.append(Paragraph(f"SON: {numero_a_moneda(deposit.amount)}", styles['DepositText']))
        elements.append(Spacer(3, 3))
        
        # Líneas separadoras
        # elements.append(DashedLine(width=500, dash_pattern=[3, 3]))
        elements.append(Spacer(0, 50))
        elements.append(DashedLine(width=500, dash_pattern=[3, 3]))

        # Pie de página en dos columnas
        pie_data = [
            [Paragraph("ENTREGADO", styles['DepositText']), Paragraph("RECIBIDO", styles['DepositTextRight'])]
        ]
        pie_table = Table(pie_data, colWidths=[_wt * 0.5, _wt * 0.5])
        pie_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),   # Primera columna (ENTREGADO) a la izquierda
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Segunda columna (RECIBIDO) a la derecha
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(pie_table)
        elements.append(DashedLine(width=500, dash_pattern=[3, 3]))
        elements.append(Spacer(0, 2))
        
        # Información de contacto
        if deposit.subsidiary_encargada and deposit.subsidiary_encargada.phone:
            elements.append(Paragraph(f"***OF_PRINCIPAL: _{deposit.subsidiary_encargada.phone}*** www.peru-lider.com", styles['DepositSubtitle']))
        else:
            elements.append(Paragraph("SUCURSAL PRINCIPAL", styles['DepositSubtitle']))

        # Construir el PDF
        doc.build(elements)
        
        # Obtener el valor del buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        return pdf
        
    except Exception as e:
        print(f"Error generando PDF: {str(e)}")
        return None


def download_deposit_pdf(request, deposit_id):
    """
    Vista para descargar el PDF del depósito
    """
    try:
        from .models import DepositOrder
        from django.http import HttpResponse
        
        # Verificar que el depósito existe
        deposit = DepositOrder.objects.get(id=deposit_id)
        
        # Generar el PDF
        pdf_content = generate_deposit_pdf(deposit_id)
        
        if pdf_content:
            # Crear respuesta HTTP con el PDF
            response = HttpResponse(pdf_content, content_type='application/pdf')
            # Forzar descarga automática del PDF
            # response['Content-Disposition'] = f'attachment; filename="Deposito_{deposit.deposit_number}.pdf"'
            return response
        else:
            return HttpResponse("Error generando el PDF", status=500)
            
    except DepositOrder.DoesNotExist:
        return HttpResponse("Depósito no encontrado", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


class DashedLine(Flowable):
    from reportlab.lib.colors import grey, black, darkgrey
    def __init__(self, width, dash_pattern=[3, 3], thickness=1, color=black, spaceBefore=6, spaceAfter=4):
        Flowable.__init__(self)
        self.width = width
        self.dash_pattern = dash_pattern
        self.thickness = thickness
        self.color = color
        self.spaceBefore = spaceBefore
        self.spaceAfter = spaceAfter

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.setDash(self.dash_pattern)
        self.canv.line(0, 0, self.width, 0)