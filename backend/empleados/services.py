from datetime import timedelta

from django.utils import timezone

from .models import Ausencia, SolicitudAusencia, Turno

HORAS_PLAZO_REGISTRO = 12

# Cuanto tiempo se conserva una SolicitudAusencia despues de quedar
# 'resuelta' (Procesada), antes de que limpiar_solicitudes_procesadas() la
# borre.
DIAS_RETENCION_SOLICITUDES = 7


def _limite_vencido():
    """
    Punto de corte: cualquier plazo que haya empezado antes de este momento
    ya lleva mas de HORAS_PLAZO_REGISTRO horas corriendo. Tiene que ser el
    mismo instante para detectar_ausencias_automaticas() y
    marcar_turnos_por_ausencia() (via _inicio_plazo) dentro de una misma
    llamada.
    """
    return timezone.now().replace(tzinfo=None) - timedelta(hours=HORAS_PLAZO_REGISTRO)


def _inicio_plazo(turno, ausencia_con_sustituto=None):
    """
    Desde cuando se cuentan las HORAS_PLAZO_REGISTRO horas para ESTE turno.

    Por defecto es el fin programado del turno. Pero si hay una sustitucion
    armada (Ausencia.sustituto cubriendo a este turno) y esa Ausencia se creo
    DESPUES de que el turno ya habia vencido, el plazo se corre al momento en
    que se creo esa Ausencia -- sin este ajuste, el sustituto quedaria con el
    plazo "ya vencido" apenas se lo asigna, sin ninguna ventana real para
    registrar sus horas. Se toma el MAS TARDE de los dos.

    `ausencia_con_sustituto`, si se pasa, evita una consulta repetida cuando
    el llamador ya sabe cual es (marcar_turnos_por_ausencia).
    """
    inicio = turno.datetime_fin_programado
    if ausencia_con_sustituto is None:
        ausencia_con_sustituto = Ausencia.objects.filter(
            empleado=turno.empleado,
            sustituto__isnull=False,
            fecha_inicio__lte=turno.fecha,
            fecha_fin__gte=turno.fecha,
        ).first()
    if ausencia_con_sustituto:
        creada_en_naive = ausencia_con_sustituto.creada_en.replace(tzinfo=None)
        if creada_en_naive > inicio:
            inicio = creada_en_naive
    return inicio


def plazo_registro_vencido(turno):
    """
    True si ya paso el plazo de HORAS_PLAZO_REGISTRO horas de ESTE turno. Se
    usa desde TurnoViewSet.registrar_horas_reales para bloquear el
    autoregistro de un empleado fuera de su ventana -- un admin nunca pasa
    por aca.
    """
    return _inicio_plazo(turno) <= _limite_vencido()


def detectar_ausencias_automaticas():
    """
    No hay scheduler ni cron en este proyecto: esta funcion se aprovecha de
    cada consulta a Turno o Ausencia para revisar si algun turno vencio hace
    mas de HORAS_PLAZO_REGISTRO horas sin que se registraran horas_reales.

    Si es asi, se asume que el empleado no trabajo:
    - horas_reales pasa a 0 (no se deja en None: queda un valor explicito en
      vez de un vacio ambiguo entre "no se sabe" y "no trabajo").
    - El turno se marca con marca='ausencia_automatica'.
    - Se crea una Ausencia de un dia, para poder pedir una correccion
      despues -- pero solo si todavia no existe ninguna Ausencia que ya
      cubra a ese empleado en esa fecha (evita duplicar una Ausencia al lado
      de una ya cargada a mano con o sin sustituto).

    Es idempotente: un turno que ya tiene horas_reales no vuelve a tocarse.
    """
    limite = _limite_vencido()

    vencidos = Turno.objects.filter(horas_reales__isnull=True, activo=True)
    for turno in vencidos:
        if _inicio_plazo(turno) > limite:
            continue

        turno.horas_reales = 0
        turno.marca = 'ausencia_automatica'
        turno.save()

        ya_cubierta = Ausencia.objects.filter(
            empleado=turno.empleado,
            fecha_inicio__lte=turno.fecha,
            fecha_fin__gte=turno.fecha,
        ).exists()
        if not ya_cubierta:
            Ausencia.objects.get_or_create(
                empleado=turno.empleado,
                fecha_inicio=turno.fecha,
                fecha_fin=turno.fecha,
                defaults={
                    'motivo': 'Ausencia detectada automáticamente: no se registraron horas '
                              'reales dentro de las 12 horas siguientes al turno.',
                },
            )


