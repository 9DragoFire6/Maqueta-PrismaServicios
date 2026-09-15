from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts import views

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/2fa/setup/', views.setup_2fa, name='setup-2fa'),
    path('auth/2fa/verificar/', views.verificar_2fa, name='verificar-2fa'),
    path('auth/2fa/validar/', views.validar_2fa, name='validar-2fa'),
    path('auth/2fa/estado/', views.estado_2fa, name='estado-2fa'),
    path('auth/verificar-password/', views.verificar_password, name='verificar-password'),
    path('auth/perfil/', views.perfil, name='perfil'),
    path('auth/cambiar-password/', views.cambiar_password, name='cambiar-password'),
    path('auth/solicitar-recuperacion/', views.solicitar_recuperacion, name='solicitar-recuperacion'),
    path('auth/restablecer-password/', views.restablecer_password, name='restablecer-password'),
    path('auth/verificar-username/', views.verificar_username, name='verificar-username'),
    path('auth/usuarios/', views.lista_usuarios, name='lista-usuarios'),
    path('auth/usuarios/<int:usuario_id>/', views.usuario_detalle, name='usuario-detalle'),
    path('auth/crear-usuario/', views.crear_usuario, name='crear-usuario'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/mensual/', views.dashboard_mensual, name='dashboard-mensual'),
]
