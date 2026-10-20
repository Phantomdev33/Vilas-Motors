# Vila’s Motor

Aplicación de gestión de mantención de flota con React, Vite, Django REST Framework y PostgreSQL. Incluye equipos, lecturas, mantenciones, calendario, alertas, reportes PDF/Excel y usuarios con permisos por rol.

## Inicio local en Windows

Desde la raíz del proyecto, en PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-runtime.ps1
powershell -ExecutionPolicy Bypass -File scripts/setup-postgres.ps1
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

Los scripts instalan las herramientas en `.runtime/` y generan `backend/.env` con credenciales locales. Si ya está preparado, basta con ejecutar `scripts/start.ps1`.

Frontend: http://localhost:5173. API: http://localhost:8000/api/. PostgreSQL local: `127.0.0.1:55432`.

Para detener los servicios:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop.ps1
```

## Instalación con herramientas propias

1. Instala Python 3.13, Node.js 24 y PostgreSQL.
2. Instala las dependencias Python de `backend/requirements.txt` en un entorno virtual.
3. Copia `backend/.env.example` a `backend/.env` y configura la clave de Django y la conexión PostgreSQL.
4. Desde `backend/`, ejecuta `python manage.py migrate` y crea un administrador con `python manage.py createsuperuser`.
5. Desde `frontend/`, ejecuta `npm ci` y `npm run dev`. Inicia la API desde `backend/` con `python manage.py runserver`.

Para usar PostgreSQL con Docker, define `POSTGRES_PASSWORD`, ejecuta `docker compose up -d db` y configura `backend/.env` para el puerto 5432.

Para cargar datos ficticios de forma explícita, ejecuta `python manage.py seed_demo`. Las cuentas demo son `admin@vilasmotor.cl`, `james@vilasmotor.cl`, `ayudante@vilasmotor.cl` y `jefe@vilasmotor.cl`, con contraseña `VilasDemo2026!`. Utilízalas solo para pruebas.

## Verificación

```powershell
.runtime/python/python.exe backend/manage.py check
.runtime/python/python.exe backend/manage.py test fleet --noinput
```

Desde `frontend/`, `npm run build` compila la página. Con ambos servidores iniciados, `scripts/check.ps1` ejecuta además las pruebas de navegador. Estas usan Edge y las cuentas demo, y crean registros de prueba; ejecútalas en un entorno de desarrollo.

## Repositorio y despliegue

Sube el código, las migraciones, `frontend/package-lock.json` y `backend/.env.example`. `.gitignore` excluye credenciales, bases locales, adjuntos, dependencias, herramientas y resultados generados. Conserva copias de la base y los adjuntos por separado.

La aplicación completa requiere un servidor para Django y una base PostgreSQL. GitHub almacena el código; GitHub Pages por sí solo no ejecuta este backend. El frontend usa `/api/`, por lo que el servidor de producción debe dirigir esa ruta a Django y servir la compilación de `frontend/dist/`.

Configura las variables de `backend/.env.example` para el dominio de destino, `DJANGO_DEBUG=false`, una clave secreta propia, HTTPS, correo SMTP y almacenamiento persistente de los adjuntos. Ejecuta las migraciones y `python manage.py collectstatic` durante el despliegue. Usa un servidor WSGI de producción para `config.wsgi:application`; el servidor de desarrollo se utiliza para trabajo local.

## Estructura

- `frontend/src/`: interfaz, cliente API y cola de lecturas sin conexión.
- `frontend/public/`: imágenes, fuentes y sus licencias.
- `backend/config/`: configuración de Django.
- `backend/fleet/`: modelos, API, permisos, servicios, migraciones y pruebas funcionales.
- `scripts/`: instalación, inicio, detención y verificación local.
- `compose.yaml`: PostgreSQL para desarrollo con Docker.
# Vilas-Motors
