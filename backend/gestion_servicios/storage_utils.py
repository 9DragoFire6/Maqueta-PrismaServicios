def borrar_archivos_reemplazados(instance, campos):
    """Si la instancia ya existia en la base de datos y alguno de los
    campos de archivo indicados en `campos` cambio de valor, borra del
    almacenamiento el archivo ANTERIOR de ese campo en ESA instancia
    especifica.

    Se llama al inicio de save(), antes de super().save(). Evita que se
    acumulen copias huerfanas cada vez que se reemplaza un archivo (ej.
    subir una foto de perfil nueva encima de una ya subida).
    """
    if not instance.pk:
        return  # objeto nuevo: no puede haber un archivo anterior que borrar
    try:
        anterior = type(instance).objects.get(pk=instance.pk)
    except type(instance).DoesNotExist:
        return
    for campo in campos:
        archivo_anterior = getattr(anterior, campo)
        archivo_nuevo = getattr(instance, campo)
        if archivo_anterior and archivo_anterior.name != archivo_nuevo.name:
            archivo_anterior.delete(save=False)
