from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HorarioViewSet, AsignacionHorarioViewSet

router = DefaultRouter()
router.register(r'horarios', HorarioViewSet) # Registra el ViewSet para los turnos
router.register(r'asignacion-horario', AsignacionHorarioViewSet) # Registra el ViewSet para las asignaciones

urlpatterns = [
    path('', include(router.urls)),
]
