from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Rol y perfil', {'fields': ('rol', 'nif', 'direccion', 'nacionalidad', 'foto')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Rol y perfil', {'fields': ('rol',)}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'rol', 'is_staff']


admin.site.register(Usuario, UsuarioAdmin)
