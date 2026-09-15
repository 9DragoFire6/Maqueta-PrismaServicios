from django.db import models


class Empleado(models.Model):
    """
    Version minima, solo para que Servicio/AcuerdoServicio (Fase 2) tengan a
    quien asignar un servicio contratado. La Fase 3 completa este modelo con
    Turno, Ausencia, SolicitudAusencia, datos personales cifrados y el
    vinculo con Usuario -- sobre esta misma tabla, sin recrearla.
    """
    nombre = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    # Debe calzar con Servicio.categoria: un servicio de una categoria solo
    # puede prestarlo un empleado de esa misma categoria (ver
    # AcuerdoServicio.clean() en clientes/models.py). Reemplaza la regla fija
    # founder/colaboradora del original por una categoria libre y
    # configurable.
    categoria = models.CharField(max_length=30, default='estandar')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
