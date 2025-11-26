import base64
import numpy as np
import cv2
from datetime import timedelta, datetime
import face_recognition
from django.utils import timezone
from django.core.cache import cache
import logging
from .signals import KNOWN_FACES_CACHE_KEY

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from empleados.models import Empleado
from empleados.serializer import EmpleadoBasicoSerializer, EmpleadoSerializer
from .models import Rostro, Asistencia
from horarios.models import AsignacionHorario, Horarios
from empleados.mixins import AdminWriteAccessMixin
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .serializers import AsistenciaSerializer, RostroSerializer

# Obtenemos una instancia del logger para este módulo.
logger = logging.getLogger(__name__)

@extend_schema(tags=['Asistencias'])
class EmpleadosSinRostroAPIView(AdminWriteAccessMixin, ListAPIView):
    """
    API para obtener una lista de empleados que aún no tienen un rostro registrado.
    Solo los administradores pueden acceder.
    """
    serializer_class = EmpleadoBasicoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Devuelve todos los empleados que no están en la tabla de Rostros.
        """
        empleados_con_rostro_ids = Rostro.objects.values_list('id_empl_id', flat=True)
        return Empleado.objects.exclude(id__in=empleados_con_rostro_ids)


@extend_schema(tags=['Asistencias'])
class EmpleadosConRostroAPIView(AdminWriteAccessMixin, ListAPIView):
    """
    API para obtener una lista de empleados que ya tienen un rostro registrado.
    Ideal para la sección de edición de rostros.
    Solo los administradores pueden acceder.
    """
    serializer_class = EmpleadoBasicoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Devuelve todos los empleados que sí están en la tabla de Rostros.
        """
        empleados_con_rostro_ids = Rostro.objects.values_list('id_empl_id', flat=True)
        return Empleado.objects.filter(id__in=empleados_con_rostro_ids)


