from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReciboSueldosViewSet

router = DefaultRouter()
router.register(r'recibos', ReciboSueldosViewSet)

urlpatterns = [
    path('', include(router.urls)),
]