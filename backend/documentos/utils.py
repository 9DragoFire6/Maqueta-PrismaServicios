import re
import unicodedata
from html import escape as esc
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


def sanitizar_nombre(texto):
    """Normaliza un texto para usarlo en un nombre de archivo: sin acentos
    ni caracteres especiales, espacios como guion bajo."""
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'[^A-Za-z0-9]+', '_', texto).strip('_')
    return texto or 'contrato'


def nombre_archivo_contrato(contrato, firmado=False):
    """Nombre de archivo estandar para el PDF de un contrato, para poder
    identificar y ordenar los contratos por su nombre de archivo. Se usa
    tanto al descargar el borrador (plantilla generada) como al guardar la
    version firmada -- en ambos casos se ignora cualquier nombre que traiga
    el archivo original.

    Formato: DDMMAAAA_C<id>_NombreContacto[_firmado].pdf
    La fecha es la de inicio del contrato (Contrato.fecha_inicio), no la de
    creacion en el sistema. El ID del contrato va siempre incluido para que
    el nombre sea unico aun si el mismo cliente tiene mas de un contrato con
    la misma fecha de inicio.
    """
    identificador = sanitizar_nombre(contrato.cliente.nombre_contacto)
    fecha_ref = contrato.fecha_inicio or contrato.creado_en.date()
    fecha = fecha_ref.strftime('%d%m%Y')
    base = f"{fecha}_C{contrato.id}_{identificador}"
    if firmado:
        base += "_firmado"
    return f"{base}.pdf"


DIAS_LABEL = {
    'lun': 'Monday', 'mar': 'Tuesday', 'mie': 'Wednesday', 'jue': 'Thursday',
    'vie': 'Friday', 'sab': 'Saturday', 'dom': 'Sunday',
}

_styles = getSampleStyleSheet()
TITULO_STYLE = ParagraphStyle('TituloContrato', parent=_styles['Title'], fontSize=15, spaceAfter=16)
HEADING_STYLE = ParagraphStyle('SeccionContrato', parent=_styles['Heading3'], fontSize=11, spaceBefore=12, spaceAfter=5)
BODY_STYLE = ParagraphStyle('CuerpoContrato', parent=_styles['Normal'], fontSize=9.5, leading=13, spaceAfter=4)
LABEL_STYLE = ParagraphStyle('CampoContrato', parent=_styles['Normal'], fontSize=9.5, leading=13, spaceAfter=2)

