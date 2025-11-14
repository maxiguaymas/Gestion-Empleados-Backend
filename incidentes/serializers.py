from empleados.models import Empleado
from rest_framework import serializers
import uuid
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from notificaciones.models import Notificacion
from .models import Incidente, IncidenteEmpleado, Descargo, Resolucion
from empleados.serializer import EmpleadoSerializer

class EmpleadoBasicoSerializer(serializers.ModelSerializer):
    """Serializer básico para mostrar solo información esencial del empleado."""
    class Meta:
        model = Empleado
        fields = ['id', 'nombre', 'apellido', 'dni']

logger = logging.getLogger(__name__)

class IncidenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incidente
        fields = '__all__'

class DescargoGrupoSerializer(serializers.ModelSerializer):
    """Serializer para descargos dentro de un grupo, con datos básicos del autor."""
    autor = EmpleadoBasicoSerializer(read_only=True)
    class Meta:
        model = Descargo
        fields = ['id', 'autor', 'fecha_descargo', 'contenido_descargo']

class DescargoSerializer(serializers.ModelSerializer):
    autor = EmpleadoSerializer(read_only=True)
    class Meta:
        model = Descargo
        fields = ['id', 'id_incid_empl', 'autor', 'fecha_descargo', 'contenido_descargo', 'ruta_archivo_descargo', 'estado']
        read_only_fields = ('fecha_descargo', 'autor')

class IncidenteEmpleadoSerializer(serializers.ModelSerializer):
    # Usamos representaciones de solo lectura para las relaciones anidadas
    id_incidente = IncidenteSerializer(read_only=True)
    id_empl = EmpleadoSerializer(read_only=True)
    responsable_registro = EmpleadoBasicoSerializer(read_only=True)
    descargos = DescargoSerializer(many=True, read_only=True)

    # Campos de solo escritura para la creación y actualización
    incidente_id = serializers.PrimaryKeyRelatedField(
        queryset=Incidente.objects.all(), source='id_incidente', write_only=True
    )
    empleado_ids = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all(), write_only=True, many=True
    )

    class Meta:
        model = IncidenteEmpleado
        fields = [
            'id', 'grupo_incidente', 'id_incidente', 'id_empl', 'fecha_ocurrencia',
            'descripcion', 'observaciones', 'responsable_registro', 'estado', 'resolucion',
            'descargos', 'resolucion', 'incidente_id', 'empleado_ids'
        ]
        read_only_fields = ('estado',)

    def to_representation(self, instance):
        """
        Asegura que los campos de solo escritura no aparezcan en la respuesta.
        """
        ret = super().to_representation(instance)
        ret.pop('incidente_id', None)
        # No es necesario hacer pop de 'empleado_ids' porque no está en el modelo y no se incluirá por defecto.
        return ret

    def create(self, validated_data):
        """
        Crea múltiples instancias de IncidenteEmpleado, una para cada empleado_id.
        """
        request = self.context.get('request')
        empleado_responsable = None
        if request and hasattr(request, "user"):
            try:
                # Buscamos el empleado que está registrando el incidente
                empleado_responsable = Empleado.objects.get(user=request.user)
            except Empleado.DoesNotExist:
                # Si el usuario no tiene un perfil de empleado (ej. superadmin),
                # el responsable quedará como null, según lo permite el modelo.
                pass

        empleados = validated_data.pop('empleado_ids')
        incidente = validated_data.get('id_incidente')
        fecha_ocurrencia = validated_data.get('fecha_ocurrencia')
        descripcion = validated_data.get('descripcion')
        observaciones = validated_data.get('observaciones')
        grupo_id = uuid.uuid4() # Generamos un único ID para este lote
        
        # Eliminamos la clave 'id_incidente' de validated_data para evitar el TypeError
        validated_data.pop('id_incidente', None)

        validated_data['responsable_registro'] = empleado_responsable

        incidentes_creados = []
        for empleado in empleados:
            # 1. Creamos la instancia de IncidenteEmpleado
            incidente_empleado = IncidenteEmpleado.objects.create(
                grupo_incidente=grupo_id,
                id_incidente=incidente,
                id_empl=empleado,
                **validated_data
            )
            incidentes_creados.append(incidente_empleado)

            # 2. Creamos la notificación para el empleado involucrado
            enlace_incidente = f"/incidentes/detalle/{grupo_id}/"
            mensaje = f"Has sido involucrado en un nuevo incidente: {incidente.tipo_incid}."
            Notificacion.objects.create(
                id_user=empleado.user,
                mensaje=mensaje,
                enlace=enlace_incidente
            )

            # 3. Enviar correo electrónico de notificación
            if empleado.email:
                try:
                    logger.info(f"Intentando enviar correo de incidente a: {empleado.email}")
                    request = self.context.get('request')
                    if request:
                        host = request.get_host()
                        protocol = 'https' if request.is_secure() else 'http'
                        detalle_url = f"{protocol}://{host.split(':')[0]}{enlace_incidente}"
                    else:
                        detalle_url = "Por favor, accede al portal para ver los detalles."

                    asunto = f"Notificación de Incidente: {incidente.tipo_incid}"

                    # Renderizar el template HTML
                    cuerpo_mensaje_html = render_to_string('email/notificacion_incidente.html', {
                        'empleado_nombre': empleado.nombre,
                        'incidente_tipo': incidente.tipo_incid,
                        'fecha_ocurrencia': fecha_ocurrencia.strftime('%d/%m/%Y'),
                        'descripcion': descripcion,
                        'detalle_url': detalle_url,
                    })
                    send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [empleado.email], html_message=cuerpo_mensaje_html)
                    logger.info(f"Correo de incidente enviado exitosamente a {empleado.email}")
                except Exception as e:
                    logger.error(f"ERROR al enviar correo de incidente a {empleado.email}: {e}")
        
        # Devolvemos la primera instancia creada como representación, o podrías devolver una lista.
        return incidentes_creados[0]

