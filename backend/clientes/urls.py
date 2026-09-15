from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ClienteViewSet,
    ContratoViewSet,
    ServicioViewSet,
    anonimizar_datos_cliente,
    exportar_datos_cliente,
)

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'contratos', ContratoViewSet)
router.register(r'servicios', ServicioViewSet)

urlpatterns = router.urls + [
    path('clientes/<int:pk>/exportar-datos/', exportar_datos_cliente, name='exportar-datos-cliente'),
    path('clientes/<int:pk>/anonimizar-datos/', anonimizar_datos_cliente, name='anonimizar-datos-cliente'),
]
