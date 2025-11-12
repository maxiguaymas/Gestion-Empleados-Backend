from django.utils import timezone
from datetime import datetime
import json
from django.db import models
from empleados.models import Empleado

class Rostro(models.Model):
    id_empl = models.OneToOneField(Empleado, on_delete=models.CASCADE, primary_key=True)
    encoding = models.TextField() # Almacenaremos el encoding facial como un string JSON

    def set_encoding(self, encoding_array):
        self.encoding = json.dumps(encoding_array.tolist())

    def get_encoding(self):
        return json.loads(self.encoding)

    def __str__(self):
        return f"Rostro de {self.id_empl.nombre} {self.id_empl.apellido}"

class Asistencia(models.Model):
    id_empl = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(default=timezone.now)
    minutos_retraso= models.IntegerField(default=0)
    # Podrías agregar un campo 'tipo' si quieres diferenciar entre 'Entrada' y 'Salida'
    
    def calcular_retraso(self):
        """
        Calcula los minutos de retraso basados en el horario asignado al empleado.
        """
        # Importación local para evitar dependencia circular
        from horarios.models import AsignacionHorario
        asignacion = AsignacionHorario.objects.filter(
            id_empl=self.id_empl,
            estado=True,
            fecha_asignacion__lte=self.fecha_hora.date()
        ).order_by('-fecha_asignacion').first()

        if asignacion:
            horario = asignacion.id_horario
            hora_entrada_esperada = horario.hora_entrada
            
            fecha_asistencia = self.fecha_hora.date()
            hora_entrada_dt = timezone.make_aware(datetime.combine(fecha_asistencia, hora_entrada_esperada))
            
            if self.fecha_hora > hora_entrada_dt:
                retraso = self.fecha_hora - hora_entrada_dt
                return int(retraso.total_seconds() / 60)
        
        return 0

    def __str__(self):
        return f"Asistencia de {self.id_empl.nombre} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"