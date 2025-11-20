from django.contrib import admin
from .models import Notificacion

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id_user', 'mensaje', 'leida', 'fecha_creacion')
    list_filter = ('leida', 'fecha_creacion')
    search_fields = ('id_user__username', 'mensaje')
