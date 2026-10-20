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

## Conexión Vercel → Render

La interfaz usa `/api/` en el mismo dominio del navegador. El build de Vercel genera un proxy hacia Render con Build Output API, conservando las cookies de sesión y CSRF. No configures `VITE_API_URL` ni cambies el cliente a llamadas directas entre dominios.

En **Vercel → Settings → Environment Variables**, agrega `BACKEND_URL=https://vilas-motors.onrender.com` para Production (y Preview si necesitas conectarlo a la misma base). Usa Root Directory `frontend`. El archivo `frontend/vercel.json` define `npm ci` y `npm run build:vercel`; elimina las sobreescrituras anteriores de Framework/Build/Output Directory del panel, ya que este build genera `.vercel/output/` en lugar de publicar directamente `dist/`. La variable BACKEND_URL es obligatoria y debe ser un origen HTTPS sin `/api`.

En **Render**, usa Root Directory `backend`, Build Command `bash build.sh` y Start Command `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. Configura:

| Variable | Valor |
| --- | --- |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | Tu secreto estable de producción |
| `DATABASE_URL` | La URI privada de Supabase con SSL |
| `FRONTEND_URL` | `https://vilas-motors-muhdcegrz-phantomdev33s-projects.vercel.app` |

El host público que proporciona Render se agrega automáticamente a ALLOWED_HOSTS. FRONTEND_URL se agrega automáticamente a los orígenes CSRF. Para dominios adicionales, usa `DJANGO_ALLOWED_HOSTS` (hosts separados por coma) y `CSRF_TRUSTED_ORIGINS` (orígenes completos HTTPS separados por coma). No uses comodines de Vercel ni agregues todos los previews: cada origen autorizado puede enviar peticiones autenticadas.

La URL de Vercel anterior identifica el despliegue que compartiste. Si asignas un dominio estable al proyecto, actualiza FRONTEND_URL para que los correos de recuperación y CSRF usen ese dominio. Un enlace al panel `vercel.com/...` no es la URL pública de la página.

`backend/.env` y los scripts de PowerShell mantienen el desarrollo local. En producción no se usan localhost por defecto: Django exige FRONTEND_URL y una conexión explícita a la base. El build de Vercel exige BACKEND_URL. No subas `.env` a GitHub: configura las variables en cada proveedor. Después de subir el código, vuelve a desplegar ambos servicios.

Documentación: [Build Output API](https://vercel.com/docs/build-output-api) y [Django en Render](https://render.com/docs/deploy-django).
## PostgreSQL en Supabase (Render)

La aplicación usa Supabase como PostgreSQL mediante Django. El login, los permisos y la API siguen en Django; no necesitas instalar el SDK de Supabase ni configurar claves de Supabase en Vercel.

1. Crea un proyecto Supabase y abre **Connect → Session pooler**. Copia la URI PostgreSQL del puerto **5432**. Este pooler permite conectar por IPv4; la conexión directa requiere IPv6 o el complemento IPv4.
2. Sustituye `[YOUR-PASSWORD]` por la contraseña de la base de datos. Si contiene caracteres especiales, codifícalos para una URI (`@` → `%40`, `#` → `%23`, `:` → `%3A`, `%` → `%25`). No uses la clave `anon` ni `service_role` como contraseña.
3. En **Render → servicio backend → Environment**, configura:

   | Variable | Valor |
   | --- | --- |
   | `DATABASE_URL` | URI de Session pooler con `?sslmode=require` |
   | `DJANGO_DEBUG` | `false` |
   | `DJANGO_SECRET_KEY` | Secreto aleatorio propio y estable |
   | `DJANGO_ALLOWED_HOSTS` | Host de tu backend, sin `https://` |
   | `FRONTEND_URL` | URL HTTPS de tu frontend |
   | `CSRF_TRUSTED_ORIGINS` | URL HTTPS de tu frontend y del backend, separadas por coma |

4. Sube los cambios a GitHub y vuelve a desplegar. Desde `backend/`, ejecuta `python manage.py migrate` como parte del despliegue para crear las tablas. Esto crea la estructura; no copia registros de tu base anterior. Crea un usuario administrador con `python manage.py createsuperuser` desde un entorno autorizado con acceso a la base.
5. En un proyecto dedicado a esta aplicación, desactiva **Data API** en Supabase antes de crear las tablas. Django accede directamente a PostgreSQL y aplica sus propios permisos. Si necesitas Data API para otros usos, configura sus esquemas, privilegios y RLS para evitar exponer las tablas internas de Django.

`DATABASE_URL` tiene prioridad sobre `POSTGRES_*` y `DATABASE_ENGINE`. Al usar una URL, SSL se activa por defecto; se conservan las opciones de la URI, incluido `sslmode=verify-full` con `sslrootcert` si configuras el certificado. Sin URL se mantiene PostgreSQL local; también puedes usar las variables `POSTGRES_*` del panel Supabase junto con `POSTGRES_SSLMODE=require`. La configuración limita a 10 segundos la espera inicial de conexión.

Para probar Supabase en tu equipo, agrega `DATABASE_URL` en `backend/.env` y ejecuta `python manage.py migrate --check` desde `backend/`. Este comando comprueba la conexión y las migraciones pendientes sin aplicarlas. No ejecutes `scripts/setup-postgres.ps1` para preparar Supabase: ese script instala y configura PostgreSQL local.

Las fotos adjuntas continúan en `backend/media/`; esta integración conecta la base de datos, no Supabase Storage. En Render Free esos archivos no son persistentes. El almacenamiento de adjuntos requiere una integración adicional antes de usarlos en el hosting.

Documentación oficial: [conexiones PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres) y [seguridad de Data API](https://supabase.com/docs/guides/api/securing-your-api).
