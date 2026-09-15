# Correos del lado financiero (solicitar factura al contador, avisarle al
# cliente que su factura esta lista, enviar la cotizacion semanal). Mismo
# backend de consola que accounts/email_utils.py: no hay proveedor de correo
# real conectado en este proyecto local.
from django.conf import settings
from django.core.mail import send_mail


def enviar_solicitud_contador(factura, email_contador):
    cliente = factura.cliente
    ingresos = factura.ingresos.select_related('servicio')

    lineas = []
    for ingreso in ingresos:
        tarifa_hora = round(ingreso.base_real / ingreso.horas, 2) if ingreso.horas else 0
        lineas.append(
            f"- {ingreso.servicio.nombre}: {ingreso.horas}h x {tarifa_hora} = {ingreso.base_real}"
        )
    detalle = '\n'.join(lineas) or '(sin líneas de detalle)'

    aplica_iva = bool(cliente.iva_porcentaje and cliente.iva_porcentaje > 0)
    if aplica_iva:
        base = factura.importe - (factura.importe * cliente.iva_porcentaje / (100 + cliente.iva_porcentaje))
        resumen = (
            f"NIF: {cliente.nif}\n"
            f"Net amount: {round(base, 2)} + IVA ({cliente.iva_porcentaje}%) = {factura.importe}"
        )
    else:
        resumen = f"Tax / company number: {cliente.nif}\nTotal: {factura.importe} (sin IVA, cliente exento)"

    send_mail(
        subject=f'{settings.APP_NAME} — Solicitud de factura para {cliente.nombre_contacto}',
        message=(
            f"Hola,\n\nSolicitamos una factura para {cliente.nombre_contacto} por los siguientes "
            f"servicios:\n\n{detalle}\n\n{resumen}\n\nSaludos."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email_contador],
    )


def enviar_factura_cliente(factura):
    cliente = factura.cliente
    send_mail(
        subject=f'{settings.APP_NAME} — Tu factura {factura.numero or ""}'.strip(),
        message=(
            f"Hola {cliente.nombre_contacto},\n\n"
            f"Adjuntamos tu factura por un total de {factura.importe}.\n\n"
            f"Saludos."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cliente.email],
    )


def enviar_cotizacion_semanal(cliente, tarea, detalle):
    lineas = [
        f"- {dia['fecha']}: {dia['servicio']} — "
        f"{dia['horas_reales'] if dia['horas_reales'] is not None else 'sin registrar'}h — {dia['subtotal']}"
        for dia in detalle['dias']
    ]
    cuerpo = '\n'.join(lineas) or '(sin días en este período)'
    send_mail(
        subject=f'{settings.APP_NAME} — Cotización semanal ({tarea.periodo_inicio} al {tarea.periodo_fin})',
        message=(
            f"Hola {cliente.nombre_contacto},\n\n"
            f"Este es el resumen de la semana del {tarea.periodo_inicio} al {tarea.periodo_fin}:\n\n"
            f"{cuerpo}\n\nTotal: {detalle['total']}\n\nSaludos."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cliente.email],
    )
