from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SancionViewSet, SancionEmpleadoViewSet, MisSancionesView

router = DefaultRouter()
router.register(r'sanciones', SancionViewSet)
router.register(r'sanciones-empleados', SancionEmpleadoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('mis-sanciones/', MisSancionesView.as_view(), name='mis-sanciones'),
]