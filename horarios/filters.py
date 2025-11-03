import django_filters
from .models import AsignacionHorario

class AsignacionHorarioFilter(django_filters.FilterSet):
    """
    Filtro para las asignaciones de horarios.
    Permite filtrar por empleado y por horario (turno).
    """
    class Meta:
        model = AsignacionHorario
        fields = {
            'id_empl': ['exact'],
            'id_horario': ['exact'],
        }

