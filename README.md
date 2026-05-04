# DistriCare

Base inicial distribuida para el proyecto de Sistemas Distribuidos.

## Componentes

- `backend`: API FastAPI, modelo SQLAlchemy, servicios de dominio, eventos y publicacion RabbitMQ.
- `simulator`: nodos de ambulancia como procesos separados con heartbeat y consumo de eventos.
- `infrastructure`: PostgreSQL y RabbitMQ para desarrollo local.
- `docs/fase_1`: notas del modelo inicial y la simulacion distribuida.

## Inicio rapido

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic -c backend/alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
```

PostgreSQL queda expuesto en `localhost:15432` y RabbitMQ en `localhost:5673` para evitar choques con instalaciones locales que ya usen `5432`, `5672` o `15672`, y tambien evitar rangos reservados por Windows. La consola web de RabbitMQ queda en `http://localhost:15673`. Si venias de una ejecucion anterior, reinicia la infraestructura con:

```powershell
docker compose -f infrastructure/docker-compose.yml down
docker compose -f infrastructure/docker-compose.yml up -d
```

Si el error persiste por credenciales viejas en el volumen de Docker, elimina el volumen del proyecto y recrealo:

```powershell
docker compose -f infrastructure/docker-compose.yml down -v
docker compose -f infrastructure/docker-compose.yml up -d
alembic -c backend/alembic.ini upgrade head
```

En otra terminal:

```powershell
python scripts/run_ambulance_node.py --code AMB-A --location "0,0"
python scripts/run_ambulance_node.py --code AMB-B --location "5,3"
```

## Pruebas

```powershell
pytest
```
