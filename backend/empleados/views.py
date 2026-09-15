from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from accounts.permissions import EsAdmin, EsAdminOEmpleado, ROLES_NIVEL_ADMIN

from .models import Ausencia, Empleado, Recibo, SolicitudAusencia, Turno
from .serializers import (
    AusenciaSerializer,
    EmpleadoPublicoSerializer,
    EmpleadoSerializer,
    ReciboSerializer,
    SolicitudAusenciaSerializer,
    TurnoSerializer,
)
from .services import (
    detectar_ausencias_automaticas,
    limpiar_solicitudes_procesadas,
    marcar_turnos_por_ausencia,
    plazo_registro_vencido,
    revertir_turnos_por_ausencia,
)


class EmpleadoViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        # Admin ve la ficha completa. Un empleado ve a los demas empleados
        # con el serializer reducido: nombre, apellido, email, telefono --
        # nada sensible.
        if self.request.user.rol in ROLES_NIVEL_ADMIN:
            return EmpleadoSerializer
        return EmpleadoPublicoSerializer

    def get_queryset(self):
        user = self.request.user
        if user.rol in ROLES_NIVEL_ADMIN:
            return Empleado.objects.all()
        # Un empleado ve a todos los empleados ACTIVOS, no solo su propia
        # ficha. Los datos sensibles quedan afuera por el serializer
        # reducido, no por el queryset.
        return Empleado.objects.filter(activo=True)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [EsAdminOEmpleado()]
        return [EsAdmin()]


class ReciboViewSet(viewsets.ModelViewSet):
    serializer_class = ReciboSerializer

    def get_queryset(self):
        # No hay scheduler/cron en este proyecto: se aprovecha cada consulta
        # a Recibos para generar los que falten junto con sus Ingreso, por
        # si se abre Pagos sin haber pasado antes por Ingresos.
        from clientes.services import generar_ingresos_semana
        generar_ingresos_semana()

        user = self.request.user
        if user.rol in ROLES_NIVEL_ADMIN:
            return Recibo.objects.all()
        return Recibo.objects.filter(empleado__email=user.email)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [EsAdminOEmpleado()]
        return [EsAdmin()]


