from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IncidenteViewSet, IncidenteEmpleadoViewSet, DescargoViewSet, ResolucionViewSet, GrupoIncidenteViewSet

# Se crea un router para registrar los ViewSets
router = DefaultRouter()

# Se registran los endpoints para cada modelo del CRUD de incidentes
router.register(r'incidentes', IncidenteViewSet)
router.register(r'incidentes-agrupados', GrupoIncidenteViewSet, basename='incidentes-agrupados')
router.register(r'incidente-empleado', IncidenteEmpleadoViewSet)
router.register(r'descargos', DescargoViewSet)
router.register(r'resoluciones', ResolucionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]