from django.db import models
from django.contrib.auth.models import User

# NOTIFICACIONES
class Notificacion(models.Model):
    id_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones', help_text="Empleado que recibirá la notificación.")
    mensaje = models.TextField(help_text="El contenido de la notificación.")
    leida = models.BooleanField(default=False, help_text="Indica si la notificación ha sido leída.")
    fecha_creacion = models.DateTimeField(auto_now_add=True, help_text="Fecha y hora de creación de la notificación.")
    enlace = models.CharField(max_length=255, blank=True, null=True, help_text="URL a la que se redirigirá al hacer clic. Puede ser una URL absoluta o una ruta relativa de Django.")

    def __str__(self):
        """
        Representación en cadena del modelo, útil en el panel de administración.
        """
        return f"Notificación para {self.id_user.username} - Leída: {self.leida}"

    class Meta:
        ordering = ['-fecha_creacion']  # Ordena las notificaciones de más reciente a más antigua.
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
