from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.dobleverificacion import verificar_doble_factor
from accounts.permissions import EsAdmin, EsAdminOEmpleado, ROLES_NIVEL_ADMIN
from clientes.models import Contrato

from .utils import generar_pdf_contrato, nombre_archivo_contrato


@api_view(['GET'])
@permission_classes([IsAuthenticated, EsAdminOEmpleado])
def pdf_contrato(request, contrato_id):
    try:
        contrato = Contrato.objects.get(id=contrato_id)
    except Contrato.DoesNotExist:
        return Response({'error': 'Contrato no encontrado'}, status=404)

    # Un admin puede pedir el PDF de cualquier contrato. Un empleado solo si
    # tiene algun AcuerdoServicio propio en ESE contrato -- mismo scoping
    # por email que ContratoViewSet.get_queryset().
    if request.user.rol not in ROLES_NIVEL_ADMIN:
        tiene_acceso = contrato.acuerdos.filter(profesional__email=request.user.email).exists()
        if not tiene_acceso:
            return Response({'error': 'No tenés acceso a este contrato.'}, status=403)

    buffer = generar_pdf_contrato(contrato)
    return FileResponse(buffer, as_attachment=True, filename=nombre_archivo_contrato(contrato))


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, EsAdmin])
def plantilla_clausulas(request):
    """
    Texto (Markdown) de las clausulas 2 en adelante del contrato.

    El PATCH exige, ademas de EsAdmin, la misma doble verificacion que
    ContratoViewSet.update(): el request tiene que traer la contraseña o el
    codigo de 2FA ya verificado en el primer paso del flujo del frontend
    (POST /api/auth/verificar-password/) -- se revalida aca del lado del
    servidor para que no sea solo un guardarraiz de interfaz.
    """
    from .utils import obtener_plantilla_activa

    plantilla = obtener_plantilla_activa()

    if request.method == 'GET':
        return Response({
            'contenido': plantilla.contenido,
            'actualizado_en': plantilla.actualizado_en,
            'actualizado_por': plantilla.actualizado_por.get_full_name() if plantilla.actualizado_por else None,
        })

    ok, error = verificar_doble_factor(request.user, request.data)
    if not ok:
        return Response({'error': error}, status=400)

    contenido = request.data.get('contenido')
    if contenido is None or not contenido.strip():
        return Response({'error': 'El contenido no puede quedar vacío.'}, status=400)

    plantilla.contenido = contenido
    plantilla.actualizado_por = request.user
    plantilla.save()
    return Response({
        'contenido': plantilla.contenido,
        'actualizado_en': plantilla.actualizado_en,
        'actualizado_por': plantilla.actualizado_por.get_full_name(),
    })
