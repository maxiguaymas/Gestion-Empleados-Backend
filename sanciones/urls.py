from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SancionViewSet, SancionEmpleadoViewSet

router = DefaultRouter()
router.register(r'sanciones', SancionViewSet)
router.register(r'sanciones-empleados', SancionEmpleadoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]