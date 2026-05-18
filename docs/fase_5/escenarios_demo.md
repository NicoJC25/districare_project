# Escenarios demo - Fase 5

## Preparacion

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
alembic -c backend/alembic.ini upgrade head
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En otra terminal:

```powershell
python scripts/seed_demo_data.py
```

## Escenarios creados

- Recomendacion normal: una ambulancia recomendada por IA acepta la emergencia.
- Intento distribuido: una ambulancia distinta a la recomendada gana por intento manual.
- Reasignacion automatica: una ambulancia asignada falla y el sistema recomienda/asigna una alternativa.
- Cierre operativo: una emergencia pasa a `EN_ATENCION` y luego a `CERRADA`.

Las ubicaciones simuladas se registran como `latitud,longitud`. La distancia que aparece en recomendaciones corresponde a kilometros aproximados calculados con Haversine.

## Recorrido sugerido

1. Abrir Panel General y revisar contadores por estado.
2. Entrar a Recomendaciones IA y revisar ranking, puntaje y explicacion.
3. Entrar a Asignaciones y confirmar asignaciones activas, historicas, reasignadas y finalizadas.
4. Entrar a Trazabilidad y elegir emergencias demo para ver eventos cronologicos.
5. Entrar a Eventos del sistema y filtrar por `ASSIGNMENT`, `REASSIGNMENT` o `EMERGENCY`.

## Criterios de aceptacion visibles

- Solo queda una asignacion activa confirmada por emergencia.
- Los intentos rechazados aparecen como eventos auditables.
- Un fallo de nodo asignado genera eventos de reasignacion.
- Una emergencia cerrada muestra `closed_at`, asignacion finalizada y ambulancia liberada.
