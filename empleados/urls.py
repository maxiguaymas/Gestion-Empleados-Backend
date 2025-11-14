from django.urls import path, include
from rest_framework import routers
from .views import EmpleadoViewSet, LegajoViewSet, DocumentoViewSet, RequisitoDocumentoViewSet, EmpleadoBasicoViewSet

router = routers.DefaultRouter()
router.register(r'empleados', EmpleadoViewSet)
router.register(r'empleados-basico', EmpleadoBasicoViewSet, basename='empleado-basico')
router.register(r'legajos', LegajoViewSet)
router.register(r'documentos', DocumentoViewSet)
router.register(r'requisitos', RequisitoDocumentoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]