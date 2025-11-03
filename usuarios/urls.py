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
    path('profile/', views.profile, name='profile')
]