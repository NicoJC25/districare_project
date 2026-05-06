# Trazabilidad de creacion - Fase 2 DistriCare

Este documento resume el orden seguido para completar la fase 2 del proyecto
DistriCare. La fase se enfoco en dejar evidencia de comunicacion distribuida con
RabbitMQ, publicacion de emergencias, nodos de ambulancia independientes,
heartbeat, estados de nodo y log de eventos recibidos/procesados.

## 1. Punto de partida

La fase 2 parte de la base inicial documentada en `docs/fase_1/`:

- API FastAPI en `backend/`.
- Modelos SQLAlchemy y migracion inicial.
- PostgreSQL para persistencia.
- RabbitMQ disponible en `infrastructure/docker-compose.yml`.
- Simulador de ambulancias en `simulator/ambulance_node/`.
- Bitacora persistente en `system_events`.

No fue necesario crear nuevas tablas para esta fase, porque la bitacora de
eventos existente permite registrar tanto eventos del backend como eventos
reportados por los nodos.

## 2. Broker de eventos

Primero se mantuvo RabbitMQ como broker oficial de la fase:

- `infrastructure/docker-compose.yml`: ya define RabbitMQ con consola web.
- `backend/app/core/config.py`: conserva `rabbitmq_url` y `rabbitmq_exchange`.
- `backend/app/messaging/rabbitmq.py`: publica mensajes JSON en un exchange
  `topic` llamado `districare.events`.

La ruta usada para emergencias priorizadas es:

```text
emergency.prioritized
```

Credenciales locales de RabbitMQ:

- usuario: `guest`
- contrasena: `guest`
- AMQP: `amqp://guest:guest@localhost:5673/`
- consola web: `http://localhost:15673`

## 3. Publicacion de emergencias

Luego se ajusto el flujo de creacion de emergencias en:

- `backend/app/services/emergencies.py`

Al crear una emergencia, el backend:

1. Guarda la emergencia con estado `REGISTRADA`.
2. Registra `EMERGENCY_CREATED` en la bitacora.
3. Ejecuta la recomendacion heuristica.
4. Cambia la emergencia a `PUBLICADA`.
5. Publica en RabbitMQ el evento `emergency.prioritized`.
6. Registra `EMERGENCY_PUBLISHED`.

El payload publicado incluye:

- `event`
- `emergency_id`
- `type`
- `severity`
- `simulated_location`
- `recommended_ambulance_id`
- `priority`

Esto permite que los nodos tengan suficiente informacion para decidir si deben
intentar atender la emergencia.

## 4. Estados de nodo

Despues se alinearon los estados visibles de ambulancia con la rubrica en:

- `backend/app/domain/enums.py`
- `backend/app/services/assignments.py`
- `backend/app/services/failures.py`
- `backend/app/services/ambulances.py`

Estados usados en fase 2:

- `DISPONIBLE`: nodo activo y listo para recibir emergencias.
- `OCUPADO`: nodo con una asignacion activa confirmada.
- `INACTIVO`: estado reservado para nodos sin comunicacion.
- `FALLIDO`: nodo marcado como fallido manualmente o por timeout.

Cuando una ambulancia acepta una emergencia, pasa a `OCUPADO`. Cuando se detecta
fallo manual o por heartbeat vencido, pasa a `FALLIDO`. Si se recupera por
endpoint manual o por nuevo heartbeat, vuelve a `DISPONIBLE`.

## 5. Recepcion y procesamiento de eventos por nodo

Para registrar que cada nodo recibe y procesa eventos, se agrego un endpoint
interno en:

- `backend/app/api/router.py`
- `backend/app/schemas/event.py`
- `backend/app/services/ambulances.py`

Endpoint creado:

```text
POST /ambulances/{ambulance_id}/node-events
```

Este endpoint recibe reportes del simulador y los guarda en `system_events`.
Los tipos de evento nuevos son:

- `NODE_EVENT_RECEIVED`: el nodo recibio un evento desde RabbitMQ.
- `NODE_EVENT_PROCESSED`: el nodo tomo una decision sobre el evento.

