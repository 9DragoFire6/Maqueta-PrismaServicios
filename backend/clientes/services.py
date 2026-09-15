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

    Nota: cuando exista Turno (Fase 3), hay que borrar tambien los turnos ya
    generados antes de eliminar el contrato (ver eliminar_turnos_de_contrato
    en el original) -- por ahora el contrato no tiene nada mas que limpiar.
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
    Contrato.objects.filter(id__in=ids_vencidos).delete()
