from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReciboSueldosViewSet, MisRecibosView, RecibosPorDNIView

router = DefaultRouter()
router.register(r'recibos', ReciboSueldosViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Endpoint para que un empleado vea sus propios recibos
    path('mis-recibos/', MisRecibosView.as_view(), name='mis-recibos'),
    # Endpoint para que un admin/consultor busque recibos por DNI de empleado
    path('recibos/por-dni/<str:dni>/', RecibosPorDNIView.as_view(), name='recibos-por-dni'),
]