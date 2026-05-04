# Modelo inicial DistriCare

La base modela cinco conceptos principales: emergencia, nodo de ambulancia, asignacion, evento del sistema y recomendacion IA. Tambien se incluye `NodeFailure` para documentar y automatizar fallos de nodos.

La asignacion unica no depende solo de Python: se declara un indice unico parcial sobre `assignments.emergency_id` cuando la asignacion esta activa y confirmada. En una reasignacion, la asignacion anterior se desactiva antes de confirmar la nueva.

La simulacion distribuida queda visible por:

- nodos separados que emiten heartbeat;
- deteccion de timeout;
- eventos persistidos por cada transicion;
- publicacion y consumo de eventos en RabbitMQ;
- intentos de aceptacion concurrentes controlados por transaccion;
- heuristica de seleccion de ambulancia por estado, carga, confiabilidad y distancia simulada.
