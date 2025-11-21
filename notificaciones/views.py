from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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

@extend_schema(
    tags=['Notificaciones'],
    summary="Marcar todas las notificaciones como leídas",
    description="Marca todas las notificaciones no leídas del usuario autenticado como leídas y devuelve el número de notificaciones actualizadas.",
    responses={200: {"description": "Notificaciones marcadas como leídas.", "examples": {"application/json": {"mensaje": "3 notificaciones marcadas como leídas."}}}}
)
class MarcarTodasLeidasView(APIView):
    """
    POST: /api/notificaciones/marcar-todas-leidas/
    
    Marca todas las notificaciones no leídas del usuario que realiza la petición como leídas.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Maneja la petición POST para marcar todas las notificaciones como leídas.
        """
        notificaciones_no_leidas = Notificacion.objects.filter(id_user=request.user, leida=False)
        count = notificaciones_no_leidas.count()
        notificaciones_no_leidas.update(leida=True)
        
        return Response({"mensaje": f"{count} notificaciones marcadas como leídas."}, status=status.HTTP_200_OK)
