from rest_framework import serializers

from .models import Factura, PagoEmpleado, TareaCobro, TareaRecurrente


class FacturaSerializer(serializers.ModelSerializer):
    # La Factura se agrupa por contrato, no por cliente -- un mismo cliente
    # puede tener varias Factura con el mismo nombre y (mientras no responda
    # el contador) el mismo "Sin responder". Estos tres campos son solo para
    # que el frontend pueda distinguirlas a simple vista; no existen en el
    # modelo.
    contrato_fecha_inicio = serializers.SerializerMethodField()
    contrato_fecha_fin = serializers.SerializerMethodField()
    contrato_servicios = serializers.SerializerMethodField()

    class Meta:
        model = Factura
        fields = '__all__'
        # numero ya no se autogenera: lo escribe un admin cuando sube el PDF
        # que responde el contador.
        read_only_fields = ['creado_en']

    def get_contrato_fecha_inicio(self, factura):
        return factura.contrato.fecha_inicio if factura.contrato else None

    def get_contrato_fecha_fin(self, factura):
        return factura.contrato.fecha_fin if factura.contrato else None

    def get_contrato_servicios(self, factura):
        if not factura.contrato:
            return []
        return list(
            factura.contrato.acuerdos.order_by('servicio__nombre')
            .values_list('servicio__nombre', flat=True).distinct()
        )


class PagoEmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagoEmpleado
        fields = '__all__'


class TareaRecurrenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TareaRecurrente
        fields = '__all__'


class TareaCobroSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.SerializerMethodField()
    cliente_email = serializers.SerializerMethodField()

    class Meta:
        model = TareaCobro
        fields = [
            'id', 'contrato', 'cliente_nombre', 'cliente_email', 'periodo_inicio', 'periodo_fin',
            'estado', 'enviada_en', 'enviada_por', 'monto_enviado', 'detalle_enviado', 'creada_en',
        ]
        read_only_fields = [
            'contrato', 'periodo_inicio', 'periodo_fin', 'estado',
            'enviada_en', 'enviada_por', 'monto_enviado', 'detalle_enviado', 'creada_en',
        ]

    def get_cliente_nombre(self, tarea):
        if not tarea.contrato:
            return None
        return tarea.contrato.cliente.nombre_contacto

    def get_cliente_email(self, tarea):
        if not tarea.contrato:
            return None
        return tarea.contrato.cliente.email
