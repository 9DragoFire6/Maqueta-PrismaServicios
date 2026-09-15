from rest_framework import serializers

from accounts.permissions import ROLES_NIVEL_ADMIN

from .models import Ausencia, Empleado, Recibo, SolicitudAusencia, Turno


class ReciboSerializer(serializers.ModelSerializer):
    # 'pago' es una relacion inversa (PagoEmpleado.recibo, OneToOne): fields
    # = '__all__' no la incluye sola, hay que declararla para que el
    # frontend sepa si este recibo ya tiene un pago registrado.
    pago = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Recibo
        fields = '__all__'


class EmpleadoSerializer(serializers.ModelSerializer):
    recibos = ReciboSerializer(many=True, read_only=True)

    class Meta:
        model = Empleado
        fields = '__all__'


class EmpleadoPublicoSerializer(serializers.ModelSerializer):
    """
    Version reducida de EmpleadoSerializer, para cuando un empleado consulta
    el listado de OTROS empleados: solo datos de contacto basicos, nada
    sensible (direccion, datos cifrados como fecha_nacimiento/numero_documento).
    """
    class Meta:
        model = Empleado
        fields = ['id', 'nombre', 'apellido', 'email', 'telefono', 'color', 'activo']


class TurnoSerializer(serializers.ModelSerializer):
    # Ingreso previsto: horas programadas x tarifa del servicio. Ingreso
    # real: lo mismo pero con horas_reales (null hasta que se registren). Se
    # calculan aca (no en el frontend) para no duplicar la logica de tarifas
    # (tarifa_manual vs tarifa_cliente) en JS. Ambos quedan en None si el
    # turno no viene de un AcuerdoServicio.
    ingreso_previsto = serializers.SerializerMethodField()
    ingreso_real = serializers.SerializerMethodField()
    modificado_por_nombre = serializers.SerializerMethodField()
    # Categoria del servicio de este turno (via acuerdo_servicio) -- el
    # frontend la usa para filtrar el selector de sustituto en el panel del
    # turno: un servicio solo puede cubrirlo un empleado de su misma
    # categoria (ver empleados/services.py:payee_de_turno).
    servicio_categoria = serializers.SerializerMethodField()

    class Meta:
        model = Turno
        fields = '__all__'
        # 'marca' y 'confirmado_por_empleado' las maneja el sistema
        # (deteccion automatica de ausencias, procesar solicitudes, o
        # registrar-horas-reales): no se editan por PATCH directo.
        read_only_fields = ['marca', 'confirmado_por_empleado', 'modificado_por']

    def get_modificado_por_nombre(self, turno):
        if not turno.modificado_por:
            return None
        nombre = turno.modificado_por.get_full_name() or turno.modificado_por.username
        return f"{nombre}[Modificó]"

    def get_servicio_categoria(self, turno):
        acuerdo = turno.acuerdo_servicio
        return acuerdo.servicio.categoria if acuerdo else None

    def _tarifa(self, turno):
        acuerdo = turno.acuerdo_servicio
        if not acuerdo:
            return None
        servicio = acuerdo.servicio
        if servicio.precio_manual:
            return acuerdo.tarifa_manual if acuerdo.tarifa_manual is not None else servicio.tarifa_cliente
        return servicio.tarifa_cliente

    def get_ingreso_previsto(self, turno):
        tarifa = self._tarifa(turno)
        if tarifa is None:
            return None
        horas = (turno.datetime_fin_programado - turno.datetime_inicio).total_seconds() / 3600
        return round(float(horas) * float(tarifa), 2)

    def get_ingreso_real(self, turno):
        if turno.horas_reales is None:
            return None
        tarifa = self._tarifa(turno)
        if tarifa is None:
            return None
        return round(float(turno.horas_reales) * float(tarifa), 2)


class AusenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ausencia
        fields = '__all__'

    def validate(self, data):
        # DRF no llama a Model.clean(), asi que esta validacion tiene que
        # vivir aca. En un PATCH parcial alguno de los dos campos puede no
        # venir en `data`; se completa con el valor actual de la instancia.
        fecha_inicio = data.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fecha_fin = data.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                'La fecha de fin de la ausencia no puede ser anterior a la fecha de inicio.'
            )

        # Un empleado solo puede cubrir servicios de su misma categoria --
        # misma regla que AcuerdoServicio.clean(), aplicada tambien a
        # sustituciones. Esta Ausencia (caso puntual) no tiene FK a Turno --
        # se relaciona por empleado + rango de fechas -- asi que se busca si
        # algun Turno de ese rango es de un servicio de otra categoria.
        sustituto = data.get('sustituto', getattr(self.instance, 'sustituto', None))
        empleado = data.get('empleado', getattr(self.instance, 'empleado', None))
        if sustituto and empleado and fecha_inicio and fecha_fin:
            hay_turno_incompatible = Turno.objects.filter(
                empleado=empleado, fecha__gte=fecha_inicio, fecha__lte=fecha_fin,
                acuerdo_servicio__isnull=False,
            ).exclude(acuerdo_servicio__servicio__categoria=sustituto.categoria).exists()
            if hay_turno_incompatible:
                raise serializers.ValidationError(
                    {'sustituto': "El empleado sustituto debe ser de la misma categoría que el servicio a cubrir."}
                )
        return data


