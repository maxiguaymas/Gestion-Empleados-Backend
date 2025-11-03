from django.db import models

# MODELS DE RECIBOS
class Recibo_Sueldos(models.Model):
    id_empl = models.ForeignKey('empleados.Empleado', on_delete=models.CASCADE, related_name='recibos')
    fecha_emision = models.DateField()
    periodo = models.CharField(max_length=7)
    ruta_pdf = models.FileField(upload_to='recibos/pdf/')
    ruta_imagen = models.ImageField(upload_to='recibos/imagenes/', blank=True, null=True)

    def __str__(self):
        return f"Recibo {self.pk} - {self.id_empl.nombre} {self.id_empl.apellido}"
  #Clase horarios debe estar al mismo nivel que Empleado