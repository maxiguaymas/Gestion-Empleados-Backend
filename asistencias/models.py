from django.utils import timezone
from datetime import datetime
import json
from django.db import models
from empleados.models import Empleado
from horarios.models import AsignacionHorario

# Create your models here.

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
    minutos_retraso = models.IntegerField(default=0)
    # NUEVO CAMPO: Vincula la asistencia a un turno específico.
    # Es nullable para permitir registros manuales o casos sin turno asignado.
    id_asignacion_horario = models.ForeignKey(
        AsignacionHorario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def calcular_retraso(self):
        """
        Calcula los minutos de retraso basados en el turno vinculado a esta asistencia.
        """
        # La lógica ahora es más simple: usa el horario de la asignación ya vinculada.
        if self.id_asignacion_horario and self.id_asignacion_horario.id_horario:
            horario = self.id_asignacion_horario.id_horario
            hora_entrada_esperada = horario.hora_entrada

            fecha_hora_local = timezone.localtime(self.fecha_hora)
            fecha_asistencia = fecha_hora_local.date()

            naive_hora_entrada = datetime.combine(fecha_asistencia, hora_entrada_esperada)
            hora_entrada_dt = timezone.make_aware(naive_hora_entrada)

            if self.fecha_hora > hora_entrada_dt:
                retraso = self.fecha_hora - hora_entrada_dt
                return int(retraso.total_seconds() / 60)

        return 0

    def __str__(self):
        return f"Asistencia de {self.id_empl.nombre} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"