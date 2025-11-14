from rest_framework import viewsets, status, generics, mixins
from rest_framework.response import Response
from .models import Incidente, IncidenteEmpleado, Descargo, Resolucion, Empleado
from .serializers import IncidenteSerializer, IncidenteEmpleadoSerializer, DescargoSerializer, ResolucionSerializer, GrupoIncidenteDetalleSerializer, GrupoIncidenteListSerializer
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from empleados.mixins import AdminWriteAccessMixin
from rest_framework.decorators import action
from django.db import transaction
import uuid
from rest_framework.views import APIView

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
class GrupoIncidenteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para listar incidentes agrupados y ver el detalle de un grupo.
    - **GET /api/incidentes-agrupados/**: Lista todos los incidentes agrupados.
    - **GET /api/incidentes-agrupados/{grupo_incidente}/**: Muestra el detalle completo de un grupo de incidentes.
    """
    queryset = IncidenteEmpleado.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'grupo_incidente' # Usamos el UUID para buscar

    def get_serializer_class(self):
        """
        Devuelve un serializer diferente para la acción 'list' y 'retrieve'.
        """
        if self.action == 'list':
            return GrupoIncidenteListSerializer
        return GrupoIncidenteDetalleSerializer

    def list(self, request, *args, **kwargs):
        # Obtenemos todos los incidentes y optimizamos las consultas
        queryset = self.get_queryset().select_related('id_incidente', 'id_empl').prefetch_related('descargos__autor')
        
        # Agrupamos los incidentes por 'grupo_incidente'
        grupos = {}
        for ie in queryset:
            grupo_id = str(ie.grupo_incidente)
            if grupo_id not in grupos:
                grupos[grupo_id] = {
                    'grupo_incidente': ie.grupo_incidente,
                    'grupo_anterior': ie.grupo_anterior,
                    'incidente': ie.id_incidente,
                    'empleados_involucrados': [],
                    'fecha_ocurrencia': ie.fecha_ocurrencia,
                    'descripcion': ie.descripcion,
                    'observaciones': ie.observaciones,
                    'responsable_registro': ie.responsable_registro,
                    'estado': ie.estado,
                    'descargos_del_grupo': []
                }
            grupos[grupo_id]['empleados_involucrados'].append(ie.id_empl)
            # Usamos extend para añadir todos los descargos de este IncidenteEmpleado
            grupos[grupo_id]['descargos_del_grupo'].extend(ie.descargos.all())

        # Convertimos el diccionario de grupos a una lista para el serializer
        lista_agrupada = list(grupos.values())
        
        serializer = self.get_serializer(lista_agrupada, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        grupo_uuid = self.kwargs.get('grupo_incidente')
        
        # Obtenemos todos los registros de IncidenteEmpleado para este grupo
        # Optimizamos la consulta para traer todos los datos relacionados eficientemente.
        incidentes_del_grupo = IncidenteEmpleado.objects.filter(
            grupo_incidente=grupo_uuid
        ).select_related( # JOIN en las tablas relacionadas
            'id_incidente',
            'id_empl',
            'responsable_registro'
        ).prefetch_related( # Carga eficiente de relaciones "many"
            'descargos__autor'   # Prefetch de los descargos y el autor de cada descargo
        )

        if not incidentes_del_grupo.exists():
            return Response({"detail": "No se encontró un grupo de incidentes con ese identificador."}, status=status.HTTP_404_NOT_FOUND)

        # Recopilamos la información
        primer_incidente = incidentes_del_grupo.first()
        empleados_involucrados = [ie.id_empl for ie in incidentes_del_grupo]
        
        # Extraemos los descargos ya precargados
        descargos_del_grupo = []
        for ie in incidentes_del_grupo:
            descargos_del_grupo.extend(list(ie.descargos.all()))

        resolucion = Resolucion.objects.filter(grupo_incidente=grupo_uuid).first()

        # Construimos el objeto de datos para el serializer
        data = {
            'grupo_incidente': primer_incidente.grupo_incidente,
            'grupo_anterior': primer_incidente.grupo_anterior,
            'incidente': primer_incidente.id_incidente,
            'empleados_involucrados': empleados_involucrados,
            'fecha_ocurrencia': primer_incidente.fecha_ocurrencia,
            'descripcion': primer_incidente.descripcion,
            'observaciones': primer_incidente.observaciones,
            'responsable_registro': primer_incidente.responsable_registro,
            'estado': primer_incidente.estado,
            'descargos_del_grupo': descargos_del_grupo,
            'resolucion': resolucion,
        }

        serializer = self.get_serializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='corregir')
    @transaction.atomic
    def corregir(self, request, grupo_incidente=None):
        """
        Crea un nuevo grupo de incidentes como corrección de uno existente.
        El grupo de incidente anterior es cerrado y se crea una resolución automática.
        """
        grupo_original_uuid = grupo_incidente
        incidentes_originales = IncidenteEmpleado.objects.filter(grupo_incidente=grupo_original_uuid)

        if not incidentes_originales.exists():
            return Response({"detail": "El grupo de incidentes a corregir no existe."}, status=status.HTTP_404_NOT_FOUND)

        if incidentes_originales.first().estado == 'CERRADO':
            return Response({"detail": "Este incidente ya ha sido cerrado y no puede ser corregido."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = IncidenteEmpleadoSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        try:
            empleado_responsable = Empleado.objects.get(user=request.user)
        except Empleado.DoesNotExist:
            return Response({"detail": "Solo los usuarios con un perfil de empleado pueden realizar esta acción."}, status=status.HTTP_403_FORBIDDEN)

        # 1. Crear el nuevo grupo de incidentes
        nuevo_grupo_id = uuid.uuid4()
        nuevos_incidentes = []
        for empleado in validated_data.get('empleado_ids'):
            nuevo_incidente = IncidenteEmpleado.objects.create(
                grupo_incidente=nuevo_grupo_id,
                grupo_anterior=grupo_original_uuid,
                id_incidente=validated_data.get('id_incidente'),
                id_empl=empleado,
                fecha_ocurrencia=validated_data.get('fecha_ocurrencia'),
                descripcion=validated_data.get('descripcion'),
                observaciones=validated_data.get('observaciones', ''),
                responsable_registro=empleado_responsable,
                estado='ABIERTO'
            )
            nuevos_incidentes.append(nuevo_incidente)

        # 2. Crear una resolución para el grupo de incidente original
        Resolucion.objects.create(
            grupo_incidente=grupo_original_uuid,
            descripcion=f"Incidente corregido y reemplazado por el nuevo grupo de incidentes: {nuevo_grupo_id}",
            responsable=empleado_responsable
        )

        # 3. Devolver el nuevo grupo de incidentes creado
        response_data = {
            'grupo_incidente': nuevo_grupo_id,
            'grupo_anterior': grupo_original_uuid,
            'incidente': nuevos_incidentes[0].id_incidente,
            'empleados_involucrados': [ie.id_empl for ie in nuevos_incidentes],
            'fecha_ocurrencia': nuevos_incidentes[0].fecha_ocurrencia,
            'descripcion': nuevos_incidentes[0].descripcion,
            'observaciones': nuevos_incidentes[0].observaciones,
            'responsable_registro': nuevos_incidentes[0].responsable_registro,
            'estado': nuevos_incidentes[0].estado,
            'descargos_del_grupo': [], # El nuevo incidente no tiene descargos aún
            'resolucion': None, # El nuevo incidente no tiene resolución aún
        }
        response_serializer = GrupoIncidenteDetalleSerializer(response_data, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['Incidentes'])
class MisIncidentesView(generics.ListAPIView):
    """
    Devuelve los incidentes del empleado relacionado al usuario que hace la peticion.
    """
    serializer_class = IncidenteEmpleadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            empleado = Empleado.objects.get(user=user)
            return IncidenteEmpleado.objects.filter(id_empl=empleado)
        except Empleado.DoesNotExist:
            return IncidenteEmpleado.objects.none()
