from django.urls import path
from .views import NotificacionesUsuarioView, MarcarTodasLeidasView

urlpatterns = [
    path('mis-notificaciones/', NotificacionesUsuarioView.as_view(), name='mis-notificaciones'),
    path('notificaciones/marcar-todas-leidas/', MarcarTodasLeidasView.as_view(), name='marcar-todas-leidas'),
]