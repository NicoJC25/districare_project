# Integracion API - Fase 5

## Configuracion

El frontend usa `VITE_API_BASE_URL` como URL base. Si no existe, usa:

```text
http://127.0.0.1:8000
```

La aplicacion Electron empaqueta solo el frontend y conserva el mismo consumo HTTP. Por eso, antes de abrir el ejecutable, el backend debe estar disponible en `http://127.0.0.1:8000`.

El backend se ajusto con CORS local para permitir:

```text
http://localhost:5173
http://127.0.0.1:5173
null
```

El origen `null` cubre el caso de Electron en produccion, donde el frontend se carga desde `dist/index.html` como archivo local.

## Endpoints consumidos

- `GET /health`
- `GET /emergencies`
- `POST /emergencies`
- `PATCH /emergencies/{emergency_id}/state`
- `GET /ambulances`
- `POST /ambulances`
- `POST /ambulances/{ambulance_id}/fail`
- `POST /ambulances/{ambulance_id}/recover`
- `POST /failures/detect-stale`
- `GET /assignments`
- `POST /assignments/attempt`
- `GET /recommendations`
- `GET /events`
- `GET /emergencies/{emergency_id}/candidate-ranking`
- `GET /emergencies/{emergency_id}/trace`

## Modelos frontend

Se crearon tipos TypeScript para:

- `Emergency`
- `Ambulance`
- `Assignment`
- `AIRecommendation`
- `CandidateRanking`
- `EmergencyTrace`
- `SystemEvent`

Estos tipos reflejan los schemas Pydantic actuales y no agregan campos inexistentes.

El cambio manual de estado usa `EmergencyStateUpdate` y solo acepta:

```json
{ "state": "EN_ATENCION" }
```

```json
{ "state": "CERRADA" }
```

Reglas principales: una emergencia cerrada no acepta nuevas asignaciones; al cerrar una emergencia asignada se finaliza la asignacion activa y se libera la ambulancia.

## Manejo de estados

- `LoadingState`: mientras se cargan datos iniciales.
- `ErrorState`: cuando falla la conexion inicial con API.
- `EmptyState`: cuando una tabla o panel no tiene registros.
- Topbar: muestra `API conectada` o `API sin conexion`.
- Auto-refresh: cada 10 segundos, mas boton manual `Actualizar`.

## Limitaciones actuales

- No hay autenticacion.
- No hay paginacion backend.
- No hay streaming ni WebSockets; la actualizacion es por polling.
- Las acciones POST muestran resultado basico y refrescan datos al terminar.
