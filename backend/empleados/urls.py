from rest_framework.routers import DefaultRouter

from .views import AusenciaViewSet, EmpleadoViewSet, SolicitudAusenciaViewSet, TurnoViewSet

router = DefaultRouter()
router.register(r'empleados', EmpleadoViewSet, basename='empleado')
router.register(r'turnos', TurnoViewSet, basename='turno')
router.register(r'ausencias', AusenciaViewSet, basename='ausencia')
router.register(r'solicitudes-ausencia', SolicitudAusenciaViewSet, basename='solicitud-ausencia')

urlpatterns = router.urls
