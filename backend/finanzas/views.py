from django.db import models as django_models
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import EsAdmin

from .email_utils import enviar_cotizacion_semanal, enviar_factura_cliente, enviar_solicitud_contador
from .models import Factura, PagoEmpleado, TareaCobro, TareaRecurrente
from .serializers import FacturaSerializer, PagoEmpleadoSerializer, TareaCobroSerializer, TareaRecurrenteSerializer
from .services import calcular_detalle_cobro, generar_tareas_cobro, solicitar_facturas_pendientes


class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
    permission_classes = [EsAdmin]

    @action(detail=True, methods=['post'], url_path='subir-pago', parser_classes=[MultiPartParser, FormParser])
    def subir_pago(self, request, pk=None):
        """
        Sube el comprobante de pago que envia el cliente. A diferencia de
        subir el PDF de la factura (un PATCH generico sin efectos
        colaterales), esto ademas marca la Factura como cobrada y cascada
        ese estado a los Ingreso que agrupa -- por eso es una accion aparte.
        """
        factura = self.get_object()
        archivo = request.FILES.get('comprobante_pago')
        if not archivo:
            return Response({'error': 'No se envio ningun archivo'}, status=400)

        factura.comprobante_pago = archivo
        factura.estado = 'cobrada'
        factura.save()

        from clientes.models import Ingreso
        Ingreso.objects.filter(factura=factura).update(estado='pagado')

        return Response(FacturaSerializer(factura).data)


class PagoEmpleadoViewSet(viewsets.ModelViewSet):
    queryset = PagoEmpleado.objects.all()
    serializer_class = PagoEmpleadoSerializer
    permission_classes = [EsAdmin]


class TareaRecurrenteViewSet(viewsets.ModelViewSet):
    queryset = TareaRecurrente.objects.filter(activa=True)
    serializer_class = TareaRecurrenteSerializer
    permission_classes = [EsAdmin]


class TareaCobroViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura + dos acciones (detalle/enviar): las tareas de cobro se
    generan solas (generar_tareas_cobro), nunca se crean ni editan a mano.
    """
    serializer_class = TareaCobroSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        generar_tareas_cobro()
        return TareaCobro.objects.all()

    @action(detail=True, methods=['get'], url_path='detalle')
    def detalle(self, request, pk=None):
        tarea = self.get_object()
        if tarea.estado == 'enviada':
            return Response({
                'dias': tarea.detalle_enviado or [],
                'total': float(tarea.monto_enviado) if tarea.monto_enviado is not None else 0,
                'congelado': True,
            })
        if not tarea.contrato:
            return Response({'error': 'El contrato de esta tarea ya no existe.'}, status=400)
        detalle = calcular_detalle_cobro(tarea.contrato, tarea.periodo_inicio, tarea.periodo_fin)
        detalle = detalle or {'dias': [], 'total': 0}
        return Response({**detalle, 'congelado': False})

    @action(detail=True, methods=['post'], url_path='enviar')
    def enviar(self, request, pk=None):
        tarea = self.get_object()
        if tarea.estado == 'enviada':
            return Response({'error': 'Esta cotización ya fue enviada.'}, status=400)
        if not tarea.contrato:
            return Response({'error': 'El contrato de esta tarea ya no existe.'}, status=400)

        cliente = tarea.contrato.cliente
        if not cliente.email:
            return Response({'error': 'El cliente no tiene email registrado.'}, status=400)

        detalle = calcular_detalle_cobro(tarea.contrato, tarea.periodo_inicio, tarea.periodo_fin)
        detalle = detalle or {'dias': [], 'total': 0}

        enviar_cotizacion_semanal(cliente, tarea, detalle)

        tarea.estado = 'enviada'
        tarea.enviada_en = timezone.now()
        tarea.enviada_por = request.user
        tarea.monto_enviado = detalle['total']
        tarea.detalle_enviado = detalle['dias']
        tarea.save()
        return Response(TareaCobroSerializer(tarea).data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def solicitar_facturas_pendientes_view(request):
    email_contador = request.data.get('email_contador')
    if not email_contador:
        return Response({'error': 'Email del contador requerido'}, status=400)

    cliente_id = request.data.get('cliente')
    resultado = solicitar_facturas_pendientes(email_contador, cliente_id=cliente_id)
    return Response(resultado)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_contador_view(request, factura_id):
    email_contador = request.data.get('email_contador')
    if not email_contador:
        return Response({'error': 'Email del contador requerido'}, status=400)

    try:
        factura = Factura.objects.get(id=factura_id)
    except Factura.DoesNotExist:
        return Response({'error': 'Factura no encontrada'}, status=404)

    enviar_solicitud_contador(factura, email_contador)
    return Response({'mensaje': 'Solicitud enviada al contador correctamente'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_cliente_view(request, factura_id):
    try:
        factura = Factura.objects.get(id=factura_id)
    except Factura.DoesNotExist:
        return Response({'error': 'Factura no encontrada'}, status=404)

    if not factura.cliente.email:
        return Response({'error': 'El cliente no tiene email registrado'}, status=400)

    enviar_factura_cliente(factura)
    return Response({'mensaje': 'Factura enviada al cliente correctamente'})


@api_view(['GET'])
@permission_classes([EsAdmin])
def tareas_hoy(request):
    hoy = timezone.now().date()
    dia_semana = hoy.weekday()
    dia_mes = hoy.day

    tareas = TareaRecurrente.objects.filter(activa=True).filter(
        django_models.Q(frecuencia='diaria')
        | django_models.Q(frecuencia='semanal', dia_semana=dia_semana)
        | django_models.Q(frecuencia='mensual', dia_mes=dia_mes)
    )

    return Response(TareaRecurrenteSerializer(tareas, many=True).data)
