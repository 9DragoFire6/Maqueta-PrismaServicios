from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FacturaViewSet,
    PagoEmpleadoViewSet,
    TareaCobroViewSet,
    TareaRecurrenteViewSet,
    enviar_cliente_view,
    enviar_contador_view,
    solicitar_facturas_pendientes_view,
    tareas_hoy,
)

router = DefaultRouter()
router.register(r'facturas', FacturaViewSet)
router.register(r'pagos-empleado', PagoEmpleadoViewSet)
router.register(r'tareas', TareaRecurrenteViewSet)
router.register(r'tareas-cobro', TareaCobroViewSet, basename='tareacobro')

urlpatterns = [
    # Va antes que router.urls: "solicitar-pendientes" tiene la misma forma
    # que facturas/<pk>/ -- si fuera despues, el router la interpretaria
    # como un pk y devolveria 405 en vez de llegar a esta vista.
    path('facturas/solicitar-pendientes/', solicitar_facturas_pendientes_view, name='solicitar-facturas-pendientes'),
] + router.urls + [
    path('facturas/<int:factura_id>/enviar-contador/', enviar_contador_view, name='enviar-contador'),
    path('facturas/<int:factura_id>/enviar-cliente/', enviar_cliente_view, name='enviar-cliente'),
    path('tareas/hoy/', tareas_hoy, name='tareas-hoy'),
]
