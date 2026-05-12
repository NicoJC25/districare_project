# Comprobacion funcional - Fase 3 DistriCare

Esta guia explica como verificar que la fase 3 funciona correctamente: una
emergencia solo puede tener una ambulancia activa confirmada, una ambulancia no
puede aceptar dos emergencias activas, y la emergencia guarda la ambulancia
seleccionada.

## 1. Preparar entorno

Levantar PostgreSQL y RabbitMQ:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Activar entorno e instalar dependencias si hace falta:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Aplicar migraciones:

```powershell
alembic -c backend/alembic.ini upgrade head
```

Iniciar API:

```powershell
uvicorn app.main:app --app-dir backend --reload
```

## 2. Registrar ambulancias

En otra terminal, crear dos ambulancias:

```powershell
$ambA = Invoke-RestMethod -Method Post http://localhost:8000/ambulances `
  -ContentType "application/json" `
  -Body '{"code":"AMB-A","simulated_location":"0,0","operational_load":0,"reliability":1.0}'

$ambB = Invoke-RestMethod -Method Post http://localhost:8000/ambulances `
  -ContentType "application/json" `
  -Body '{"code":"AMB-B","simulated_location":"2,2","operational_load":0,"reliability":0.9}'
```

Comprobar que existen:

```powershell
Invoke-RestMethod http://localhost:8000/ambulances
```

Resultado esperado:

- `AMB-A` existe;
- `AMB-B` existe;
- ambas inician disponibles si no tenian asignaciones previas.

## 3. Crear emergencia

Crear una emergencia:

```powershell
$emergency = Invoke-RestMethod -Method Post http://localhost:8000/emergencies `
  -ContentType "application/json" `
  -Body '{"type":"Accidente","severity":8,"simulated_location":"1,1"}'
```

Consultar la emergencia:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency.id)"
```

Resultado esperado antes de aceptar:

- `state` debe estar en `PUBLICADA`;
- `assigned_ambulance_id` debe ser `null`.

## 4. Confirmar primera asignacion

Hacer que `AMB-A` intente aceptar:

```powershell
$first = Invoke-RestMethod -Method Post http://localhost:8000/assignments/attempt `
  -ContentType "application/json" `
  -Body "{`"emergency_id`":`"$($emergency.id)`",`"ambulance_id`":`"$($ambA.id)`"}"

$first
```

Resultado esperado:

- `accepted` debe ser `true`;
- `assignment.state` debe ser `CONFIRMADA`;
- `assignment.active` debe ser `true`;
- `assignment.ambulance_id` debe ser el id de `AMB-A`.

Comprobar emergencia:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency.id)"
```

Resultado esperado:

- `state` debe ser `ASIGNADA`;
- `assigned_ambulance_id` debe ser el id de `AMB-A`.

Comprobar ambulancias:

```powershell
Invoke-RestMethod http://localhost:8000/ambulances
```

Resultado esperado:

- `AMB-A` debe estar `OCUPADO`.

## 5. Rechazar segunda ambulancia para la misma emergencia

Hacer que `AMB-B` intente aceptar la misma emergencia:

```powershell
$second = Invoke-RestMethod -Method Post http://localhost:8000/assignments/attempt `
  -ContentType "application/json" `
  -Body "{`"emergency_id`":`"$($emergency.id)`",`"ambulance_id`":`"$($ambB.id)`"}"

$second
```

Resultado esperado:

- `accepted` debe ser `false`;
- `assignment` debe ser `null`;
- `reason` debe indicar que la emergencia ya esta asignada.

Comprobar asignaciones:

```powershell
Invoke-RestMethod http://localhost:8000/assignments
```

Resultado esperado:

- solo debe existir una asignacion activa confirmada para esa emergencia;
- la asignacion activa debe pertenecer a `AMB-A`.

## 6. Rechazar una ambulancia ya ocupada en otra emergencia

Crear otra emergencia:

```powershell
$emergency2 = Invoke-RestMethod -Method Post http://localhost:8000/emergencies `
  -ContentType "application/json" `
  -Body '{"type":"Infarto","severity":9,"simulated_location":"3,3"}'
```

Intentar que `AMB-A`, que ya esta ocupada, acepte la segunda emergencia:

```powershell
$busyAttempt = Invoke-RestMethod -Method Post http://localhost:8000/assignments/attempt `
  -ContentType "application/json" `
  -Body "{`"emergency_id`":`"$($emergency2.id)`",`"ambulance_id`":`"$($ambA.id)`"}"

$busyAttempt
```

Resultado esperado:

- `accepted` debe ser `false`;
- `assignment` debe ser `null`;
- `reason` debe indicar que el nodo ya esta asignado o no esta disponible.

Comprobar la segunda emergencia:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency2.id)"
```

Resultado esperado:

- `assigned_ambulance_id` debe seguir en `null`.

## 7. Ver eventos de evidencia

Consultar la bitacora:

```powershell
Invoke-RestMethod http://localhost:8000/events
```

Eventos esperados:

- `ASSIGNMENT_ATTEMPTED`;
- `ASSIGNMENT_CONFIRMED`;
- `ASSIGNMENT_REJECTED`.

Estos eventos sirven como evidencia de competencia entre nodos y de rechazo
controlado por asignacion exclusiva.

## 8. Verificacion automatizada

Ejecutar pruebas:

```powershell
pytest
```

Resultado esperado:

```text
10 passed
```

La prueba automatizada valida los mismos puntos principales:

- rechazo de segunda asignacion sobre la misma emergencia;
- guardado de `assigned_ambulance_id`;
- rechazo de ambulancia con asignacion activa;
- reasignacion por fallo con nueva ambulancia confirmada.

## 9. Archivos clave para revisar

- `backend/app/services/assignments.py`: validacion atomica y confirmacion.
- `backend/app/models/assignment.py`: restricciones unicas parciales.
- `backend/app/models/emergency.py`: campo `assigned_ambulance_id`.
- `backend/alembic/versions/0002_assignment_confirmation_fields.py`: migracion.
- `backend/tests/test_distributed_base.py`: pruebas de fase 3.