class TurnoViewSet(viewsets.ModelViewSet):
    serializer_class = TurnoSerializer

    def get_queryset(self):
        # No hay scheduler/cron en este proyecto: se aprovecha cada consulta
        # a Turnos para detectar los que vencieron hace mas de 12 horas sin
        # horas_reales registradas.
        detectar_ausencias_automaticas()

        user = self.request.user
        if user.rol in ROLES_NIVEL_ADMIN:
            return Turno.objects.all()

        # Ademas de sus propios turnos, un empleado ve los que este
        # cubriendo como sustituto -- para poder entrar a registrar ahi sus
        # propias horas reales. Ausencia no tiene FK directa a Turno (se
        # relaciona por empleado + rango de fechas), asi que se arma un Q
        # por cada Ausencia vigente donde el es el sustituto.
        filtro = Q(empleado__email=user.email)
        for ausencia in Ausencia.objects.filter(sustituto__email=user.email):
            # Reasignacion extendida (Ausencia.acuerdo_servicio seteado): solo
            # se incluyen los turnos de ESE contrato puntual, no todos los del
            # titular en ese rango de fechas.
            rango = Q(empleado_id=ausencia.empleado_id, fecha__gte=ausencia.fecha_inicio, fecha__lte=ausencia.fecha_fin)
            if ausencia.acuerdo_servicio_id:
                rango &= Q(acuerdo_servicio_id=ausencia.acuerdo_servicio_id)
            filtro |= rango

        qs = Turno.objects.filter(filtro)

        # Contrapartida: si este usuario es el TITULAR de una reasignacion
        # extendida, deja de ver durante el rango los turnos de ese contrato
        # puntual. No afecta otros turnos suyos en las mismas fechas que
        # sean de otro AcuerdoServicio, ni a la sustitucion puntual de
        # siempre (que no toca acuerdo_servicio).
        for ausencia in Ausencia.objects.filter(
            empleado__email=user.email, sustituto__isnull=False, acuerdo_servicio__isnull=False,
        ):
            qs = qs.exclude(
                acuerdo_servicio_id=ausencia.acuerdo_servicio_id,
                fecha__gte=ausencia.fecha_inicio, fecha__lte=ausencia.fecha_fin,
            )

        return qs

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [EsAdminOEmpleado()]
        if self.action == 'registrar_horas_reales':
            return [EsAdminOEmpleado()]
        return [EsAdmin()]

    @action(detail=True, methods=['post'], url_path='registrar-horas-reales')
    def registrar_horas_reales(self, request, pk=None):
        turno = self.get_object()
        acuerdo = turno.acuerdo_servicio
        if acuerdo and acuerdo.contrato.estado in ('finalizado', 'anulado'):
            return Response(
                {'error': f"No se pueden registrar horas: el contrato de este turno ya esta '{acuerdo.contrato.get_estado_display()}'."},
                status=400,
            )

        if request.user.rol not in ROLES_NIVEL_ADMIN:
            # (a) Si este turno esta cubierto por un sustituto que NO es
            # quien esta llamando, quien llama no puede tocarlo -- ni
            # siquiera si es el titular (que sigue VIENDO el turno pintado
            # con el nombre de quien lo cubre, pero ya no puede escribir
            # sobre el).
            cubierto_por_otro = Ausencia.objects.filter(
                empleado=turno.empleado, sustituto__isnull=False,
                fecha_inicio__lte=turno.fecha, fecha_fin__gte=turno.fecha,
            ).exclude(sustituto__email=request.user.email).exists()
            if cubierto_por_otro:
                return Response(
                    {'error': 'Este turno está cubierto por un sustituto. No puedes registrar horas sobre él.'},
                    status=403,
                )

            # (b) Fuera de la ventana de 12h, un empleado ya no puede
            # autoregistrar ni autocorregir directo -- tiene que pedir una
            # SolicitudAusencia tipo 'mal_ingresada' para que la revise un
            # admin.
            if plazo_registro_vencido(turno):
                return Response(
                    {'error': 'Ya pasó el plazo de 12 horas para registrar este turno. Pide una '
                              'solicitud de "Ausencia mal ingresada" para que la revise un administrador.'},
                    status=403,
                )

        # Un empleado no puede volver a tocar horas que ya confirmo el
        # mismo, aunque este dentro de plazo -- tiene que pedir una
        # solicitud de correccion.
        if turno.confirmado_por_empleado and request.user.rol not in ROLES_NIVEL_ADMIN:
            return Response(
                {'error': 'Ya confirmaste tus horas para este turno. Si necesitas corregirlas, '
                          'crea una solicitud de corrección de horas.'},
                status=400,
            )
        # Un admin tampoco puede sobreescribir libremente horas ya
        # confirmadas por el empleado -- necesita que exista una
        # SolicitudAusencia tipo='correccion_horas' apuntando a este turno.
        # El primer registro (turno todavia sin confirmar) sigue siendo
        # libre.
        if turno.confirmado_por_empleado and request.user.rol in ROLES_NIVEL_ADMIN:
            hay_solicitud = SolicitudAusencia.objects.filter(
                turno=turno, tipo='correccion_horas',
            ).exclude(estado='resuelta', resolucion='rechazada').exists()
            if not hay_solicitud:
                return Response(
                    {'error': 'Este empleado ya confirmó estas horas. Para corregirlas, primero '
                              'tiene que existir una solicitud de corrección de horas de su parte.'},
                    status=400,
                )
        horas = request.data.get('horas_reales')
        if horas in (None, ''):
            return Response({'error': 'Falta indicar horas_reales'}, status=400)
        try:
            horas = float(horas)
        except (TypeError, ValueError):
            return Response({'error': 'horas_reales debe ser un numero'}, status=400)
        if horas < 0 or horas > 24:
            return Response({'error': 'horas_reales debe estar entre 0 y 24'}, status=400)
        turno.horas_reales = horas
        # Si el turno estaba marcado (ausencia automatica u otra), registrar
        # horas de nuevo significa que alguien la esta corrigiendo a mano.
        turno.marca = ''
        turno.confirmado_por_empleado = request.user.rol not in ROLES_NIVEL_ADMIN
        if request.user.rol in ROLES_NIVEL_ADMIN:
            turno.modificado_por = request.user
        turno.save()
        return Response(TurnoSerializer(turno).data)


