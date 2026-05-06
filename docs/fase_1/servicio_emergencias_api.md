# Servicio de emergencias y gestion por API

Este documento explica como consumir la API inicial de DistriCare desde Postman o curl. La segunda parte de la fase 1 ya cuenta con servicio de emergencias, estados base y endpoints para gestionar ambulancias simuladas.

## 1. Que ya esta implementado

El backend ya permite:

- crear emergencias simuladas;
- listar emergencias;
- consultar una emergencia por id;
- registrar ambulancias simuladas;
- listar ambulancias;
- enviar heartbeat de ambulancia;
- simular caida de nodo;
- recuperar nodo;
- intentar asignar una ambulancia a una emergencia;
- consultar eventos y recomendaciones IA.

Archivos principales:

- `backend/app/api/router.py`: define los endpoints REST.
- `backend/app/services/emergencies.py`: contiene la logica de creacion y publicacion de emergencias.
- `backend/app/services/ambulances.py`: contiene registro, heartbeat y recuperacion de ambulancias.
- `backend/app/services/assignments.py`: contiene intentos de asignacion y control de asignacion unica.
- `backend/app/domain/enums.py`: contiene estados base de emergencias, ambulancias, asignaciones y eventos.

## 2. Estados base de emergencia

Los estados disponibles estan definidos en `EmergencyState`:

```text
REGISTRADA
PRIORIZADA
PUBLICADA
EN_PROCESO_ASIGNACION
ASIGNADA
SIN_UNIDAD_DISPONIBLE
EN_ATENCION
FALLO_DETECTADO
REASIGNACION_PENDIENTE
REASIGNADA
CERRADA
```

Flujo inicial usado al crear una emergencia:

1. La API recibe `POST /emergencies`.
2. La emergencia se crea como `REGISTRADA`.
3. El modulo IA calcula prioridad y recomendacion.
4. La emergencia pasa por `PRIORIZADA`.
5. Se publica evento en RabbitMQ.
6. La emergencia queda como `PUBLICADA`.

## 3. Levantar el entorno

Desde la raiz del proyecto:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Instalar dependencias si aun no estan:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Ejecutar migraciones:

```powershell
alembic -c backend/alembic.ini upgrade head
```

Levantar API:

```powershell
uvicorn app.main:app --app-dir backend --reload
```

Verificar salud:

```powershell
curl.exe http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "service": "districare",
  "database": "ok"
}
```

## 4. Configuracion para Postman

Crear una variable de entorno en Postman:

```text
base_url = http://localhost:8000
```

Usar headers para requests con body:

```text
Content-Type: application/json
```

Orden recomendado para probar:

1. `GET {{base_url}}/health`
2. `POST {{base_url}}/ambulances`
3. `GET {{base_url}}/ambulances`
4. `POST {{base_url}}/emergencies`
5. `GET {{base_url}}/emergencies`
6. `GET {{base_url}}/recommendations`
7. `POST {{base_url}}/assignments/attempt`
8. `GET {{base_url}}/events`

## 5. Crear ambulancias simuladas

Endpoint:

```http
POST /ambulances
```

Body:

```json
{
  "code": "AMB-A",
  "simulated_location": "0,0",
  "operational_load": 0,
  "reliability": 1.0
}
```

curl:

```powershell
curl.exe -X POST http://localhost:8000/ambulances `
  -H "Content-Type: application/json" `
  -d "{\"code\":\"AMB-A\",\"simulated_location\":\"0,0\",\"operational_load\":0,\"reliability\":1.0}"
```

Crear otra ambulancia:

```powershell
curl.exe -X POST http://localhost:8000/ambulances `
  -H "Content-Type: application/json" `
  -d "{\"code\":\"AMB-B\",\"simulated_location\":\"5,3\",\"operational_load\":2,\"reliability\":0.85}"
```

Listar ambulancias:

```powershell
curl.exe http://localhost:8000/ambulances
```

Guarda el `id` de cada ambulancia, porque se usa en heartbeat, fallos y asignaciones.

## 6. Enviar heartbeat de ambulancia

Endpoint:

```http
POST /ambulances/{ambulance_id}/heartbeat
```

curl:

```powershell
curl.exe -X POST http://localhost:8000/ambulances/ID_AMBULANCIA/heartbeat
```

Esto actualiza `last_heartbeat_at` y registra un evento `HEARTBEAT_RECEIVED`.

## 7. Crear una emergencia simulada

Endpoint:

```http
POST /emergencies
```

Body:

```json
{
  "type": "Accidente de transito",
  "severity": 8,
  "simulated_location": "1,1"
}
```

curl:

