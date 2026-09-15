from django.contrib.auth.models import AbstractUser
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField

from gestion_servicios.validators import validar_tamano_archivo
from gestion_servicios.storage_utils import borrar_archivos_reemplazados


class Usuario(AbstractUser):
    # Dos roles alcanzan para mostrar el sistema de permisos: 'admin'
    # (dueño/gerente del negocio, acceso total) y 'empleado' (personal
    # operativo, ver accounts/permissions.py para el detalle de que puede
    # hacer cada uno).
    ROL_CHOICES = [
        ('admin', 'Administrador/a'),
        ('empleado', 'Empleado/a'),
    ]
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='admin')
    email = models.EmailField(unique=True)

    # Datos personales identificables: cifrados en la base de datos (ver
    # FIELD_ENCRYPTION_KEY en settings). El nombre y el email quedan en
    # claro porque Django los necesita para autenticar/mostrar en listas.
    nif = EncryptedCharField(max_length=50, blank=True)
    direccion = EncryptedTextField(blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True)

    foto = models.ImageField(upload_to='usuarios/', null=True, blank=True, validators=[validar_tamano_archivo])

    def save(self, *args, **kwargs):
        borrar_archivos_reemplazados(self, ['foto'])
        super().save(*args, **kwargs)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} ({self.rol})"
