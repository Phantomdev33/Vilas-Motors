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

Desde la raíz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

El verificador ejecuta Django con `config.prototype` y SQLite aislado, compila el
frontend y corre las pruebas actuales de escritorio/móvil con API simulada. No
modifica Supabase. Playwright inicia o reutiliza Vite automáticamente; no requiere
un backend real para estas pruebas. Edge debe estar instalado.

La revisión contra la pauta, sus medidas y limitaciones están documentadas en
[Revisión de entrega](docs/REVISION-ENTREGA.md). Los pasos de presentación están
en [Demostración de entrega](docs/DEMOSTRACION-ENTREGA.md).

## Repositorio y despliegue

Sube el código, las migraciones, `frontend/package-lock.json` y `backend/.env.example`. `.gitignore` excluye credenciales, bases locales, adjuntos, dependencias, herramientas y resultados generados. Conserva copias de la base y los adjuntos por separado.

La aplicación completa requiere un servidor para Django y una base PostgreSQL. GitHub almacena el código; GitHub Pages por sí solo no ejecuta este backend. El frontend usa `/api/`, por lo que el servidor de producción debe dirigir esa ruta a Django y servir la compilación de `frontend/dist/`.

Configura las variables de `backend/.env.production.example` para el dominio de destino, `DJANGO_DEBUG=false`, una clave secreta propia, HTTPS, SMS y almacenamiento persistente de los adjuntos. Ejecuta las migraciones y `python manage.py collectstatic` durante el despliegue. Usa un servidor WSGI de producción para `config.wsgi:application`; el servidor de desarrollo se utiliza para trabajo local.

## Estructura

- `frontend/src/`: interfaz, cliente API y cola de lecturas sin conexión.
- `frontend/public/`: imágenes, fuentes y sus licencias.
- `backend/config/`: configuración de Django.
- `backend/fleet/`: modelos, API, permisos, servicios, migraciones y pruebas funcionales.
- `scripts/`: instalación, inicio, detención y verificación local.
- `compose.yaml`: PostgreSQL para desarrollo con Docker.

## Conexión Vercel → Render

La interfaz usa `/api/` en el mismo dominio del navegador. `frontend/vercel.json` reenv?a esas rutas a `https://vilas-motors.onrender.com/api/`. Esto conserva las cookies bajo el dominio del frontend.

En Vercel usa Root Directory `frontend`, Framework `Vite`, Build Command `npm run build` y Output Directory `dist`. El proxy queda expl?cito en `vercel.json`; esta configuraci?n ya no necesita BACKEND_URL ni el build especial de Build Output API. Desactiva las sobreescrituras antiguas del panel si todav?a indican `npm run build:vercel`.

En **Render**, usa Root Directory `backend`, Build Command `bash build.sh` y Start Command `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. Configura:

| Variable | Valor |
| --- | --- |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | Tu secreto estable de producción |
| `DATABASE_URL` | La URI privada de Supabase con SSL |
| `FRONTEND_URL` | `https://vilas-motors-muhdcegrz-phantomdev33s-projects.vercel.app` |

El host público que proporciona Render se agrega automáticamente a ALLOWED_HOSTS.
Configura `FRONTEND_URL` para el acceso a la aplicación y `CSRF_TRUSTED_ORIGINS`
con los orígenes HTTPS de frontend y backend, separados por coma. La lista de
orígenes CORS usa por defecto esos mismos valores. Para hosts adicionales usa
`DJANGO_ALLOWED_HOSTS`. No uses comodines ni publiques credenciales en el frontend.

La URL de Vercel anterior identifica el despliegue que compartiste. Si asignas un dominio estable al proyecto, actualiza `FRONTEND_URL` y los orígenes de CSRF.

`backend/.env` y los scripts de PowerShell mantienen el desarrollo local. En producción no se usan localhost por defecto: Django exige FRONTEND_URL y una conexión explícita a la base. El destino de Render se configura en frontend/vercel.json. No subas `.env` a GitHub: configura las variables en cada proveedor. Después de subir el código, vuelve a desplegar ambos servicios.

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

## Diseño visual y pruebas de interfaz

La interfaz usa el tema oscuro de `frontend/src/design.css`, sobre los estilos estructurales existentes. El resumen de flota, los filtros, los contadores y la búsqueda utilizan los registros de la API. Arriendo de maquinaria es una vista informativa con acceso a las fichas; la gestión comercial de contratos aún no está implementada.

Con el frontend local iniciado, ejecuta desde `frontend/`:

```powershell
npm run test:e2e -- tests/changes.spec.js tests/design.spec.js
```

Estas pruebas usan una API simulada y no modifican la base de datos. Cubren escritorio y móvil, formularios, filtros, navegación y desbordes de pantalla. Las capturas de diseño se guardan en `.runtime/design-review/` respecto de la carpeta desde la que ejecutas las pruebas y quedan excluidas de Git.
# Prototipo académico con datos simulados

Ejecuta `powershell -ExecutionPolicy Bypass -File scripts/start-prototype.ps1`
desde la raíz y, en otra terminal, inicia el frontend con `npm run dev` desde
`frontend` (Node debe estar disponible en PATH).

