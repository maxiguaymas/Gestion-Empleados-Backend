from rest_framework import serializers
from .models import Sancion, SancionEmpleado
from empleados.models import Empleado
from empleados.serializer import EmpleadoBasicoSerializer
from incidentes.models import IncidenteEmpleado


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
    id_empl = EmpleadoBasicoSerializer(read_only=True)
    id_sancion = SancionSerializer(read_only=True)
    responsable = EmpleadoBasicoSerializer(read_only=True)

    # Campos de solo escritura para la creación
    empleado_id = serializers.PrimaryKeyRelatedField(queryset=Empleado.objects.all(), source='id_empl', write_only=True)
    sancion_id = serializers.PrimaryKeyRelatedField(queryset=Sancion.objects.all(), source='id_sancion', write_only=True)
    grupo_incidente = serializers.UUIDField(write_only=True, required=False, allow_null=True, help_text="UUID del grupo de incidentes para asociar a la sanción.")

    class Meta:
        model = SancionEmpleado
        fields = ['id', 'id_empl', 'id_sancion', 'incidente_asociado', 'fecha_sancion', 'fecha_inicio', 'fecha_fin', 'motivo', 'responsable', 'empleado_id', 'sancion_id', 'grupo_incidente']
        read_only_fields = ('fecha_sancion', 'responsable', 'incidente_asociado')

    def create(self, validated_data):
        grupo_incidente = validated_data.pop('grupo_incidente', None)
        incidente_asociado_instance = None
        if grupo_incidente:
            incidente_asociado_instance = IncidenteEmpleado.objects.filter(grupo_incidente=grupo_incidente).first()
        
        sancion_empleado = SancionEmpleado.objects.create(incidente_asociado=incidente_asociado_instance, **validated_data)
        return sancion_empleado