class AusenciaViewSet(viewsets.ModelViewSet):
    serializer_class = AusenciaSerializer

    def get_queryset(self):
        detectar_ausencias_automaticas()

        user = self.request.user
        if user.rol in ROLES_NIVEL_ADMIN:
            return Ausencia.objects.all()
        return Ausencia.objects.filter(empleado__email=user.email)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [EsAdminOEmpleado()]
        if self.action == 'create':
            return [EsAdminOEmpleado()]
        return [EsAdmin()]

    def perform_create(self, serializer):
        ausencia = serializer.save()
        marcar_turnos_por_ausencia(ausencia)

    def perform_update(self, serializer):
        # Se guarda el rango/empleado ANTES de aplicar los cambios: hay que
        # revertir lo que la version vieja habia marcado antes de volver a
        # marcar con los valores nuevos.
        anterior = serializer.instance
        empleado_anterior = anterior.empleado
        fecha_inicio_anterior = anterior.fecha_inicio
        fecha_fin_anterior = anterior.fecha_fin

        serializer.save()
        self._resolver_solicitudes_pendientes(serializer.instance)

        revertir_turnos_por_ausencia(empleado_anterior, fecha_inicio_anterior, fecha_fin_anterior)
        marcar_turnos_por_ausencia(serializer.instance)

    def perform_destroy(self, instance):
        self._resolver_solicitudes_pendientes(instance)
        revertir_turnos_por_ausencia(instance.empleado, instance.fecha_inicio, instance.fecha_fin)
        instance.delete()

    def _resolver_solicitudes_pendientes(self, ausencia):
        from finanzas.models import TareaRecurrente

        solicitudes = SolicitudAusencia.objects.filter(ausencia=ausencia, estado='pendiente')
        for s in solicitudes:
            s.estado = 'resuelta'
            s.resuelta_en = timezone.now()
            s.save()
            # Fragilidad conocida (igual que en el original): la tarea se
            # localiza por texto en el titulo, no por FK. Si la misma
            # persona tiene varias solicitudes abiertas, resolver una
            # desactiva todas sus tareas.
            TareaRecurrente.objects.filter(
                titulo__contains=s.solicitante.get_full_name() or s.solicitante.username,
                activa=True,
            ).update(activa=False)


