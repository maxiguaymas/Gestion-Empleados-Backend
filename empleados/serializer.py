from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
import logging
from .models import Empleado, Legajo, Documento, RequisitoDocumento
from notificaciones.models import Notificacion
logger = logging.getLogger(__name__)

# SERIALIZERS EMPLEADOS

class EmpleadoBasicoSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para Empleado.
    Muestra solo los campos principales, sin relaciones anidadas.
    """
    grupo = serializers.SerializerMethodField()
    ruta_foto = serializers.SerializerMethodField()

    class Meta:
        model = Empleado
        fields = ['id', 'nombre', 'apellido', 'dni', 'email', 'telefono', 'estado', 'fecha_ingreso', 'grupo', 'ruta_foto']

    def get_grupo(self, obj):
        """
        Devuelve el nombre del primer grupo al que pertenece el usuario asociado al empleado.
        """
        if hasattr(obj, 'user') and obj.user.groups.exists():
            return obj.user.groups.first().name
        return None

    def get_ruta_foto(self, obj):
        request = self.context.get('request')
        if request and obj.ruta_foto and hasattr(obj.ruta_foto, 'url'):
            return request.build_absolute_uri(obj.ruta_foto.url)
        return None

class DocumentoSerializer(serializers.ModelSerializer):
    ruta_archivo = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = ['id', 'id_requisito', 'ruta_archivo', 'fecha_hora_subida', 'descripcion_doc', 'estado_doc']

    def get_ruta_archivo(self, obj):
        request = self.context.get('request')
        if obj.ruta_archivo and hasattr(obj.ruta_archivo, 'url'):
            # Si el nombre del archivo es como 'vacio_*.txt', no construyas una URL completa
            if obj.ruta_archivo.name.startswith('vacio_') and obj.ruta_archivo.name.endswith('.txt'):
                return None
            return request.build_absolute_uri(obj.ruta_archivo.url)
        return None

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
    grupo = serializers.SerializerMethodField()
    grupo_input = serializers.CharField(write_only=True, required=True, source='grupo')
    ruta_foto = serializers.SerializerMethodField()
    legajo = LegajoSerializer(read_only=True)

    class Meta:
        model = Empleado
        fields = [
            'id', 'nombre', 'apellido', 'dni', 'telefono', 'email', 'genero', 'estado_civil', 
            'fecha_nacimiento', 'estado', 'ruta_foto', 'fecha_ingreso', 'fecha_egreso', 
            'legajo', 'grupo', 'grupo_input'
        ]
        read_only_fields = ('legajo',)
        extra_kwargs = {
            'dni': {
                'validators': [UniqueValidator(
                    queryset=Empleado.objects.all(),
                    message='Ya existe un empleado con este DNI.'
                )]
            },
            'email': {
                'validators': [UniqueValidator(
                    queryset=Empleado.objects.all(),
                    message='Ya existe un empleado con este correo electrónico.'
                )]
            },
            'telefono': {
                'validators': [UniqueValidator(
                    queryset=Empleado.objects.all(),
                    message='Ya existe un empleado con este número de teléfono.'
                )]
            },
        }

    def get_grupo(self, obj):
        """
        Devuelve el nombre del primer grupo al que pertenece el usuario asociado al empleado.
        """
        if hasattr(obj, 'user') and obj.user.groups.exists():
            return obj.user.groups.first().name
        return None

    def get_ruta_foto(self, obj):
        request = self.context.get('request')
        if obj.ruta_foto and hasattr(obj.ruta_foto, 'url'):
            return request.build_absolute_uri(obj.ruta_foto.url)
        return None

    def validate(self, data):
        """
        Validación a nivel de objeto para asegurar que se envíen los documentos obligatorios en la creación.
        """
        # Solo ejecutar esta validación en la creación (cuando no hay instancia)
        if self.instance is not None:
            return data

        request = self.context.get('request')
        # En la creación, los archivos pueden ser opcionales si no hay requisitos obligatorios
        if not request or not hasattr(request, 'FILES'):
            # Si no hay requisitos obligatorios, está bien no enviar archivos.
            if not RequisitoDocumento.objects.filter(obligatorio=True, estado_doc=True).exists():
                return data
            # Si hay requisitos obligatorios, pero no se envía ningún archivo, falla.
            raise serializers.ValidationError("No se proporcionaron archivos de documentos en la creación.")

        requisitos_obligatorios = RequisitoDocumento.objects.filter(obligatorio=True, estado_doc=True)
        for requisito in requisitos_obligatorios:
            nombre_campo_archivo = f'documento_{requisito.id}'
            if nombre_campo_archivo not in request.FILES:
                raise serializers.ValidationError(f"El documento obligatorio '{requisito.nombre_doc}' no fue proporcionado.")
        return data

    def update(self, instance, validated_data):
        """
        Sobrescribe el método de actualización para manejar la actualización de
        los datos del empleado y sus documentos asociados.
        """
        request = self.context.get('request')
        
        # El campo 'grupo' se maneja por separado. Si se envía 'grupo_input', actualizamos el grupo.
        if 'grupo' in validated_data:
            grupo_nombre = validated_data.pop('grupo')
            try:
                grupo = Group.objects.get(name=grupo_nombre)
                instance.user.groups.set([grupo])
            except Group.DoesNotExist:
                raise serializers.ValidationError({'grupo': f"El grupo '{grupo_nombre}' no existe."})

        # Si se recibe un nuevo email, actualizarlo también en el modelo User.
        if 'email' in validated_data:
            new_email = validated_data['email']
            user = instance.user
            if user.email != new_email:
                user.email = new_email
                user.save(update_fields=['email'])

        # Actualizar la instancia del empleado con los datos validados
        # Usamos pop para quitar 'ruta_foto' de validated_data si existe, ya que se maneja por separado.
        validated_data.pop('ruta_foto', None)
        instance = super().update(instance, validated_data)

        # Manejar la actualización de la foto de perfil si se envía un nuevo archivo
        if 'ruta_foto' in request.FILES:
            instance.ruta_foto = request.FILES['ruta_foto']
            instance.save(update_fields=['ruta_foto'])

        # Manejar la actualización de documentos del legajo
        if request and hasattr(request, 'FILES'):
            legajo = instance.legajo
            from django.core.files.base import ContentFile

            for key, file in request.FILES.items():
                if key.startswith('documento_'):
                    try:
                        requisito_id = int(key.split('_')[1])
                        requisito = RequisitoDocumento.objects.get(id=requisito_id)
                        
                        # Busca si ya existe un documento para este requisito y legajo
                        documento, created = Documento.objects.update_or_create(
                            id_leg=legajo,
                            id_requisito=requisito,
                            defaults={'ruta_archivo': file}
                        )
                        # Si el documento estaba 'vacío', actualiza su estado o lo que sea necesario
                        if not created and 'vacio' in documento.ruta_archivo.name:
                            # Opcional: Lógica adicional si se está reemplazando un placeholder
                            pass

                    except (ValueError, IndexError, RequisitoDocumento.DoesNotExist):
                        # Ignora archivos que no coincidan con un requisito válido
                        continue
        
        return instance

    def create(self, validated_data):
        """
        Sobrescribe el método de creación para:
        1. Crear un usuario con su DNI.
        2. Asignar el usuario al grupo especificado.
        3. Crear el Empleado y asociarlo al nuevo usuario.
        4. Crear el Legajo asociado al nuevo empleado.
        5. Guardar los documentos adjuntos y crear los faltantes.
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
                    enlace="/perfil/"
                )
                # 4. Crear el Legajo asociado y generar nro_leg secuencial.
                last_legajo = Legajo.objects.order_by('-nro_leg').first()
                new_nro_leg = (last_legajo.nro_leg + 1) if last_legajo else 1
                legajo = Legajo.objects.create(id_empl=empleado, estado_leg='Pendiente', nro_leg=new_nro_leg)

                # 5. Guardar los documentos adjuntos y crear los faltantes
                from django.core.files.base import ContentFile
                requisitos = RequisitoDocumento.objects.filter(estado_doc=True)
                uploaded_docs = {}
                if request and hasattr(request, 'FILES'):
                    for key, file in request.FILES.items():
                        if key.startswith('documento_'):
                            try:
                                requisito_id = int(key.split('_')[1])
                                uploaded_docs[requisito_id] = file
                            except (ValueError, IndexError):
                                continue

                for requisito in requisitos:
                    file = uploaded_docs.get(requisito.id)
                    if file:
                        Documento.objects.create(
                            id_leg=legajo,
                            id_requisito=requisito,
                            ruta_archivo=file
                        )
                    else:
                        empty_file = ContentFile(b"", name=f'vacio_{requisito.id}.txt')
                        Documento.objects.create(
                            id_leg=legajo,
                            id_requisito=requisito,
                            ruta_archivo=empty_file
                        )

                # 6. Enviar correo de bienvenida
                if empleado.email:
                    try:
                        logger.info(f"Intentando enviar correo de bienvenida a: {empleado.email}")
                        # La URL de login se construye a partir del request
                        # Asumimos que el frontend está en una URL base y añadimos /login
                        # Esto es más robusto que depender de `reverse` que apunta a la API.
                        host = request.get_host()
                        protocol = 'https' if request.is_secure() else 'http'
                        # Idealmente, la URL base del frontend debería estar en settings.
                        # Por ahora, asumimos que el login está en la raíz.
                        login_url = f"{protocol}://{host.split(':')[0]}/login" # Ajusta esta URL si es necesario

                        asunto = "¡Bienvenido/a a Nuevas Energías! - Tu cuenta ha sido creada"
                        
                        # Renderizar el template HTML
                        cuerpo_mensaje_html = render_to_string('email/bienvenida_empleado.html', {
                            'empleado_nombre': empleado.nombre,
                            'username': dni,
                            'password': dni, # La contraseña es el DNI
                            'login_url': login_url,
                        })
                        
                        send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [empleado.email], html_message=cuerpo_mensaje_html)
                        logger.info(f"Correo de bienvenida enviado exitosamente a {empleado.email}")
                    except Exception as e:
                        logger.error(f"ERROR al enviar correo de bienvenida a {empleado.email}: {e}")

                return empleado
        except Exception as e:
            # Si algo falla, lanzamos una excepción para que la transacción haga rollback.
            raise serializers.ValidationError(str(e))
