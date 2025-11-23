from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import password_validation
from rest_framework.exceptions import ValidationError

# SERIALIZERS USUARIOS
import uuid

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'read_only': True}
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
        return data

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        
        # Generar un nombre de usuario único a partir del email
        username_base = email.split('@')[0]
        username = username_base
        while User.objects.filter(username=username).exists():
            # Si el usuario ya existe, añade un hash corto para hacerlo único
            unique_hash = uuid.uuid4().hex[:4]
            username = f"{username_base}_{unique_hash}"

        # Crear el usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password': 'Las nuevas contraseñas no coinciden.'})
        
        user = self.context['request'].user
        new_password = data['new_password']

        # --- Validación de contraseña personalizada ---        
        # 1. Creamos un validador de similitud que explícitamente ignora el email.
        custom_similarity_validator = password_validation.UserAttributeSimilarityValidator(
            user_attributes=('username', 'first_name', 'last_name') # Excluimos 'email'
        )

        # 2. Creamos la lista de validadores que vamos a usar.
        validators = [
            custom_similarity_validator,
            password_validation.MinimumLengthValidator(),
            password_validation.CommonPasswordValidator(),
            password_validation.NumericPasswordValidator(),
        ]

        # 3. Ejecutamos la validación.
        try:
            password_validation.validate_password(new_password, user, password_validators=validators)
        except ValidationError as e:
            # Si hay errores de validación, los lanzamos.
            raise serializers.ValidationError({'new_password': list(e.messages)})

        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña antigua no es correcta.')
        return value

# --- SERIALIZERS OLVIDÉ MI CONTRASEÑA ---

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value).exists():
            # Por seguridad, no revelamos si el email existe o no.
            # Simplemente no hacemos nada, pero el serializer es válido.
            # La vista se encargará de no enviar el correo.
            pass
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password2 = serializers.CharField(required=True, write_only=True)
