# Fase 2: eventos, nodos y heartbeat

Esta fase usa RabbitMQ como broker de eventos y simula ambulancias como procesos
independientes. Cada emergencia creada se publica como evento, cada nodo escucha
su cola, reporta recepcion/procesamiento al backend y mantiene heartbeat.

## Componentes cubiertos

- Broker de eventos: RabbitMQ en Docker, exchange `districare.events`.
- Publicacion de emergencias: `POST /emergencies` publica `emergency.prioritized`.
- Nodos de ambulancia: procesos lanzados con `scripts/run_ambulance_node.py`.
- Recepcion de eventos: cada nodo consume RabbitMQ y reporta a `/node-events`.
- Heartbeat basico: cada nodo llama periodicamente a `/heartbeat`.
- Estados de nodo: `DISPONIBLE`, `OCUPADO`, `INACTIVO`, `FALLIDO`.
- Log de eventos: `/events` lista eventos publicados, recibidos y procesados.

## Demo local

Levantar infraestructura:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Preparar base de datos y API:

```powershell
.\.venv\Scripts\Activate.ps1
alembic -c backend/alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
```

En dos o tres terminales separadas, iniciar nodos:

```powershell
.\.venv\Scripts\python.exe scripts/run_ambulance_node.py --code AMB-A --location "0,0"
.\.venv\Scripts\python.exe scripts/run_ambulance_node.py --code AMB-B --location "5,3"
.\.venv\Scripts\python.exe scripts/run_ambulance_node.py --code AMB-C --location "9,1" --accept-all
```

Crear una emergencia:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/emergencies `
  -ContentType "application/json" `
  -Body '{"type":"Accidente","severity":8,"simulated_location":"1,1"}'
```

Consultar evidencia:

```powershell
Invoke-RestMethod http://localhost:8000/ambulances
Invoke-RestMethod http://localhost:8000/assignments
Invoke-RestMethod http://localhost:8000/events
```

La consola de RabbitMQ queda disponible en `http://localhost:15673`.
