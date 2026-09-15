from django.core.exceptions import ValidationError

MB = 1024 * 1024
TAMANO_MAXIMO_ARCHIVO = 10 * MB


def validar_tamano_archivo(archivo):
    """Validador reutilizable para FileField/ImageField: rechaza archivos que
    superen TAMANO_MAXIMO_ARCHIVO."""
    if archivo and archivo.size > TAMANO_MAXIMO_ARCHIVO:
        limite_mb = TAMANO_MAXIMO_ARCHIVO // MB
        peso_mb = archivo.size / MB
        raise ValidationError(
            f"El archivo pesa {peso_mb:.1f} MB. El máximo permitido es {limite_mb} MB."
        )
