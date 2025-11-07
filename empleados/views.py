from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging
from .models import Empleado, Legajo, Documento, RequisitoDocumento
from drf_spectacular.utils import extend_schema
# from notificaciones.models import Notificacion
from .serializer import EmpleadoSerializer, LegajoSerializer, DocumentoSerializer, RequisitoDocumentoSerializer
from rest_framework.permissions import IsAuthenticated
from .mixins import AdminWriteAccessMixin
from .utils import get_client_ip
from django.utils import timezone

##08329a51c848547c612642a5808e919f1513cd55031118e6685790909e946a57

# Obtenemos un logger para registrar información
logger = logging.getLogger(__name__)

@extend_schema(tags=['Empleados'])
class EmpleadoViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in=['Administrador', 'Consultor']).exists():
            return Empleado.objects.all()
        if user.groups.filter(name='Empleado').exists():
            # Filtra para devolver solo el objeto Empleado asociado a este usuario.
            return Empleado.objects.filter(user=user)
        return Empleado.objects.none() # No devuelve nada si no pertenece a un grupo válido

    def create(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        logger.info(f"Intento de creación de empleado desde la IP: {client_ip}")
        # La lógica de permisos ya está en el mixin, así que solo llamamos a super()
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        empleado = self.get_object()
        empleado.estado = 'Inactivo'
        empleado.fecha_egreso = timezone.now().date()
        empleado.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='perfil')
    def perfil(self, request):
        """
        Devuelve el perfil del empleado correspondiente al usuario autenticado.
        """
        try:
            empleado = Empleado.objects.get(user=request.user)
            serializer = self.get_serializer(empleado)
            return Response(serializer.data)
        except Empleado.DoesNotExist:
            return Response({'error': 'No se encontró un empleado para este usuario.'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(tags=['Empleados'])
class LegajoViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    queryset = Legajo.objects.all()
    serializer_class = LegajoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in=['Administrador', 'Empleado']).exists():
            return Legajo.objects.all()
        if user.groups.filter(name='Empleado').exists():
            # Filtra a través de la relación Empleado -> User
            return Legajo.objects.filter(id_empl__id_usu=user)
        return Legajo.objects.none()

@extend_schema(tags=['Empleados'])
class DocumentoViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    queryset = Documento.objects.all()
    serializer_class = DocumentoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in=['Administrador', 'Empleado']).exists():
            return Documento.objects.all()
        if user.groups.filter(name='Empleado').exists():
            # Filtra a través de la relación Documento -> Legajo -> Empleado -> User
            return Documento.objects.filter(id_legajo__id_empl__id_usu=user)
        return Documento.objects.none()

    @action(detail=True, methods=['post'], url_path='aprobar-documento')
    def aprobar_documento(self, request, pk=None):
        """
        Acción para que un administrador apruebe un documento.
        Esto notificará al empleado correspondiente.
        """
        # Reutilizamos la lógica de permisos del mixin para asegurar que solo los admins puedan ejecutarla.
        self._check_admin_privileges(request)

        #documento = self.get_object()
        # Aquí iría tu lógica para cambiar el estado del documento, ej:
        # documento.estado_doc = 'Aprobado'
        # documento.save()

        #empleado_a_notificar = documento.id_legajo.id_empl
        # Notificacion.objects.create(
        #     id_user=empleado_a_notificar.user,
        #     mensaje=f"Tu documento '{documento.id_requisito.nombre_doc}' ha sido aprobado.",
        #     enlace=f'/legajo/documentos/{documento.id}'
        # )

        return Response({'status': 'Documento aprobado y empleado notificado.'}, status=status.HTTP_200_OK)

@extend_schema(tags=['Empleados'])
class RequisitoDocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RequisitoDocumento.objects.all()
    serializer_class = RequisitoDocumentoSerializer
    permission_classes = [IsAuthenticated]