# Justificacion de DistriCare como sistema distribuido

## Proposito del documento

Este documento justifica por que DistriCare puede considerarse realmente un sistema distribuido dentro del alcance academico definido en el documento base del proyecto. La explicacion contrasta los requerimientos planteados con la implementacion actual y usa conceptos propios de sistemas distribuidos: nodos independientes, comunicacion asincronica, coordinacion, concurrencia, tolerancia a fallos, consistencia, trazabilidad y monitoreo.

El sistema no busca simular un servicio medico real en produccion. Su valor esta en demostrar, de forma controlada, como varios componentes separados cooperan para resolver un problema operativo: asignar emergencias medicas a ambulancias evitando duplicidades y manteniendo evidencia auditable.

## Que lo vuelve distribuido

DistriCare no es solo una aplicacion web con base de datos. El sistema esta dividido en componentes autonomos que se comunican mediante API y eventos:

- Backend FastAPI: coordina reglas de negocio, expone endpoints REST, registra eventos y publica emergencias.
- PostgreSQL: mantiene persistencia compartida de emergencias, ambulancias, asignaciones, recomendaciones, fallos y eventos.
- RabbitMQ: funciona como broker de mensajeria para desacoplar la publicacion de emergencias del procesamiento por nodos.
- Nodos de ambulancia simulados: procesos independientes ejecutados con `scripts/run_ambulance_node.py`, cada uno con identidad, ubicacion, heartbeat y decision propia.
- Frontend web/Electron: cliente de monitoreo y operacion que consume la API, visualiza trazabilidad y permite acciones operativas.

La distribucion aparece porque cada ambulancia no es solamente una fila en una tabla: puede ejecutarse como proceso separado, escuchar eventos, reportar recepcion/procesamiento y participar en intentos de asignacion. El backend no invoca directamente a cada ambulancia; publica un evento y los nodos reaccionan de forma independiente.

## Relacion con el alcance del documento base

El documento del proyecto establece que el sistema debe simular la interaccion entre operador, broker de mensajeria, nodos ambulancia, base de datos, dashboard e IA heuristica. La implementacion cubre esa estructura:

| Requerimiento del documento | Evidencia en DistriCare |
| --- | --- |
| Registrar emergencias medicas simuladas | `POST /emergencies` crea la emergencia, calcula prioridad y publica evento. |
| Usar comunicacion por eventos | RabbitMQ recibe eventos `emergency.prioritized`; los nodos consumen y reportan actividad. |
| Manejar ambulancias como nodos distribuidos | Cada nodo puede ejecutarse como proceso independiente con codigo, ubicacion, estado y heartbeat. |
| Evitar asignaciones duplicadas | `POST /assignments/attempt` usa bloqueo transaccional e indices unicos para permitir solo una asignacion activa por emergencia. |
| Incorporar IA heuristica | `RecommendationService` calcula prioridad, ranking y recomendacion explicable con distancia, carga, disponibilidad y confiabilidad. |
| Tolerancia a fallos | Heartbeat, deteccion de nodos inactivos, marcado de fallo y reasignacion automatica. |
| Trazabilidad completa | `/events` y `/emergencies/{id}/trace` muestran eventos, recomendacion, asignacion, fallos, reasignacion y cierre. |
| Dashboard de monitoreo | Frontend muestra panel general, emergencias, ambulancias, asignaciones, recomendaciones, trazabilidad y eventos. |

## Sincronismo y asincronismo

El sistema combina comunicacion sincronica y asincronica, que es una caracteristica comun en arquitecturas distribuidas.

La comunicacion sincronica ocurre cuando un cliente espera respuesta inmediata:

- El frontend llama a FastAPI para crear emergencias, consultar datos, intentar asignaciones o cambiar estados.
- Los nodos llaman a endpoints como `/heartbeat`, `/assignments/attempt` y `/node-events`.
- El backend responde aceptando, rechazando o retornando el estado actual.

La comunicacion asincronica ocurre cuando los componentes no dependen de una respuesta directa entre ellos:

- Al crear una emergencia, el backend publica un evento en RabbitMQ.
- Los nodos de ambulancia reciben el evento desde el broker cuando estan disponibles.
- El productor de la emergencia no necesita conocer cuantos nodos existen ni contactar a cada uno directamente.

Esta separacion permite desacoplamiento: el backend puede publicar una emergencia aunque un nodo este temporalmente caido, y los nodos pueden procesar eventos segun su propio ritmo.

## Concurrencia y coordinacion distribuida

Uno de los problemas centrales del proyecto es que varias ambulancias pueden intentar aceptar la misma emergencia. Esto reproduce un conflicto tipico de sistemas distribuidos: multiples participantes compiten por un recurso compartido.

DistriCare resuelve esa competencia con una coordinacion central transaccional:

- Varias ambulancias pueden recibir el mismo evento.
- Cada una puede intentar aceptar la emergencia mediante `POST /assignments/attempt`.
- El servicio de asignaciones consulta la emergencia y la ambulancia con bloqueo transaccional.
- La base de datos refuerza la regla con indices unicos sobre asignaciones activas confirmadas.
- Si una ambulancia ya gano, los demas intentos se rechazan y quedan registrados como eventos.

Esto demuestra consistencia fuerte en el punto critico del sistema: una emergencia no puede terminar con dos ambulancias activas asignadas al mismo tiempo.

## Consistencia y estado compartido

El sistema mantiene un estado compartido persistente en PostgreSQL. Ese estado incluye:

- Emergencias y su ciclo de vida.
- Ambulancias y su estado operativo.
- Asignaciones activas, historicas, reasignadas y finalizadas.
- Recomendaciones IA y ranking de candidatos.
- Eventos del sistema.
- Fallos de nodos.

La consistencia se garantiza en reglas como:

