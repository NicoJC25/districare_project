# Trazabilidad de creacion - Base inicial DistriCare

Este documento resume el orden seguido para construir la base inicial del proyecto DistriCare y explica que papel cumple cada grupo de archivos. La idea es dejar evidencia del proceso de construccion, desde la estructura del monorepo hasta la simulacion distribuida con nodos de ambulancia.

## 1. Preparacion del monorepo

El primer paso fue crear una estructura base para separar responsabilidades:

- `backend/`: API central, modelo de datos, servicios de dominio y migraciones.
- `simulator/`: procesos independientes que representan nodos de ambulancia.
- `infrastructure/`: servicios externos necesarios para ejecutar el sistema localmente.
- `docs/`: documentacion de fase y trazabilidad.
- `scripts/`: comandos auxiliares para ejecutar componentes del proyecto.

Archivos creados en esta etapa:

- `pyproject.toml`: define dependencias principales: FastAPI, SQLAlchemy, Alembic, PostgreSQL, RabbitMQ, HTTPX y Pytest.
- `.env.example`: documenta variables de entorno usadas por backend y simulador.
- `.gitignore`: evita versionar entornos virtuales, cache de Python, archivos `.env` y artefactos de instalacion.
- `README.md`: deja los pasos de inicio rapido del proyecto.
- `docs/fase_1/modelo_inicial.md`: describe el modelo inicial y los objetivos distribuidos.

## 2. Infraestructura local

Luego se definio la infraestructura minima para simular un sistema distribuido en desarrollo:

- PostgreSQL para persistencia transaccional.
- RabbitMQ para publicacion y consumo de eventos.

Archivo principal:

- `infrastructure/docker-compose.yml`

Durante la validacion local se ajustaron los puertos para evitar conflictos con servicios existentes y rangos reservados por Windows:

- PostgreSQL externo: `localhost:15432`
- RabbitMQ AMQP externo: `localhost:5673`
- RabbitMQ UI externa: `http://localhost:15673`

Este ajuste fue necesario porque el puerto `5432` podia estar ocupado por otro PostgreSQL local y un puerto anterior de prueba caia dentro de un rango reservado por Windows.

## 3. Configuracion del backend

Despues se creo la base de configuracion del backend:

- `backend/app/core/config.py`: carga configuracion desde variables de entorno y define valores por defecto.
- `backend/app/db/session.py`: crea el engine SQLAlchemy, la sesion de base de datos y el `Base` declarativo.
- `backend/app/main.py`: instancia FastAPI e incluye el router principal.

Tambien se agregaron archivos `__init__.py` para que los paquetes Python fueran importables.

## 4. Dominio y estados del sistema

Antes de crear modelos se definieron los estados principales del dominio en:

- `backend/app/domain/enums.py`

Los estados cubren:

- ciclo de vida de emergencias;
- estados de ambulancias/nodos;
- estados de asignacion;
- estados de recuperacion de fallos;
- tipos de eventos del sistema.

Esto permite que el flujo distribuido sea explicito y trazable desde el codigo.

## 5. Modelo de datos

Se implementaron los modelos SQLAlchemy alineados con los diagramas de fases anteriores:

- `backend/app/models/emergency.py`: emergencia medica simulada.
- `backend/app/models/ambulance.py`: nodo de ambulancia simulado.
- `backend/app/models/assignment.py`: asignacion entre emergencia y ambulancia.
- `backend/app/models/event.py`: bitacora de eventos del sistema.
- `backend/app/models/recommendation.py`: recomendacion generada por IA heuristica.
- `backend/app/models/failure.py`: fallo y recuperacion de nodo.
- `backend/app/models/common.py`: utilidades comunes para UUID y fecha de creacion.
- `backend/app/models/__init__.py`: centraliza imports de modelos.

La restriccion mas importante se agrego en `Assignment`: una emergencia solo puede tener una asignacion activa confirmada. Esta regla no queda solo en Python, sino tambien en base de datos mediante un indice unico parcial:

```sql
CREATE UNIQUE INDEX uq_active_confirmed_assignment_per_emergency
ON assignments (emergency_id)
WHERE active IS TRUE AND state = 'CONFIRMADA';
```

Esto permite soportar reasignacion: antes de confirmar una nueva ambulancia, la asignacion anterior se desactiva.

## 6. Migraciones Alembic

Una vez definido el modelo, se agrego Alembic para que el esquema sea reproducible:

- `backend/alembic.ini`: configuracion de Alembic.
- `backend/alembic/env.py`: carga metadata de SQLAlchemy y configuracion del proyecto.
- `backend/alembic/script.py.mako`: plantilla de migraciones.
- `backend/alembic/versions/0001_initial_schema.py`: migracion inicial de tablas, relaciones, indices y restriccion unica parcial.

La migracion crea:

- `emergencies`
- `ambulance_nodes`
- `assignments`
- `system_events`
- `ai_recommendations`
- `node_failures`

## 7. Esquemas de entrada y salida

Se agregaron esquemas Pydantic para separar API y persistencia:

- `backend/app/schemas/emergency.py`
- `backend/app/schemas/ambulance.py`
- `backend/app/schemas/assignment.py`
- `backend/app/schemas/event.py`
- `backend/app/schemas/recommendation.py`

Estos esquemas definen los cuerpos de entrada y las respuestas de la API.

## 8. Servicios de dominio

Despues se implemento la logica principal del sistema:

