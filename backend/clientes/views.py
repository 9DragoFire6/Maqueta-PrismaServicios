from django.db.models.deletion import ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from accounts.dobleverificacion import verificar_doble_factor
from accounts.permissions import EsAdmin, EsAdminOEmpleado, ROLES_NIVEL_ADMIN

from .models import AcuerdoServicio, Cliente, Contrato, Servicio
from .serializers import (
    ClienteSerializer,
    ContratoPublicoSerializer,
    ContratoSerializer,
    ServicioSerializer,
)
from .services import eliminar_contratos_borrador_vencidos, finalizar_contratos_vencidos


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [EsAdminOEmpleado()]
        return [EsAdmin()]


class ContratoViewSet(viewsets.ModelViewSet):
    queryset = Contrato.objects.all()

    def get_serializer_class(self):
        # Un empleado lee con el serializer reducido (sin tarifa_manual, para
        # que no pueda reconstruir el "ingreso esperado"). Admin sigue viendo
        # todo.
        if self.request.user.rol in ROLES_NIVEL_ADMIN:
            return ContratoSerializer
        return ContratoPublicoSerializer

    def get_permissions(self):
        # Cualquier rol autenticado puede LEER (scoped a lo suyo, ver
        # get_queryset), pero solo un admin puede escribir.
        if self.request.method in SAFE_METHODS:
            return [EsAdminOEmpleado()]
        return [EsAdmin()]

    def get_queryset(self):
        # No hay scheduler/cron en este proyecto: se aprovecha cada consulta
        # a Contrato para poner en 'finalizado' los que ya vencieron, y para
        # eliminar los 'borrador' cuya fecha_inicio paso sin activarse.
        finalizar_contratos_vencidos()
        eliminar_contratos_borrador_vencidos()

        user = self.request.user
        if user.rol in ROLES_NIVEL_ADMIN:
            return Contrato.objects.all()
        # Un empleado solo ve los contratos donde tiene algun AcuerdoServicio
        # asignado, vinculado por email.
        return Contrato.objects.filter(acuerdos__profesional__email=user.email).distinct()

    # Campos que, si vienen en el PATCH, significan "esto es una edicion de
    # verdad del contrato" -- ahi aplica la doble verificacion. Un PATCH que
    # solo trae 'estado' (botón Activar) o 'firmas_completas' (checkbox) es
    # una accion puntual de un click, no una edicion del contenido, asi que
    # no interrumpe con un popup.
    CAMPOS_EDICION_PROTEGIDA = {'cliente', 'observaciones', 'acuerdos'}

    def update(self, request, *args, **kwargs):
        # Doble verificacion para editar un contrato ya existente (no aplica
        # a crear uno nuevo: no hay nada previo con que comparar). El PATCH
        # tiene que traer la misma contraseña o codigo de 2FA que ya se
        # verifico en el primer paso del flujo del frontend
        # (POST /api/auth/verificar-password/) -- se vuelve a chequear aca,
        # del lado del servidor, para que no sea solo un candado de interfaz.
        if self.CAMPOS_EDICION_PROTEGIDA & set(request.data.keys()):
            ok, error = verificar_doble_factor(request.user, request.data)
            if not ok:
                return Response({'error': error}, status=400)
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.estado != 'borrador':
            raise ValidationError(
                'Solo se pueden eliminar contratos en borrador. '
                'Un contrato activo, finalizado o anulado no se borra: usa "Anular" '
                'si el servicio dejo de prestarse, para conservar el historial real.'
            )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='anular')
    def anular(self, request, pk=None):
        """
        Anula un contrato activo desde una fecha hasta otra (ambas
        obligatorias e inclusive). Requiere un motivo.
        """
        contrato = self.get_object()
        if contrato.estado != 'activo':
            return Response(
                {'error': 'Solo se puede anular un contrato que este activo.'},
                status=400,
            )

        motivo = (request.data.get('motivo') or '').strip()
        fecha_inicio_anulacion = request.data.get('fecha_inicio_anulacion')
        fecha_fin_anulacion = request.data.get('fecha_fin_anulacion')

        if not motivo:
            return Response({'error': 'El motivo de la anulacion es obligatorio.'}, status=400)
        if not fecha_inicio_anulacion or not fecha_fin_anulacion:
            return Response(
                {'error': 'Debes indicar desde que fecha hasta que fecha se anula el contrato.'},
                status=400,
            )
        if fecha_fin_anulacion < fecha_inicio_anulacion:
            return Response(
                {'error': 'La fecha de fin de la anulacion no puede ser anterior a la fecha de inicio.'},
                status=400,
            )

        contrato.estado = 'anulado'
        contrato.motivo_anulacion = motivo
        contrato.fecha_inicio_anulacion = fecha_inicio_anulacion
        contrato.fecha_fin_anulacion = fecha_fin_anulacion
        contrato.save()
        # Fase 3: eliminar_turnos_de_contrato(contrato, desde=..., hasta=...) aca.

        return Response(ContratoSerializer(contrato).data)


