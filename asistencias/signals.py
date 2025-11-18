from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Rostro

# Definimos la clave del caché como una constante para reutilizarla de forma segura
# y evitar errores de tipeo en otras partes del código.
KNOWN_FACES_CACHE_KEY = 'known_faces_data'

@receiver([post_save, post_delete], sender=Rostro)
def invalidar_cache_rostros(sender, instance, **kwargs):
    """
    Esta señal se activa cada vez que un objeto Rostro se guarda (crea/actualiza)
    o se elimina. Su única función es borrar el caché de rostros conocidos.
    La próxima vez que la vista de reconocimiento se ejecute, reconstruirá
    este caché con los datos actualizados de la base de datos.
    """
    cache.delete(KNOWN_FACES_CACHE_KEY)