from datetime import timedelta


def _tarifa_de_turno(turno):
    """Misma logica de tarifa que TurnoSerializer (empleados): tarifa_manual
    si el servicio es de precio manual, si no tarifa_cliente. None si el
    turno no viene de un AcuerdoServicio. Duplicada a proposito -- si la
    regla de precios cambia, hay que tocar los dos lugares."""
    acuerdo = turno.acuerdo_servicio
    if not acuerdo:
        return None
    servicio = acuerdo.servicio
    if servicio.precio_manual:
        return acuerdo.tarifa_manual if acuerdo.tarifa_manual is not None else servicio.tarifa_cliente
    return servicio.tarifa_cliente


def calcular_detalle_cobro(contrato, periodo_inicio, periodo_fin):
    """
    Arma el detalle de cobro de un contrato para un periodo: por cada turno
    programado en ese rango, dia, servicio, horas reales trabajadas (None si
    todavia no se registraron) y subtotal. Los dias sin horas_reales aportan
    0 al total (se cobra por lo realmente trabajado, no por lo programado).

    Devuelve {'dias': [...], 'total': float} o None si no hay ningun turno
    programado en el periodo.
    """
    from empleados.models import Turno

    turnos = Turno.objects.filter(
        acuerdo_servicio__contrato=contrato,
        fecha__gte=periodo_inicio,
        fecha__lte=periodo_fin,
    ).select_related('acuerdo_servicio__servicio').order_by('fecha')

    if not turnos.exists():
        return None

    dias = []
    total = 0.0
    for turno in turnos:
        tarifa = _tarifa_de_turno(turno)
        horas_reales = turno.horas_reales
        subtotal = round(float(horas_reales) * float(tarifa), 2) if (horas_reales is not None and tarifa is not None) else 0.0
        dias.append({
            'fecha': str(turno.fecha),
            'servicio': turno.acuerdo_servicio.servicio.nombre if turno.acuerdo_servicio else '',
            'horas_reales': float(horas_reales) if horas_reales is not None else None,
            'tarifa': float(tarifa) if tarifa is not None else None,
            'subtotal': subtotal,
        })
        total += subtotal

    return {'dias': dias, 'total': round(total, 2)}


def generar_tareas_cobro():
    """
    Genera las tareas de cobro semanales (semana anclada a lunes) que
    falten, para todo contrato que no este en 'borrador'. Solo genera
    periodos ya completamente transcurridos, y solo si hay al menos un
    turno programado en ese periodo. No hay scheduler/cron en este
    proyecto: se corre cada vez que se consulta la lista de tareas de
    cobro.
    """
    from django.utils import timezone

    from clientes.models import Contrato

    from .models import TareaCobro

    hoy = timezone.now().date()

    for contrato in Contrato.objects.exclude(estado='borrador'):
        fecha_inicio = contrato.fecha_inicio
        fecha_fin = contrato.fecha_fin
        if not fecha_inicio or not fecha_fin:
            continue

        cursor = fecha_inicio
        while cursor <= hoy and cursor <= fecha_fin:
            dias_hasta_domingo = 6 - cursor.weekday()
            periodo_fin = min(cursor + timedelta(days=dias_hasta_domingo), fecha_fin)
            if periodo_fin >= hoy:
                break
            periodo_inicio = cursor

            existe = TareaCobro.objects.filter(contrato=contrato, periodo_inicio=periodo_inicio).exists()
            if not existe:
                detalle = calcular_detalle_cobro(contrato, periodo_inicio, periodo_fin)
                if detalle is not None:
                    TareaCobro.objects.create(
                        contrato=contrato,
                        periodo_inicio=periodo_inicio,
                        periodo_fin=periodo_fin,
                    )
            cursor = periodo_fin + timedelta(days=1)


def solicitar_facturas_pendientes(email_contador, cliente_id=None):
    """
    Agrupa los Ingreso sin facturar (estado='pendiente', sin Factura
    vinculada) por CONTRATO -- un cliente con mas de un contrato recibe una
    Factura separada por cada uno, para poder rendirlos por separado con el
    contador. Crea una Factura 'pendiente' por grupo (importe = suma, sin
    numero ni fechas todavia) y envia un correo individual por grupo.

    Los Ingreso sin acuerdo_servicio (cargados a mano) se agrupan por
    cliente, ya que no hay contrato del que tirar.

    Si el envio de un grupo falla, la Factura y el vinculo con sus Ingreso
    ya quedaron creados; se puede reintentar el envio despues. Devuelve un
    resumen con los grupos enviados y los que fallaron.
    """
    from clientes.models import Ingreso

    from .email_utils import enviar_solicitud_contador
    from .models import Factura

    pendientes = Ingreso.objects.filter(
        estado='pendiente', factura__isnull=True,
    ).select_related('cliente', 'acuerdo_servicio__contrato').order_by('cliente_id', 'fecha')
    if cliente_id:
        pendientes = pendientes.filter(cliente_id=cliente_id)

    por_grupo = {}
    for ingreso in pendientes:
        contrato = ingreso.acuerdo_servicio.contrato if ingreso.acuerdo_servicio else None
        clave = ('contrato', contrato.id) if contrato else ('cliente', ingreso.cliente_id)
        grupo = por_grupo.setdefault(clave, {'contrato': contrato, 'cliente': ingreso.cliente, 'ingresos': []})
        grupo['ingresos'].append(ingreso)

    enviadas = []
    errores = []
    for grupo in por_grupo.values():
        ingresos = grupo['ingresos']
        cliente = grupo['cliente']
        contrato = grupo['contrato']
        importe = sum(i.cobrado for i in ingresos)

        factura = Factura.objects.create(
            cliente=cliente, contrato=contrato, importe=importe, estado='pendiente',
        )
        Ingreso.objects.filter(id__in=[i.id for i in ingresos]).update(factura=factura, estado='facturado')

        etiqueta = cliente.nombre_contacto
        if contrato:
            etiqueta += f" (contrato {contrato.fecha_inicio}–{contrato.fecha_fin})"

        try:
            enviar_solicitud_contador(factura, email_contador)
            enviadas.append(etiqueta)
        except Exception as e:
            errores.append({'cliente': etiqueta, 'error': str(e)})

    return {'enviadas': enviadas, 'errores': errores}
