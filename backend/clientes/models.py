from datetime import timedelta
from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField

from gestion_servicios.storage_utils import borrar_archivos_reemplazados
from gestion_servicios.validators import validar_tamano_archivo


class Cliente(models.Model):
    nombre_contacto = models.CharField(max_length=200)
    telefono = EncryptedCharField(max_length=20, blank=True)
    email = EncryptedEmailField(blank=True)
    direccion = EncryptedTextField(blank=True)
    nif = models.CharField(max_length=50, blank=True, help_text="NIF/identificador fiscal del cliente")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=21.0,
        help_text="Porcentaje de impuesto (IVA o similar) a aplicar a este cliente. 0 para clientes exentos.")
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_contacto


class Servicio(models.Model):
    COMPENSACION_TIPOS = [
        ('por_hora', 'Por hora'),
        ('porcentaje_base', 'Porcentaje de lo facturado'),
    ]
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    # Categoria libre (no una lista fija): un AcuerdoServicio solo puede
    # asignar a este servicio un Empleado de la misma categoria (ver
    # AcuerdoServicio.clean() mas abajo). Reemplaza el "tipo" fijo
    # (founder/colaboradora) del original.
    categoria = models.CharField(max_length=30, default='estandar')
    tarifa_cliente = models.DecimalField(max_digits=8, decimal_places=2,
        help_text="Importe por hora que se le cobra al cliente")
    compensacion_tipo = models.CharField(max_length=20, choices=COMPENSACION_TIPOS, default='por_hora',
        help_text="Como se le paga al empleado por este servicio")
    compensacion_valor = models.DecimalField(max_digits=8, decimal_places=2, default=0,
        help_text="Si 'por_hora': importe por hora pagado al empleado. Si 'porcentaje_base': "
                   "porcentaje (0-100) de lo facturado al cliente que recibe el empleado.")
    cruza_medianoche = models.BooleanField(default=False,
        help_text="Marcar para servicios que empiezan un dia y terminan al dia siguiente")
    precio_manual = models.BooleanField(default=False,
        help_text="Marcar si el precio se pacta caso a caso, en vez de usar tarifa_cliente fija")
    notas = models.TextField(blank=True)
    activo = models.BooleanField(default=True,
        help_text="Un servicio inactivo deja de estar disponible para contratos nuevos, pero los "
                   "AcuerdoServicio que ya lo usan siguen intactos (proteccion PROTECT)")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Contrato(models.Model):
    """
    El acuerdo comercial general entre la empresa y un cliente. No tiene
    fechas propias: cada servicio contratado (AcuerdoServicio) define su
    propio fecha_inicio/fecha_fin, porque distintos servicios dentro del
    mismo contrato pueden empezar y terminar en momentos distintos.
    """
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('activo', 'Activo'),
        ('finalizado', 'Finalizado'),
        ('anulado', 'Anulado'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contratos')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    documento_pdf = models.FileField(upload_to='contratos/', null=True, blank=True,
        validators=[validar_tamano_archivo], help_text="PDF del contrato. Se reemplaza por la version firmada cuando esta disponible")
    firmas_completas = models.BooleanField(default=False,
        help_text="Marcar cuando se haya reemplazado el PDF por la version con las firmas")
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    motivo_anulacion = models.TextField(blank=True,
        help_text="Motivo por el que se anulo el contrato (o una parte de su periodo)")
    fecha_inicio_anulacion = models.DateField(null=True, blank=True,
        help_text="Desde que fecha el contrato dejo de prestarse (inclusive)")
    fecha_fin_anulacion = models.DateField(null=True, blank=True,
        help_text="Hasta que fecha el contrato dejo de prestarse (inclusive)")

    @property
    def fecha_inicio(self):
        """La fecha_inicio mas temprana entre todos los AcuerdoServicio del contrato."""
        primero = self.acuerdos.order_by('fecha_inicio').first()
        return primero.fecha_inicio if primero else None

    @property
    def fecha_fin(self):
        """
        La fecha_fin mas tardia entre todos los AcuerdoServicio del contrato.
        El contrato completo no se considera finalizado hasta que se cumple
        esta fecha, aunque servicios individuales hayan terminado antes.
        """
        ultimo = self.acuerdos.exclude(fecha_fin__isnull=True).order_by('-fecha_fin').first()
        return ultimo.fecha_fin if ultimo else None

    def save(self, *args, **kwargs):
        borrar_archivos_reemplazados(self, ['documento_pdf'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Contrato {self.cliente} - {self.estado}"


class AcuerdoServicio(models.Model):
    """
    Un servicio especifico contratado dentro de un Contrato: que servicio,
    quien lo presta, que dias, en que horario, y desde/hasta cuando. Un
    Contrato puede tener uno o varios de estos.
    """
    DIAS = [
        ('lun', 'Lunes'),
        ('mar', 'Martes'),
        ('mie', 'Miércoles'),
        ('jue', 'Jueves'),
        ('vie', 'Viernes'),
        ('sab', 'Sábado'),
        ('dom', 'Domingo'),
    ]
    # Codigo de dia por indice de date.weekday() (0=lunes .. 6=domingo), usado
    # para expandir dias_semana a fechas concretas (Turno, Fase 3).
    DIAS_POR_WEEKDAY = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
    DURACION_MINIMA_SEMANAS = 4

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='acuerdos')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='acuerdos')
    profesional = models.ForeignKey('empleados.Empleado', on_delete=models.PROTECT, related_name='acuerdos_servicio')
    dias_semana = ArrayField(
        models.CharField(max_length=3, choices=DIAS),
        size=7,
        help_text="Dias de la semana en que se presta este servicio"
    )
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    horas_estimadas = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Duracion tipica del turno, solo referencial para planificar")
    tarifa_manual = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Solo para servicios de precio manual. Se ignora si el servicio no lo requiere")
    fecha_inicio = models.DateField()
    duracion_semanas = models.PositiveIntegerField(null=True, blank=True,
        help_text="Si se deja vacio, se asumen 4 semanas (el minimo)")
    fecha_fin = models.DateField(null=True, blank=True, editable=False)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.duracion_semanas is not None and self.duracion_semanas < self.DURACION_MINIMA_SEMANAS:
            raise ValidationError({
                'duracion_semanas': f"La duracion minima de un servicio contratado es de {self.DURACION_MINIMA_SEMANAS} semanas."
            })
        if self.servicio_id and self.profesional_id and self.servicio.categoria != self.profesional.categoria:
            raise ValidationError({
                'profesional': f"{self.profesional} es de categoria '{self.profesional.categoria}' pero "
                               f"'{self.servicio}' es un servicio de categoria '{self.servicio.categoria}'."
            })

    def save(self, *args, **kwargs):
        if not self.duracion_semanas:
            self.duracion_semanas = self.DURACION_MINIMA_SEMANAS
        if self.fecha_inicio and self.duracion_semanas:
            self.fecha_fin = self.fecha_inicio + timedelta(weeks=self.duracion_semanas) - timedelta(days=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contrato.cliente} - {self.servicio} - {self.profesional}"