class SolicitudAusenciaViewSet(viewsets.ModelViewSet):
    serializer_class = SolicitudAusenciaSerializer

    def get_queryset(self):
        # Mismo patron "sin cron": de paso se borran las solicitudes que ya
        # llevan mas de DIAS_RETENCION_SOLICITUDES dias en estado 'resuelta'.
        limpiar_solicitudes_procesadas()

        user = self.request.user
        if user.rol in ROLES_NIVEL_ADMIN:
            return SolicitudAusencia.objects.all().order_by('-creada_en')
        return SolicitudAusencia.objects.filter(solicitante=user).order_by('-creada_en')

    def get_permissions(self):
        # Procesar (aceptar/rechazar/corregir) una solicitud es una decision
        # de administracion: cualquier otro rol solo puede crear/ver las suyas.
        if self.action == 'procesar':
            return [EsAdmin()]
        return [EsAdminOEmpleado()]

    @action(detail=True, methods=['post'], url_path='procesar')
    def procesar(self, request, pk=None):
        """
        Marca una SolicitudAusencia como procesada, con 3 caminos posibles:
        aceptarla tal cual, rechazarla, o corregirla con un valor distinto
        al pedido. Esta accion NO edita Turno ni Ausencia por si sola -- las
        horas reales las tiene que escribir un admin a mano, reusando
        "registrar-horas-reales". La unica excepcion es 'permiso' aceptado:
        ahi se marca el/los Turno del rango con marca='autorizado'.
        """
        solicitud = self.get_object()
        if solicitud.estado == 'resuelta':
            return Response({'error': 'Esta solicitud ya fue procesada.'}, status=400)

        resolucion = request.data.get('resolucion')
        if resolucion not in dict(SolicitudAusencia.RESOLUCIONES):
            return Response({'error': 'resolucion invalida. Debe ser aceptada, rechazada o corregida.'}, status=400)

        # Para 'reasignacion_extendida' que se acepta/corrige, hay que crear
        # una Ausencia -- se valida y arma ANTES de tocar el estado de la
        # solicitud: si fallara despues, la solicitud quedaria "Procesada"
        # sin haber creado nada, y no habria forma de reintentar (procesar
        # rechaza de entrada cualquier solicitud ya resuelta).
        ausencia_a_crear = None
        if solicitud.tipo == 'reasignacion_extendida' and resolucion in ('aceptada', 'corregida'):
            from datetime import date as date_cls

            def _fecha(valor, default):
                if not valor:
                    return default
                return date_cls.fromisoformat(valor) if isinstance(valor, str) else valor

            fecha_inicio = _fecha(request.data.get('fecha_inicio_reasignacion'), solicitud.fecha_inicio_reasignacion)
            fecha_fin = _fecha(request.data.get('fecha_fin_reasignacion'), solicitud.fecha_fin_reasignacion)
            if fecha_fin < fecha_inicio:
                return Response({'error': 'La fecha de fin no puede ser anterior a la de inicio.'}, status=400)

            sustituto_id = request.data.get('sustituto_reasignacion', solicitud.sustituto_reasignacion_id)

            if sustituto_id and solicitud.acuerdo_servicio:
                sustituto = Empleado.objects.filter(id=sustituto_id).first()
                if sustituto and sustituto.categoria != solicitud.acuerdo_servicio.servicio.categoria:
                    return Response(
                        {'error': "El sustituto debe ser de la misma categoría que el servicio a cubrir."},
                        status=400,
                    )

            ausencia_a_crear = {
                'empleado': solicitud.empleado_afectado,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'motivo': solicitud.motivo or 'Reasignación extendida',
                'sustituto_id': sustituto_id or None,
                'acuerdo_servicio': solicitud.acuerdo_servicio,
            }

        solicitud.estado = 'resuelta'
        solicitud.resolucion = resolucion
        solicitud.nota_resolucion = request.data.get('nota_resolucion', '')
        solicitud.resuelta_en = timezone.now()
        solicitud.resuelta_por = request.user
        solicitud.save()

        if solicitud.tipo == 'permiso' and resolucion == 'aceptada':
            ausencia = solicitud.ausencia
            Turno.objects.filter(
                empleado=ausencia.empleado,
                fecha__gte=ausencia.fecha_inicio,
                fecha__lte=ausencia.fecha_fin,
            ).update(marca='autorizado')

        if ausencia_a_crear is not None:
            ausencia_creada = Ausencia.objects.create(**ausencia_a_crear)
            marcar_turnos_por_ausencia(ausencia_creada)

        return Response(SolicitudAusenciaSerializer(solicitud).data)

    def perform_create(self, serializer):
        from finanzas.models import TareaRecurrente

        tipo = serializer.validated_data['tipo']
        ausencia = serializer.validated_data.get('ausencia')
        turno = serializer.validated_data.get('turno')
        solicitud = serializer.save(solicitante=self.request.user)

        # Tarea automatica para que la solicitud aparezca en la pantalla de
        # Tareas de administracion hasta que se atienda. 'correccion_horas'
        # no depende de ninguna Ausencia, asi que la descripcion se arma
        # distinto segun el caso.
        if tipo == 'correccion_horas':
            descripcion = f'Tipo: {tipo}. Turno del {turno.fecha}.'
        elif tipo == 'reasignacion_extendida':
            descripcion = (
                f'Tipo: {tipo}. {solicitud.empleado_afectado} del '
                f'{solicitud.fecha_inicio_reasignacion} al {solicitud.fecha_fin_reasignacion}.'
            )
        else:
            descripcion = f'Tipo: {tipo}. Ausencia del {ausencia.fecha_inicio} al {ausencia.fecha_fin}.'

        TareaRecurrente.objects.create(
            titulo=f'Solicitud - Corrección de Ausencia de {self.request.user.get_full_name() or self.request.user.username}',
            descripcion=descripcion,
            frecuencia='diaria',
            activa=True,
        )
