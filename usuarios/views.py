from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
import logging
from drf_spectacular.utils import extend_schema
from empleados.utils import get_client_ip


# Create your views here.
logger = logging.getLogger(__name__)


@extend_schema(tags=['Usuarios'])
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    client_ip = get_client_ip(request)
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Se requieren usuario y contraseña.'}, status=status.HTTP_400_BAD_REQUEST)

    logger.info(f"Intento de login para el usuario '{username}' desde la IP: {client_ip}")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning(f"Login fallido: El usuario '{username}' no existe. IP: {client_ip}")
        return Response({'error': 'Usuario o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.check_password(password):
        logger.warning(f"Login fallido: Contraseña incorrecta para el usuario '{username}'. IP: {client_ip}")
        return Response({'error': 'Usuario o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)

    # Eliminar token existente y crear uno nuevo para reiniciar la expiración.
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)

    serializer = UserSerializer(instance=user)
    logger.info(f"Login exitoso para el usuario '{user.username}'. IP: {client_ip}")
    return Response({'token': token.key, 'user': serializer.data}, status=status.HTTP_200_OK)

@extend_schema(tags=['Usuarios'])
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token = Token.objects.create(user=user)
        client_ip = get_client_ip(request)
        logger.info(f"Nuevo usuario '{user.username}' registrado desde la IP: {client_ip}")
        return Response({'token': token.key, 'user': serializer.data}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=['Usuarios'])
@api_view(['GET'])
# No se necesita @permission_classes([IsAuthenticated]) porque es el default.
def profile(request):
    """
    Una vista protegida que devuelve los datos del usuario autenticado.
    """
    serializer = UserSerializer(instance=request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
