from django.contrib import admin

from .models import Ausencia, Empleado, Recibo, SolicitudAusencia, Turno


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'categoria', 'especialidad', 'telefono', 'email', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['nombre', 'apellido', 'email']


admin.site.register(Turno)
admin.site.register(Ausencia)
admin.site.register(SolicitudAusencia)
admin.site.register(Recibo)