- Solo una asignacion activa confirmada por emergencia.
- Solo una asignacion activa confirmada por ambulancia.
- Una emergencia `CERRADA` no acepta nuevas asignaciones.
- Al cerrar una emergencia, la asignacion activa pasa a `FINALIZADA` y la ambulancia vuelve a `DISPONIBLE`.
- Si un nodo asignado falla, la asignacion anterior se desactiva y se intenta una reasignacion.

Esto permite que distintos clientes o procesos observen un mismo estado coherente aunque interactuen desde lugares diferentes.

## Tolerancia a fallos

La tolerancia a fallos esta representada en los nodos de ambulancia. El sistema asume que un nodo puede dejar de responder, fallar manualmente o perder heartbeat.

Mecanismos implementados:

- Heartbeat: cada nodo puede reportar que sigue activo.
- Deteccion de inactividad: `/failures/detect-stale` identifica nodos que superan el tiempo permitido sin heartbeat.
- Fallo manual: `/ambulances/{id}/fail` permite simular la caida de una unidad.
- Recuperacion: `/ambulances/{id}/recover` permite devolver una ambulancia al estado disponible.
- Reasignacion automatica: si falla una ambulancia con asignacion activa, el sistema desactiva la asignacion anterior, genera una nueva recomendacion y confirma otra unidad si existe candidata.
- Auditoria: los eventos `NODE_FAILED`, `REASSIGNMENT_STARTED` y `REASSIGNMENT_CONFIRMED` permiten explicar que ocurrio.

Esto cumple con el alcance del documento cuando plantea deteccion de nodos inactivos y reasignacion de emergencias ante fallos parciales.

## Inteligencia artificial como apoyo distribuido

La IA de DistriCare no reemplaza la coordinacion distribuida. Su papel es recomendar y priorizar, no asignar por si sola.

El modulo heuristico calcula:

- Prioridad de la emergencia segun severidad.
- Distancia simulada entre emergencia y ambulancia.
- Disponibilidad del nodo.
- Carga operativa.
- Confiabilidad.
- Tiempo de espera.

Luego genera un ranking auditable en `/recommendations` y `/emergencies/{id}/candidate-ranking`. Sin embargo, la asignacion definitiva sigue dependiendo del proceso distribuido de intento/confirmacion. Esto es importante porque separa decision asistida de consistencia distribuida: la IA recomienda, pero el sistema coordinador confirma una unica asignacion valida.

## Trazabilidad y observabilidad

Un sistema distribuido necesita observabilidad porque las acciones no ocurren en un solo lugar ni necesariamente en orden lineal visible para el usuario.

DistriCare registra eventos para:

- Creacion y publicacion de emergencias.
- Priorizacion y recomendacion IA.
- Recepcion/procesamiento por nodos.
- Intentos de asignacion.
- Confirmaciones y rechazos.
- Fallos y recuperaciones.
- Reasignaciones.
- Cambio de estado y cierre de emergencia.

La trazabilidad se expone en:

- `GET /events`: auditoria global.
- `GET /emergencies/{id}/trace`: reconstruccion del ciclo de vida de una emergencia.
- Frontend: pantallas de Trazabilidad y Eventos del sistema.

Esto permite defender que el prototipo no solo ejecuta acciones, sino que deja evidencia de como se comportan los componentes distribuidos.

## Escalabilidad y desacoplamiento

RabbitMQ permite que el sistema no dependa de una lista fija de ambulancias conectadas directamente al backend. En una simulacion local se pueden levantar dos o tres nodos; conceptualmente, se pueden levantar mas procesos consumidores sin cambiar el endpoint de creacion de emergencias.

El desacoplamiento aparece en tres niveles:

- El frontend no accede directamente a la base de datos; usa API.
- El backend no llama directamente a cada ambulancia; publica eventos.
- Los nodos no comparten memoria entre ellos; coordinan mediante API, broker y base de datos.

Esto refleja una arquitectura distribuida basica, modular y extensible.

## Limites del prototipo

Para ser tecnicamente honestos, DistriCare es un prototipo academico, no un sistema distribuido productivo de alta disponibilidad. Sus limites actuales son:

- No hay multiples instancias del backend en balanceo.
- No hay replicacion de PostgreSQL ni cluster de RabbitMQ.
- No hay consenso distribuido tipo Raft/Paxos.
- No hay autenticacion ni control de usuarios.
- No hay GPS real ni integracion con servicios medicos reales.
- Los nodos son procesos simulados, no dispositivos fisicos.

Estos limites no invalidan su caracter distribuido dentro del alcance del curso. El objetivo era aplicar conceptos de sistemas distribuidos a un entorno realista y controlado, no construir una plataforma hospitalaria productiva.

## Conclusiones

DistriCare puede justificarse como sistema distribuido porque integra componentes independientes que cooperan mediante comunicacion sincronica y asincronica, usa un broker de eventos, simula nodos autonomos, maneja concurrencia, evita asignaciones duplicadas, tolera fallos parciales, reasigna automaticamente y mantiene trazabilidad completa.

Frente al documento base, la aplicacion cumple el nucleo conceptual del proyecto:

- Arquitectura cliente/servidor ampliada con eventos.
- Ambulancias como nodos distribuidos.
- Broker de mensajeria para asincronismo.
- Persistencia y auditoria centralizada.
- IA heuristica explicable.
- Coordinacion para asignacion exclusiva.
- Tolerancia a fallos con heartbeat y reasignacion.
- Dashboard para monitoreo y validacion.

Por tanto, el aplicativo no se limita a una interfaz CRUD. Su comportamiento principal depende de la interaccion coordinada entre procesos, servicios, eventos, base de datos y nodos simulados, que son precisamente los elementos que lo convierten en un sistema distribuido academico defendible.
