from datetime import timedelta


def generar_turnos_de_acuerdo(acuerdo):
    """
    Genera los Turno concretos de un AcuerdoServicio: uno por cada fecha
    entre fecha_inicio y fecha_fin que coincida con dias_semana. Idempotente.

    Si el turno de esa fecha ya existe pero todavia no se trabajo (sin
    horas_reales), se actualiza para reflejar cambios en el acuerdo (ej. se
    edito el empleado asignado mientras el contrato seguia en borrador). Si
    ya tiene horas_reales, se deja intacto.

    Devuelve (creados, actualizados, ya_al_dia), o None si el acuerdo no
    tiene horario o dias_semana definidos.
    """
    from empleados.models import Turno

    from .models import AcuerdoServicio

    if not acuerdo.hora_inicio or not acuerdo.hora_fin or not acuerdo.dias_semana:
        return None

    creados = 0
    actualizados = 0
    ya_al_dia = 0
    fecha = acuerdo.fecha_inicio
    fecha_fin = acuerdo.fecha_fin
    while fecha <= fecha_fin:
        codigo_dia = AcuerdoServicio.DIAS_POR_WEEKDAY[fecha.weekday()]
        if codigo_dia in acuerdo.dias_semana:
            turno, fue_creado = Turno.objects.get_or_create(
                acuerdo_servicio=acuerdo,
                fecha=fecha,
                defaults={
                    'empleado': acuerdo.profesional,
                    'cliente': acuerdo.contrato.cliente,
                    'hora_inicio': acuerdo.hora_inicio,
                    'hora_fin': acuerdo.hora_fin,
                },
            )
            if fue_creado:
                creados += 1
            elif turno.horas_reales is None:
                cambios = (
                    turno.empleado_id != acuerdo.profesional_id
                    or turno.hora_inicio != acuerdo.hora_inicio
                    or turno.hora_fin != acuerdo.hora_fin
                )
                if cambios:
                    turno.empleado = acuerdo.profesional
                    turno.hora_inicio = acuerdo.hora_inicio
                    turno.hora_fin = acuerdo.hora_fin
                    turno.save()
                    actualizados += 1
                else:
                    ya_al_dia += 1
            else:
                ya_al_dia += 1
        fecha += timedelta(days=1)

    return creados, actualizados, ya_al_dia


def eliminar_turnos_de_acuerdo(acuerdo, desde=None, hasta=None):
    """
    Elimina los Turno de un AcuerdoServicio que todavia no se trabajaron
    (horas_reales vacio), opcionalmente acotado a un rango de fechas. Los
    turnos con horas_reales registradas se protegen: nunca se borran, quedan
    como historial real.
    """
    from empleados.models import Turno

    qs = Turno.objects.filter(acuerdo_servicio=acuerdo, horas_reales__isnull=True)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    qs.delete()


def eliminar_turnos_de_contrato(contrato, desde=None, hasta=None):
    """Aplica eliminar_turnos_de_acuerdo a todos los acuerdos del contrato."""
    for acuerdo in contrato.acuerdos.all():
        eliminar_turnos_de_acuerdo(acuerdo, desde=desde, hasta=hasta)


def podar_turnos_de_acuerdo(acuerdo):
    """
    Complemento de generar_turnos_de_acuerdo: borra los Turno de un
    AcuerdoServicio que ya NO corresponden a su horario actual (fecha fuera
    de fecha_inicio..fecha_fin, o un dia de la semana que ya no esta en
    dias_semana). Caso tipico: se edita un contrato en borrador para achicar
    el horario de un servicio antes de activarlo. Llamar siempre despues de
    generar_turnos_de_acuerdo. Misma proteccion: un turno con horas_reales
    ya registradas nunca se borra.
    """
    from empleados.models import Turno

    from .models import AcuerdoServicio

    turnos = Turno.objects.filter(acuerdo_servicio=acuerdo, horas_reales__isnull=True)
    for turno in turnos:
        fuera_de_rango = turno.fecha < acuerdo.fecha_inicio or turno.fecha > acuerdo.fecha_fin
        dia_ya_no_aplica = AcuerdoServicio.DIAS_POR_WEEKDAY[turno.fecha.weekday()] not in acuerdo.dias_semana
        if fuera_de_rango or dia_ya_no_aplica:
            turno.delete()


def generar_turnos_de_contrato(contrato):
    """
    Corre generar_turnos_de_acuerdo sobre todos los AcuerdoServicio activos
    del contrato. Devuelve un resumen con creados, actualizados, ya_al_dia y
    la lista de acuerdos que no tenian horario/dias_semana definidos.
    """
    creados = 0
    actualizados = 0
    ya_al_dia = 0
    sin_horario = []

    for acuerdo in contrato.acuerdos.filter(activo=True):
        resultado = generar_turnos_de_acuerdo(acuerdo)
        if resultado is None:
            sin_horario.append(str(acuerdo))
            continue
        c, a, y = resultado
        creados += c
        actualizados += a
        ya_al_dia += y

    return {
        'creados': creados,
        'actualizados': actualizados,
        'ya_al_dia': ya_al_dia,
        'acuerdos_sin_horario': sin_horario,
    }


def finalizar_contratos_vencidos():
    """
    Pasa a 'finalizado' los contratos en estado 'activo' cuya fecha_fin (la
    mas tardia entre sus AcuerdoServicio) ya paso. No hay scheduler/cron en
    este proyecto: esto se corre cada vez que se consulta la lista o el
    detalle de un Contrato (ver ContratoViewSet.get_queryset).
    """
    from django.db.models import Max
    from django.utils import timezone

    from .models import Contrato

    hoy = timezone.now().date()
    ids_vencidos = list(
        Contrato.objects.filter(estado='activo')
        .annotate(ultima_fecha_fin=Max('acuerdos__fecha_fin'))
        .filter(ultima_fecha_fin__lt=hoy)
        .values_list('id', flat=True)
    )
    # Se resuelve en dos pasos (no .update() encadenado al annotate) porque
    # un UPDATE con GROUP BY/HAVING no es valido en SQL.
    if ids_vencidos:
        Contrato.objects.filter(id__in=ids_vencidos).update(estado='finalizado')


def eliminar_contratos_borrador_vencidos():
    """
    Un contrato 'borrador' que se dejo pendiente y llego a su fecha_inicio
    sin haberse activado se elimina automaticamente.

    Solo aplica a contratos creados POR ADELANTADO (creado_en es anterior o
    igual a su fecha_inicio) a los que se les dejo pasar la fecha sin
    activar. Una carga retroactiva (documentar hoy un servicio que ya
    empezo) nunca entra en esta limpieza, porque nunca tuvo una ventana
    previa en la que alguien pudiera haberla activado a tiempo.
    """
    from django.db.models import F, Min
    from django.db.models.functions import TruncDate
    from django.utils import timezone

    from .models import Contrato

    hoy = timezone.now().date()
    ids_vencidos = list(
        Contrato.objects.filter(estado='borrador')
        .annotate(
            primera_fecha_inicio=Min('acuerdos__fecha_inicio'),
            creado_fecha=TruncDate('creado_en'),
        )
        .filter(
            primera_fecha_inicio__lt=hoy,
            creado_fecha__lte=F('primera_fecha_inicio'),
        )
        .values_list('id', flat=True)
    )
    for contrato in Contrato.objects.filter(id__in=ids_vencidos):
        eliminar_turnos_de_contrato(contrato)
        contrato.delete()
