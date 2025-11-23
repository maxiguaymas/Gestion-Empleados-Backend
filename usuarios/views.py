from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status, generics
from .serializers import UserSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string



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
    
    # Comprobar si el usuario es un empleado y si necesita cambiar la contraseña.
    must_change_password = False
    nombre_empleado = None
    apellido_empleado = None
    grupo_usuario = None

    if hasattr(user, 'empleado'):
        empleado = user.empleado
        if not user.empleado.password_cambiada:
            must_change_password = True
        
        nombre_empleado = empleado.nombre
        apellido_empleado = empleado.apellido

    if user.groups.exists():
        grupo_usuario = user.groups.first().name

    logger.info(f"Login exitoso para el usuario '{user.username}'. IP: {client_ip}")
    return Response({
        'token': token.key, 
        'user': serializer.data,
        'must_change_password': must_change_password,
        'nombre': nombre_empleado,
        'apellido': apellido_empleado,
        'grupo': grupo_usuario,
    }, status=status.HTTP_200_OK)

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

@extend_schema(
    tags=['Usuarios'],
    request=ChangePasswordSerializer,
    responses={200: 'Contraseña cambiada exitosamente.'}
)
@api_view(['POST'])
# Por defecto, se requiere que el usuario esté autenticado.
def change_password(request):
    """
    Permite a un usuario autenticado cambiar su contraseña.
    """
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Si el usuario es un empleado, marcar que la contraseña ha sido cambiada.
        if hasattr(user, 'empleado'):
            user.empleado.password_cambiada = True
            user.empleado.save(update_fields=['password_cambiada'])

        logger.info(f"El usuario '{user.username}' ha cambiado su contraseña exitosamente. IP: {get_client_ip(request)}")
        return Response({'message': 'Contraseña cambiada exitosamente.'}, status=status.HTTP_200_OK)
    
    logger.warning(f"Fallo al cambiar contraseña para el usuario '{request.user.username}'. Errores: {serializer.errors}. IP: {get_client_ip(request)}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- VISTAS OLVIDÉ MI CONTRASEÑA ---

@extend_schema(tags=['Usuarios'])
class PasswordResetRequestView(generics.GenericAPIView):
    """
    Vista para solicitar el reseteo de contraseña.
    Recibe un email y envía un correo con el token de reseteo si el usuario existe.
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        user = User.objects.filter(email__iexact=email).first()

        if user:
            # Generar token y UID
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # URL del frontend (debes configurarla en tu frontend)
            # TODO: Mover esta URL a settings.py para que sea configurable
            frontend_url = 'http://localhost:3000/nueva-contrasena' 
            reset_link = f'{frontend_url}?uid={uid}&token={token}'

            # Renderizar el template HTML para el correo
            html_message = render_to_string('email/password_reset_email.html', {
                'user': user,
                'reset_link': reset_link,
            })

            # Enviar correo electrónico
            send_mail(
                'Restablecimiento de Contraseña',
                '', # El mensaje de texto plano se puede dejar vacío si se usa html_message
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message
            )
        
        # Por seguridad, siempre devolvemos la misma respuesta
        return Response(
            {'detail': 'Si existe una cuenta con ese correo, se ha enviado un email con las instrucciones.'},
            status=status.HTTP_200_OK
        )

@extend_schema(tags=['Usuarios'])
class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Vista para confirmar el reseteo de contraseña.
    Recibe uid, token y la nueva contraseña.
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        if data['new_password'] != data['new_password2']:
            return Response({'new_password': 'Las contraseñas no coinciden.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.warning(f"Fallo en reseteo de contraseña: UID inválido ('{data['uid']}') o usuario no existe. Error: {e}. IP: {get_client_ip(request)}")
            user = None

        if user is not None and default_token_generator.check_token(user, data['token']):
            try:
                # --- Validación de contraseña personalizada (igual que en change_password) ---
                # 1. Creamos un validador de similitud que explícitamente ignora el email.
                custom_similarity_validator = password_validation.UserAttributeSimilarityValidator(
                    user_attributes=('username', 'first_name', 'last_name') # Excluimos 'email'
                )
                # 2. Creamos la lista de validadores que vamos a usar.
                validators = [
                    custom_similarity_validator,
                    password_validation.MinimumLengthValidator(),
                    password_validation.CommonPasswordValidator(),
                    password_validation.NumericPasswordValidator(),
                ]
                password_validation.validate_password(data['new_password'], user, password_validators=validators)
            except ValidationError as e:
                logger.warning(f"Fallo en reseteo de contraseña para '{user.username}': La nueva contraseña no pasó la validación. Errores: {e.messages}. IP: {get_client_ip(request)}")
                return Response({'new_password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(data['new_password'])
            user.save()
            logger.info(f"El usuario '{user.username}' ha restablecido su contraseña exitosamente. IP: {get_client_ip(request)}")
            return Response({'detail': 'Contraseña restablecida con éxito.'}, status=status.HTTP_200_OK)
        else:
            # Este es el punto más probable de fallo si el token ha expirado o es incorrecto.
            log_username = user.username if user else "desconocido"
            logger.warning(f"Fallo en reseteo de contraseña para usuario '{log_username}': El token es inválido o ha expirado. IP: {get_client_ip(request)}")
            return Response({'detail': 'El enlace de reseteo es inválido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)
