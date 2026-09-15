from rest_framework import serializers

from .models import AcuerdoServicio, Cliente, Contrato, Ingreso, Servicio
from .services import eliminar_turnos_de_acuerdo, generar_turnos_de_acuerdo, podar_turnos_de_acuerdo


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'


class AcuerdoServicioSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)
    # Categoria del servicio (ej. para filtrar el selector de sustituto en
    # Fase 3: un servicio solo puede cubrirlo un empleado de su misma
    # categoria).
    servicio_categoria = serializers.CharField(source='servicio.categoria', read_only=True)
    profesional_nombre = serializers.CharField(source='profesional.__str__', read_only=True)

    class Meta:
        model = AcuerdoServicio
        fields = [
            'id', 'servicio', 'servicio_nombre', 'servicio_categoria', 'profesional', 'profesional_nombre',
            'dias_semana', 'hora_inicio', 'hora_fin', 'horas_estimadas', 'tarifa_manual',
            'fecha_inicio', 'duracion_semanas', 'fecha_fin', 'activo',
        ]
        read_only_fields = ['fecha_fin']

    def validate(self, data):
        servicio = data.get('servicio') or getattr(self.instance, 'servicio', None)
        profesional = data.get('profesional') or getattr(self.instance, 'profesional', None)
        if servicio and profesional and servicio.categoria != profesional.categoria:
            raise serializers.ValidationError({
                'profesional': f"{profesional} es de categoria '{profesional.categoria}' pero "
                               f"'{servicio}' es un servicio de categoria '{servicio.categoria}'."
            })
        return data


class AcuerdoServicioPublicoSerializer(serializers.ModelSerializer):
    """
    Version reducida de AcuerdoServicioSerializer para "Mis Contratos": un
    empleado puede ver sus propios servicios contratados -- que servicio,
    dias, horario, fechas -- pero no `tarifa_manual` (precio puntual pactado
    con el cliente, dato de negocio).
    """
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)
    profesional_nombre = serializers.CharField(source='profesional.__str__', read_only=True)

    class Meta:
        model = AcuerdoServicio
        fields = [
            'id', 'servicio', 'servicio_nombre', 'profesional', 'profesional_nombre',
            'dias_semana', 'hora_inicio', 'hora_fin', 'horas_estimadas',
            'fecha_inicio', 'duracion_semanas', 'fecha_fin', 'activo',
        ]
        read_only_fields = fields