- `backend/app/services/events.py`: registra eventos por cada transicion importante.
- `backend/app/services/location.py`: calcula distancia simulada entre ubicaciones.
- `backend/app/services/recommendations.py`: selecciona ambulancia con heuristica por severidad, distancia, carga y confiabilidad.
- `backend/app/services/ambulances.py`: registra ambulancias, procesa heartbeat y recuperacion.
- `backend/app/services/assignments.py`: procesa intentos de asignacion y respeta la restriccion unica.
- `backend/app/services/failures.py`: detecta o fuerza caida de nodo y activa reasignacion automatica.
- `backend/app/services/emergencies.py`: crea emergencia, genera recomendacion y publica evento al broker.

La logica quedo separada de los endpoints para poder probarla y evolucionarla con menos acoplamiento.

## 9. Mensajeria con RabbitMQ

Para representar comunicacion distribuida se agrego:

- `backend/app/messaging/rabbitmq.py`

Este componente publica eventos de emergencia priorizada en RabbitMQ. Si RabbitMQ no esta disponible durante pruebas unitarias, el publisher falla de forma controlada y registra advertencia.

## 10. API REST

Se implemento el router principal en:

- `backend/app/api/router.py`

Endpoints incluidos:

- `GET /health`
- `POST /emergencies`
- `GET /emergencies`
- `GET /emergencies/{id}`
- `POST /ambulances`
- `GET /ambulances`
- `POST /ambulances/{id}/heartbeat`
- `POST /ambulances/{id}/fail`
- `POST /ambulances/{id}/recover`
- `POST /assignments/attempt`
- `POST /failures/detect-stale`
- `GET /events`
- `GET /recommendations`

Tambien se mejoro `GET /health` para validar la conexion real a la base de datos y no solo responder que la API esta viva.

## 11. Simulador de nodos de ambulancia

Luego se construyo el simulador como proceso independiente:

- `simulator/ambulance_node/node_client.py`: cliente HTTP contra el backend.
- `simulator/ambulance_node/heartbeat.py`: hilo que envia heartbeat periodico.
- `simulator/ambulance_node/main.py`: registra el nodo, inicia heartbeat y escucha eventos RabbitMQ.
- `scripts/run_ambulance_node.py`: punto de entrada para lanzar un nodo desde consola.

Flujo del simulador:

1. El proceso registra la ambulancia en el backend.
2. Inicia envio periodico de heartbeat.
3. Se conecta a RabbitMQ.
4. Escucha eventos `emergency.prioritized`.
5. Si la emergencia fue recomendada para ese nodo, intenta aceptarla.
6. El backend confirma o rechaza segun la restriccion de asignacion unica.

Este comportamiento permite demostrar concurrencia: varios nodos pueden recibir el mismo evento, pero solo uno queda confirmado.

## 12. Scripts auxiliares

Se agregaron scripts para facilitar ejecucion:

- `scripts/run_infrastructure.ps1`: levanta PostgreSQL y RabbitMQ.
- `scripts/run_backend.ps1`: inicia FastAPI con Uvicorn.
- `scripts/run_ambulance_node.py`: inicia un nodo de ambulancia simulado.

## 13. Pruebas automatizadas

Finalmente se agrego una suite de pruebas:

- `backend/tests/conftest.py`: configura base SQLite en memoria y cliente de pruebas.
- `backend/tests/test_distributed_base.py`: valida el comportamiento principal.

Casos cubiertos:

- creacion de emergencia y eventos iniciales;
- heartbeat de ambulancia;
- deteccion de nodo caido por timeout;
- recuperacion de nodo;
- recomendacion IA;
- rechazo de segundo intento de asignacion;
- reasignacion automatica cuando falla la ambulancia asignada.

Comando de verificacion usado:

```powershell
python -m pytest -p no:cacheprovider
```

Resultado esperado:

```text
6 passed
```

## 14. Flujo funcional completo

El flujo principal implementado queda asi:

1. Se levanta infraestructura con Docker Compose.
2. Alembic crea el esquema en PostgreSQL.
3. Se inicia el backend FastAPI.
4. Se lanzan uno o mas nodos de ambulancia como procesos separados.
5. Cada nodo se registra y envia heartbeat.
6. El operador crea una emergencia con `POST /emergencies`.
7. El backend registra evento de creacion.
8. La IA heuristica calcula prioridad y ranking.
9. El backend publica el evento `emergency.prioritized` en RabbitMQ.
10. Los nodos reciben el evento.
11. Los nodos candidatos intentan aceptar la emergencia.
12. El backend confirma una unica asignacion por transaccion y restriccion de BD.
13. Los intentos duplicados quedan rechazados y registrados como eventos.
14. Si la ambulancia asignada falla, el sistema registra el fallo, desactiva la asignacion anterior y busca reasignar automaticamente.

## 15. Ajustes realizados durante validacion

Durante la ejecucion local se hicieron ajustes para mejorar estabilidad y trazabilidad:

- PostgreSQL se movio a `localhost:15432` por conflicto con `5432` y rangos reservados de Windows.
- RabbitMQ se movio a `localhost:5673` y su consola a `localhost:15673`.
- Se enlazaron puertos a `127.0.0.1` para evitar problemas de permisos de socket en Windows.
- Se agrego timeout corto de conexion a PostgreSQL.
- El endpoint `/health` ahora revisa base de datos.
- El simulador valida `/health` antes de registrar una ambulancia, para mostrar errores mas claros.

## 16. Estado final

La base del proyecto queda lista para demostrar:

- arquitectura distribuida con backend, broker y nodos simulados;
- persistencia transaccional en PostgreSQL;
- trazabilidad por eventos;
- heartbeat, caida y recuperacion de nodos;
- reasignacion automatica;
- seleccion heuristica de ambulancia;
- control de asignacion unica desde base de datos.