def marcar_turnos_por_ausencia(ausencia):
    """
    Aplica a una Ausencia cargada a mano el mismo tratamiento que la
    deteccion automatica: los turnos de ese empleado dentro del rango, que
    todavia no tengan horas_reales, pasan a horas_reales=0 y
    marca='ausencia_automatica'.

    Sin sustituto (permiso, ausencia generica): se marca de inmediato. Con
    sustituto: cada turno respeta su propio plazo de HORAS_PLAZO_REGISTRO
    horas antes de marcarse (ver _inicio_plazo) -- asignar un sustituto a un
    turno futuro o recien vencido no lo marca "ausencia" al instante.

    Nunca toca un turno que ya tiene horas_reales.
    """
    turnos = Turno.objects.filter(
        empleado=ausencia.empleado,
        fecha__gte=ausencia.fecha_inicio,
        fecha__lte=ausencia.fecha_fin,
        horas_reales__isnull=True,
    )
    if not ausencia.sustituto_id:
        turnos.update(horas_reales=0, marca='ausencia_automatica')
        return

    limite = _limite_vencido()
    ids_vencidos = [t.id for t in turnos if _inicio_plazo(t, ausencia) <= limite]
    if ids_vencidos:
        Turno.objects.filter(id__in=ids_vencidos).update(horas_reales=0, marca='ausencia_automatica')


def revertir_turnos_por_ausencia(empleado, fecha_inicio, fecha_fin):
    """
    Contraparte de marcar_turnos_por_ausencia(): al borrar una Ausencia o al
    editarla para que ya no cubra ciertas fechas, los turnos que esa
    Ausencia habia marcado vuelven a quedar sin registrar (horas_reales=None,
    marca=''). Solo revierte turnos con marca='ausencia_automatica' Y
    horas_reales=0 -- si ya se registraron horas reales de verdad, no se
    toca.
    """
    Turno.objects.filter(
        empleado=empleado,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
        marca='ausencia_automatica',
        horas_reales=0,
    ).update(horas_reales=None, marca='')


def limpiar_solicitudes_procesadas():
    """
    Se llama desde SolicitudAusenciaViewSet.get_queryset() y borra las
    solicitudes que llevan mas de DIAS_RETENCION_SOLICITUDES dias en estado
    'resuelta', para que la lista no acumule historial viejo indefinidamente.
    Las 'pendiente' nunca se tocan.
    """
    limite = timezone.now() - timedelta(days=DIAS_RETENCION_SOLICITUDES)
    SolicitudAusencia.objects.filter(estado='resuelta', resuelta_en__lt=limite).delete()


def payee_de_turno(turno):
    """
    A quien se le debe pagar un Turno ya trabajado (horas_reales
    registradas), para clientes.services.generar_ingresos_semana() (Fase 4).
    Puede devolver None si el turno no debe contarse ni para facturarle al
    cliente ni para pagarle a nadie por la via automatica.

    Sin sustitucion: cobra el titular del turno, como siempre.

    Con sustitucion: cobra el sustituto, EXCEPTO que su categoria no
    coincida con la del servicio del acuerdo -- un empleado solo puede
    cubrir servicios de su misma categoria (misma regla que
    AcuerdoServicio.clean(), aplicada tambien a sustituciones). Si no
    coincide, el turno queda afuera del calculo automatico: ni se le cobra
    al cliente por el, ni se le paga a nadie -- requiere resolucion manual.

    Un turno sin acuerdo_servicio (creado a mano) nunca pasa por esta
    funcion en la practica, pero se devuelve None por si se llama desde
    otro lado.
    """
    acuerdo = turno.acuerdo_servicio
    if not acuerdo:
        return None

    ausencia = Ausencia.objects.filter(
        empleado=turno.empleado,
        sustituto__isnull=False,
        fecha_inicio__lte=turno.fecha,
        fecha_fin__gte=turno.fecha,
    ).first()
    if not ausencia:
        return turno.empleado

    if acuerdo.servicio.categoria != ausencia.sustituto.categoria:
        return None

    return ausencia.sustituto


def calcular_pago_profesional(acuerdo, horas):
    """
    Cuanto se le paga a quien haya trabajado `horas` de un AcuerdoServicio,
    usando la compensacion configurada en el SERVICIO del contrato (no de
    quien fisicamente las trabajo) -- ver Servicio.compensacion_tipo/
    compensacion_valor en clientes/models.py. Misma formula que va a usar
    Ingreso.save() (Fase 4) sobre el total de horas de la semana; aca se
    aplica por empleado cuando la semana se reparte entre el titular y quien
    lo sustituyo, para que el total y la suma de las partes coincidan
    siempre por construccion.

    Si esta formula cambia, hay que actualizar tambien Ingreso.save().
    """
    servicio = acuerdo.servicio
    if servicio.compensacion_tipo == 'porcentaje_base':
        base = horas * servicio.tarifa_cliente
        return base * servicio.compensacion_valor / 100
    return horas * servicio.compensacion_valor
