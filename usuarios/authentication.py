from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Extiende la autenticación por token para añadir un tiempo de expiración.
    """
    def authenticate_credentials(self, key):
        # Llama al método original para obtener el usuario y el token
        user, token = super().authenticate_credentials(key)

        # Comprueba si el token ha expirado
        token_lifetime = getattr(settings, 'TOKEN_LIFETIME', timedelta(days=1))

        if token.created < timezone.now() - token_lifetime:
            # El token ha expirado, lo eliminamos y lanzamos un error
            token.delete()
            raise AuthenticationFailed('El token ha expirado.')

        # Si se quiere que el token se renueve con cada petición (sliding window)
        # token.created = timezone.now()
        # token.save()

        return (user, token)