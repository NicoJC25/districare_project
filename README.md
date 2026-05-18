# DistriCare

Base inicial distribuida para el proyecto de Sistemas Distribuidos.

## Componentes

- `backend`: API FastAPI, modelo SQLAlchemy, servicios de dominio, eventos y publicacion RabbitMQ.
- `simulator`: nodos de ambulancia como procesos separados con heartbeat y consumo de eventos.
- `infrastructure`: PostgreSQL y RabbitMQ para desarrollo local.
- `docs/fase_1`: notas del modelo inicial y la simulacion distribuida.
- `docs/fase_2`: eventos, nodos de ambulancia, heartbeat y trazabilidad de fase.
- `docs/fase_4`: extension de IA heuristica auditable, ranking y trazabilidad de recomendaciones.

## Inicio rapido

Infraestructura y backend:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic -c backend/alembic.ini upgrade head
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

El backend queda disponible en `http://127.0.0.1:8000`. Puedes verificarlo con:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

En otra terminal, levanta el frontend:

```powershell
cd frontend
npm install
npm run dev
```

El dashboard queda disponible en `http://127.0.0.1:5173`.

Aplicacion de escritorio con Electron:

```powershell
cd frontend
npm run dev
```

En otra terminal:

```powershell
cd frontend
npm run electron:dev
```

Para probar la app de escritorio usando el build estatico:

```powershell
cd frontend
npm run electron:preview
```

Para generar el instalador de Windows:

```powershell
cd frontend
npm run electron:build
```

El instalador queda en `frontend/release/`. Esta aplicacion de escritorio solo empaqueta el frontend; antes de abrirla deben estar activos Docker/PostgreSQL/RabbitMQ y el backend FastAPI en `http://127.0.0.1:8000`.

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
python scripts/run_ambulance_node.py --code AMB-A --location "4.7110,-74.0721"
python scripts/run_ambulance_node.py --code AMB-B --location "4.6500,-74.0900"
```

Datos demo para sustentacion:

```powershell
python scripts/seed_demo_data.py
```

Este script requiere que el backend este activo en `http://127.0.0.1:8000`. Crea escenarios para recomendacion normal, intento distribuido distinto a IA, fallo con reasignacion automatica y emergencia cerrada.

Flujo sugerido de demostracion:

1. Abrir Panel General para ver resumen por estado.
2. Revisar Recomendaciones IA y ranking de candidatos.
3. Intentar una asignacion desde Asignaciones y observar aceptados/rechazados.
4. Marcar fallo en una ambulancia asignada y revisar Trazabilidad.
5. Iniciar atencion y cerrar una emergencia desde Emergencias.
6. Confirmar en Eventos del sistema la secuencia completa.

## Pruebas

```powershell
pytest
```

## Guias de fase

- [Modelo inicial](docs/fase_1/modelo_inicial.md)
- [Trazabilidad de creacion](docs/fase_1/trazabilidad_creacion.md)
- [Servicio de emergencias y consumo API](docs/fase_1/servicio_emergencias_api.md)
- [Fase 2: eventos, nodos y heartbeat](docs/fase_2/fase_2.md)
- [Trazabilidad fase 2](docs/fase_2/trazabilidad_fase_2.md)
- [Extension IA heuristica](docs/fase_4/heuristica_ia.md)
- [Trazabilidad de recomendaciones](docs/fase_4/trazabilidad_recomendaciones.md)
- [Justificacion como sistema distribuido](docs/fase_5/justificacion_sistema_distribuido.md)
