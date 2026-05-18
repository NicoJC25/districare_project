# Alcance final del programa DistriCare

## Proposito

Este documento resume el alcance final implementado de DistriCare y lo contrasta con el documento base del proyecto, donde se definieron el analisis, la planeacion, los objetivos, la arquitectura distribuida, los requerimientos y la interfaz esperada.

DistriCare queda como un prototipo academico funcional de sistema distribuido para la gestion simulada de emergencias medicas. Su objetivo no es operar un servicio real de ambulancias, sino demostrar conceptos de sistemas distribuidos aplicados a un escenario cercano a la realidad: registro de emergencias, recomendacion inteligente, comunicacion por eventos, competencia entre nodos, asignacion exclusiva, tolerancia a fallos, reasignacion, trazabilidad y visualizacion operativa.

## Alcance funcional implementado

El programa permite registrar emergencias medicas simuladas, calcular su prioridad, recomendar ambulancias mediante una heuristica explicable y publicar eventos para que nodos de ambulancia independientes reaccionen. Cada emergencia puede ser asignada a una unica ambulancia, pasar a atencion y cerrarse, dejando trazabilidad del ciclo completo.

Funcionalidades principales:

- Registro de emergencias con tipo, severidad y ubicacion simulada en formato `latitud,longitud`.
- Registro de ambulancias con codigo, ubicacion, carga operativa y confiabilidad.
- Calculo de prioridad de emergencia.
- Ranking IA de ambulancias candidatas.
- Publicacion de emergencias mediante RabbitMQ.
- Nodos simulados de ambulancia ejecutados como procesos separados.
- Heartbeat de nodos.
- Deteccion de nodos inactivos.
- Marcado manual de fallos.
- Recuperacion de ambulancias.
- Intento de asignacion por ambulancia.
- Regla de asignacion exclusiva por emergencia.
- Regla de una asignacion activa por ambulancia.
- Reasignacion automatica si falla una ambulancia asignada.
- Cambio de estado de emergencia a `EN_ATENCION`.
- Cierre de emergencia con `closed_at`.
- Finalizacion de asignacion al cerrar emergencia.
- Liberacion de ambulancia al cerrar emergencia.
- Registro global de eventos del sistema.
- Trazabilidad por emergencia.
- Dashboard web y aplicacion de escritorio Electron para visualizacion.

## Contraste con el documento base

| Elemento definido en el Word | Estado final en el programa |
| --- | --- |
| Sistema distribuido basado en eventos | Implementado con FastAPI, RabbitMQ, PostgreSQL y nodos simulados de ambulancia. |
| Operador de emergencias | Representado por el dashboard, desde donde se registran emergencias, ambulancias y acciones operativas. |
| Broker de mensajeria | Implementado con RabbitMQ y publicacion de eventos `emergency.prioritized`. |
| Ambulancias como nodos distribuidos | Implementadas como procesos independientes con `scripts/run_ambulance_node.py`. |
| Persistencia de datos | Implementada con PostgreSQL, SQLAlchemy y migraciones Alembic. |
| Comunicacion asincronica | Implementada mediante RabbitMQ para publicar emergencias hacia nodos. |
| Comunicacion sincronica | Implementada mediante API REST para frontend, nodos y acciones de asignacion. |
| Asignacion exclusiva | Implementada con bloqueo transaccional e indices unicos para evitar duplicidad. |
| IA heuristica | Implementada con reglas ponderadas: gravedad, distancia, disponibilidad, carga, confiabilidad y espera. |
| Distancia simulada | Mejorada a distancia geografica aproximada usando latitud/longitud y formula Haversine. |
| Tolerancia a fallos | Implementada con heartbeat, deteccion de nodos inactivos, fallo manual, recuperacion y reasignacion. |
| Trazabilidad completa | Implementada con `/events` y `/emergencies/{id}/trace`. |
| Dashboard de monitoreo | Implementado en React con paginas de panel general, emergencias, ambulancias, asignaciones, IA, trazabilidad y eventos. |
| Aplicacion ejecutable | Implementada como app Electron que empaqueta el frontend. |
| Alcance academico | Se mantiene: no se integra con servicios reales ni se usa informacion clinica real. |

## Arquitectura final

La arquitectura queda compuesta por varios componentes cooperando:

- `backend/`: API FastAPI, servicios de dominio, modelos, esquemas y reglas de negocio.
- `infrastructure/`: servicios Docker para PostgreSQL y RabbitMQ.
- `scripts/`: nodos simulados de ambulancia y datos demo.
- `frontend/`: dashboard React/Vite/Tailwind.
- `frontend/electron/`: envoltura Electron para abrir el dashboard como aplicacion de escritorio.
- `docs/`: documentacion tecnica y de fases.

La separacion entre estos componentes permite demostrar que el sistema no depende de un unico proceso monolitico. El backend coordina, RabbitMQ desacopla, la base de datos persiste, los nodos simulan participantes distribuidos y el frontend observa/actua sobre el sistema.

## Alcance de la inteligencia artificial

