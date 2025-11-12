import base64
import numpy as np
import cv2
import face_recognition
from datetime import date

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from empleados.models import Empleado
from empleados.serializer import EmpleadoSerializer
from .models import Rostro, Asistencia
from empleados.mixins import AdminWriteAccessMixin
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .serializers import AsistenciaSerializer, RostroSerializer


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

        rostros_conocidos = Rostro.objects.all()
        encodings_conocidos = [np.array(r.get_encoding()) for r in rostros_conocidos]
        empleados_ids = [r.id_empl_id for r in rostros_conocidos]

        format, imgstr = image_data.split(';base64,')
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

                if not Asistencia.objects.filter(id_empl=empleado, fecha_hora__date=date.today()).exists():
                    asistencia = Asistencia.objects.create(id_empl=empleado)
                    asistencia.minutos_retraso = asistencia.calcular_retraso()
                    asistencia.save()
                    serializer = AsistenciaSerializer(asistencia)
                    return Response({
                        'status': 'success',
                        'message': 'Asistencia registrada correctamente.',
                        'asistencia': serializer.data,
                        'empleado': f'{empleado.nombre} {empleado.apellido}'
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'status': 'already_marked',
                        'message': 'Este empleado ya marcó su asistencia hoy.',
                        'empleado': f'{empleado.nombre} {empleado.apellido}'
                    }, status=status.HTTP_200_OK)

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
