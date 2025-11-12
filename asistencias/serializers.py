from rest_framework import serializers
from .models import Asistencia, Rostro
from empleados.serializer import EmpleadoSerializer

class RostroSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Rostro.
    """
    # Usamos el serializer de Empleado para mostrar los detalles del empleado asociado.
    id_empl = EmpleadoSerializer(read_only=True)
    class Meta:
        model = Rostro
        # El encoding no se expone por seguridad y tamaño.
        fields = ['id_empl']

class AsistenciaSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Asistencia.
    """
    class Meta:
        model = Asistencia
        fields = ['id', 'id_empl', 'fecha_hora', 'minutos_retraso']
        read_only_fields = ('fecha_hora', 'minutos_retraso')