from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReciboSueldosViewSet, MisRecibosView

router = DefaultRouter()
router.register(r'recibos', ReciboSueldosViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('mis-recibos/', MisRecibosView.as_view(), name='mis-recibos'),
]