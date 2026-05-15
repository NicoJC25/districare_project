# Extension IA heuristica - DistriCare

Esta extension convierte la recomendacion de ambulancias en una heuristica
auditable por reglas y ponderaciones. El flujo distribuido no cambia: el backend
solo recomienda, publica el evento y los nodos siguen intentando aceptar la
emergencia mediante el endpoint de asignaciones.

## Criterios y pesos

Cada ambulancia candidata recibe puntajes normalizados entre `0` y `100`.
El puntaje final se calcula con estos pesos:

```text
total_score =
  gravedad * 0.25 +
  distancia_simulada * 0.25 +
  disponibilidad * 0.15 +
  carga_operativa * 0.15 +
  confiabilidad * 0.15 +
  tiempo_espera * 0.05
```

Los criterios son:

- `severity`: gravedad de la emergencia, usando `severity * 10` con maximo `100`.
- `distance`: cercania segun `simulated_distance`, degradada hasta una distancia de referencia de `50`.
- `availability`: `DISPONIBLE` puntua `100`; `RECUPERADA` puntua `85`.
- `operational_load`: menor carga operativa puntua mejor, con referencia maxima de `10`.
- `reliability`: confiabilidad del nodo en escala `0.0` a `1.0`.
- `waiting_time`: tiempo transcurrido desde `created_at`, con referencia maxima de `30` minutos.

## Candidatos

Solo participan ambulancias en estados:

```text
DISPONIBLE
RECUPERADA
```

La recomendacion no autoasigna ni bloquea intentos. La confirmacion sigue en
`POST /assignments/attempt`, donde se mantiene la asignacion exclusiva y atomica.

## Evidencia en API

La evidencia queda en `GET /recommendations`, dentro de `criteria`.
Ese JSON incluye:

- `weights`: pesos usados para cada criterio.
- `references`: limites y valores de referencia de la heuristica.
- `emergency`: gravedad, prioridad y puntaje de espera.
- `selected`: ambulancia seleccionada con desglose completo.
- `ranking`: lista completa de candidatos ordenados por `total_score`.
- `no_candidate_reason`: razon cuando no hay unidad disponible.

Ejemplo resumido:

```json
{
  "recommended_ambulance_id": "...",
  "calculated_priority": 80,
  "total_score": 91.73,
  "criteria": {
    "weights": {
      "severity": 0.25,
      "distance": 0.25,
      "availability": 0.15,
      "operational_load": 0.15,
      "reliability": 0.15,
      "waiting_time": 0.05
    },
    "selected": {
      "code": "AMB-A",
      "normalized_scores": {
        "severity": 80,
        "distance": 97.17,
        "availability": 100,
        "operational_load": 100,
        "reliability": 100,
        "waiting_time": 0.03
      },
      "weighted_scores": {
        "severity": 20,
        "distance": 24.29,
        "availability": 15,
        "operational_load": 15,
        "reliability": 15,
        "waiting_time": 0
      },
      "total_score": 89.29
    }
  }
}
```

## Comprobacion rapida

Crear ambulancias con diferentes condiciones:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/ambulances `
  -ContentType "application/json" `
  -Body '{"code":"AMB-A","simulated_location":"0,0","operational_load":0,"reliability":1.0}'

Invoke-RestMethod -Method Post http://localhost:8000/ambulances `
  -ContentType "application/json" `
  -Body '{"code":"AMB-B","simulated_location":"10,0","operational_load":8,"reliability":0.5}'
```

Crear una emergencia:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/emergencies `
  -ContentType "application/json" `
  -Body '{"type":"Accidente","severity":8,"simulated_location":"1,1"}'
```

Consultar la evidencia:

```powershell
Invoke-RestMethod http://localhost:8000/recommendations
```

## Pruebas automatizadas

Ejecutar:

```powershell
pytest
```

Las pruebas cubren:

- seleccion por menor distancia cuando lo demas es equivalente;
- balance entre distancia, carga operativa y confiabilidad;
- penalizacion de disponibilidad para nodos `RECUPERADA`;
- presencia de los seis criterios en `criteria`;
- recomendacion sin candidato cuando no hay unidades elegibles.
