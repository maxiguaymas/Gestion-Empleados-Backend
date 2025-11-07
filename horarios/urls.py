from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HorarioViewSet, AsignacionHorarioViewSet, MisHorariosView

router = DefaultRouter()
router.register(r'horarios', HorarioViewSet) # Registra el ViewSet para los turnos
router.register(r'asignacion-horario', AsignacionHorarioViewSet) # Registra el ViewSet para las asignaciones

urlpatterns = [
    path('mis-horarios/', MisHorariosView.as_view(), name='mis-horarios'),
    path('', include(router.urls)),
]
