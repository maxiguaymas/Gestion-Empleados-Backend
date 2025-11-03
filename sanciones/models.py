from datetime import timezone
from django.db import models
from empleados.models import Empleado
from incidentes.models import IncidenteEmpleado

# MODELS DE SANCIONES

class Sancion(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class SancionEmpleado(models.Model):
    id_empl = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='sanciones_empleado')
    id_sancion = models.ForeignKey(Sancion, on_delete=models.CASCADE)
    incidente_asociado = models.ForeignKey(IncidenteEmpleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='sanciones')
    fecha_sancion = models.DateField(auto_now_add=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    motivo = models.CharField(max_length=255)
    responsable = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='sanciones_creadas', help_text="Empleado que registra la sanción.")

    class Meta:
        verbose_name = "Sanción de Empleado"
        verbose_name_plural = "Sanciones de Empleados"

    @property
    def esta_activa(self):
        """
        Determina si la sanción está activa dinámicamente.
        Una sanción está activa si la fecha actual se encuentra
        entre la fecha de inicio y la fecha de fin (inclusive).
        Si no hay fecha_fin, se considera activa indefinidamente
        a partir de la fecha_inicio.
        """
        hoy = timezone.now().date()
        if self.fecha_fin is None:
            return hoy >= self.fecha_inicio
        return self.fecha_inicio <= hoy <= self.fecha_fin

    def __str__(self):
        return f"Sancion {self.id_sancion.nombre} para {self.id_empl.nombre} {self.id_empl.apellido}"
