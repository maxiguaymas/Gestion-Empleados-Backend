from rest_framework import serializers
from .models import Horarios, AsignacionHorario
from empleados.serializer import EmpleadoSerializer
from empleados.models import Empleado

class HorarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo de Horarios (turnos).
    """
    class Meta:
        model = Horarios
        fields = '__all__'

class AsignacionHorarioDetalleSerializer(serializers.Serializer):
    """
    Serializer para la vista agrupada de asignaciones.
    Muestra un horario y la lista de empleados asignados a él.
    """
    horario = HorarioSerializer()
    empleados_asignados = EmpleadoSerializer(many=True)


class AsignacionHorarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo de AsignacionHorario.
    """
    # Campo de solo escritura para recibir una lista de IDs de empleados
    empleado_ids = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all(), 
        write_only=True, 
        many=True,
        help_text="Lista de IDs de empleados a asignar al horario."
    )

    class Meta:
        model = AsignacionHorario
        fields = ['id', 'id_horario', 'fecha_asignacion', 'estado', 'empleado_ids']
        read_only_fields = ('fecha_asignacion',)

    def validate(self, data):
        """
        Valida que el número de empleados a asignar no exceda la capacidad del horario.
        """
        horario = data.get('id_horario')
        empleados_a_asignar = data.get('empleado_ids')
        
        if not horario or not empleados_a_asignar:
            return data # La validación de campos requeridos se hace antes

        # 1. Validar que los empleados no estén ya asignados a este horario.
        empleados_duplicados = AsignacionHorario.objects.filter(
            id_horario=horario,
            id_empl__in=empleados_a_asignar,
            estado=True
        ).values_list('id_empl__nombre', 'id_empl__apellido')

        if empleados_duplicados:
            nombres_duplicados = [f"{nombre} {apellido}" for nombre, apellido in empleados_duplicados]
            raise serializers.ValidationError(f"Los siguientes empleados ya están asignados a este horario: {', '.join(nombres_duplicados)}.")

        # 2. Validar capacidad del horario.
        capacidad_maxima = horario.cantidad_personal_requerida
        # Contamos las asignaciones activas existentes para este horario
        asignados_actualmente = AsignacionHorario.objects.filter(id_horario=horario, estado=True).count()
        
        if (asignados_actualmente + len(empleados_a_asignar)) > capacidad_maxima:
            disponibles = capacidad_maxima - asignados_actualmente
            raise serializers.ValidationError(
                f"No se pueden asignar {len(empleados_a_asignar)} empleados. El horario '{horario.nombre}' "
                f"tiene una capacidad de {capacidad_maxima} y ya hay {asignados_actualmente} asignados. "
                f"Solo puede asignar {disponibles} más."
            )
        return data