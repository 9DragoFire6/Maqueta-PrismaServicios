# Helper compartido de "doble verificacion" para acciones sensibles (editar
# un contrato, guardar tarifas de un servicio, eliminar un respaldo, etc. --
# se va a ir reusando a medida que esos modulos existan) y para el segundo
# paso del login.
#
# Si el usuario ya activo su 2FA (TOTPDevice confirmado, ver
# accounts/views.py:setup_2fa/verificar_2fa), se le exige y valida el codigo
# de 6 digitos. Si todavia no lo activo, se cae a pedir la contraseña otra
# vez -- para no dejar a nadie bloqueado mientras no configura su 2FA.
#
# Un solo lugar con esta logica: todo lo que necesite reconfirmar identidad
# le pregunta a este modulo en vez de repetir el check_password/verify_token
# cada uno por su cuenta.


def tiene_2fa_activo(user):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def verificar_doble_factor(user, data):
    """
    data: el request.data de la vista que llama esto (dict-like). Busca
    'codigo' si el usuario tiene 2FA activo, o 'password' si no.

    Devuelve (ok: bool, error: str | None).
    """
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device:
        codigo = (data.get('codigo') or '').strip()
        if not codigo:
            return False, 'Ingresa el código de tu app de autenticación.'
        if not device.verify_token(codigo):
            return False, 'Código incorrecto.'
        return True, None

    password = data.get('password', '')
    if not password:
        return False, 'Ingresa tu contraseña.'
    if not user.check_password(password):
        return False, 'Contraseña incorrecta.'
    return True, None
