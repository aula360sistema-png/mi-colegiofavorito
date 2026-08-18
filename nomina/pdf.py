"""Generación del recibo de pago (boleta) en PDF para nómina.

Replica el diseño de `nomina/templates/nomina/boleta_pago.html` usando
reportlab, para adjuntarlo a los correos de notificación de nómina.
"""

from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NEGRO = colors.HexColor('#111111')
INDIGO = colors.HexColor('#3730a3')
GRIS = colors.HexColor('#f3f4f6')
VERDE = colors.HexColor('#f0fdf4')
ROJO = colors.HexColor('#fef2f2')

ENCABEZADO = ParagraphStyle(
    'Encabezado',
    parent=getSampleStyleSheet()['Normal'],
    alignment=TA_CENTER,
    fontSize=15,
    leading=18,
    textColor=colors.HexColor('#312e81'),
    fontName='Helvetica-Bold',
    spaceAfter=2,
)

SUBENCABEZADO = ParagraphStyle(
    'Subencabezado',
    parent=getSampleStyleSheet()['Normal'],
    alignment=TA_CENTER,
    fontSize=9,
    leading=12,
    textColor=colors.HexColor('#4b5563'),
)

TITULO = ParagraphStyle(
    'Titulo',
    parent=getSampleStyleSheet()['Normal'],
    alignment=TA_CENTER,
    fontSize=11,
    leading=14,
    fontName='Helvetica-Bold',
    spaceBefore=6,
    spaceAfter=4,
)

CELDA = ParagraphStyle(
    'Celda',
    parent=getSampleStyleSheet()['Normal'],
    fontSize=9,
    leading=12,
    textColor=colors.HexColor('#1f2937'),
)

CELDA_DER = ParagraphStyle(
    'CeldaDer',
    parent=CELDA,
    alignment=2,
)

CELDA_NEGRA = ParagraphStyle(
    'CeldaNegra',
    parent=CELDA,
    textColor=colors.white,
    fontName='Helvetica-Bold',
)

ENCABEZADO_TABLA = ParagraphStyle(
    'EncabezadoTabla',
    parent=CELDA,
    textColor=colors.HexColor('#374151'),
    fontName='Helvetica-Bold',
)


def formatear_monto(valor):
    """Da formato 1,234.56 a un valor Decimal (como el filtro |dop)."""
    if valor is None or valor == '':
        valor = 0
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return '0.00'
    return f"{numero:,.2f}"


def _par(texto, estilo=CELDA):
    return Paragraph(escape(str(texto)), estilo)


