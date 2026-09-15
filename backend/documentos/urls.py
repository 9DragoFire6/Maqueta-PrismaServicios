from django.urls import path

from . import views

urlpatterns = [
    path('contratos/<int:contrato_id>/pdf/', views.pdf_contrato, name='pdf-contrato'),
    path('plantilla-clausulas/', views.plantilla_clausulas, name='plantilla-clausulas'),
]
