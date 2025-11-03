# API de Gestión de Recursos Humanos - Nuevas Energías

![Django](https://img.shields.io/badge/Django-4.2-blue?logo=django)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-blue?logo=postgresql)
![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.14-red)

API RESTful desarrollada con Django y Django REST Framework para la gestión integral de los recursos humanos de la empresa "Nuevas Energías". El sistema centraliza la información de empleados, legajos, incidentes, sanciones y recibos de sueldo, proporcionando un acceso seguro y basado en roles.

## ✨ Características Principales

- **Gestión de Empleados:** CRUD completo para empleados, incluyendo datos personales, legajo digital y documentos.
- **Control de Incidentes:** Registro de incidentes, asignación a empleados, gestión de descargos y resoluciones.
- **Sistema de Sanciones:** Aplicación y seguimiento de sanciones a empleados.
- **Recibos de Sueldo:** Carga y consulta de recibos de sueldo digitales.
- **Autenticación por Token:** Sistema de autenticación seguro con tokens de duración limitada que expiran automáticamente.
- **Notificaciones Automáticas:** Notificaciones en tiempo real para eventos clave (nuevos incidentes, resoluciones, sanciones, etc.).
- **Roles y Permisos:** Acceso diferenciado para Administradores y Empleados, garantizando que los usuarios solo accedan a la información permitida.
- **Documentación de API Automatizada:** Documentación interactiva generada con `drf-spectacular` (Swagger/OpenAPI).
- **Gestión de Archivos:** Soporte para carga de fotos de perfil, documentos de legajo y archivos adjuntos en incidentes.

## 🛠️ Tecnologías Utilizadas

- **Backend:** Django, Django REST Framework
- **Base de Datos:** PostgreSQL
- **Autenticación:** `rest_framework.authtoken` (extendido para expiración)
- **Documentación:** `drf-spectacular`
- **CORS:** `django-cors-headers`
- **Variables de Entorno:** `python-decouple` (recomendado)

## 📂 Estructura del Proyecto

El proyecto está organizado en las siguientes aplicaciones de Django:

- `usuarios`: Gestiona la autenticación, usuarios y grupos.
- `empleados`: Contiene los modelos y la lógica para Empleados, Legajos y Documentos.
- `incidentes`: Maneja todo lo relacionado con Incidentes, Descargos y Resoluciones.
- `sanciones`: Define los tipos de sanciones y su aplicación a los empleados.
- `recibos`: Gestiona los recibos de sueldo de los empleados.
- `notificaciones`: Provee el sistema de notificaciones para los usuarios.
- `horarios`: (Placeholder para futura funcionalidad de gestión de horarios).

---

## 🚀 Instalación y Puesta en Marcha

Sigue estos pasos para configurar el entorno de desarrollo local.

### 1. Prerrequisitos

- Python 3.10 o superior
- Pip & venv
- Git
- PostgreSQL

### 2. Clonar el Repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd backend-nuevas-energias
```

### 3. Configurar el Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows
.\venv\Scripts\activate

# Activar en macOS/Linux
source venv/bin/activate
```

### 4. Instalar Dependencias

Crea un archivo `requirements.txt` con las dependencias del proyecto y luego instálalo.

```bash
# Congela las dependencias si tienes el proyecto corriendo
pip freeze > requirements.txt

# Instala las dependencias desde el archivo
pip install -r requirements.txt
```

### 5. Aplicar Migraciones

Aplica las migraciones para crear las tablas en la base de datos.

```bash
python manage.py migrate
```

### 6. Crear un Superusuario

Esto te permitirá acceder al panel de administración de Django.

```bash
python manage.py createsuperuser
```

### 7. Ejecutar el Servidor de Desarrollo

```bash
python manage.py runserver
```

La API estará disponible en `http://127.0.0.1:8000/`.

---

## 📚 Documentación de la API (Swagger)

Una vez que el servidor esté en funcionamiento, puedes acceder a la documentación interactiva de la API a través de Swagger UI.

- **Swagger UI:** `http://127.0.0.1:8000/api/schema/swagger-ui/`
- **Schema JSON:** `http://127.0.0.1:8000/api/schema/`

Desde esta interfaz, podrás ver todos los endpoints disponibles, sus parámetros, y probarlos directamente.

## 🔑 Autenticación

La API utiliza un sistema de autenticación por token con tiempo de expiración.

1.  **Obtener un Token:** Envía una petición `POST` al endpoint `/api/login/` con el `username` y `password` del usuario.

    ```json
    {
        "username": "user_dni",
        "password": "user_password"
    }
    ```

2.  **Usar el Token:** Incluye el token recibido en la cabecera `Authorization` de tus peticiones a los endpoints protegidos.

    ```
    Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
    ```

El token tiene una vida útil de **12 horas** (configurable en `settings.py` con `TOKEN_LIFETIME`). Después de este tiempo, el token expira y se debe solicitar uno nuevo.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.