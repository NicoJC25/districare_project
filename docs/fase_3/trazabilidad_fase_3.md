# Trazabilidad de creacion - Fase 3 DistriCare

Este documento resume los cambios realizados para la fase 3 del proyecto
DistriCare. La fase se enfoco en agregar un mecanismo plano de asignacion
exclusiva antes de pasar a una heuristica de IA mas compleja.

## 1. Objetivo de la fase

La fase 3 cubre tres funcionalidades:

- Mecanismo de asignacion exclusiva: evitar que dos nodos acepten la misma emergencia.
- Bloqueo logico o validacion atomica: validar estado antes de confirmar la asignacion.
- Confirmacion de asignacion: guardar en la emergencia la ambulancia seleccionada.

## 2. Punto de partida

La fase parte de la base construida en `docs/fase_2/`:

- `POST /emergencies` crea, prioriza y publica emergencias.
- Los nodos de ambulancia reciben eventos desde RabbitMQ.
- Los nodos intentan aceptar emergencias con `POST /assignments/attempt`.
- La tabla `assignments` ya registraba asignaciones confirmadas.
- Existia una restriccion unica parcial para impedir mas de una asignacion
  activa confirmada por emergencia.

La fase 3 refuerza ese flujo para que la confirmacion quede mas explicita y
para que una ambulancia tampoco pueda quedar activa en dos emergencias a la vez.

## 3. Orden de creacion de archivos

Los archivos nuevos de esta fase se crearon en este orden:

1. `backend/alembic/versions/0002_assignment_confirmation_fields.py`
2. `docs/fase_3/trazabilidad_fase_3.md`
3. `docs/fase_3/comprobacion_funcional.md`

El primer archivo corresponde al cambio real de esquema. Los otros dos archivos
documentan la implementacion y la forma de comprobarla.

## 4. Migracion nueva

Archivo creado:

- `backend/alembic/versions/0002_assignment_confirmation_fields.py`

La migracion agrega:

- columna `assigned_ambulance_id` en `emergencies`;
- llave foranea desde `emergencies.assigned_ambulance_id` hacia
  `ambulance_nodes.id`;
- indice `ix_emergencies_assigned_ambulance_id`;
- restriccion unica parcial `uq_active_confirmed_assignment_per_ambulance`.

La nueva restriccion impide que una misma ambulancia tenga mas de una
asignacion activa confirmada.

Tambien se ajusto `backend/alembic/versions/0001_initial_schema.py` para que la
restriccion unica previa por emergencia tenga condicion parcial en SQLite,
igual que en el modelo SQLAlchemy.

## 5. Modelo de emergencia

Archivo modificado:

- `backend/app/models/emergency.py`

Se agrego `assigned_ambulance_id` como campo nullable. Este campo permite ver
directamente cual ambulancia quedo confirmada para una emergencia, sin depender
solo de consultar la tabla `assignments`.

Tambien se agrego la relacion `assigned_ambulance` para navegar desde una
emergencia hacia la ambulancia confirmada.

## 6. Modelo de asignacion

Archivo modificado:

- `backend/app/models/assignment.py`

Se agrego el indice unico parcial:

```text
uq_active_confirmed_assignment_per_ambulance
```

Este indice aplica solamente a asignaciones con:

```text
active = true
state = CONFIRMADA
```

Con esto se permite conservar historial de reasignaciones, pero se evita que una
ambulancia quede ocupando dos emergencias activas al mismo tiempo.

## 7. Esquema de lectura de emergencia

Archivo modificado:

- `backend/app/schemas/emergency.py`

Se expone `assigned_ambulance_id` en `EmergencyRead`. Asi, las respuestas de:

- `POST /emergencies`
- `GET /emergencies`
- `GET /emergencies/{emergency_id}`

pueden mostrar si una emergencia ya tiene ambulancia confirmada.

## 8. Servicio de asignaciones

Archivo modificado:

- `backend/app/services/assignments.py`

El metodo principal sigue siendo:

```text
attempt_assignment(emergency_id, ambulance_id)
```

Cambios aplicados:

- obtiene emergencia y ambulancia con `with_for_update`;
- valida si ya existe asignacion activa para la emergencia;
- retorna idempotentemente la asignacion si el mismo nodo ganador repite el
  intento;
- valida que la emergencia este en un estado asignable;
- valida que la ambulancia no tenga otra asignacion activa;
- valida que la ambulancia este en un estado disponible para asignacion;
- crea la asignacion en estado `CONFIRMADA`;
- cambia la emergencia temporalmente a `EN_PROCESO_ASIGNACION`;
- confirma la emergencia como `ASIGNADA`;
- guarda `emergency.assigned_ambulance_id`;
- cambia la ambulancia a `OCUPADO`;
- registra eventos de intento, rechazo o confirmacion.

Si la base de datos detecta una condicion de carrera mediante restriccion unica,
el servicio captura `IntegrityError`, consulta el ganador real y registra un
evento `ASSIGNMENT_REJECTED`.

## 9. Pruebas automatizadas

Archivo modificado:

- `backend/tests/test_distributed_base.py`

Se reforzaron pruebas para validar:

- una segunda ambulancia no puede aceptar una emergencia ya asignada;
- `assigned_ambulance_id` queda guardado en la emergencia confirmada;
- una ambulancia con asignacion activa no puede aceptar otra emergencia;
- la reasignacion por fallo actualiza `assigned_ambulance_id` con la nueva
  ambulancia.

Comando usado:

```powershell
pytest
```

Resultado esperado:

```text
10 passed
```

## 10. Flujo final

El flujo final de fase 3 queda asi:

1. Una emergencia se crea y queda publicada.
2. Uno o mas nodos intentan aceptarla.
3. El backend valida atomicamente emergencia, ambulancia y asignaciones activas.
4. Solo un intento crea una asignacion `CONFIRMADA` y `active = true`.
5. La emergencia queda `ASIGNADA`.
6. La emergencia guarda `assigned_ambulance_id`.
7. La ambulancia ganadora queda `OCUPADO`.
8. Los demas intentos se rechazan con razon funcional.
9. Si el nodo asignado falla, se desactiva la asignacion actual.
10. El sistema puede confirmar una reasignacion y actualizar la emergencia.

## 11. Estado final

La fase 3 queda lista para demostrar:

- asignacion exclusiva por emergencia;
- asignacion exclusiva por ambulancia;
- validacion atomica antes de confirmar;
- confirmacion persistida en emergencia;
- soporte para reasignacion por fallo;
- pruebas automatizadas del flujo.