# Clausulas por defecto del contrato (secciones 2 a 12), en Markdown -- ver
# documentos/models.py:PlantillaClausulasContrato y obtener_plantilla_activa()
# mas abajo. Generalizadas a un rubro de ejemplo (servicios de limpieza y
# mantenimiento a domicilio, ver docs/DATOS_FICTICIOS.md en la raiz del
# repo) -- sin nombre de empresa real ni jurisdiccion real. El titulo del
# PDF usa settings.EMPRESA_NOMBRE (ver _titulo_contrato) y no depende de los
# servicios contratados. Esta constante es el respaldo que usa
# obtener_plantilla_activa() si la fila de la plantilla no existiera todavia
# -- para que generar un PDF nunca falle por falta de plantilla.
PLANTILLA_CLAUSULAS_DEFECTO = """## 2. PRIMARY RESPONSIBILITIES

2.1. Provide professional services in accordance with the service(s) specified in this Agreement.

2.2. Perform duties consistent with the assigned service, including:
- Carrying out the contracted tasks with care and professionalism
- Using appropriate equipment and supplies, provided by the Company or the Client as agreed
- Following any specific instructions provided by the Client for the property or premises
- Reporting any incident, damage, or issue observed during the service
- Keeping a record of hours worked and tasks completed

2.3. Maintain an orderly and safe environment while performing the service, including proper handling of any equipment or supplies used.

2.4. Provide practical guidance to the Client regarding the scope of the contracted service when requested.

2.5. Maintain clear and continuous communication with the Client regarding the progress of the service and any relevant observations.

2.6. The Specialist does not provide services outside the scope defined in this Agreement but will promptly inform the Client of any additional need observed.

## 3. COMMUNICATION & AVAILABILITY

3.1. Non-urgent questions, guidance, or follow-up discussions should take place during the scheduled service hours to ensure the Specialist's rest and professional boundaries.

3.2. Communication outside scheduled service hours should be limited to urgent matters related to the service. Brief clarifications of up to fifteen (15) minutes may be provided when necessary.

3.3. Any consultation, phone call, or guidance exceeding fifteen (15) minutes outside scheduled service hours shall be considered additional billable time and charged at the agreed hourly rate.

## 4. SCHEDULE & FLEXIBILITY

4.1. The specific weekly schedule (number of shifts and hours per shift) will be defined in the Service Details section of this Agreement.

4.2. Minor schedule adjustments may be agreed directly between the Client and the Specialist, subject to mutual consent and the Specialist's availability, and provided that such adjustments do not alter the overall agreed weekly structure without Company approval.

4.3. Any requested schedule changes should ideally be communicated at least one (1) week in advance to allow proper planning.

4.4. Cancellation of a scheduled shift with less than forty-eight (48) hours' notice, and without confirmed rescheduling, shall result in the scheduled hours remaining payable.

4.5. In cases of unforeseen emergencies affecting either party, both parties agree to communicate in good faith to determine a reasonable solution.

4.6. If both parties mutually agree to reschedule a shift within the same service period, no additional charge will apply.

## 5. SERVICE INTERRUPTIONS

5.1. Specialist Availability
- If the assigned Specialist is unable to provide the service, the Company must be notified as soon as possible.
- The Company will make reasonable efforts to assign a replacement of similar qualification, subject to availability.
- If no replacement is available, the corresponding scheduled shift will not be billed.

5.2. Access & Conditions
- The Client must inform the Company in advance of any condition on-site that may affect the safe provision of the service.
- In cases where the working environment may pose a risk, the Company reserves the right to reschedule the service.
- Standard cancellation terms will apply where applicable.

## 6. PAYMENT TERMS

6.1. The agreed hourly rate(s) for each contracted service are specified in the Service Details section of this Agreement.

6.2. Payment for scheduled and confirmed services shall be made weekly by the Client to the Company.

6.3. Weekly payment must be completed within 48 hours of the end of each service week.

6.4. The Company will issue the corresponding invoice for all services provided during that period.

6.5. Failure to complete weekly payment may result in temporary suspension of services until the outstanding balance is settled.

## 7. TERMINATION & MINIMUM COMMITMENT

7.1. Each contracted service is subject to a minimum commitment of four (4) consecutive weeks.

7.2. After the initial commitment period, the Client or the Company may terminate the service with fourteen (14) days written notice.

7.3. If termination occurs before the minimum commitment period ends, the remaining scheduled hours within that period will be payable.

## 8. CANCELLATION PRIOR TO SERVICE COMMENCEMENT

8.1. Once this Agreement is signed, the scheduled service period is considered exclusively reserved for the Client.

8.2. In the event of cancellation prior to the agreed start date, the following terms shall apply:
- Cancellation with more than four (4) weeks' written notice: no charge.
- Cancellation with three (3) weeks' written notice: fifty percent (50%) of the agreed four-week minimum commitment shall be payable.
- Cancellation with two (2) weeks' written notice or less: one hundred percent (100%) of the agreed four-week minimum commitment shall be payable.

## 9. NON-COMPLIANCE

9.1. In the event that either the Client or the Company fails to comply with the material terms of this Agreement, the non-complying party may be held liable for any direct financial loss resulting from such breach.

9.2. Material terms include, but are not limited to:
- Agreed payment obligations
- Scheduled service commitments
- Minimum commitment period
- Conditions affecting the safe provision of services

9.3. Any unresolved material breach may result in termination of this Agreement and, where applicable, payment of outstanding amounts due under the terms herein.

## 10. BINDING NATURE

10.1. By signing this Agreement, all parties acknowledge that it represents a legally binding commitment.

10.2. Any material modification to the agreed terms must be made in writing and mutually accepted.

10.3. All parties agree to act in good faith in the execution of this Agreement.

## 11. DISPUTE RESOLUTION

11.1. Any dispute arising from this Agreement shall first be addressed through good faith negotiation.

11.2. If unresolved, the parties agree to seek mediation prior to initiating formal legal proceedings.

## 12. GOVERNING LAW

This Agreement shall be governed by and interpreted in accordance with the laws applicable at the location where the services are provided, as agreed by both parties."""