class ServicioViewSet(viewsets.ModelViewSet):
    """
    Catalogo de servicios: tarifas y compensacion por servicio, editable
    solo por administradores. Es la base de como se calculan tarifas y
    pagos en toda la app, asi que el acceso es mas restrictivo que el resto
    de los endpoints de esta app -- ni siquiera un empleado puede leerlo.
    """
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [EsAdmin]

    # 'activo' se toca solo desde la accion desactivar() (con su propia
    # confirmacion en el frontend), nunca como parte del lote de "Guardar
    # cambios" -- igual que 'estado'/'firmas_completas' en ContratoViewSet.
    CAMPOS_SIN_DOBLE_VERIFICACION = {'activo'}

    def create(self, request, *args, **kwargs):
        # Un servicio nuevo define tarifas/compensacion que impactan todo el
        # sistema -- misma doble verificacion que editar uno existente.
        ok, error = verificar_doble_factor(request.user, request.data)
        if not ok:
            return Response({'error': error}, status=400)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if set(request.data.keys()) - self.CAMPOS_SIN_DOBLE_VERIFICACION:
            ok, error = verificar_doble_factor(request.user, request.data)
            if not ok:
                return Response({'error': error}, status=400)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        """
        Si el servicio nunca se uso en ningun AcuerdoServicio (ni siquiera en
        un contrato borrador), se elimina de verdad -- asi el catalogo no
        acumula servicios creados por error o de prueba que nunca llegaron a
        usarse. Si SI tiene historial, el PROTECT de AcuerdoServicio.servicio
        hace que Servicio.delete() tire ProtectedError, y en ese caso se cae
        al comportamiento de siempre: solo se desactiva, se conserva el
        historial real.
        """
        servicio = self.get_object()
        try:
            servicio.delete()
            return Response({'eliminado': True})
        except ProtectedError:
            servicio.activo = False
            servicio.save(update_fields=['activo'])
            return Response({'eliminado': False, 'servicio': ServicioSerializer(servicio).data})

    @action(detail=False, methods=['post'], url_path='reordenar')
    def reordenar(self, request):
        """Recibe {'orden': [id1, id2, ...]} con el nuevo orden completo y
        reescribe el campo 'orden' de cada Servicio segun su posicion en la lista."""
        ids = request.data.get('orden')
        if not isinstance(ids, list) or not ids:
            return Response({'error': "Se esperaba 'orden': [id, id, ...]"}, status=400)
        servicios = {s.id: s for s in Servicio.objects.filter(id__in=ids)}
        if len(servicios) != len(ids):
            return Response({'error': 'Alguno de los ids no corresponde a un servicio existente.'}, status=400)
        for posicion, servicio_id in enumerate(ids):
            servicio = servicios[servicio_id]
            if servicio.orden != posicion:
                servicio.orden = posicion
                servicio.save(update_fields=['orden'])
        return Response(ServicioSerializer(Servicio.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([EsAdmin])
def exportar_datos_cliente(request, pk):
    try:
        cliente = Cliente.objects.get(pk=pk)
    except Cliente.DoesNotExist:
        return Response({'error': 'Cliente no encontrado'}, status=404)

    datos = {
        'nombre_contacto': cliente.nombre_contacto,
        'telefono': cliente.telefono,
        'email': cliente.email,
        'direccion': cliente.direccion,
        'nif': cliente.nif,
        'iva_porcentaje': str(cliente.iva_porcentaje),
        'activa': cliente.activa,
        'creada_en': str(cliente.creada_en),
        'contratos': [
            {
                'fecha_inicio': str(c.fecha_inicio) if c.fecha_inicio else None,
                'fecha_fin': str(c.fecha_fin) if c.fecha_fin else None,
                'estado': c.estado,
                'servicios': [
                    {
                        'servicio': a.servicio.nombre,
                        'profesional': str(a.profesional),
                        'fecha_inicio': str(a.fecha_inicio),
                        'fecha_fin': str(a.fecha_fin) if a.fecha_fin else None,
                    }
                    for a in c.acuerdos.all()
                ],
            }
            for c in cliente.contratos.all()
        ],
    }
    return Response(datos)


@api_view(['DELETE'])
@permission_classes([EsAdmin])
def anonimizar_datos_cliente(request, pk):
    """
    Anonimiza, no borra: la fila se conserva (contratos/ingresos/recibos
    cuelgan de ella y son documentacion fiscal que hay que conservar), pero
    los datos personales identificables se vacian.
    """
    try:
        cliente = Cliente.objects.get(pk=pk)
    except Cliente.DoesNotExist:
        return Response({'error': 'Cliente no encontrado'}, status=404)

    cliente.nombre_contacto = f'ELIMINADO_{pk}'
    cliente.telefono = ''
    cliente.email = ''
    cliente.direccion = ''
    cliente.nif = ''
    cliente.activa = False
    cliente.save()

    return Response({'mensaje': f'Datos personales del cliente {pk} eliminados correctamente'})
