from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Incidente, IncidenteEmpleado, Descargo, Resolucion
from .serializers import IncidenteSerializer, IncidenteEmpleadoSerializer, DescargoSerializer, ResolucionSerializer, GrupoIncidenteDetalleSerializer
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from empleados.mixins import AdminWriteAccessMixin
from empleados.models import Empleado

@extend_schema(tags=['Incidentes'])
class IncidenteViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    queryset = Incidente.objects.filter(estado_incid=True)
    serializer_class = IncidenteSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=['Incidentes'])
class IncidenteEmpleadoViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    queryset = IncidenteEmpleado.objects.all()
    serializer_class = IncidenteEmpleadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='Administrador').exists():
            return IncidenteEmpleado.objects.all()
        
        if user.groups.filter(name='Empleado').exists():
            try:
                empleado = Empleado.objects.get(user=user)
                return IncidenteEmpleado.objects.filter(id_empl=empleado)
            except Empleado.DoesNotExist:
                return IncidenteEmpleado.objects.none()
        
        return IncidenteEmpleado.objects.none()

@extend_schema(tags=['Incidentes'])
class DescargoViewSet(viewsets.ModelViewSet):
    queryset = Descargo.objects.all()
    serializer_class = DescargoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            # Buscamos el empleado asociado al usuario que está haciendo la petición
            empleado_autor = Empleado.objects.get(user=self.request.user)
            serializer.save(autor=empleado_autor)
        except Empleado.DoesNotExist:
            # Si el usuario no es un empleado (ej. un superadmin), guardamos el autor como null.
            serializer.save(autor=None)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='Administrador').exists():
            return Descargo.objects.all()
        
        if user.groups.filter(name='Empleado').exists():
            return Descargo.objects.filter(id_incid_empl__id_empl__user=user)
        
        return Descargo.objects.none()

@extend_schema(tags=['Incidentes'])
class ResolucionViewSet(AdminWriteAccessMixin, viewsets.ModelViewSet):
    queryset = Resolucion.objects.all()
    serializer_class = ResolucionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            # Buscamos el empleado asociado al usuario que está haciendo la petición
            empleado_responsable = Empleado.objects.get(user=self.request.user)
            serializer.save(responsable=empleado_responsable)
        except Empleado.DoesNotExist:
            # Si el usuario no es un empleado (ej. un superadmin), guardamos el responsable como null.
            serializer.save(responsable=None)

@extend_schema(tags=['Incidentes'])
class GrupoIncidenteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver el detalle agrupado de un incidente por su UUID de grupo.
    """
    queryset = IncidenteEmpleado.objects.all()
    serializer_class = GrupoIncidenteDetalleSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'grupo_incidente' # Usamos el UUID para buscar

    def retrieve(self, request, *args, **kwargs):
        grupo_uuid = self.kwargs.get('grupo_incidente')
        
        # Obtenemos todos los registros de IncidenteEmpleado para este grupo
        # Optimizamos la consulta para traer todos los datos relacionados eficientemente.
        incidentes_del_grupo = IncidenteEmpleado.objects.filter(
            grupo_incidente=grupo_uuid
        ).select_related(
            'id_incidente',      # JOIN en la tabla de incidentes
            'id_empl',           # JOIN en la tabla de empleados
            'id_empl__user'      # JOIN en la tabla de usuarios desde empleado
        ).prefetch_related(
            'descargos__autor'   # Prefetch de los descargos y el autor de cada descargo
        )

        if not incidentes_del_grupo.exists():
            return Response({"detail": "No se encontró un grupo de incidentes con ese identificador."}, status=status.HTTP_404_NOT_FOUND)

        # Recopilamos la información
        primer_incidente = incidentes_del_grupo.first()
        empleados_involucrados = [ie.id_empl for ie in incidentes_del_grupo] # Esto ya no genera queries gracias a select_related
        
        # Extraemos los descargos ya precargados
        descargos_del_grupo = []
        for ie in incidentes_del_grupo:
            descargos_del_grupo.extend(list(ie.descargos.all()))

        resolucion = Resolucion.objects.filter(grupo_incidente=grupo_uuid).first()

        # Construimos el objeto de datos para el serializer
        data = {
            'incidente': primer_incidente.id_incidente,
            'empleados_involucrados': empleados_involucrados,
            'descargos_del_grupo': descargos_del_grupo,
            'resolucion': resolucion
        }

        serializer = self.get_serializer(data)
        return Response(serializer.data)
