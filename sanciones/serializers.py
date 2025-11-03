from rest_framework import serializers
from .models import Sancion, SancionEmpleado
from empleados.models import Empleado
from empleados.serializer import EmpleadoSerializer

class SancionSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Sancion.
    Se usa principalmente para consulta, ya que las sanciones se precargan.
    """
    class Meta:
        model = Sancion
        fields = '__all__'

class SancionEmpleadoSerializer(serializers.ModelSerializer):
    """
    Serializer para gestionar las sanciones de los empleados.
    """
    # Relaciones de solo lectura para la representación
    id_empl = EmpleadoSerializer(read_only=True)
    id_sancion = SancionSerializer(read_only=True)
    responsable = EmpleadoSerializer(read_only=True)

    # Campos de solo escritura para la creación
    empleado_id = serializers.PrimaryKeyRelatedField(queryset=Empleado.objects.all(), source='id_empl', write_only=True)
    sancion_id = serializers.PrimaryKeyRelatedField(queryset=Sancion.objects.all(), source='id_sancion', write_only=True)

    class Meta:
        model = SancionEmpleado
        fields = ['id', 'id_empl', 'id_sancion', 'incidente_asociado', 'fecha_sancion', 'fecha_inicio', 'fecha_fin', 'motivo', 'responsable', 'empleado_id', 'sancion_id']
        read_only_fields = ('fecha_sancion', 'responsable')