@extend_schema(tags=['Asistencias'])
class EmpleadosSinRostroAPIView(AdminWriteAccessMixin, ListAPIView):
    """
    API para obtener una lista de empleados que aún no tienen un rostro registrado.
    Solo los administradores pueden acceder.
    """
    serializer_class = EmpleadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Devuelve todos los empleados que no están en la tabla de Rostros.
        """
        empleados_con_rostro_ids = Rostro.objects.values_list('id_empl_id', flat=True)
        return Empleado.objects.exclude(id__in=empleados_con_rostro_ids)


@extend_schema(tags=['Asistencias'])
class RegistrarRostroAPIView(AdminWriteAccessMixin, APIView):
    """
    API para registrar el rostro de un empleado.
    Recibe una imagen en base64 y el ID del empleado.
    Solo los administradores pueden acceder a esta vista.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        empleado_id = request.data.get('empleado_id')
        image_data = request.data.get('image') # Imagen en formato base64

        if not empleado_id or not image_data:
            return Response(
                {'error': 'Se requiere el ID del empleado y la imagen.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Decodificar la imagen
            format, imgstr = image_data.split(';base64,')
            data = base64.b64decode(imgstr)

            # Convertir a imagen de OpenCV
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Encontrar rostros y calcular encoding
            face_locations = face_recognition.face_locations(rgb_img)
            if len(face_locations) != 1:
                return Response(
                    {'error': f'Se detectaron {len(face_locations)} rostros. Se necesita exactamente uno.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

            # Guardar en la base de datos
            empleado = Empleado.objects.get(id=empleado_id)
            rostro, created = Rostro.objects.get_or_create(id_empl=empleado)
            rostro.set_encoding(face_encodings[0])
            rostro.save()

            return Response(
                {'message': f'Rostro de {empleado.nombre} registrado exitosamente.'},
                status=status.HTTP_201_CREATED
            )

        except Empleado.DoesNotExist:
            return Response({'error': 'Empleado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, *args, **kwargs):
        """
        Actualiza el rostro de un empleado existente.
        """
        empleado_id = request.data.get('empleado_id')
        image_data = request.data.get('image')

        if not empleado_id or not image_data:
            return Response(
                {'error': 'Se requiere el ID del empleado y la imagen.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            empleado = Empleado.objects.get(id=empleado_id)
            rostro = Rostro.objects.get(id_empl=empleado)

            format, imgstr = image_data.split(';base64,')
            data = base64.b64decode(imgstr)
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_img)
            if len(face_locations) != 1:
                return Response(
                    {'error': f'Se detectaron {len(face_locations)} rostros. Se necesita exactamente uno.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            rostro.set_encoding(face_encodings[0])
            rostro.save()

            return Response({'message': f'Rostro de {empleado.nombre} actualizado exitosamente.'}, status=status.HTTP_200_OK)
        except Empleado.DoesNotExist:
            return Response({'error': 'Empleado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=['Asistencias'])
class ReconocerRostroAPIView(APIView):
    """
    API para recibir un frame de la cámara, reconocer el rostro y registrar la asistencia.
    """
    permission_classes = [IsAuthenticated] # O podría ser AllowAny si el dispositivo de marcado es público

    def post(self, request, *args, **kwargs):
        image_data = request.data.get('image')
        if not image_data:
            return Response({'error': 'No se recibió imagen.'}, status=status.HTTP_400_BAD_REQUEST)

        # --- Optimización con Caché ---
        # Intenta obtener los datos de rostros conocidos desde el caché.
        known_faces_data = cache.get(KNOWN_FACES_CACHE_KEY)
        if not known_faces_data:
            # Si no está en caché, lo generamos desde la BD.
            rostros_conocidos = Rostro.objects.all()
            encodings_conocidos = [np.array(r.get_encoding()) for r in rostros_conocidos]
            empleados_ids = [r.id_empl_id for r in rostros_conocidos]
            known_faces_data = {
                'encodings': encodings_conocidos,
                'ids': empleados_ids
            }
            # Guardamos los datos en caché para futuras peticiones.
            cache.set(KNOWN_FACES_CACHE_KEY, known_faces_data, timeout=None) # None = no expira

        encodings_conocidos = known_faces_data['encodings']
        empleados_ids = known_faces_data['ids']
        # --- Fin de la optimización ---

        # Manejo robusto de la decodificación de la imagen en base64
        try:
            imgstr = image_data.split(';base64,')[1] if ';base64,' in image_data else image_data
        except IndexError:
            return Response({'error': 'Formato de imagen base64 inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        data = base64.b64decode(imgstr)
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(encodings_conocidos, face_encoding, tolerance=0.5)
            if True in matches:
                first_match_index = matches.index(True)
                empleado_id = empleados_ids[first_match_index]
                empleado = Empleado.objects.get(id=empleado_id)

                logger.info(f"Rostro reconocido: {empleado.nombre} {empleado.apellido} (ID: {empleado.id})")

                now = timezone.localtime(timezone.now())
                today_local = now.date()

                # 1. Obtener los turnos asignados al empleado para el día de la semana actual.
                # El día de la semana en Python es 0=Lunes, 6=Domingo. En Django es 1=Domingo, 7=Sábado.
                # Usamos el formato de Python y lo ajustamos.
                dia_semana_python = today_local.weekday() # Lunes=0, Martes=1, ..., Domingo=6
                
                # Mapeamos el día de la semana de Python al nombre del campo en el modelo Horario.
                dias_map = {
                    0: 'lunes',
                    1: 'martes',
                    2: 'miercoles',
                    3: 'jueves',
                    4: 'viernes',
                    5: 'sabado',
                    6: 'domingo',
                }
                campo_dia_actual = dias_map.get(dia_semana_python)

                # 1. Construimos el filtro dinámico y obtenemos los IDs de los horarios del día.
                filtro_dia = {campo_dia_actual: True}
                horarios_del_dia_ids = Horarios.objects.filter(**filtro_dia).values_list('id', flat=True)

                # 2. Filtrar las asignaciones del empleado que corresponden a esos horarios.
                asignaciones = AsignacionHorario.objects.filter(
                    id_empl=empleado,
                    estado=True,
                    id_horario_id__in=horarios_del_dia_ids
                ).select_related('id_horario').order_by('id_horario__hora_entrada')

                if not asignaciones.exists():
                    logger.warning(f"Intento de marcado para {empleado.nombre}, pero no tiene turnos asignados para hoy ({campo_dia_actual}).")
                    return Response({
                        'status': 'no_schedule_for_today',
                        'message': 'No tiene turnos asignados para el día de hoy.',
                        'empleado': f'{empleado.nombre} {empleado.apellido}'
                    }, status=status.HTTP_403_FORBIDDEN)

                # 3. Iterar sobre los turnos del día y encontrar uno válido para marcar.
                for asignacion in asignaciones:
                    horario = asignacion.id_horario
                    logger.info(f"Verificando turno '{horario.nombre}' para {empleado.nombre}.")

                    # 4. Verificar si la hora actual está dentro del rango permitido para este turno.
                    inicio_permiso = (datetime.combine(today_local, horario.hora_entrada) - timedelta(minutes=30)).time()
                    fin_turno = horario.hora_salida

                    if inicio_permiso <= now.time() <= fin_turno:
                        logger.info(f"¡Rango de horario válido para el turno '{horario.nombre}'! Intentando registrar...")
                        
                        # 5. OPERACIÓN ATÓMICA: Usamos update_or_create para garantizar la unicidad por turno y día.
                        # Busca un registro que coincida con el empleado, el turno y la fecha.
                        # Si no lo encuentra, lo crea con los valores en 'defaults'.
                        # Si lo encuentra, no hace nada (porque no pasamos valores para actualizar).
                        asistencia, created = Asistencia.objects.update_or_create(
                            id_empl=empleado,
                            id_asignacion_horario=asignacion,
                            fecha_hora__date=today_local,
                            defaults={
                                'id_empl': empleado,
                                'id_asignacion_horario': asignacion,
                                'fecha_hora': now # Usamos la hora actual consciente que ya teníamos.
                            }
                        )

                        if created:
                            # Si se creó un nuevo registro, calculamos el retraso y lo guardamos.
                            asistencia.minutos_retraso = asistencia.calcular_retraso()
                            asistencia.save()
                            serializer = AsistenciaSerializer(asistencia)
                            logger.info(f"Asistencia registrada exitosamente para el turno '{horario.nombre}'.")
                            return Response({
                                'status': 'success',
                                'message': f'Asistencia registrada para el turno {horario.nombre}.',
                                'asistencia': serializer.data,
                                'empleado': f'{empleado.nombre} {empleado.apellido}'
                            }, status=status.HTTP_201_CREATED)
                        else:
                            # Si no se creó, significa que ya existía. Saltamos al siguiente turno.
                            logger.info(f"El empleado ya marcó para el turno '{horario.nombre}'. Saltando al siguiente.")
                            continue

                # 7. Si el bucle termina, significa que ya marcó todos sus turnos o está fuera de horario para los turnos restantes.
                logger.warning(f"No se encontró un turno válido para marcar en este momento para {empleado.nombre}.")
                return Response({
                    'status': 'no_valid_schedule_at_this_time',
                    'message': 'Ya ha marcado todos sus turnos para hoy o se encuentra fuera del horario de marcado.',
                    'empleado': f'{empleado.nombre} {empleado.apellido}'
                }, status=status.HTTP_403_FORBIDDEN)

                # Salimos del bucle principal una vez que hemos encontrado y procesado a una persona.
                break

        return Response({'status': 'not_found', 'message': 'Rostro no reconocido.'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Asistencias'],
    parameters=[
        OpenApiParameter(name='month', description='Filtrar por mes (1-12)', required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name='year', description='Filtrar por año (ej. 2024)', required=False, type=OpenApiTypes.INT),
    ]
)
class AsistenciaEmpleadoAPIView(ListAPIView):
    """
    API para obtener las asistencias de un empleado específico.
    El ID del empleado se pasa en la URL.
    Permite filtrar por mes y año a través de query params.
    """
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        empleado_id = self.kwargs.get('empleado_id')
        
        # Seguridad: Un empleado solo puede ver sus propias asistencias.
        # Un admin o consultor puede ver las de cualquiera.
        user = self.request.user
        if not (user.is_superuser or user.groups.filter(name__in=['Administrador', 'Consultor']).exists()):
            empleado_id = user.empleado.id

        queryset = Asistencia.objects.filter(id_empl_id=empleado_id).order_by('-fecha_hora')

        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')

        if month: queryset = queryset.filter(fecha_hora__month=month)
        if year: queryset = queryset.filter(fecha_hora__year=year)
        
        return queryset

@extend_schema(tags=['Asistencias'])
class ResumenAsistenciaDiariaAPIView(AdminWriteAccessMixin, APIView):
    """
    Devuelve un resumen de las asistencias del día actual.
    - `asistencias_hoy`: Número de empleados que marcaron asistencia hoy.
    - `total_empleados_activos`: Número total de empleados activos.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Usamos localtime para obtener la fecha correspondiente a la zona horaria del servidor.
        today = timezone.localtime(timezone.now()).date()
        
        # Contar asistencias únicas de empleados para hoy
        asistencias_hoy = Asistencia.objects.filter(fecha_hora__date=today).values('id_empl').distinct().count()
        
        # Contar total de empleados activos
        total_empleados_activos = Empleado.objects.filter(estado='Activo').count()
        
        data = { 'asistencias_hoy': asistencias_hoy, 'total_empleados_activos': total_empleados_activos }
        
        return Response(data, status=status.HTTP_200_OK)