Este modo utiliza exclusivamente `backend/prototype.sqlite3`, con seis equipos,
lecturas, mantenciones y usuarios ficticios. No conecta la aplicación a Supabase.
Las regiones de ejemplo son Arica y Parinacota, Tarapacá, Antofagasta, Atacama
y Coquimbo; no representan ubicaciones verificadas de la empresa.

Acceso de ejemplo: `admin@vilasmotor.cl`, contraseña `VilasDemo2026!`.
Tras ingresar la contraseña y el CAPTCHA, copia el código de seis dígitos de la
línea `[SMS simulado]` en la terminal de Django. La recuperación usa la misma
terminal. Con `scripts/start.ps1`, la salida de Django queda en `.runtime/backend.log`.
La carga se puede repetir sin duplicar registros. El modo normal de despliegue
mantiene su configuración existente; este cambio no publica el prototipo.

El filtro «Disponibles» significa operativo y sin mantención en curso.
Los filtros se combinan y «Limpiar filtros» restablece también la búsqueda.
La ficha permite volver a la flota mediante una barra fija, conservando filtros.

## Mantención preventiva por equipo

Al crear o editar un equipo, selecciona su tipo e indica la marca y el modelo.
La ficha muestra las referencias disponibles con su tarea, unidad y manual.
Aplica una referencia si corresponde a la variante y las condiciones de faena,
o registra el intervalo del manual específico. La flota calcula la próxima
mantención a partir del horómetro o kilometraje. Si hay una mantención cerrada,
el cálculo usa el intervalo guardado en esa intervención. Los límites por
calendario que figuran en los manuales se pueden programar por separado.

Las referencias investigadas están en [el catálogo de intervalos](backend/fleet/service_references.py).
Algunos equipos del inventario solo indican la familia, como Volvo FMX o Liebherr LTM.
En esos casos, registra el intervalo de la unidad según su serie y uso. Los datos
de demostración incluyen intervalos ficticios para equipos sin coincidencia exacta.

## Acceso y recuperación por SMS

En **Mi perfil**, cada usuario puede editar su nombre, apellido y correo,
además de subir o quitar su foto. Para cambiar el correo necesita su
contraseña actual. Para cambiar el celular necesita su contraseña actual y
el código que llega al nuevo número. Después vuelve a iniciar sesión.
Las fotos se guardan en la base de datos y se muestran dentro de la sesión.

El administrador puede registrar el celular en **Usuarios y roles** y cambiar
el estado de acceso. Una cuenta inactiva queda fuera del sistema hasta que se
reactiva. Las cuentas existentes necesitan un celular con prefijo internacional.
Para preparar el primer administrador existente, ejecuta desde `backend/`
`python manage.py set_sms_phone correo@empresa.cl +56912345678` con los datos
de la cuenta. Las cuentas nuevas creadas con `createsuperuser` pueden indicar
el celular en el asistente.

Para recibir SMS reales en el prototipo local, configura `TWILIO_ACCOUNT_SID`,
`TWILIO_AUTH_TOKEN` y `TWILIO_FROM` en `backend/.env`. Usa como remitente un
número de Twilio habilitado para SMS y comprueba que Chile figure habilitado
en los permisos geográficos de la cuenta. Desde la raíz registra un celular
real en la base del prototipo e inicia el backend con el envío habilitado:

```powershell
$env:DJANGO_SETTINGS_MODULE = 'config.prototype'
./.runtime/python/python.exe backend/manage.py migrate
./.runtime/python/python.exe backend/manage.py seed_demo
./.runtime/python/python.exe backend/manage.py set_sms_phone admin@vilasmotor.cl +56912345678
powershell -ExecutionPolicy Bypass -File scripts/start-prototype.ps1 -RealSms
```

Sustituye el celular de ejemplo por el número que recibirá los códigos.
El script conserva SQLite y los números ficticios quedan excluidos del envío
real. Para un despliegue Django fuera de ese script, configura además
`SMS_BACKEND=twilio`. Twilio requiere Internet y un remitente habilitado
por el proveedor. Una cuenta de prueba puede limitar el contenido a plantillas
predefinidas, mientras que Vila’s Motor genera sus propios mensajes.
[Guía de Twilio para Chile](https://www.twilio.com/en-us/guidelines/cl/sms) ·
[Limitaciones de la prueba](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account).
Ejecuta `python manage.py migrate` en la base del entorno antes de habilitar
el flujo. El panel técnico de Django usa la sesión de la aplicación y requiere
que el navegador pueda enviarle la misma cookie.

# GPS Teltonika y fotos en MongoDB

El prototipo incorpora eventos de encendido GPS **simulados**, horas estimadas y
almacenamiento MongoDB exclusivo para evidencias de lecturas manuales. No incorpora
OCR ni conecta aún una plataforma GPS real. Para configuración, límites del cálculo,
migraciones y comandos de simulación, consulta [GPS y MongoDB](docs/GPS-Y-MONGODB.md).

