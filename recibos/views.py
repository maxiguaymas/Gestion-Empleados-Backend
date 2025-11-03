from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Recibo_Sueldos
from .serializers import ReciboSueldosSerializer
from drf_spectacular.utils import extend_schema
from notificaciones.models import Notificacion
from empleados.mixins import AdminWriteAccessMixin
from empleados.models import Empleado

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
        Notificacion.objects.create(
            id_user=empleado.user,
            mensaje=mensaje,
            enlace="/recibos/mis-recibos/"
        )
