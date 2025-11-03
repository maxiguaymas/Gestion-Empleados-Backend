from rest_framework import viewsets
from .models import Sancion, SancionEmpleado
from .serializers import SancionSerializer, SancionEmpleadoSerializer
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from notificaciones.models import Notificacion
from empleados.mixins import AdminWriteAccessMixin
from empleados.models import Empleado

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
        mensaje = f"Se te ha aplicado una nueva sanción: {sancion_empleado.id_sancion.nombre}."
        
        Notificacion.objects.create(
            id_user=empleado_sancionado.user,
            mensaje=mensaje,
            enlace=f"/sanciones/detalle/{sancion_empleado.id}/"
        )
