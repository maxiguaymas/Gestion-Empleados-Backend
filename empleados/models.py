from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse

# Create your models here.
def validar_mayor_18(value):
    hoy = timezone.now().date()
    edad = hoy.year - value.year - ((hoy.month, hoy.day) < (value.month, value.day))
    if edad < 18:
        raise ValidationError('El empleado debe ser mayor de 18 años.')

# MODELS EMPLEADOS
class Empleado(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empleado')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.IntegerField(unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    genero = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], default='O')
    estado_civil = models.CharField(max_length=20, choices=[('Soltero', 'Soltero'), ('Casado', 'Casado'), ('Divorciado', 'Divorciado'), ('Viudo', 'Viudo')], default='Soltero')
    fecha_nacimiento = models.DateField(validators=[validar_mayor_18])
    estado = models.CharField(max_length=20, choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo'), ('Suspendido', 'Suspendido'), ('Licencia', 'Licencia')], default='Activo')
    ruta_foto = models.ImageField(upload_to='empleados/fotos/', blank=True, null=True)
    fecha_ingreso = models.DateField(auto_now_add=True)
    fecha_egreso = models.DateField(blank=True, null=True)
    


    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.dni}"
    
    def get_iniciales(self):
        # Misma lógica que arriba
        if self.nombre and self.apellido:
            return f"{self.nombre[0]}{self.apellido[0]}".upper()
        elif self.nombre:
            return f"{self.nombre[0]}".upper()
        return ""

    def get_absolute_url(self):
        return reverse('ver_empleado', kwargs={'id': self.id})
    

class RequisitoDocumento(models.Model):
    nombre_doc = models.CharField(max_length=100)
    estado_doc = models.BooleanField(default=True)  # Activo/Inactivo
    obligatorio = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_doc

class Legajo(models.Model):
    id_empl = models.OneToOneField('Empleado', on_delete=models.CASCADE, related_name='legajo')
    estado_leg = models.CharField(max_length=50)
    fecha_creacion_leg = models.DateField(auto_now_add=True)
    nro_leg = models.IntegerField(unique=True)
    fecha_modificacion_leg = models.DateField(auto_now=True)

class Documento(models.Model):
    id_leg = models.ForeignKey(Legajo, on_delete=models.CASCADE)
    id_requisito = models.ForeignKey(RequisitoDocumento, on_delete=models.CASCADE)
    ruta_archivo = models.FileField(upload_to='legajos/documentos/')
    fecha_hora_subida = models.DateTimeField(auto_now_add=True)
    descripcion_doc = models.CharField(max_length=255, blank=True, null=True)
    estado_doc = models.BooleanField(default=True)