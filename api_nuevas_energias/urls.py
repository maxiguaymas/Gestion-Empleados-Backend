"""
URL configuration for api_nuevas_energias project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    # Redirige la ruta raíz a la documentación de Swagger UI
    path('', RedirectView.as_view(url='/api/schema/swagger-ui/', permanent=False)),
    path('admin/', admin.site.urls),
    
    path('api/', include([
        path('', include('empleados.urls')),
        path('', include('usuarios.urls')),
        path('', include('recibos.urls')),
        path('', include('horarios.urls')),
        path('', include('incidentes.urls')),
        path('', include('sanciones.urls')),
        path('', include('asistencias.urls')),
       
        # demas apps...
    ])),
    # URLs de la documentación de la API (Swagger / OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
