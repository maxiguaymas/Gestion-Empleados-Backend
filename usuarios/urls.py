from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
# router.register(r'empleados', EmpleadoViewSet)
# router.register(r'legajos', LegajoViewSet)
# router.register(r'documentos', DocumentoViewSet)

urlpatterns = [
    # path('', include(router.urls)),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change-password'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]