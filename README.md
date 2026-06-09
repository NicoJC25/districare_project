# DistriCare

DistriCare es un sistema distribuido para simular registro, priorizacion y asignacion de ambulancias ante emergencias medicas. El proyecto combina una API FastAPI, base de datos PostgreSQL, eventos RabbitMQ, nodos simulados de ambulancia y un dashboard React/Vite.

## Componentes

- `backend`: API FastAPI, modelos SQLAlchemy, migraciones Alembic, servicios de dominio y publicacion de eventos.
- `frontend`: dashboard React/Vite, con empaquetado opcional de escritorio mediante Electron.
- `simulator`: nodos de ambulancia que consumen eventos RabbitMQ, envian heartbeats e intentan asignaciones.
- `infrastructure`: Docker Compose local para PostgreSQL y RabbitMQ.
- `scripts`: utilidades para levantar servicios y cargar datos demo.

## Variables de entorno

El backend lee configuracion desde `.env`. El archivo `.env.example` es solo una plantilla.

```powershell
Copy-Item .env.example .env
```

Para desarrollo local puedes usar los puertos del `docker-compose.yml`, pero ajusta `API_KEY` por una clave propia. En produccion no uses credenciales demo ni la clave de ejemplo.

Variables principales:

- `APP_ENV`: `development` o `production`.
- `DATABASE_URL`: URL SQLAlchemy para PostgreSQL.
- `RABBITMQ_URL`: URL AMQP de RabbitMQ.
- `RABBITMQ_EXCHANGE`: exchange usado para eventos.
- `BACKEND_CORS_ORIGINS`: origenes permitidos separados por coma.
- `API_KEY`: clave requerida en `X-API-Key` para endpoints de escritura.
- `ENABLE_API_DOCS`: `true` en desarrollo, `false` en produccion.

El frontend llama a la API usando una ruta relativa `/api` por defecto. En desarrollo, Vite actua como proxy hacia el backend:

```powershell
cd frontend
@"
API_PROXY_TARGET=http://127.0.0.1:8000
API_KEY=tu-api-key-local
"@ | Out-File -Encoding utf8 .env.local
```

No uses `VITE_API_KEY`: las variables con prefijo `VITE_` quedan embebidas en el build del navegador. La clave debe quedarse en un proxy, backend-for-frontend o reverse proxy que agregue `X-API-Key` del lado servidor.

## Desarrollo local

Levanta PostgreSQL y RabbitMQ:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Prepara Python e instala dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Ejecuta migraciones y backend:

```powershell
alembic -c backend/alembic.ini upgrade head
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Verifica salud:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Levanta el frontend:

```powershell
cd frontend
npm install
npm run dev
```

El dashboard queda en `http://127.0.0.1:5173`.

## Simulador y datos demo

En terminales separadas, con la misma `API_KEY` configurada:

```powershell
$env:API_KEY = "tu-api-key-local"
python scripts/run_ambulance_node.py --code AMB-A --location "4.7110,-74.0721"
python scripts/run_ambulance_node.py --code AMB-B --location "4.6500,-74.0900"
```

Carga escenarios demo:

```powershell
$env:API_KEY = "tu-api-key-local"
python scripts/seed_demo_data.py
```

El script crea datos para recomendacion normal, intento distribuido distinto a la IA, fallo con reasignacion automatica y cierre de emergencia.

## Pruebas

Backend:

```powershell
pytest
```

Frontend:

```powershell
cd frontend
npm run build
```

## Despliegue sugerido

- Frontend: sitio estatico detras de un reverse proxy o backend-for-frontend.
- Backend: Render Free Web Service ejecutando Uvicorn.
- PostgreSQL: Supabase Free.
- RabbitMQ: CloudAMQP Little Lemur Free.

Variables recomendadas para Render:

```text
APP_ENV=production
DATABASE_URL=<connection-string-supabase>
RABBITMQ_URL=<amqp-url-cloudamqp>
RABBITMQ_EXCHANGE=districare.events
BACKEND_CORS_ORIGINS=https://tu-frontend.example.com
API_KEY=<clave-larga-y-unica>
ENABLE_API_DOCS=false
```

Comandos de Render:

```text
pip install -e .
alembic -c backend/alembic.ini upgrade head
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
```

Para desplegar el frontend como sitio estatico, publica el dashboard detras de un reverse proxy o backend-for-frontend que exponga `/api/*`, reenvie al backend real y agregue `X-API-Key` del lado servidor. Evita configurar `VITE_API_BASE_URL` con una URL publica salvo que aceptes que el navegador muestre ese host en Network.

Ejemplo de variables para un proxy de frontend:

```text
API_PROXY_TARGET=https://tu-backend.onrender.com
API_KEY=<misma-api-key>
```

Render Free puede dormir por inactividad y generar cold starts. Para una demo o primera version publica ligera es aceptable; para uso continuo conviene migrar a un plan pago o VPS.

## Checklist de release

1. Confirmar que `.env` no esta versionado.
2. Confirmar que `docs/` no esta versionado en el commit final.
3. Ejecutar `pytest`.
4. Ejecutar `npm run build` en `frontend`.
5. Probar una emergencia completa: registro, recomendacion, asignacion, fallo/reasignacion y cierre.
6. Probar que una escritura sin `X-API-Key` valida responde `401`.
7. Desactivar documentacion de API en produccion con `ENABLE_API_DOCS=false`.
8. Publicar en `main` y crear tag sugerido `v1.0.0`.
