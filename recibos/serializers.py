from rest_framework import serializers
from .models import Recibo_Sueldos

class ReciboSueldosSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Recibo_Sueldos.
    """
    class Meta:
        model = Recibo_Sueldos
        fields = ['id', 'id_empl', 'fecha_emision', 'periodo', 'ruta_pdf', 'ruta_imagen']
        read_only_fields = ('id',)