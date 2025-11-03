from rest_framework import serializers
from django.contrib.auth.models import User


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