La IA del proyecto es heuristica y explicable, tal como se planteo en el documento base. No usa aprendizaje automatico real ni modelos entrenados, porque el alcance academico prioriza reglas auditables y viables.

La recomendacion considera:

- Gravedad de la emergencia.
- Distancia geografica aproximada en kilometros.
- Disponibilidad de la ambulancia.
- Carga operativa.
- Confiabilidad del nodo.
- Tiempo de espera.

La IA no asigna automaticamente por si sola. Su funcion es recomendar y justificar. La asignacion real sigue dependiendo del proceso distribuido de intento y confirmacion, lo cual mantiene separada la capa de apoyo a decision de la capa de consistencia del sistema.

## Alcance distribuido

DistriCare evidencia conceptos de sistemas distribuidos en los siguientes puntos:

- Nodos independientes: cada ambulancia puede ejecutarse como proceso separado.
- Ausencia de memoria compartida entre nodos: los nodos coordinan mediante API, broker y base de datos.
- Comunicacion asincronica: RabbitMQ distribuye emergencias publicadas.
- Comunicacion sincronica: API REST para operaciones que requieren respuesta inmediata.
- Concurrencia: varias ambulancias pueden intentar aceptar la misma emergencia.
- Consistencia: solo una ambulancia puede quedar asignada activamente a una emergencia.
- Tolerancia a fallos: deteccion de nodos inactivos, fallos manuales, recuperacion y reasignacion.
- Observabilidad: todos los eventos relevantes quedan registrados.
- Trazabilidad: se puede reconstruir el ciclo de vida de una emergencia.

## Alcance de interfaz

El frontend final funciona como dashboard operativo y tambien como aplicacion de escritorio mediante Electron. Incluye:

- Panel General: resumen de emergencias, flota, asignaciones, recomendaciones y eventos.
- Emergencias: creacion, consulta, inicio de atencion, cierre y acceso a trazabilidad.
- Ambulancias: registro, fallo, recuperacion, heartbeat visible y estado de flota.
- Asignaciones: intentos manuales, resultado, asignaciones activas, historicas, reasignadas y finalizadas.
- Recomendaciones IA: ranking de candidatos y explicacion del puntaje.
- Trazabilidad: auditoria por emergencia, comparacion IA/asignacion y eventos cronologicos.
- Eventos del sistema: auditoria global con filtros y metadata expandible.

Electron no empaqueta el backend ni la base de datos. Su alcance es presentar el frontend como aplicacion ejecutable, manteniendo la arquitectura distribuida externa.

## Alcance de datos y simulacion

Las ubicaciones se manejan como coordenadas `latitud,longitud` en el campo `simulated_location`. Esta decision permite mayor realismo sin modificar la estructura de base de datos ni los contratos principales.

El sistema incluye un script de datos demo:

```powershell
python scripts/seed_demo_data.py
```

Este script crea escenarios para demostrar:

- Recomendacion normal.
- Asignacion distinta a la recomendacion IA por intento distribuido.
- Fallo de ambulancia asignada.
- Reasignacion automatica.
- Emergencia cerrada.

## Fuera de alcance

Por tratarse de un prototipo academico, quedan fuera del alcance final:

- Integracion con sistemas reales de emergencia.
- GPS real o seguimiento en mapa.
- Datos clinicos reales.
- Usuarios, autenticacion y roles.
- Alta disponibilidad real con multiples instancias de backend.
- Cluster real de RabbitMQ.
- Replicacion de base de datos.
- Consenso distribuido tipo Raft o Paxos.
- Machine Learning entrenado con datos historicos.
- Notificaciones reales a dispositivos moviles.
- Despliegue productivo en nube.
- Empaquetado del backend dentro de Electron.

Estos elementos no se implementan porque exceden el objetivo academico y no eran necesarios para demostrar los conceptos principales de sistemas distribuidos.

## Evidencia sugerida para sustentacion

Para demostrar el alcance final, se recomienda seguir este recorrido:

1. Levantar infraestructura con Docker.
2. Ejecutar migraciones y backend.
3. Ejecutar `scripts/seed_demo_data.py`.
4. Abrir el dashboard web o Electron.
5. Mostrar Panel General con contadores por estado.
6. Mostrar Recomendaciones IA con ranking y distancia en kilometros.
7. Mostrar Asignaciones y explicar la asignacion exclusiva.
8. Marcar fallo en una ambulancia asignada.
9. Abrir Trazabilidad y mostrar la reasignacion.
10. Cerrar una emergencia y verificar asignacion finalizada.
11. Abrir Eventos del sistema y mostrar la auditoria completa.

## Conclusion

El alcance final de DistriCare cumple el nucleo definido en el documento base: un sistema distribuido academico, basado en eventos, con nodos simulados de ambulancia, coordinacion de asignaciones, IA heuristica, tolerancia a fallos, trazabilidad y dashboard de monitoreo.

El resultado final no es solo una aplicacion CRUD. Es un prototipo que permite observar como varios componentes independientes cooperan para resolver un problema de asignacion critica, manteniendo consistencia, auditabilidad y capacidad de recuperacion ante fallos.
