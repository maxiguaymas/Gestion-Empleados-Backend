from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Notificacion
from .serializers import NotificacionSerializer

@extend_schema(
    tags=['Notificaciones'],
    summary="Listar mis notificaciones",
    description="Devuelve una lista de todas las notificaciones asociadas al usuario que realiza la petición, ordenadas de la más reciente a la más antigua."
)
class NotificacionesUsuarioView(ListAPIView):
    """
    GET: /api/mis-notificaciones/
    
    Este endpoint devuelve todas las notificaciones para el usuario autenticado.
    """
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Este método filtra el queryset para devolver solo las notificaciones del usuario actual.
        """
        return Notificacion.objects.filter(id_user=self.request.user)