def _tabla_totales(header, filas, total_etiqueta, total_monto, total_estilo):
    data = [
        [_par(header[0], ENCABEZADO_TABLA), _par(header[1], ENCABEZADO_TABLA)],
    ]
    for etiqueta, monto in filas:
        data.append([_par(etiqueta), _par('RD$ ' + formatear_monto(monto), CELDA_DER)])

    data.append([
        _par(total_etiqueta, ParagraphStyle(
            'TotalEtq', parent=CELDA, fontName='Helvetica-Bold')),
        _par('RD$ ' + formatear_monto(total_monto), ParagraphStyle(
            'TotalMto', parent=CELDA_DER, fontName='Helvetica-Bold')),
    ])

    tabla = Table(data, colWidths=[11.5 * cm, 5 * cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GRIS),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#d1d5db')),
        ('BACKGROUND', (0, -1), (-1, -1), total_estilo),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tabla


def generar_pdf_boleta(nomina, ingresos, descuentos):
    """Devuelve el recibo de pago de una nómina como bytes de PDF."""
    periodo = nomina.periodo
    centro = periodo.centro
    usuario = nomina.usuario

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        title=f"Recibo de pago {usuario.get_full_name() or usuario.username} - {periodo.descripcion}",
        author=centro.nombre,
    )

    def _pie(canvas, _doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6b7280'))
        canvas.drawCentredString(
            A4[0] / 2, 0.8 * cm,
            f"{centro.nombre} · Código MINERD {centro.codigo_minerd}",
        )
        canvas.restoreState()

    estilo = []

    estilo.append(_par(centro.nombre, ENCABEZADO))
    estilo.append(_par(
        f"Código MINERD: {centro.codigo_minerd}",
        SUBENCABEZADO,
    ))
    estilo.append(Spacer(1, 0.3 * cm))
    estilo.append(HRFlowable(
        width='100%', thickness=1, color=NEGRO,
    ))
    estilo.append(Spacer(1, 0.25 * cm))
    estilo.append(_par('BOLETA DE PAGO DE NÓMINA', TITULO))
    estilo.append(Spacer(1, 0.25 * cm))

    cargo = nomina.configuracion.cargo.nombre if nomina.configuracion.cargo else '—'

    info = Table(
        [
            [_par('Empleado:', ParagraphStyle(
                'Lbl', parent=CELDA, fontName='Helvetica-Bold')),
             _par(usuario.get_full_name() or usuario.username)],
            [_par('Cargo:', ParagraphStyle(
                'Lbl2', parent=CELDA, fontName='Helvetica-Bold')),
             _par(cargo)],
            [_par('Período:', ParagraphStyle(
                'Lbl3', parent=CELDA, fontName='Helvetica-Bold')),
             _par(periodo.descripcion)],
            [_par('Fecha de pago:', ParagraphStyle(
                'Lbl4', parent=CELDA, fontName='Helvetica-Bold')),
             _par(periodo.fecha_pago.strftime('%d/%m/%Y'))],
            [_par('Estado:', ParagraphStyle(
                'Lbl5', parent=CELDA, fontName='Helvetica-Bold')),
             _par(nomina.get_estado_display())],
            [_par('Boleta No.:', ParagraphStyle(
                'Lbl6', parent=CELDA, fontName='Helvetica-Bold')),
             _par(nomina.id)],
        ],
        colWidths=[4.5 * cm, 12 * cm],
    )
    info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    estilo.append(info)
    estilo.append(Spacer(1, 0.35 * cm))

    filas_ingresos = [
        (ing.descripcion, ing.monto) for ing in ingresos
    ]
    estilo.append(_tabla_totales(
        ('Ingresos', 'Monto'),
        filas_ingresos,
        'Total devengado',
        nomina.total_ingresos,
        VERDE,
    ))
    estilo.append(Spacer(1, 0.3 * cm))

    filas_descuentos = [
        (desc.descripcion, desc.monto) for desc in descuentos
    ]
    estilo.append(_tabla_totales(
        ('Descuentos', 'Monto'),
        filas_descuentos,
        'Total descuentos',
        nomina.total_descuentos,
        ROJO,
    ))
    estilo.append(Spacer(1, 0.4 * cm))

    neto = Table(
        [[_par('Neto a pagar', ParagraphStyle(
            'NetoEtq', parent=CELDA, fontSize=12, leading=15,
            fontName='Helvetica-Bold')),
          _par('RD$ ' + formatear_monto(nomina.neto_pagar), ParagraphStyle(
              'NetoMto', parent=CELDA_DER, fontSize=12, leading=15,
              fontName='Helvetica-Bold', textColor=INDIGO))]],
        colWidths=[11.5 * cm, 5 * cm],
    )
    neto.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#9ca3af')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    estilo.append(neto)
    estilo.append(Spacer(1, 1.4 * cm))

    firmas = Table(
        [
            [_par('Firma del empleado', ParagraphStyle(
                'Firma1', parent=CELDA, alignment=TA_CENTER,
                textColor=colors.HexColor('#374151'))),
             _par('Firma del encargado de nómina', ParagraphStyle(
                 'Firma2', parent=CELDA, alignment=TA_CENTER,
                 textColor=colors.HexColor('#374151')))],
        ],
        colWidths=[8.25 * cm, 8.25 * cm],
    )
    firmas.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 0.6, colors.HexColor('#9ca3af')),
        ('LINEABOVE', (1, 0), (1, 0), 0.6, colors.HexColor('#9ca3af')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    estilo.append(firmas)

    doc.build(estilo, onFirstPage=_pie, onLaterPages=_pie)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