La metadata registrada puede incluir:

- etapa (`received` o `processed`);
- decision tomada;
- resultado;
- detalle del rechazo o procesamiento;
- payload original recibido desde RabbitMQ.

## 6. Consulta de asignaciones

Para facilitar la demo y la verificacion del flujo, se agrego:

- `GET /assignments`

Este endpoint quedo en `backend/app/api/router.py` y devuelve las asignaciones
ordenadas por fecha. Sirve para comprobar que solo una ambulancia queda asignada
activamente a cada emergencia.

## 7. Simulador de ambulancias

Luego se actualizo el simulador para reportar trazabilidad de nodo:

- `simulator/ambulance_node/node_client.py`
- `simulator/ambulance_node/main.py`

Flujo del nodo:

1. Se registra en `POST /ambulances`.
2. Inicia heartbeat periodico con `POST /ambulances/{id}/heartbeat`.
3. Declara una cola durable `ambulance.{codigo}` en RabbitMQ.
4. Se suscribe a `emergency.prioritized`.
5. Al recibir un mensaje, reporta `NODE_EVENT_RECEIVED`.
6. Si fue recomendado, intenta aceptar con `POST /assignments/attempt`.
7. Reporta `NODE_EVENT_PROCESSED` con resultado `accepted` o `rejected`.
8. Si no fue recomendado, reporta `NODE_EVENT_PROCESSED` con decision `ignored`.

La opcion `--accept-all` permite que un nodo intente aceptar cualquier
emergencia publicada, util para demostrar competencia entre nodos.

## 8. Documentacion de demo

Se creo la carpeta de documentacion de fase 2:

- `docs/fase_2/`

Archivos de esta carpeta:

- `docs/fase_2/fase_2.md`: guia corta de demo local.
- `docs/fase_2/trazabilidad_fase_2.md`: este documento de trazabilidad.

Tambien se actualizo:

- `README.md`

El README enlaza la guia de fase 2 para que sea facil encontrar los comandos de
ejecucion.

## 9. Pruebas automatizadas

Finalmente se ampliaron las pruebas en:

- `backend/tests/test_distributed_base.py`

Casos cubiertos para fase 2:

- la emergencia publica un payload enriquecido a RabbitMQ;
- el endpoint de eventos de nodo registra recepcion y procesamiento;
- una asignacion confirmada cambia la ambulancia a `OCUPADO`;
- una falla manual o por heartbeat vencido marca el nodo como `FALLIDO`;
- `/events` expone eventos publicados, recibidos y procesados;
- `/assignments` lista asignaciones confirmadas.

Comando de verificacion usado:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Resultado esperado:

```text
9 passed
```

## 10. Flujo funcional completo

El flujo final de fase 2 queda asi:

1. Se levanta PostgreSQL y RabbitMQ con Docker Compose.
2. Alembic asegura el esquema de base de datos.
3. Se inicia el backend FastAPI.
4. Se lanzan dos o mas nodos de ambulancia como procesos independientes.
5. Cada nodo se registra y envia heartbeat periodico.
6. Se crea una emergencia con `POST /emergencies`.
7. El backend calcula prioridad y recomendacion.
8. El backend publica `emergency.prioritized` en RabbitMQ.
9. Los nodos reciben el evento desde sus colas.
10. Cada nodo reporta la recepcion al backend.
11. El nodo recomendado intenta aceptar la emergencia.
12. El backend confirma una sola asignacion activa.
13. La ambulancia asignada queda `OCUPADO`.
14. Cada nodo reporta como proceso el evento.
15. `/events`, `/ambulances` y `/assignments` muestran la evidencia de la demo.

## 11. Estado final

La fase 2 queda lista para demostrar:

- broker RabbitMQ configurado;
- publicacion de emergencias como eventos;
- nodos de ambulancia independientes;
- recepcion y procesamiento de eventos por nodo;
- heartbeat basico;
- estados `DISPONIBLE`, `OCUPADO`, `INACTIVO`, `FALLIDO`;
- log centralizado de eventos publicados, recibidos y procesados;
- pruebas automatizadas para validar el flujo.
