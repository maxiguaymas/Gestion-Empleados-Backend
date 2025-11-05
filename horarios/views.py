from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from .models import Horarios, AsignacionHorario
from .serializers import HorarioSerializer, AsignacionHorarioSerializer, AsignacionHorarioDetalleSerializer
from drf_spectacular.utils import extend_schema
from notificaciones.models import Notificacion
from empleados.mixins import AdminWriteAccessMixin
from .filters import AsignacionHorarioFilter

logger = logging.getLogger(__name__)

@extend_schema(tags=['Horarios'])
class HorarioViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet): # Renombrado de HorariosViewSet a HorarioViewSet para consistencia
    """
    ViewSet para gestionar los Horarios (turnos de trabajo).

    - Todos los usuarios autenticados pueden ver.
    - Solo Admins pueden crear, editar o eliminar.
    """
    queryset = Horarios.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=['Horarios'])
class AsignacionHorarioViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestionar la asignación de horarios a empleados.

    - Todos los usuarios autenticados pueden ver.
    - Solo Admins pueden crear, editar o eliminar.
    """
    queryset = AsignacionHorario.objects.select_related('id_empl', 'id_horario').all()
    serializer_class = AsignacionHorarioSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = AsignacionHorarioFilter

    def list(self, request, *args, **kwargs):
        """
        Sobrescribe el método list para devolver los empleados agrupados por horario.
        """
        # Obtenemos el queryset filtrado (por ejemplo, si se usa ?id_horario=1)
        queryset = self.filter_queryset(self.get_queryset())

        # Agrupamos los empleados por horario
        horarios_agrupados = {}
        for asignacion in queryset.filter(estado=True):
            horario = asignacion.id_horario
            if horario.id not in horarios_agrupados:
                horarios_agrupados[horario.id] = {
                    'horario': horario,
                    'empleados_asignados': []
                }
            horarios_agrupados[horario.id]['empleados_asignados'].append(asignacion.id_empl)

        # Convertimos el diccionario a una lista y lo serializamos
        data_para_serializar = list(horarios_agrupados.values())
        serializer = AsignacionHorarioDetalleSerializer(data_para_serializar, many=True)

        return Response(serializer.data)


    def create(self, request, *args, **kwargs):
        """
        Sobrescribe el método de creación para manejar la asignación de múltiples empleados.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        empleados = serializer.validated_data.pop('empleado_ids')
        horario = serializer.validated_data.get('id_horario')
        
        asignaciones_creadas = []
        for empleado in empleados:
            # 1. Creamos una asignación para cada empleado
            asignacion = AsignacionHorario.objects.create(id_horario=horario, id_empl=empleado)
            asignaciones_creadas.append(asignacion)

            # 2. Creamos la notificación para el empleado
            Notificacion.objects.create(
                id_user=empleado.user,
                mensaje=f"Se te ha asignado un nuevo horario: {horario.nombre}.",
                enlace="/horarios/mis-horarios/"
            )

            # 3. Enviar correo electrónico de notificación
            if empleado.email:
                try:
                    logger.info(f"Intentando enviar correo de horario a: {empleado.email}")
                    
                    # Construir la URL absoluta para el portal
                    host = request.get_host()
                    protocol = 'https' if request.is_secure() else 'http'
                    portal_url = f"{protocol}://{host.split(':')[0]}/horarios/mis-horarios/" # Ajusta esta URL si es necesario

                    asunto = f"Asignación de nuevo horario: {horario.nombre}"
                    
                    dias = []
                    if horario.lunes: dias.append('Lunes')
                    if horario.martes: dias.append('Martes')
                    if horario.miercoles: dias.append('Miércoles')
                    if horario.jueves: dias.append('Jueves')
                    if horario.viernes: dias.append('Viernes')
                    if horario.sabado: dias.append('Sábado')
                    if horario.domingo: dias.append('Domingo')
                    dias_laborables = ", ".join(dias)

                    # Renderizar el template HTML
                    cuerpo_mensaje_html = render_to_string('email/notificacion_horario.html', {
                        'empleado_nombre': empleado.nombre,
                        'horario': horario,
                        'dias_laborables': dias_laborables,
                        'portal_url': portal_url,
                    })
                    send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [empleado.email], html_message=cuerpo_mensaje_html)
                    logger.info(f"Correo de horario enviado exitosamente a {empleado.email}")
                except Exception as e:
                    logger.error(f"ERROR al enviar correo de horario a {empleado.email}: {e}")
            
        # Serializamos la lista de asignaciones creadas para la respuesta
        response_serializer = self.get_serializer(asignaciones_creadas, many=True)
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
