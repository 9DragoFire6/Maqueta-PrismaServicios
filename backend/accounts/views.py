import base64
import io
import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.dobleverificacion import tiene_2fa_activo, verificar_doble_factor
from accounts.email_utils import enviar_email_credenciales, enviar_email_recuperacion
from accounts.models import Usuario
from accounts.permissions import EsAdmin, EsAdminOEmpleado


def _generar_password_temporal():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))


class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = user.rol
        token['email'] = user.email
        return token

    def validate(self, attrs):
        # super().validate() ya autentica email+password (self.user queda
        # seteado) y arma los tokens. Si el usuario tiene 2FA activado
        # (TOTPDevice confirmado), se le exige ademas el codigo de 6 digitos
        # actual antes de devolver esos tokens -- si falta o es invalido, se
        # descartan y se avisa con 'requiere_2fa' para que el frontend sepa
        # que tiene que mostrar el segundo paso (y no confundirlo con
        # "contraseña incorrecta").
        data = super().validate(attrs)

        from rest_framework import serializers as drf_serializers

        if tiene_2fa_activo(self.user):
            codigo = (self.initial_data.get('codigo_2fa') or '').strip()
            device = TOTPDevice.objects.filter(user=self.user, confirmed=True).first()
            if not codigo:
                raise drf_serializers.ValidationError({
                    'requiere_2fa': True,
                    'error': 'Ingresa el código de tu app de autenticación.',
                })
            if not device.verify_token(codigo):
                raise drf_serializers.ValidationError({
                    'requiere_2fa': True,
                    'error': 'Código incorrecto.',
                })

        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token requerido'}, status=400)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'mensaje': 'Sesión cerrada correctamente'})
    except TokenError:
        return Response({'error': 'Token inválido o ya expirado'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def setup_2fa(request):
    from django.conf import settings

    # Elimina cualquier dispositivo sin confirmar de un intento anterior,
    # para no acumular secretos huerfanos cada vez que se reabre el QR.
    TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()

    device = TOTPDevice.objects.create(
        user=request.user,
        name=f'{settings.APP_NAME}-{request.user.email}',
        confirmed=False,
    )

    qr = qrcode.make(device.config_url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return Response({
        'qr_code': f'data:image/png;base64,{qr_b64}',
        'secret': device.bin_key.hex(),
        'mensaje': 'Escanea el QR con Google Authenticator, Authy o similar.',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verificar_2fa(request):
    codigo = request.data.get('codigo')
    if not codigo:
        return Response({'error': 'Código requerido'}, status=400)

    device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    if not device:
        return Response({'error': 'No hay dispositivo 2FA pendiente de confirmar'}, status=404)

    if not device.verify_token(codigo):
        return Response({'error': 'Código incorrecto'}, status=400)

    device.confirmed = True
    device.save()
    return Response({'mensaje': '2FA activado correctamente'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validar_2fa(request):
    codigo = request.data.get('codigo')
    if not codigo:
        return Response({'error': 'Código requerido'}, status=400)

    device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if not device:
        return Response({'error': 'No tienes 2FA configurado'}, status=404)

    if device.verify_token(codigo):
        return Response({'valido': True, 'mensaje': 'Código correcto'})
    return Response({'valido': False, 'error': 'Código incorrecto'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estado_2fa(request):
    """
    Le dice al frontend, antes de mostrar cualquier popup de reverificacion
    o el paso 2 del login, si le toca pedir contraseña o codigo -- ver
    accounts/dobleverificacion.py.
    """
    return Response({'activo': tiene_2fa_activo(request.user)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verificar_password(request):
    """
    Reconfirma la identidad de quien esta autenticada, sin crear ningun
    estado de sesion elevada -- quien la llama decide que hacer con el
    resultado. Pide contraseña o codigo de 2FA segun tenga o no activado el
    2FA quien llama.

    Endpoint generico: cualquier modulo que necesite un "reingresa tu
    contraseña" antes de una accion sensible (editar un contrato, cambiar
    tarifas, borrar un respaldo) llama a este mismo endpoint como primer
    paso, en vez de reimplementar la verificacion cada vez.
    """
    ok, error = verificar_doble_factor(request.user, request.data)
    if not ok:
        return Response({'error': error}, status=400)
    return Response({'ok': True})


def _serializar_perfil(user, request):
    return {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'rol': user.rol,
        'nif': user.nif,
        'direccion': user.direccion,
        'nacionalidad': user.nacionalidad,
        'foto': request.build_absolute_uri(user.foto.url) if user.foto else None,
    }


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def perfil(request):
    user = request.user
    if request.method == 'GET':
        return Response(_serializar_perfil(user, request))

    campos = ['first_name', 'last_name', 'email', 'nif', 'direccion', 'nacionalidad']
    for campo in campos:
        if campo in request.data:
            setattr(user, campo, request.data[campo])
    if 'foto' in request.FILES:
        user.foto = request.FILES['foto']
    user.save()
    return Response(_serializar_perfil(user, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_password(request):
    """
    Cambio de contraseña desde 'Mi perfil', con la persona ya logueada.
    Exige la contraseña actual (para que no baste con tener la sesion
    abierta en un dispositivo compartido) y valida la nueva con las mismas
    reglas de AUTH_PASSWORD_VALIDATORS que usa el resto de Django.
    """
    user = request.user
    password_actual = request.data.get('password_actual', '')
    password_nueva = request.data.get('password_nueva', '')

    if not password_actual or not password_nueva:
        return Response({'error': 'Debes ingresar tu contraseña actual y la nueva.'}, status=400)
    if not user.check_password(password_actual):
        return Response({'error': 'La contraseña actual no es correcta.'}, status=400)

    try:
        validate_password(password_nueva, user=user)
    except DjangoValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=400)

    user.set_password(password_nueva)
    user.save()
    return Response({'mensaje': 'Contraseña actualizada correctamente.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_recuperacion(request):
    """
    Paso 1 de 'Olvidé mi contraseña', desde el login (sin sesion). Responde
    SIEMPRE el mismo mensaje generico exista o no el email -- no hay que
    revelarle a quien hace la consulta si un correo esta o no registrado.
    """
    email = request.data.get('email', '').strip()
    mensaje_generico = {
        'mensaje': 'Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.'
    }

    if not email:
        return Response({'error': 'Debes ingresar un correo.'}, status=400)

    try:
        usuario = Usuario.objects.get(email=email)
    except Usuario.DoesNotExist:
        return Response(mensaje_generico)

    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    enviar_email_recuperacion(usuario, uid, token)

    return Response(mensaje_generico)


@api_view(['POST'])
@permission_classes([AllowAny])
def restablecer_password(request):
    """
    Paso 2 de 'Olvidé mi contraseña'. Se valida el token con el mismo
    generador estandar de Django que usa el admin (PasswordResetTokenGenerator),
    asi que un link ya usado para cambiar la contrasena, o vencido, deja de
    servir automaticamente.
    """
    uid = request.data.get('uid', '')
    token = request.data.get('token', '')
    password_nueva = request.data.get('password_nueva', '')

    if not uid or not token or not password_nueva:
        return Response({'error': 'Faltan datos para restablecer la contraseña.'}, status=400)

    try:
        usuario_id = force_str(urlsafe_base64_decode(uid))
        usuario = Usuario.objects.get(pk=usuario_id)
    except (Usuario.DoesNotExist, ValueError, TypeError, OverflowError):
        return Response({'error': 'El enlace no es válido.'}, status=400)

    if not default_token_generator.check_token(usuario, token):
        return Response({'error': 'El enlace no es válido o ya expiró. Solicita uno nuevo.'}, status=400)

    try:
        validate_password(password_nueva, user=usuario)
    except DjangoValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=400)

    usuario.set_password(password_nueva)
    usuario.save()
    return Response({'mensaje': 'Contraseña restablecida correctamente. Ya puedes iniciar sesión.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verificar_username(request):
    username = request.query_params.get('username', '').strip()
    if not username:
        return Response({'error': 'Username requerido'}, status=400)
    existe = Usuario.objects.filter(username=username).exists()
    return Response({'username': username, 'disponible': not existe})


@api_view(['GET'])
@permission_classes([EsAdmin])
def lista_usuarios(request):
    usuarios = Usuario.objects.all().order_by('username')
    data = [{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'rol': u.rol,
        'is_active': u.is_active,
        'date_joined': str(u.date_joined),
    } for u in usuarios]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def crear_usuario(request):
    """
    Alta de usuario con password temporal, enviada por correo. En esta fase
    solo crea la cuenta de acceso (Usuario) -- vincularla a una ficha de
    Empleado se agrega en una fase posterior, cuando ese modelo exista.
    """
    data = request.data

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    nombre = data.get('first_name', '').strip()
    apellido = data.get('last_name', '').strip()
    rol = data.get('rol', '')

    if rol not in dict(Usuario.ROL_CHOICES):
        return Response({'error': 'Rol inválido'}, status=400)
    if not username or not email or not nombre:
        return Response({'error': 'username, email y nombre son obligatorios'}, status=400)
    if Usuario.objects.filter(username=username).exists():
        return Response({'error': f'El usuario {username} ya existe, elige otro username'}, status=400)
    if Usuario.objects.filter(email=email).exists():
        return Response({'error': f'El email {email} ya está registrado'}, status=400)

    password_temporal = _generar_password_temporal()

    with transaction.atomic():
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password_temporal,
            first_name=nombre,
            last_name=apellido,
            rol=rol,
        )

    enviar_email_credenciales(nombre, username, email, password_temporal)

    return Response({
        'mensaje': f'Usuario {nombre} {apellido} creado correctamente. Se enviaron las credenciales a {email}.',
        'usuario_id': usuario.id,
    })


@api_view(['PATCH', 'DELETE'])
@permission_classes([EsAdmin])
def usuario_detalle(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'DELETE':
        username = usuario.username
        usuario.delete()
        return Response({'mensaje': f'Usuario {username} eliminado.'})

    data = request.data
    if 'email' in data and Usuario.objects.exclude(id=usuario.id).filter(email=data['email']).exists():
        return Response({'error': f"El email {data['email']} ya está registrado"}, status=400)

    for campo in ['first_name', 'last_name', 'email']:
        if campo in data:
            setattr(usuario, campo, data[campo])
    if 'is_active' in data:
        usuario.is_active = bool(data['is_active'])
    usuario.save()

    return Response({
        'id': usuario.id,
        'username': usuario.username,
        'email': usuario.email,
        'first_name': usuario.first_name,
        'last_name': usuario.last_name,
        'rol': usuario.rol,
        'is_active': usuario.is_active,
    })


@api_view(['GET'])
@permission_classes([EsAdminOEmpleado])
def dashboard_stats(request):
    """
    Numeros resumen para la pantalla de inicio. Deliberadamente simple
    (Fase 6: "completo pero simple") -- un admin ve los totales de todo el
    negocio, un empleado ve un resumen acotado a lo suyo.
    """
    from django.db.models import Sum

    from clientes.models import Cliente, Ingreso
    from empleados.models import Recibo

    if request.user.rol in ('admin',):
        cobros_pendientes = Ingreso.objects.exclude(estado='pagado').aggregate(total=Sum('cobrado'))['total'] or 0
        pagos_pendientes = Recibo.objects.filter(pago__isnull=True).aggregate(total=Sum('importe'))['total'] or 0
        return Response({
            'clientes_activos': Cliente.objects.filter(activa=True).count(),
            'cobros_pendientes': float(cobros_pendientes),
            'pagos_pendientes': float(pagos_pendientes),
        })

    mis_recibos_pendientes = Recibo.objects.filter(
        empleado__email=request.user.email, pago__isnull=True,
    ).aggregate(total=Sum('importe'))['total'] or 0
    return Response({'mis_pagos_pendientes': float(mis_recibos_pendientes)})


@api_view(['GET'])
@permission_classes([EsAdmin])
def dashboard_mensual(request):
    """Facturacion/gastos/pagos de los ultimos 6 meses, para el grafico del dashboard."""
    from datetime import date, timedelta

    from django.db.models import Sum

    from clientes.models import Ingreso
    from finanzas.models import PagoEmpleado

    hoy = date.today()
    meses = []
    for i in range(5, -1, -1):
        primer_dia = date(hoy.year, hoy.month, 1) - timedelta(days=i * 30)
        primer_dia = date(primer_dia.year, primer_dia.month, 1)
        if primer_dia.month == 12:
            ultimo_dia = date(primer_dia.year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(primer_dia.year, primer_dia.month + 1, 1) - timedelta(days=1)

        facturacion = Ingreso.objects.filter(fecha__gte=primer_dia, fecha__lte=ultimo_dia).aggregate(
            total=Sum('cobrado'))['total'] or 0
        pagos_empleados = PagoEmpleado.objects.filter(fecha_pago__gte=primer_dia, fecha_pago__lte=ultimo_dia).aggregate(
            total=Sum('importe'))['total'] or 0

        meses.append({
            'mes': primer_dia.strftime('%b %Y'),
            'facturacion': float(facturacion),
            'pagos_empleados': float(pagos_empleados),
        })

    return Response(meses)
