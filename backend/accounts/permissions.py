from rest_framework.permissions import BasePermission

# Roles con acceso administrativo total.
ROLES_NIVEL_ADMIN = ['admin']

# Personal operativo (agenda propia, sin acceso a gestión de usuarios ni
# finanzas globales).
ROLES_EMPLEADO = ['empleado']


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol in ROLES_NIVEL_ADMIN


class EsAdminOEmpleado(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol in ROLES_NIVEL_ADMIN + ROLES_EMPLEADO


class EsEmpleado(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol in ROLES_EMPLEADO