def obtener_plantilla_activa():
    """
    Devuelve la fila (unica) de PlantillaClausulasContrato, creandola con el
    contenido por defecto si todavia no existe -- asi generar un PDF nunca
    falla por falta de plantilla.
    """
    from documentos.models import PlantillaClausulasContrato
    plantilla = PlantillaClausulasContrato.objects.first()
    if plantilla is None:
        plantilla = PlantillaClausulasContrato.objects.create(contenido=PLANTILLA_CLAUSULAS_DEFECTO)
    return plantilla


def _titulo_contrato(acuerdos):
    """
    Titulo fijo del PDF, independiente de los servicios contratados -- usa
    el nombre configurado en settings.EMPRESA_NOMBRE. Sigue recibiendo
    `acuerdos` para no tener que tocar el call site, aunque no lo use.
    """
    return f"{esc(settings.EMPRESA_NOMBRE)} Agreement"


def _md_inline(texto):
    """
    Escapa el texto y recien despues aplica el unico formato inline que
    soporta la plantilla: '**negrita**' se convierte en la etiqueta de
    negrita que ya entiende Paragraph. El orden importa: escapar primero
    evita que esa etiqueta nueva termine escapada de vuelta.
    """
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', esc(texto))


def _clausulas_flowables():
    """
    Convierte el Markdown de PlantillaClausulasContrato a los mismos
    flowables que arma el resto de generar_pdf_contrato. Formato soportado,
    deliberadamente minimo: '## ' para el titulo de una seccion, lineas
    sueltas como parrafo, y lineas consecutivas que empiezan con '- ' como
    una lista con vinetas.
    """
    flow = []
    lineas_bullet = []

    def cerrar_bullets():
        if lineas_bullet:
            flow.append(ListFlowable(
                [ListItem(Paragraph(_md_inline(l), BODY_STYLE)) for l in lineas_bullet],
                bulletType='bullet', leftIndent=18,
            ))
            lineas_bullet.clear()

    contenido = obtener_plantilla_activa().contenido
    for linea in contenido.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith('## '):
            cerrar_bullets()
            flow.append(Paragraph(_md_inline(linea[3:]), HEADING_STYLE))
        elif linea.startswith('- '):
            lineas_bullet.append(linea[2:])
        else:
            cerrar_bullets()
            flow.append(Paragraph(_md_inline(linea), BODY_STYLE))
    cerrar_bullets()
    return flow


