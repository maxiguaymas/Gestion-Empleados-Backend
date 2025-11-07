from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from .models import Recibo_Sueldos
from rest_framework.response import Response
from .serializers import ReciboSueldosSerializer
from drf_spectacular.utils import extend_schema
from notificaciones.models import Notificacion
from empleados.mixins import AdminWriteAccessMixin
from empleados.models import Empleado

logger = logging.getLogger(__name__)
from rest_framework.generics import ListAPIView

@extend_schema(tags=['Recibos'])
class ReciboSueldosViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestionar los recibos de sueldo.

    - Los Administradores pueden ver todos los recibos.
    - Los Empleados solo pueden ver sus propios recibos.
    - Solo los Administradores pueden crear, actualizar o eliminar recibos.
    """
    queryset = Recibo_Sueldos.objects.all()
    serializer_class = ReciboSueldosSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtra los recibos para que los empleados solo puedan ver los suyos,
        mientras que los administradores y consultores pueden ver todos.
        """
        user = self.request.user

        # Superusuarios, Administradores y Consultores ven todos los recibos.
        if user.is_superuser or user.groups.filter(name__in=['Administrador', 'Empleado']).exists():
            return Recibo_Sueldos.objects.all()

        # Los empleados solo ven sus propios recibos.
        if user.groups.filter(name='Empleado').exists():
            try:
                # Buscamos el empleado asociado al usuario actual
                empleado = Empleado.objects.get(id_usu=user)
                return Recibo_Sueldos.objects.filter(id_empl=empleado)
            except Empleado.DoesNotExist:
                return Recibo_Sueldos.objects.none()

        # Si el usuario no pertenece a un grupo válido, no ve ningún recibo.
        return Recibo_Sueldos.objects.none()

    def perform_create(self, serializer):
        """
        Sobrescribe el método para enviar una notificación al empleado
        cuando se le carga un nuevo recibo de sueldo.
        """
        # 1. Guardamos el recibo de sueldo.
        recibo = serializer.save()

        # 2. Creamos la notificación para el empleado.
        empleado = recibo.id_empl
        mensaje = f"Se ha cargado tu recibo de sueldo para el período {recibo.periodo}."
        enlace_recibos = "/recibos/mis-recibos/"
        Notificacion.objects.create(
            id_user=empleado.user,
            mensaje=mensaje,
            enlace=enlace_recibos
        )

        # 3. Enviar correo electrónico de notificación
        if empleado.email:
            try:
                logger.info(f"Intentando enviar correo de recibo a: {empleado.email}")
                request = self.request
                host = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
                portal_url = f"{protocol}://{host.split(':')[0]}{enlace_recibos}"

                asunto = f"Nuevo recibo de sueldo disponible: Período {recibo.periodo}"

                # Renderizar el template HTML
                cuerpo_mensaje_html = render_to_string('email/notificacion_recibo.html', {
                    'empleado_nombre': empleado.nombre,
                    'periodo': recibo.periodo,
                    'portal_url': portal_url,
                })
                
                send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [empleado.email], html_message=cuerpo_mensaje_html)
                logger.info(f"Correo de recibo enviado exitosamente a {empleado.email}")
            except Exception as e:
                logger.error(f"ERROR al enviar correo de recibo a {empleado.email}: {e}")

@extend_schema(tags=['Recibos'])
class MisRecibosView(ListAPIView):
    """
    Devuelve los recibos de sueldo del empleado relacionado al usuario que hace la petición.
    """
    serializer_class = ReciboSueldosSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Este método filtra y devuelve solo los recibos de sueldo
        del empleado que está realizando la solicitud.
        """
        user = self.request.user
        try:
            # Buscamos el empleado asociado al usuario autenticado
            empleado = Empleado.objects.get(user=user)
            return Recibo_Sueldos.objects.filter(id_empl=empleado)
        except Empleado.DoesNotExist:
            # Si el usuario no tiene un perfil de empleado, no se devuelven recibos.
            return Recibo_Sueldos.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "No se encontraron recibos de sueldo para tu usuario."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
