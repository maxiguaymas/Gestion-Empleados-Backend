from django.urls import path
from .views import NotificacionesUsuarioView

urlpatterns = [
    path('mis-notificaciones/', NotificacionesUsuarioView.as_view(), name='mis-notificaciones'),
]