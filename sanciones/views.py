from rest_framework import viewsets, generics, status
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from .models import Sancion, SancionEmpleado
from .serializers import SancionSerializer, SancionEmpleadoSerializer
from drf_spectacular.utils import extend_schema
from notificaciones.models import Notificacion
from empleados.mixins import AdminWriteAccessMixin
from empleados.models import Empleado
from rest_framework.response import Response

logger = logging.getLogger(__name__)

@extend_schema(tags=['Sanciones'])
class SancionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver las sanciones predefinidas. Solo permite la lectura.
    """
    queryset = Sancion.objects.filter(estado=True)
    serializer_class = SancionSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=['Sanciones'])
class SancionEmpleadoViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestionar las sanciones de los empleados.
    - Administradores: Pueden realizar cualquier operación (CRUD).
    - Empleados: Solo pueden ver sus propias sanciones.
    """
    queryset = SancionEmpleado.objects.all()
    serializer_class = SancionEmpleadoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        1. Asigna automáticamente al empleado que está registrando la sanción como responsable.
        2. Envía una notificación al empleado sancionado.
        """
        responsable = None
        if hasattr(self.request.user, 'empleado'):
            responsable = self.request.user.empleado
        
        # 1. Guardamos la sanción y obtenemos la instancia creada.
        sancion_empleado = serializer.save(responsable=responsable)

        # 2. Creamos y enviamos la notificación al empleado sancionado.
        empleado_sancionado = sancion_empleado.id_empl
        enlace_sancion = f"/sanciones/detalle/{sancion_empleado.id}/"
        mensaje = f"Se te ha aplicado una nueva sanción: {sancion_empleado.id_sancion.nombre}."
        
        Notificacion.objects.create(
            id_user=empleado_sancionado.user,
            mensaje=mensaje,
            enlace=enlace_sancion
        )

        # 3. Enviar correo electrónico de notificación
        if empleado_sancionado.email:
            try:
                logger.info(f"Intentando enviar correo de sanción a: {empleado_sancionado.email}")
                request = self.request
                host = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
                detalle_url = f"{protocol}://{host.split(':')[0]}{enlace_sancion}"

                asunto = f"Notificación de Nueva Sanción: {sancion_empleado.id_sancion.nombre}"

                # Renderizar el template HTML
                cuerpo_mensaje_html = render_to_string('email/notificacion_sancion.html', {
                    'empleado_nombre': empleado_sancionado.nombre,
                    'sancion_empleado': sancion_empleado,
                    'detalle_url': detalle_url,
                })
                
                send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [empleado_sancionado.email], html_message=cuerpo_mensaje_html)
                logger.info(f"Correo de sanción enviado exitosamente a {empleado_sancionado.email}")
            except Exception as e:
                logger.error(f"ERROR al enviar correo de sanción a {empleado_sancionado.email}: {e}")

@extend_schema(tags=['Sanciones'])
class MisSancionesView(generics.ListAPIView):
    """
    Devuelve las sanciones del empleado relacionado al usuario que hace la petición.
    """
    serializer_class = SancionEmpleadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtra y devuelve solo las sanciones del empleado que realiza la solicitud.
        """
        user = self.request.user
        try:
            # Buscamos el empleado asociado al usuario autenticado
            empleado = Empleado.objects.get(user=user)
            return SancionEmpleado.objects.filter(id_empl=empleado)
        except Empleado.DoesNotExist:
            # Si el usuario no tiene un perfil de empleado, no se devuelven sanciones.
            return SancionEmpleado.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "No se encontraron sanciones para tu usuario."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
