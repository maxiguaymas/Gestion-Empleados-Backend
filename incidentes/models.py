from django.db import models
from empleados.models import Empleado
from django.conf import settings
import uuid
from django.utils import timezone

# INCIDENTES
class Incidente(models.Model):
    tipo_incid = models.CharField(max_length=255)
    descripcion_incid= models.CharField(max_length=255)
    estado_incid = models.BooleanField(default=True)

    def __str__(self):
        return self.tipo_incid
    
class Descargo(models.Model):
    id_incid_empl = models.ForeignKey('IncidenteEmpleado', on_delete=models.CASCADE, related_name='descargos')
    autor = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_descargo = models.DateTimeField(default=timezone.now)
    contenido_descargo = models.CharField(max_length=255)
    ruta_archivo_descargo = models.FileField(upload_to='descargos/', blank=True, null=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"Descargo para Incidente ID: {self.id_incid_empl.id}"

class IncidenteEmpleado(models.Model):
    ESTADO_CHOICES = [
        ('ABIERTO', 'Abierto'),
        ('CERRADO', 'Cerrado'),
        ('CORREGIDO', 'Corregido'),
    ]
    grupo_incidente = models.UUIDField(default=uuid.uuid4, editable=False, help_text="Identificador único para agrupar incidentes creados en la misma operación.")

    id_incidente = models.ForeignKey(Incidente, on_delete=models.CASCADE)
    id_empl = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_ocurrencia = models.DateField()
    observaciones = models.CharField(max_length=255)
    responsable_registro = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ABIERTO')

    class Meta:
        # Se elimina unique_together para permitir que un empleado tenga múltiples incidentes del mismo tipo en fechas diferentes.
        pass

    def __str__(self):
        return f"Inc. {self.id_incidente.tipo_incid} - Emp. {self.id_empl.nombre} {self.id_empl.apellido}"

class Resolucion(models.Model):
    grupo_incidente = models.UUIDField(unique=True, help_text="El grupo de incidentes que esta resolución cierra.")
    fecha_resolucion = models.DateTimeField(default=timezone.now)
    descripcion = models.CharField(max_length=255)
    responsable = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"Resolucion para Grupo de Incidentes: {self.grupo_incidente}"

    def save(self, *args, **kwargs):
        # Al guardar la resolución, cerramos todos los incidentes del grupo.
        super().save(*args, **kwargs)
        IncidenteEmpleado.objects.filter(grupo_incidente=self.grupo_incidente).update(estado='CERRADO')
        
    def get_incidentes_asociados(self):
        return IncidenteEmpleado.objects.filter(grupo_incidente=self.grupo_incidente)
