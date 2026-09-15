from django.contrib import admin

from .models import Factura, PagoEmpleado, TareaCobro, TareaRecurrente


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'importe', 'estado', 'creado_en']
    list_filter = ['estado']


admin.site.register(PagoEmpleado)
admin.site.register(TareaCobro)
admin.site.register(TareaRecurrente)
