# Envio de correos transaccionales (alta de usuario, recuperacion de
# contraseña). Usa el backend de consola de Django (ver EMAIL_BACKEND en
# settings): en este proyecto local, el "envio" queda impreso en la terminal
# donde corre runserver -- no hay ningun proveedor de correo real conectado.
from django.conf import settings
from django.core.mail import send_mail


def enviar_email_credenciales(nombre, username, email, password_temporal):
    send_mail(
        subject=f'Bienvenido/a a {settings.APP_NAME} — tus credenciales de acceso',
        message=(
            f'Hola {nombre},\n\n'
            f'Tu cuenta fue creada correctamente. Estas son tus credenciales de acceso:\n\n'
            f'Usuario: {username}\n'
            f'Contraseña temporal: {password_temporal}\n\n'
            f'Por favor cambia tu contraseña después de iniciar sesión por primera vez.\n\n'
            f'Accede al sistema en: {settings.FRONTEND_URL}\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def enviar_email_recuperacion(usuario, uid, token):
    link = f'{settings.FRONTEND_URL}/restablecer-password/{uid}/{token}'
    send_mail(
        subject=f'{settings.APP_NAME} — Recupera tu contraseña',
        message=(
            f'Hola {usuario.first_name or usuario.username},\n\n'
            f'Recibimos una solicitud para restablecer tu contraseña. Si fuiste tú, entra al '
            f'siguiente enlace para elegir una nueva:\n\n{link}\n\n'
            f'El enlace es válido por un tiempo limitado y solo se puede usar una vez. Si tú no '
            f'pediste este cambio, puedes ignorar este correo.\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
    )
