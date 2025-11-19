# c:\proyectos\backend-nuevas-energias\asistencias\urls.py

from django.urls import path
from .views import (
    RegistrarRostroAPIView,
    ReconocerRostroAPIView,
    AsistenciaEmpleadoAPIView,
    EmpleadosSinRostroAPIView, 
    EmpleadosConRostroAPIView,
    ResumenAsistenciaDiariaAPIView
)

urlpatterns = [
    # Endpoint para obtener la lista de empleados sin rostro (para el admin)
    # GET: /api/asistencias/empleados-sin-rostro/
    path('empleados-sin-rostro/', EmpleadosSinRostroAPIView.as_view(), name='api_empleados_sin_rostro'),

    # Endpoint para obtener la lista de empleados con rostro (para el admin)
    # GET: /api/asistencias/empleados-con-rostro/
    path('empleados-con-rostro/', EmpleadosConRostroAPIView.as_view(), name='api_empleados_con_rostro'),

    # Endpoint para registrar o actualizar un rostro
    # POST: /api/asistencias/rostro/ (Crea un nuevo registro de rostro)
    # PUT: /api/asistencias/rostro/ (Actualiza un registro de rostro existente)
    path('rostro/', RegistrarRostroAPIView.as_view(), name='api_gestionar_rostro'),

    # Endpoint para que un empleado marque su asistencia
    # POST: /api/asistencias/marcar/
    path('marcar/', ReconocerRostroAPIView.as_view(), name='api_marcar_asistencia'),

    # Endpoint para ver las asistencias de un empleado específico
    # GET: /api/asistencias/por-empleado/123/
    path('asistencias-empleado/<int:empleado_id>/', AsistenciaEmpleadoAPIView.as_view(), name='api_asistencias_por_empleado'),
    
    # Endpoint para que un empleado vea sus propias asistencias (más seguro)
    # GET: /api/asistencias/mis-asistencias/
    path('mis-asistencias/', AsistenciaEmpleadoAPIView.as_view(), name='api_mis_asistencias'),

    # Endpoint para obtener un resumen de las asistencias del día
    # GET: /api/asistencias/resumen-diario/
    path('resumen-diario/', ResumenAsistenciaDiariaAPIView.as_view(), name='api_resumen_diario'),
]
