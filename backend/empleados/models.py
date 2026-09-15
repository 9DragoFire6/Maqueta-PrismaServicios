import random
from datetime import datetime, timedelta

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedDateField

from gestion_servicios.storage_utils import borrar_archivos_reemplazados
from gestion_servicios.validators import validar_tamano_archivo

PALETA_COLORES = [
    "#2563eb", "#16a361", "#b45309", "#6d5cdb", "#c44a20", "#0e7047",
    "#db2777", "#0891b2", "#7c3aed", "#65a30d",
]


class Empleado(models.Model):
    usuario = models.OneToOneField(
        'accounts.Usuario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='empleado_perfil',
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    nif = models.CharField(max_length=50, blank=True)
    direccion = models.TextField(blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True)
    fecha_nacimiento = EncryptedDateField(null=True, blank=True)
    numero_documento = EncryptedCharField(max_length=50, blank=True,
        help_text="DNI/pasaporte u otro documento de identidad")
    foto = models.ImageField(upload_to='empleados/', null=True, blank=True, validators=[validar_tamano_archivo])
    especialidad = models.CharField(max_length=100, blank=True)
    # Debe calzar con Servicio.categoria: ver clientes/models.py AcuerdoServicio.clean().
    categoria = models.CharField(max_length=30, default='estandar')
    color = models.CharField(max_length=7, blank=True,
        help_text="Color hexadecimal para diferenciarlo en el Calendario. Se asigna solo si se deja vacio")
    activo = models.BooleanField(default=True)
    fecha_alta = models.DateField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        borrar_archivos_reemplazados(self, ['foto'])
        if not self.color:
            usados = set(
                Empleado.objects.exclude(pk=self.pk).exclude(color='').values_list('color', flat=True)
            )
            disponibles = [c for c in PALETA_COLORES if c not in usados]
            self.color = disponibles[0] if disponibles else "#%06x" % random.randint(0, 0xFFFFFF)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} {self.apellido}".strip()


class Turno(models.Model):
    """
    Una ocurrencia concreta de un turno, en una fecha real (no un patron
    recurrente). hora_inicio/hora_fin son el horario programado; si
    hora_fin <= hora_inicio, se asume que el turno cruza la medianoche
    (termina al dia siguiente). horas_reales se registra despues, cuando el
    empleado efectivamente trabaja el turno, y puede ser distinto a lo
    programado.
    """
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='turnos')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE)
    acuerdo_servicio = models.ForeignKey('clientes.AcuerdoServicio', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='turnos',
        help_text="Acuerdo de servicio del que proviene este turno (vacio para turnos creados manualmente)")
    fecha = models.DateField(help_text="Fecha real en la que comienza el turno")
    hora_inicio = models.TimeField(help_text="Hora programada de inicio")
    hora_fin = models.TimeField(help_text="Hora programada de fin. Si es menor o igual a hora_inicio, se asume que cruza la medianoche")
    horas_reales = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Horas realmente trabajadas. Vacio hasta que el empleado las registre")
    activo = models.BooleanField(default=True)

    MARCAS = [
        ('ausencia_automatica', 'Ausencia'),
        ('autorizado', 'Autorizado'),
    ]
    marca = models.CharField(max_length=20, choices=MARCAS, blank=True,
        help_text="Texto adicional que muestra el Calendario para este turno (ver "
                   "empleados/services.py:detectar_ausencias_automaticas). Se limpia solo "
                   "al registrar horas_reales de nuevo.")

    confirmado_por_empleado = models.BooleanField(default=False,
        help_text="True si quien registro horas_reales fue el propio empleado (no un admin, ni "
                   "la deteccion automatica). Una vez en True, el empleado ya no puede volver a "
                   "editar horas_reales el mismo -- solo un admin, o via una SolicitudAusencia "
                   "procesada.")

    modificado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='turnos_modificados',
        help_text="Ultimo admin que registro/corrigio horas_reales sobre este turno. No se toca "
                   "cuando quien registra es el propio empleado.")

    @property
    def cruza_medianoche(self):
        return self.hora_fin <= self.hora_inicio

    @property
    def datetime_inicio(self):
        return datetime.combine(self.fecha, self.hora_inicio)

    @property
    def datetime_fin_programado(self):
        fin = datetime.combine(self.fecha, self.hora_fin)
        if self.cruza_medianoche:
            fin += timedelta(days=1)
        return fin

    @property
    def datetime_fin_real(self):
        if self.horas_reales is not None:
            return self.datetime_inicio + timedelta(hours=float(self.horas_reales))
        return self.datetime_fin_programado

    def __str__(self):
        return f"{self.empleado} - {self.fecha}"


class Ausencia(models.Model):
    """
    Registro de que un empleado no cubrio (o no va a cubrir) un rango de
    fechas, opcionalmente con quien lo sustituyo. Es deliberadamente simple:
    un registro, no un motor -- no reasigna los Turno del periodo (ver
    services.payee_de_turno para quien cobra cada turno ya trabajado).
    """
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='ausencias')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    motivo = models.CharField(max_length=200)
    sustituto = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='sustituciones')
    creada_en = models.DateTimeField(auto_now_add=True,
        help_text="Se usa para correr el plazo de HORAS_PLAZO_REGISTRO horas cuando una "
                   "sustitucion se arma DESPUES de que el turno ya vencio -- ver "
                   "empleados/services.py:_inicio_plazo.")
    acuerdo_servicio = models.ForeignKey('clientes.AcuerdoServicio', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ausencias',
        help_text="Solo para reasignacion extendida: identifica a que contrato/servicio puntual "
                   "corresponde esta Ausencia. Vacio en el caso puntual de siempre.")

    def __str__(self):
        return f"{self.empleado} - {self.fecha_inicio}"


