from django.db import models
from empleados.models import Empleado

# MODELS DE HORARIOS
class Horarios(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    lunes = models.BooleanField(default=True)
    martes = models.BooleanField(default=True)
    miercoles = models.BooleanField(default=True)
    jueves = models.BooleanField(default=True)
    viernes = models.BooleanField(default=True)
    sabado = models.BooleanField(default=False)
    domingo = models.BooleanField(default=False)
    cantidad_personal_requerida = models.PositiveIntegerField(default=1, verbose_name="Cantidad de Personal Requerida")

    def __str__(self):
        return f"{self.nombre} ({self.hora_entrada.strftime('%H:%M')} - {self.hora_salida.strftime('%H:%M')})"

class AsignacionHorario(models.Model):
    id_empl = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asignaciones_horario')
    id_horario = models.ForeignKey(Horarios, on_delete=models.CASCADE, related_name='asignaciones')
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Asignación de {self.id_empl.nombre} {self.id_empl.apellido} - {self.id_horario.nombre}"
