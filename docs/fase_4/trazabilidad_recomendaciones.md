# Trazabilidad de recomendaciones y asignaciones - Fase 4 DistriCare

Esta guia documenta la evidencia final de back-end para ranking de unidades,
registro de recomendacion y trazabilidad entre ambulancia recomendada y
ambulancia asignada.

## 1. Ranking de unidades

Cada vez que se crea una emergencia, el servicio heuristico evalua las
ambulancias candidatas en estado:

```text
DISPONIBLE
RECUPERADA
```

El ranking queda persistido en `ai_recommendations.criteria.ranking` y tambien
se puede consultar directamente con:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency.id)/candidate-ranking"
```

La respuesta incluye:

- `recommendation_id`: recomendacion usada como fuente del ranking.
- `recommended_ambulance_id`: ambulancia con mejor puntaje.
- `decision_reason`: razon legible de la decision.
- `candidates_count`: numero de ambulancias evaluadas.
- `ranking`: lista ordenada de candidatas con puntajes normalizados,
  ponderados y `total_score`.

## 2. Registro de recomendacion

La tabla `ai_recommendations` conserva la evidencia tecnica y la explicacion
funcional:

- `recommended_ambulance_id`: ambulancia recomendada, o `null` si no habia
  unidad disponible.
- `calculated_priority`: prioridad calculada desde la gravedad.
- `total_score`: puntaje final de la unidad recomendada.
- `decision_reason`: razon persistida de la recomendacion.
- `candidates_count`: cantidad de candidatas evaluadas.
- `criteria`: JSON auditable con pesos, referencias, seleccion y ranking.

Si no hay candidatas, `decision_reason` queda como:

```text
No hay ambulancias disponibles o recuperadas para recomendar.
```

## 3. Trazabilidad recomendado vs asignado

Cuando una ambulancia confirma una asignacion por `POST /assignments/attempt`,
la asignacion guarda:

- `recommendation_id`: recomendacion vigente para la emergencia.
- `recommended_ambulance_id`: ambulancia recomendada al momento de asignar.
- `ambulance_id`: ambulancia que finalmente gano la asignacion.
- `assignment_reason`: explica si coincide o no con la recomendacion.

Esto permite demostrar dos escenarios validos:

- La ambulancia asignada coincide con la recomendacion heuristica.
- Una ambulancia no recomendada gana por intento distribuido, por ejemplo con
  nodos ejecutados en modo `--accept-all`.

Consultar la trazabilidad completa:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency.id)/trace"
```

La respuesta incluye:

- emergencia;
- ultima recomendacion;
- asignacion activa o asignacion historica mas reciente;
- `recommended_ambulance_id`;
- `assigned_ambulance_id`;
- `assignment_matches_recommendation`;
- `trace_reason`;
- eventos de la emergencia ordenados cronologicamente.

## 4. Comprobacion rapida

Crear dos ambulancias:

```powershell
$near = Invoke-RestMethod -Method Post http://localhost:8000/ambulances `
  -ContentType "application/json" `
  -Body '{"code":"AMB-NEAR","simulated_location":"0,0","operational_load":0,"reliability":1.0}'

$far = Invoke-RestMethod -Method Post http://localhost:8000/ambulances `
  -ContentType "application/json" `
  -Body '{"code":"AMB-FAR","simulated_location":"30,0","operational_load":0,"reliability":1.0}'
```

Crear emergencia:

```powershell
$emergency = Invoke-RestMethod -Method Post http://localhost:8000/emergencies `
  -ContentType "application/json" `
  -Body '{"type":"Accidente","severity":8,"simulated_location":"0,0"}'
```

Ver ranking:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency.id)/candidate-ranking"
```

Confirmar una asignacion con la unidad recomendada:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/assignments/attempt `
  -ContentType "application/json" `
  -Body "{`"emergency_id`":`"$($emergency.id)`",`"ambulance_id`":`"$($near.id)`"}"
```

Ver trazabilidad:

```powershell
Invoke-RestMethod "http://localhost:8000/emergencies/$($emergency.id)/trace"
```

Resultado esperado:

- `recommended_ambulance_id` igual a `assigned_ambulance_id`;
- `assignment_matches_recommendation` en `true`;
- `trace_reason` indicando coincidencia con la recomendacion vigente.

## 5. Pruebas automatizadas

Ejecutar:

```powershell
pytest
```

Las pruebas cubren:

- ranking ordenado de candidatas;
- persistencia de `decision_reason` y `candidates_count`;
- caso sin candidatas;
- trazabilidad cuando asignado y recomendado coinciden;
- trazabilidad cuando gana una ambulancia no recomendada;
- reasignacion por fallo con nueva recomendacion vinculada.