```powershell
curl.exe -X POST http://localhost:8000/emergencies `
  -H "Content-Type: application/json" `
  -d "{\"type\":\"Accidente de transito\",\"severity\":8,\"simulated_location\":\"1,1\"}"
```

Respuesta esperada:

```json
{
  "id": "...",
  "type": "Accidente de transito",
  "severity": 8,
  "priority": 80,
  "simulated_location": "1,1",
  "state": "PUBLICADA",
  "created_at": "...",
  "closed_at": null
}
```

Al crear la emergencia tambien se generan eventos y una recomendacion IA.

## 8. Listar y consultar emergencias

Listar todas:

```powershell
curl.exe http://localhost:8000/emergencies
```

Consultar por id:

```powershell
curl.exe http://localhost:8000/emergencies/ID_EMERGENCIA
```

Si el id no existe, la API responde `404`.

## 9. Consultar recomendacion IA

Endpoint:

```http
GET /recommendations
```

curl:

```powershell
curl.exe http://localhost:8000/recommendations
```

La recomendacion muestra:

- emergencia asociada;
- ambulancia recomendada;
- prioridad calculada;
- puntaje total;
- ranking usado por la heuristica.

## 10. Intentar asignacion manual desde Postman o curl

Endpoint:

```http
POST /assignments/attempt
```

Body:

```json
{
  "emergency_id": "ID_EMERGENCIA",
  "ambulance_id": "ID_AMBULANCIA"
}
```

curl:

```powershell
curl.exe -X POST http://localhost:8000/assignments/attempt `
  -H "Content-Type: application/json" `
  -d "{\"emergency_id\":\"ID_EMERGENCIA\",\"ambulance_id\":\"ID_AMBULANCIA\"}"
```

Primera asignacion exitosa:

```json
{
  "accepted": true,
  "assignment": {
    "id": "...",
    "emergency_id": "...",
    "ambulance_id": "...",
    "state": "CONFIRMADA",
    "active": true,
    "assigned_at": "...",
    "finalized_at": null,
    "reassignment_reason": null
  },
  "reason": null
}
```

Segundo intento para la misma emergencia:

```json
{
  "accepted": false,
  "assignment": null,
  "reason": "Emergencia ya asignada"
}
```

Esto demuestra la restriccion de asignacion unica.

## 11. Simular caida y recuperacion de ambulancia

Forzar caida:

```powershell
curl.exe -X POST http://localhost:8000/ambulances/ID_AMBULANCIA/fail
```

Recuperar nodo:

```powershell
curl.exe -X POST http://localhost:8000/ambulances/ID_AMBULANCIA/recover
```

Detectar nodos sin heartbeat reciente:

```powershell
curl.exe -X POST http://localhost:8000/failures/detect-stale
```

Si falla una ambulancia asignada, el backend desactiva la asignacion anterior y busca reasignar automaticamente otra ambulancia disponible.

## 12. Consultar eventos

Endpoint:

```http
GET /events
```

curl:

```powershell
curl.exe http://localhost:8000/events
```

Aqui se puede revisar la trazabilidad del sistema:

- emergencia creada;
- emergencia priorizada;
- emergencia publicada;
- ambulancia registrada;
- heartbeat recibido;
- intento de asignacion;
- asignacion confirmada;
- intento rechazado;
- nodo caido;
- nodo recuperado;
- reasignacion iniciada;
- reasignacion confirmada.

## 13. Probar con procesos simulados

Ademas de consumir la API manualmente, se pueden ejecutar nodos reales del simulador:

```powershell
python scripts/run_ambulance_node.py --code AMB-A --location "0,0"
```

En otra terminal:

```powershell
python scripts/run_ambulance_node.py --code AMB-B --location "5,3"
```

Luego crea una emergencia:

```powershell
curl.exe -X POST http://localhost:8000/emergencies `
  -H "Content-Type: application/json" `
  -d "{\"type\":\"Infarto\",\"severity\":9,\"simulated_location\":\"1,1\"}"
```

Los nodos escuchan RabbitMQ, reciben el evento y el nodo recomendado intenta aceptar la emergencia.

## 14. Resumen de endpoints

```text
GET    /health
POST   /emergencies
GET    /emergencies
GET    /emergencies/{id}
POST   /ambulances
GET    /ambulances
POST   /ambulances/{id}/heartbeat
POST   /ambulances/{id}/fail
POST   /ambulances/{id}/recover
POST   /assignments/attempt
POST   /failures/detect-stale
GET    /events
GET    /recommendations
```

## 15. Nota importante

Si cambiaste puertos o reiniciaste Docker, reinicia tambien el backend con `Ctrl + C` y vuelve a ejecutar:

```powershell
uvicorn app.main:app --app-dir backend --reload
```

Esto asegura que FastAPI use la configuracion actual de PostgreSQL y RabbitMQ.
