from django.db import models

from gestion_servicios.storage_utils import borrar_archivos_reemplazados
from gestion_servicios.validators import validar_tamano_archivo


class Factura(models.Model):
    """
    El numero real de la factura lo asigna el contador, no este sistema: se
    crea en estado 'pendiente' sin numero ni fechas al solicitarla (importe
    = suma de los Ingreso que agrupa), y queda completa cuando llega la
    respuesta del contador y se suben numero + archivo_pdf juntos.
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('cobrada', 'Cobrada'),
        ('vencida', 'Vencida'),
        ('anulada', 'Anulada'),
    ]
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='facturas')
    contrato = models.ForeignKey('clientes.Contrato', on_delete=models.SET_NULL, null=True, blank=True)
    numero = models.CharField(max_length=20, unique=True, null=True, blank=True,
        help_text="Numero real asignado por el contador. Vacio mientras la factura esta solicitada y sin responder")
    fecha_emision = models.DateField(null=True, blank=True,
        help_text="Vacio hasta que el contador emite la factura")
    fecha_vencimiento = models.DateField(null=True, blank=True,
        help_text="Vacio hasta que el contador emite la factura")
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    archivo_pdf = models.FileField(upload_to='facturas/', null=True, blank=True, validators=[validar_tamano_archivo])
    comprobante_pago = models.FileField(upload_to='pagos_facturas/', null=True, blank=True,
        validators=[validar_tamano_archivo], help_text="Respaldo de pago que envia el cliente")
    creado_en = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        borrar_archivos_reemplazados(self, ['archivo_pdf', 'comprobante_pago'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero or 'sin numero'} - {self.cliente}"


class PagoEmpleado(models.Model):
    recibo = models.OneToOneField('empleados.Recibo', on_delete=models.CASCADE, related_name='pago')
    fecha_pago = models.DateField()
    importe = models.DecimalField(max_digits=8, decimal_places=2)
    comprobante = models.FileField(upload_to='pagos/', null=True, blank=True, validators=[validar_tamano_archivo])

    def save(self, *args, **kwargs):
        borrar_archivos_reemplazados(self, ['comprobante'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pago {self.recibo.empleado} - {self.fecha_pago}"


class TareaCobro(models.Model):
    """
    Tarea semanal de cobro: resume las horas reales trabajadas de un
    Contrato en un periodo (semana anclada a lunes) para que un admin la
    revise y, si corresponde, envie la cotizacion al cliente. Se genera
    sola para contratos que no esten en 'borrador' -- incluye activos,
    finalizados y anulados, para no perder el cobro de la ultima semana
    trabajada aunque el contrato ya haya cambiado de estado para cuando se
    genera esa tarea.

    Antes de enviarse, el monto se calcula en vivo a partir de los Turno del
    periodo. Al enviarse, se congela una copia (detalle_enviado/
    monto_enviado): si despues se corrige una hora real de esos dias, el
    correo ya enviado no cambia solo.
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
    ]
    contrato = models.ForeignKey('clientes.Contrato', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tareas_cobro')
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    enviada_en = models.DateTimeField(null=True, blank=True)
    enviada_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    monto_enviado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    detalle_enviado = models.JSONField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('contrato', 'periodo_inicio')
        ordering = ['-periodo_inicio']

    def __str__(self):
        return f"Cobro {self.contrato} — {self.periodo_inicio} a {self.periodo_fin}"


class TareaRecurrente(models.Model):
    FRECUENCIAS = [
        ('diaria', 'Diaria'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    ]
    DIAS_SEMANA = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    frecuencia = models.CharField(max_length=10, choices=FRECUENCIAS)
    dia_semana = models.IntegerField(choices=DIAS_SEMANA, null=True, blank=True)
    dia_mes = models.IntegerField(null=True, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo
