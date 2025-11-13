from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from .models import Horarios, AsignacionHorario
from .serializers import HorarioSerializer, AsignacionHorarioSerializer, AsignacionHorarioDetalleSerializer
from .serializers import AsignacionHorarioListSerializer
from notificaciones.models import Notificacion
from empleados.mixins import AdminWriteAccessMixin
from .filters import AsignacionHorarioFilter
from rest_framework.generics import ListAPIView
from empleados.models import Empleado

logger = logging.getLogger(__name__)
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['Horarios'])
class HorarioViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet): # Renombrado de HorariosViewSet a HorarioViewSet para consistencia
    """
    ViewSet para gestionar los Horarios (turnos de trabajo).

    - Todos los usuarios autenticados pueden ver.
    - Solo Admins pueden crear, editar o eliminar.
    """
    # Usamos prefetch_related para optimizar la consulta, trayendo los empleados
    # asignados en una sola consulta adicional en lugar de una por cada horario.
    queryset = Horarios.objects.prefetch_related('asignaciones__id_empl').all()
    serializer_class = HorarioSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='sincronizar-empleados')
    def sincronizar_empleados(self, request, pk=None):
        """
        Sincroniza la lista de empleados para un horario específico.
        Asigna nuevos empleados y desasigna a los que ya no están en la lista.
        """
        horario = self.get_object()
        empleado_ids_nuevos = request.data.get('empleado_ids', [])

        if not isinstance(empleado_ids_nuevos, list):
            return Response({"error": "El campo 'empleado_ids' debe ser una lista de IDs."}, status=status.HTTP_400_BAD_REQUEST)

        # Validar capacidad del horario
        if len(empleado_ids_nuevos) > horario.cantidad_personal_requerida:
            return Response({
                "error": f"La cantidad de empleados ({len(empleado_ids_nuevos)}) excede la capacidad del horario ({horario.cantidad_personal_requerida})."
            }, status=status.HTTP_400_BAD_REQUEST)

        # --- Lógica de Sincronización ---

        # 1. Obtener los IDs de los empleados actualmente asignados y activos
        asignaciones_actuales = AsignacionHorario.objects.filter(id_horario=horario, estado=True)
        empleado_ids_actuales = set(asignaciones_actuales.values_list('id_empl_id', flat=True))

        empleado_ids_nuevos_set = set(empleado_ids_nuevos)

        # 2. Identificar empleados a desasignar
        # Son los que estaban antes pero no están en la nueva lista.
        ids_a_desasignar = empleado_ids_actuales - empleado_ids_nuevos_set
        if ids_a_desasignar:
            AsignacionHorario.objects.filter(
                id_horario=horario, 
                id_empl_id__in=ids_a_desasignar,
                estado=True
            ).update(estado=False)
            # Aquí podrías agregar lógica para notificar la desasignación si es necesario.

        # 3. Identificar empleados a asignar
        # Son los que están en la nueva lista pero no estaban antes.
        ids_a_asignar = empleado_ids_nuevos_set - empleado_ids_actuales
        
        empleados_a_asignar = Empleado.objects.filter(id__in=ids_a_asignar)
        asignaciones_creadas = []

        for empleado in empleados_a_asignar:
            # Buscamos si existe una asignación inactiva para reactivarla
            asignacion_existente = AsignacionHorario.objects.filter(id_horario=horario, id_empl=empleado, estado=False).first()
            if asignacion_existente:
                asignacion_existente.estado = True
                asignacion_existente.save()
            else:
                # Si no existe, creamos una nueva
                asignacion = AsignacionHorario.objects.create(id_horario=horario, id_empl=empleado)
                asignaciones_creadas.append(asignacion)
            
            # Aquí podrías agregar la lógica de notificación por correo que ya tienes en el create original.
            # Por simplicidad, en este ejemplo no se incluye para no repetir código.

        # 4. Devolver una respuesta exitosa
        return Response({
            "message": "La lista de empleados ha sido sincronizada correctamente.",
            "asignados": len(ids_a_asignar),
            "desasignados": len(ids_a_desasignar)
        }, status=status.HTTP_200_OK)

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

@extend_schema(tags=['Horarios'])
class MisHorariosView(ListAPIView):
    """
    Vista para que un empleado vea sus horarios asignados.
    Devuelve una lista de los horarios activos asignados al empleado
    que realiza la solicitud.
    """
    serializer_class = HorarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Este método devuelve la lista de horarios asignados
        al empleado autenticado.
        """
        try:
            # 1. Obtener el empleado vinculado al usuario autenticado
            empleado = self.request.user.empleado
        except Empleado.DoesNotExist:
            # Si no hay un perfil de empleado, no hay horarios que mostrar
            return Horarios.objects.none()

        # 2. Filtrar las asignaciones activas para ese empleado
        horarios_ids = AsignacionHorario.objects.filter(
            id_empl=empleado, 
            estado=True
        ).values_list('id_horario', flat=True)

        # 3. Devolver los objetos Horario correspondientes
        return Horarios.objects.filter(id__in=horarios_ids)

    def list(self, request, *args, **kwargs):
        """
        Personaliza la respuesta para cuando no se encuentran horarios.
        """
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "No tienes horarios asignados."}, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@extend_schema(tags=['Horarios'])
class AsignacionHorarioListView(ListAPIView):
    """
    Vista para obtener una lista de todas las asignaciones de horarios (activas e inactivas),
    incluyendo los detalles del horario (turno) y los datos básicos del empleado.
    Accesible para cualquier usuario autenticado.
    """
    serializer_class = AsignacionHorarioListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Devuelve todas las asignaciones, optimizando la consulta
        para incluir los datos relacionados del horario y del empleado.
        """
        return AsignacionHorario.objects.all().select_related('id_horario', 'id_empl').order_by('id_horario__nombre', 'id_empl__apellido')