class ResolucionSerializer(serializers.ModelSerializer):
    responsable = EmpleadoSerializer(read_only=True)
    incidentes_asociados = IncidenteEmpleadoSerializer(many=True, read_only=True, source='get_incidentes_asociados')

    class Meta:
        model = Resolucion
        fields = [
            'id', 
            'grupo_incidente', 
            'fecha_resolucion', 
            'descripcion', 'responsable', 'estado',
            'incidentes_asociados'
        ]
        read_only_fields = ('fecha_resolucion', 'responsable')

    def create(self, validated_data):
        """
        Al crear una resolución, se actualiza el estado del IncidenteEmpleado a 'CERRADO'.
        La lógica está en el método save() del modelo Resolucion, pero lo llamamos desde aquí.
        """
        # 1. Creamos la resolución. El método save() del modelo se encargará de cerrar los incidentes.
        resolucion = Resolucion.objects.create(**validated_data)
        
        # 2. Obtenemos el grupo de incidentes para buscar a los empleados.
        grupo_id = validated_data.get('grupo_incidente')

        # 3. Buscamos todos los empleados involucrados en este grupo de incidentes.
        # Usamos select_related para optimizar la consulta y traer el usuario asociado.
        incidentes_del_grupo = IncidenteEmpleado.objects.filter(grupo_incidente=grupo_id).select_related('id_empl__user')
        
        # 4. Enviamos una notificación a cada empleado.
        for incidente_empleado in incidentes_del_grupo:
            empleado = incidente_empleado.id_empl
            mensaje = f"El incidente '{incidente_empleado.id_incidente.tipo_incid}' ha sido resuelto."
            Notificacion.objects.create(
                id_user=empleado.user,
                mensaje=mensaje,
                enlace=f"/incidentes/detalle/{grupo_id}/"
            )

        return resolucion

# Para resolver la dependencia circular, añadimos el campo 'resolucion'
# a IncidenteEmpleadoSerializer después de que ambas clases han sido definidas.
IncidenteEmpleadoSerializer._declared_fields['resolucion'] = ResolucionSerializer(read_only=True)

class GrupoIncidenteDetalleSerializer(serializers.Serializer):
    """
    Serializer para la vista detallada de un grupo de incidentes.
    Muestra la información del incidente, todos los empleados involucrados
    y todos los descargos asociados al grupo.
    """
    grupo_anterior = serializers.UUIDField(required=False, allow_null=True)
    grupo_incidente = serializers.UUIDField()
    incidente = IncidenteSerializer()
    empleados_involucrados = EmpleadoBasicoSerializer(many=True)
    fecha_ocurrencia = serializers.DateField()
    descripcion = serializers.CharField()
    observaciones = serializers.CharField(allow_blank=True, allow_null=True)
    responsable_registro = EmpleadoBasicoSerializer()
    estado = serializers.CharField()
    descargos_del_grupo = DescargoGrupoSerializer(many=True)
    resolucion = ResolucionSerializer(required=False)

class GrupoIncidenteListSerializer(serializers.Serializer):
    """
    Serializer para la vista de lista de incidentes agrupados.
    Muestra información resumida de cada grupo.
    """
    grupo_anterior = serializers.UUIDField(required=False, allow_null=True)
    grupo_incidente = serializers.UUIDField()
    incidente = IncidenteSerializer()
    empleados_involucrados = EmpleadoBasicoSerializer(many=True)
    fecha_ocurrencia = serializers.DateField()
    descripcion = serializers.CharField()
    observaciones = serializers.CharField(allow_blank=True, allow_null=True)
    responsable_registro = EmpleadoBasicoSerializer()
    estado = serializers.CharField()
    descargos_del_grupo = DescargoGrupoSerializer(many=True)