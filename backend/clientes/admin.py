from django.contrib import admin

from .models import AcuerdoServicio, Cliente, Contrato, Ingreso, Servicio


class AcuerdoServicioInline(admin.TabularInline):
    model = AcuerdoServicio
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre_contacto', 'nif', 'activa', 'creada_en']
    search_fields = ['nombre_contacto', 'nif']


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'categoria', 'tarifa_cliente', 'compensacion_tipo', 'compensacion_valor', 'activo']
    list_editable = ['activo']


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'estado', 'creado_en']
    list_filter = ['estado']
    inlines = [AcuerdoServicioInline]


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'servicio', 'empleado', 'fecha', 'horas', 'cobrado', 'estado']
    list_filter = ['estado']