class ContratoSerializer(serializers.ModelSerializer):
    acuerdos = AcuerdoServicioSerializer(many=True)
    fecha_inicio = serializers.ReadOnlyField()
    fecha_fin = serializers.ReadOnlyField()
    cliente_nombre = serializers.CharField(source='cliente.nombre_contacto', read_only=True)

    class Meta:
        model = Contrato
        fields = [
            'id', 'cliente', 'cliente_nombre', 'estado', 'documento_pdf', 'firmas_completas',
            'observaciones', 'creado_en', 'fecha_inicio', 'fecha_fin', 'acuerdos',
            'motivo_anulacion', 'fecha_inicio_anulacion', 'fecha_fin_anulacion',
        ]
        read_only_fields = [
            'documento_pdf', 'motivo_anulacion', 'fecha_inicio_anulacion', 'fecha_fin_anulacion',
        ]

    def validate_acuerdos(self, value):
        if not value:
            raise serializers.ValidationError("El contrato necesita al menos un servicio contratado.")
        return value

    def create(self, validated_data):
        acuerdos_data = validated_data.pop('acuerdos')
        contrato = Contrato.objects.create(**validated_data)
        for acuerdo_data in acuerdos_data:
            acuerdo_data.pop('id', None)
            acuerdo = AcuerdoServicio.objects.create(contrato=contrato, **acuerdo_data)
            generar_turnos_de_acuerdo(acuerdo)
        return contrato

    def update(self, instance, validated_data):
        # Una vez que el contrato deja de ser 'borrador' (se activo, se
        # finalizo o se anulo), los servicios contratados quedan congelados:
        # ni se agregan, ni se quitan, ni se edita ningun campo de los que ya
        # existen. Para cambios reales (otro empleado, otro horario, mas
        # semanas) hay que crear un contrato nuevo. Se usa el estado ANTES de
        # aplicar este update, asi que si esta misma llamada activa el
        # contrato, todavia se permite guardar los acuerdos junto con eso.
        estaba_en_borrador = instance.estado == 'borrador'

        acuerdos_data = validated_data.pop('acuerdos', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if acuerdos_data is not None and estaba_en_borrador:
            ids_enviados = [a['id'] for a in acuerdos_data if a.get('id')]
            acuerdos_a_quitar = instance.acuerdos.exclude(id__in=ids_enviados)
            # Antes de borrar el AcuerdoServicio hay que borrar sus Turno ya
            # generados: la FK Turno.acuerdo_servicio es SET_NULL, no CASCADE.
            for acuerdo_a_quitar in acuerdos_a_quitar:
                eliminar_turnos_de_acuerdo(acuerdo_a_quitar)
            acuerdos_a_quitar.delete()
            for acuerdo_data in acuerdos_data:
                acuerdo_id = acuerdo_data.pop('id', None)
                acuerdo_existente = instance.acuerdos.filter(id=acuerdo_id).first() if acuerdo_id else None
                if acuerdo_existente:
                    # Uno por uno (no .update() masivo) para que save() recalcule fecha_fin.
                    for attr, value in acuerdo_data.items():
                        setattr(acuerdo_existente, attr, value)
                    acuerdo_existente.save()
                    generar_turnos_de_acuerdo(acuerdo_existente)
                    # Si el horario se achico (menos dias, menos semanas),
                    # generar_turnos_de_acuerdo no borra los turnos que
                    # quedaron fuera del horario nuevo -- podar_turnos_de_acuerdo
                    # se encarga de eso.
                    podar_turnos_de_acuerdo(acuerdo_existente)
                else:
                    acuerdo = AcuerdoServicio.objects.create(contrato=instance, **acuerdo_data)
                    generar_turnos_de_acuerdo(acuerdo)
        return instance


class ContratoPublicoSerializer(serializers.ModelSerializer):
    """
    "Mis Contratos": un empleado puede ver, de solo lectura, los contratos
    donde tiene algun AcuerdoServicio asignado -- mismos datos que ve un
    admin (cliente, estado, rango de fechas, servicios con horario, PDF)
    excepto nada que sirva para calcular el ingreso esperado (dato de
    negocio, no le corresponde).
    """
    acuerdos = AcuerdoServicioPublicoSerializer(many=True, read_only=True)
    fecha_inicio = serializers.ReadOnlyField()
    fecha_fin = serializers.ReadOnlyField()
    cliente_nombre = serializers.CharField(source='cliente.nombre_contacto', read_only=True)

    class Meta:
        model = Contrato
        fields = [
            'id', 'cliente', 'cliente_nombre', 'estado', 'documento_pdf', 'firmas_completas',
            'observaciones', 'creado_en', 'fecha_inicio', 'fecha_fin', 'acuerdos',
        ]
        read_only_fields = fields


class ServicioSerializer(serializers.ModelSerializer):
    en_uso = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = '__all__'

    def get_en_uso(self, obj):
        # Si nunca se uso en ningun AcuerdoServicio (ni siquiera en un
        # contrato borrador), la accion 'desactivar' del viewset lo borra de
        # verdad en vez de solo desactivarlo -- este campo le permite al
        # frontend avisar con el texto correcto antes de que se confirme la
        # accion irreversible.
        return obj.acuerdos.exists()

    def validate(self, data):
        # Un servicio desactivado queda bloqueado para edicion: mientras el
        # estado resultante siga siendo activo=False, no se permite tocar
        # ningun otro campo -- la unica forma de volver a editarlo es
        # reactivarlo primero (lo que si se puede hacer junto con otros
        # cambios en la misma llamada).
        if self.instance:
            activo_resultante = data.get('activo', self.instance.activo)
            if not activo_resultante:
                otros_campos = set(data.keys()) - {'activo'}
                if otros_campos:
                    raise serializers.ValidationError(
                        "Este servicio está desactivado. Actívalo antes de editar otros campos."
                    )
        return data


class IngresoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingreso
        fields = '__all__'
        read_only_fields = ['cobrado', 'iva_porcentaje', 'iva_monto', 'base_real', 'pago_empleado']
