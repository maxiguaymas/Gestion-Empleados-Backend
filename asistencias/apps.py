from django.apps import AppConfig


class AsistenciasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'asistencias'

    def ready(self):
        # Importa las señales para que se registren cuando la aplicación esté lista.
        import asistencias.signals