class SolicitudAusenciaSerializer(serializers.ModelSerializer):
    empleado_afectado_nombre = serializers.SerializerMethodField()
    sustituto_reasignacion_nombre = serializers.SerializerMethodField()
    acuerdo_servicio_detalle = serializers.SerializerMethodField()
    admin_autoriza_nombre = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudAusencia
        fields = '__all__'
        # resolucion/resuelta_por/nota_resolucion tambien quedan de solo
        # lectura: se escriben desde la accion 'procesar', no por PATCH.
        read_only_fields = [
            'solicitante', 'estado', 'creada_en', 'resuelta_en',
            'resolucion', 'resuelta_por', 'nota_resolucion',
        ]

    def get_empleado_afectado_nombre(self, s):
        if not s.empleado_afectado:
            return None
        return f"{s.empleado_afectado.nombre} {s.empleado_afectado.apellido or ''}".strip()

    def get_sustituto_reasignacion_nombre(self, s):
        if not s.sustituto_reasignacion:
            return None
        return f"{s.sustituto_reasignacion.nombre} {s.sustituto_reasignacion.apellido or ''}".strip()

    def get_admin_autoriza_nombre(self, s):
        if not s.admin_autoriza:
            return None
        return f"{s.admin_autoriza.first_name} {s.admin_autoriza.last_name}".strip()

    def get_acuerdo_servicio_detalle(self, s):
        a = s.acuerdo_servicio
        if not a:
            return None
        return {
            'servicio_nombre': a.servicio.nombre,
            'servicio_categoria': a.servicio.categoria,
            'contrato_id': a.contrato_id,
            'cliente_id': a.contrato.cliente_id,
        }

    def validate(self, data):
        # 'ausencia' y 'turno' son ambos opcionales a nivel de modelo, pero
        # cual hace falta depende del tipo: 'correccion_horas' apunta a un
        # Turno; 'reasignacion_extendida' no depende de ninguna de las dos
        # (propone sus propios datos); los otros 2 tipos siguen necesitando
        # una Ausencia.
        tipo = data.get('tipo')

        if tipo == 'correccion_horas':
            if not data.get('turno'):
                raise serializers.ValidationError({'turno': "Una corrección de horas necesita indicar el turno."})
        elif tipo == 'reasignacion_extendida':
            self._validar_reasignacion_extendida(data)
        elif not data.get('ausencia'):
            raise serializers.ValidationError({'ausencia': "Este tipo de solicitud necesita estar asociada a una ausencia."})
        return data

    def _validar_reasignacion_extendida(self, data):
        # Solo un admin puede PROPONER una reasignacion extendida -- no
        # necesariamente el empleado afectado, que puede no estar disponible
        # por la urgencia del caso. El procesamiento (aceptar/rechazar/
        # corregir) ya esta restringido a EsAdmin por
        # SolicitudAusenciaViewSet.get_permissions -- este chequeo es aparte,
        # para la CREACION.
        request = self.context.get('request')
        if request is not None and request.user.rol not in ROLES_NIVEL_ADMIN:
            raise serializers.ValidationError({'tipo': "Solo un administrador puede proponer una reasignación extendida."})

        empleado_afectado = data.get('empleado_afectado')
        acuerdo = data.get('acuerdo_servicio')
        fecha_inicio = data.get('fecha_inicio_reasignacion')
        fecha_fin = data.get('fecha_fin_reasignacion')

        if not empleado_afectado:
            raise serializers.ValidationError({'empleado_afectado': "Falta indicar el empleado afectado."})
        if not acuerdo:
            raise serializers.ValidationError({'acuerdo_servicio': "Falta indicar el contrato/servicio."})
        if acuerdo.profesional_id != empleado_afectado.id:
            raise serializers.ValidationError({'acuerdo_servicio': "Ese contrato/servicio no pertenece al empleado indicado."})
        if not fecha_inicio or not fecha_fin:
            raise serializers.ValidationError({'fecha_fin_reasignacion': "Faltan las fechas del rango."})
        if fecha_fin < fecha_inicio:
            raise serializers.ValidationError({'fecha_fin_reasignacion': "La fecha de fin no puede ser anterior a la de inicio."})
        if (fecha_fin - fecha_inicio).days < 1:
            raise serializers.ValidationError({'fecha_fin_reasignacion':
                "La reasignación extendida requiere un mínimo de 2 días. Para un solo día, "
                "usá la sustitución o el permiso puntual desde el turno."})

        # Mismo freno que en AusenciaSerializer.validate(): un empleado solo
        # puede cubrir servicios de su misma categoria.
        sustituto = data.get('sustituto_reasignacion')
        if sustituto and sustituto.categoria != acuerdo.servicio.categoria:
            raise serializers.ValidationError(
                {'sustituto_reasignacion': "El sustituto debe ser de la misma categoría que el servicio a cubrir."}
            )
