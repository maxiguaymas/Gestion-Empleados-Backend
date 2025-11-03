from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django.db import transaction
from .models import Empleado, Legajo, Documento, RequisitoDocumento
from notificaciones.models import Notificacion

# SERIALIZERS EMPLEADOS

class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        exclude = ('id_leg',)

class RequisitoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisitoDocumento
        fields = '__all__'

class LegajoSerializer(serializers.ModelSerializer):
    documento_set = DocumentoSerializer(many=True, read_only=True)

    class Meta:
        model = Legajo
        fields = ['id', 'estado_leg', 'fecha_creacion_leg', 'nro_leg', 'fecha_modificacion_leg', 'documento_set']

class EmpleadoSerializer(serializers.ModelSerializer):
    grupo = serializers.CharField(write_only=True, required=True)
    ruta_foto = serializers.ImageField(required=False, allow_null=True)
    legajo = LegajoSerializer(read_only=True)

    class Meta:
        model = Empleado
        fields = [
            'id', 'nombre', 'apellido', 'dni', 'telefono', 'email', 'genero', 
            'estado_civil', 'fecha_nacimiento', 'estado', 'ruta_foto', 
            'fecha_ingreso', 'fecha_egreso', 'legajo', 'grupo'
        ]
        read_only_fields = ('legajo',)

    def validate(self, data):
        """
        Validación a nivel de objeto para asegurar que se envíen los documentos obligatorios.
        """
        request = self.context.get('request')
        if not request or not hasattr(request, 'FILES'):
            return data

        requisitos_obligatorios = RequisitoDocumento.objects.filter(obligatorio=True, estado_doc=True)
        for requisito in requisitos_obligatorios:
            nombre_campo_archivo = f'documento_{requisito.id}'
            if nombre_campo_archivo not in request.FILES:
                raise serializers.ValidationError(f"El documento obligatorio '{requisito.nombre_doc}' no fue proporcionado.")
        return data

    def create(self, validated_data):
        """
        Sobrescribe el método de creación para:
        1. Crear un usuario con su DNI.
        2. Asignar el usuario al grupo especificado.
        3. Crear el Empleado y asociarlo al nuevo usuario.
        4. Crear el Legajo asociado al nuevo empleado.
        5. Guardar los documentos adjuntos.
        Todo dentro de una transacción para asegurar la integridad de los datos.
        """
        request = self.context.get('request')
        try:
            with transaction.atomic():
                # Extraemos el nombre del grupo y el DNI de los datos validados.
                grupo_nombre = validated_data.pop('grupo')
                dni = validated_data.get('dni')
                email= validated_data.get('email')


                # 1. Crear el usuario
                if User.objects.filter(username=str(dni)).exists():
                    raise serializers.ValidationError({'dni': 'Ya existe un usuario con este DNI.'})
                
                user = User.objects.create_user(username=str(dni), password=str(dni), email=str(email))

                # 2. Asignar el grupo
                try:
                    grupo = Group.objects.get(name=grupo_nombre)
                    user.groups.add(grupo)
                except Group.DoesNotExist:
                    raise serializers.ValidationError({'grupo': f"El grupo '{grupo_nombre}' no existe."})

                # 3. Crear el Empleado, asociando el usuario recién creado.
                empleado = Empleado.objects.create(user=user, **validated_data)

                # Crear la notificación de bienvenida para el nuevo usuario.
                Notificacion.objects.create(
                    id_user=user,
                    mensaje=f"¡Bienvenido/a, {empleado.nombre}! Tu perfil ha sido creado exitosamente.",
                    enlace="/empleados/perfil/"
                )
                # 4. Crear el Legajo asociado y generar nro_leg secuencial.
                last_legajo = Legajo.objects.order_by('-nro_leg').first()
                new_nro_leg = (last_legajo.nro_leg + 1) if last_legajo else 1
                legajo = Legajo.objects.create(id_empl=empleado, estado_leg='Pendiente', nro_leg=new_nro_leg)

                # 5. Guardar los documentos adjuntos
                if request and hasattr(request, 'FILES'):
                    for key, file in request.FILES.items():
                        if key.startswith('documento_'):
                            try:
                                requisito_id = int(key.split('_')[1])
                                requisito = RequisitoDocumento.objects.get(pk=requisito_id)
                                Documento.objects.create(id_leg=legajo, id_requisito=requisito, ruta_archivo=file)
                            except (ValueError, RequisitoDocumento.DoesNotExist):
                                continue # Ignora archivos con formato de clave incorrecto o ID de requisito no válido

                return empleado
        except Exception as e:
            # Si algo falla, lanzamos una excepción para que la transacción haga rollback.
            raise serializers.ValidationError(str(e))
