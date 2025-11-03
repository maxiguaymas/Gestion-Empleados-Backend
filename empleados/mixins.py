from rest_framework.exceptions import PermissionDenied

class AdminWriteAccessMixin:
    """
    Mixin para restringir las operaciones de escritura (create, update, destroy)
    solo a usuarios del grupo 'Administradores' o superusuarios.
    """
    def _check_admin_privileges(self, request):
        """Comprueba si el usuario tiene privilegios de administrador."""
        is_admin = request.user and (
            request.user.is_superuser or
            request.user.groups.filter(name='Administrador').exists()
        )
        if not is_admin:
            raise PermissionDenied("No tiene permiso para realizar esta acción.")

    def create(self, request, *args, **kwargs):
        self._check_admin_privileges(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._check_admin_privileges(request)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._check_admin_privileges(request)
        return super().destroy(request, *args, **kwargs)