def generar_pdf_contrato(contrato):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    acuerdos = list(contrato.acuerdos.all().order_by('fecha_inicio'))
    cliente = contrato.cliente

    story = [Paragraph(_titulo_contrato(acuerdos), TITULO_STYLE)]

    story.append(Paragraph("1. SERVICE DETAILS", HEADING_STYLE))
    if not acuerdos:
        story.append(Paragraph("(This contract has no services added yet)", BODY_STYLE))
    for acuerdo in acuerdos:
        dias = ", ".join(DIAS_LABEL.get(d, d) for d in acuerdo.dias_semana)
        if acuerdo.hora_inicio and acuerdo.hora_fin:
            horario = f"{acuerdo.hora_inicio.strftime('%H:%M')} - {acuerdo.hora_fin.strftime('%H:%M')}"
        else:
            horario = "To be defined according to the client's needs"
        story.append(Paragraph(f"<b>Service:</b> {esc(acuerdo.servicio.nombre)}", LABEL_STYLE))
        story.append(Paragraph(f"<b>Assigned Specialist:</b> {esc(str(acuerdo.profesional))}", LABEL_STYLE))
        tarifa = acuerdo.tarifa_manual if acuerdo.tarifa_manual is not None else acuerdo.servicio.tarifa_cliente
        story.append(Paragraph(f"<b>Hourly Rate:</b> {tarifa} per hour (taxes as applicable)", LABEL_STYLE))
        story.append(Paragraph(f"<b>Start Date:</b> {acuerdo.fecha_inicio.strftime('%B %d, %Y')}", LABEL_STYLE))
        story.append(Paragraph(f"<b>Schedule (days):</b> {esc(dias)}", LABEL_STYLE))
        story.append(Paragraph(f"<b>Hours of work:</b> {esc(horario)}", LABEL_STYLE))
        fecha_fin_txt = acuerdo.fecha_fin.strftime('%B %d, %Y') if acuerdo.fecha_fin else '—'
        story.append(Paragraph(f"<b>Duration (weeks):</b> {acuerdo.duracion_semanas} (until {fecha_fin_txt})", LABEL_STYLE))
        story.append(Spacer(1, 10))

    if contrato.observaciones:
        story.append(Paragraph("Additional Notes:", HEADING_STYLE))
        story.append(Paragraph(esc(contrato.observaciones), BODY_STYLE))

    story += _clausulas_flowables()

    story.append(Paragraph("CONTACT INFORMATION", HEADING_STYLE))
    story.append(Paragraph(f"<b>Company Representative:</b> {esc(settings.EMPRESA_NOMBRE)}", LABEL_STYLE))

    profesionales_vistas = {}
    for acuerdo in acuerdos:
        profesionales_vistas[acuerdo.profesional_id] = acuerdo.profesional
    for profesional in profesionales_vistas.values():
        story.append(Spacer(1, 6))
        nacimiento = profesional.fecha_nacimiento.strftime('%B %d, %Y') if profesional.fecha_nacimiento else '—'
        story.append(Paragraph(f"<b>Specialist Assigned:</b> {esc(str(profesional))}", LABEL_STYLE))
        story.append(Paragraph(f"<b>Date of Birth:</b> {nacimiento}", LABEL_STYLE))
        story.append(Paragraph(f"<b>ID/Document Number:</b> {esc(profesional.numero_documento) or '—'}", LABEL_STYLE))

    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Client Contact:</b> {esc(cliente.nombre_contacto)}", LABEL_STYLE))
    story.append(Paragraph(f"<b>Client Address:</b> {esc(cliente.direccion) or '—'}", LABEL_STYLE))
    story.append(Paragraph(f"<b>Client Contact Number:</b> {esc(cliente.telefono) or '—'}", LABEL_STYLE))
    story.append(Paragraph(f"<b>Email Contact:</b> {esc(cliente.email) or '—'}", LABEL_STYLE))

    story.append(Spacer(1, 26))
    for rol in ("Company Representative Signature:", "Client Representative Signature:"):
        story.append(Paragraph(f"{rol} &nbsp;______________________________&nbsp;&nbsp;&nbsp; Date: ____________", LABEL_STYLE))
        story.append(Spacer(1, 16))

    for profesional in profesionales_vistas.values():
        story.append(Paragraph(
            f"Specialist Signature ({esc(str(profesional))}): &nbsp;______________________________&nbsp;&nbsp;&nbsp; Date: ____________",
            LABEL_STYLE,
        ))
        story.append(Spacer(1, 16))

    doc.build(story)
    buffer.seek(0)
    return buffer