class Ingreso(models.Model):
    """
    Resumen semanal (lunes a domingo) de lo efectivamente trabajado y
    cobrable para un AcuerdoServicio: se genera solo a partir de los Turno
    con horas_reales registradas (ver generar_ingresos_semana en
    services.py). fecha es el lunes de esa semana; periodo_fin el domingo
    (o la fecha_fin del acuerdo si cae antes).
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('facturado', 'Facturado'),
        ('pagado', 'Pagado'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='ingresos')
    empleado = models.ForeignKey('empleados.Empleado', on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    acuerdo_servicio = models.ForeignKey(AcuerdoServicio, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ingresos',
        help_text="Acuerdo de servicio del que se genero este ingreso (vacio en ingresos cargados a mano)")
    fecha = models.DateField(help_text="Inicio del periodo que resume este ingreso (lunes, si se genero automaticamente)")
    periodo_fin = models.DateField(null=True, blank=True,
        help_text="Fin del periodo que resume este ingreso (domingo). Vacio en ingresos cargados a mano")
    horas = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    cobrado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    iva_monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    base_real = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pago_empleado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='pendiente')
    factura = models.ForeignKey('finanzas.Factura', on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='ingresos')
    notas = models.TextField(blank=True)

    class Meta:
        unique_together = ('acuerdo_servicio', 'fecha')

    def save(self, *args, **kwargs):
        # Todo el dinero se recalcula en cada save() a partir de `horas`.
        # Volver a guardar un Ingreso viejo lo recalcula con las tarifas,
        # el IVA y la compensacion ACTUALES -- ojo con hacer save() masivo
        # sobre ingresos historicos.
        if self.horas and self.servicio_id and self.cliente_id:
            self.iva_porcentaje = self.cliente.iva_porcentaje
            base = self.horas * self.servicio.tarifa_cliente
            self.iva_monto = round(base * self.iva_porcentaje / Decimal('100'), 2)
            self.cobrado = base + self.iva_monto
            self.base_real = base

            # Misma formula que empleados.services.calcular_pago_profesional,
            # aplicada aca sobre el total semanal a nombre del titular del
            # acuerdo (acuerdo.profesional) -- duplicada a proposito, igual
            # que en el original: si esta formula cambia, hay que actualizar
            # los dos lugares.
            if self.servicio.compensacion_tipo == 'porcentaje_base':
                self.pago_empleado = round(self.base_real * self.servicio.compensacion_valor / Decimal('100'), 2)
            else:
                self.pago_empleado = round(self.horas * self.servicio.compensacion_valor, 2)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cliente} - {self.servicio} - {self.fecha}"


# Modulo de Auditoria (ver accounts/views.py). Se registran Contrato y
# AcuerdoServicio: son los que justifican saber quien y cuando modifico un
# contrato o alguno de sus servicios contratados.
from auditlog.registry import auditlog

auditlog.register(Contrato)
auditlog.register(AcuerdoServicio)