class SolicitudAusencia(models.Model):
    TIPOS = [
        ('mal_ingresada', 'Ausencia mal ingresada'),
        ('permiso', 'Permiso de ausencia'),
        # No depende de que exista una Ausencia: cubre el caso de un empleado
        # que trabajo y registro a tiempo, pero se equivoco al tipear.
        ('correccion_horas', 'Corrección de horas trabajadas'),
        # Cubre cualquier caso de 2 dias o mas -- nunca 1 solo dia, eso sigue
        # siendo sustitucion/permiso puntual. No depende de que exista ya una
        # Ausencia ni un Turno puntual: propone sus propios datos.
        ('reasignacion_extendida', 'Reasignación extendida'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        # La etiqueta es "Procesada" (no "Resuelta"): da igual por cual de
        # las 3 RESOLUCIONES se llegue, el estado visible es uniforme.
        ('resuelta', 'Procesada'),
    ]
    RESOLUCIONES = [
        ('aceptada', 'Aceptada tal cual'),
        ('rechazada', 'Rechazada'),
        ('corregida', 'Corregida con otro valor'),
    ]

    # Opcional segun el tipo: 'correccion_horas' cuelga de un Turno, el resto
    # de una Ausencia. La validacion de cual corresponde segun el tipo vive
    # en el serializer (DRF no llama a Model.clean() al guardar desde la API).
    ausencia = models.ForeignKey(Ausencia, on_delete=models.CASCADE, related_name='solicitudes',
        null=True, blank=True)
    turno = models.ForeignKey('Turno', on_delete=models.CASCADE, related_name='solicitudes_correccion',
        null=True, blank=True,
        help_text="Solo para tipo='correccion_horas': el turno puntual al que aplica.")
    solicitante = models.ForeignKey('accounts.Usuario', on_delete=models.CASCADE, related_name='solicitudes_ausencia')
    tipo = models.CharField(max_length=25, choices=TIPOS)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    creada_en = models.DateTimeField(auto_now_add=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)

    resolucion = models.CharField(max_length=20, choices=RESOLUCIONES, blank=True)
    resuelta_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_resueltas')
    nota_resolucion = models.TextField(blank=True,
        help_text="Nota libre del admin al procesar (ej. que se corrigio distinto de lo pedido, o por que se rechazo)")

    motivo = models.TextField(blank=True)

    # Campos para tipo 'permiso'
    admin_autoriza = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='permisos_autorizados')
    titulo_permiso = models.CharField(max_length=200, blank=True)
    descripcion_permiso = models.TextField(blank=True)
    respaldo_permiso = models.FileField(upload_to='permisos/', null=True, blank=True, validators=[validar_tamano_archivo])

    # Campos para tipo 'reasignacion_extendida' -- la Ausencia todavia no
    # existe, esta solicitud PROPONE los datos con los que se va a crear si
    # se acepta o se corrige.
    empleado_afectado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reasignaciones_propuestas',
        help_text="El empleado titular al que se le reasignan estos dias.")
    acuerdo_servicio = models.ForeignKey('clientes.AcuerdoServicio', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_reasignacion',
        help_text="A que contrato/servicio puntual de empleado_afectado corresponde -- pasa "
                   "directo a Ausencia.acuerdo_servicio si se acepta o se corrige.")
    fecha_inicio_reasignacion = models.DateField(null=True, blank=True)
    fecha_fin_reasignacion = models.DateField(null=True, blank=True)
    sustituto_reasignacion = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reasignaciones_como_sustituto',
        help_text="Si se indica, la ruta es sustitucion (otro empleado cubre). Vacio: ruta "
                   "permiso (el titular no trabaja esos dias, con o sin paga).")

    def save(self, *args, **kwargs):
        borrar_archivos_reemplazados(self, ['respaldo_permiso'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Solicitud {self.tipo} — {self.solicitante} — {self.estado}"


class Recibo(models.Model):
    """
    Cuanto se le debe a un empleado por un servicio especifico prestado a un
    cliente (tarifa empleado, no tarifa cliente). Se genera solo, junto con
    su Ingreso correspondiente (ver clientes.services.generar_ingresos_semana)
    -- uno por servicio/semana Y por empleado que la haya trabajado, para
    que cada uno se pueda pagar y respaldar por separado en Pagos.

    ingreso y servicio quedan en SET_NULL (no CASCADE) a proposito: si el
    Ingreso que le dio origen se llegara a borrar, el Recibo (y su
    PagoEmpleado con su comprobante, si ya se pago) se conservan como
    historial real de pago al empleado.

    ingreso es ForeignKey (no OneToOneField): si una semana se reparte entre
    el titular del AcuerdoServicio y quien lo sustituyo, puede haber mas de
    un Recibo para el mismo Ingreso.
    """
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='recibos')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE)
    servicio = models.ForeignKey('clientes.Servicio', on_delete=models.SET_NULL, null=True, blank=True)
    ingreso = models.ForeignKey('clientes.Ingreso', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recibos')
    fecha = models.DateField()
    horas = models.DecimalField(max_digits=5, decimal_places=1)
    importe = models.DecimalField(max_digits=8, decimal_places=2)
    concepto = models.CharField(max_length=200)
    pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.empleado} - {self.fecha}"
