# Inventario de componentes - Fase 5

## Componentes base

- `AppShell`: estructura global con sidebar, topbar, estado de API, fecha de ultima sincronizacion y area de contenido.
- `Sidebar`: integrado en `AppShell`; define navegacion para Panel General, Emergencias, Ambulancias, Asignaciones, Recomendaciones IA, Trazabilidad y Eventos del sistema.
- `Topbar`: integrado en `AppShell`; muestra pagina activa, estado de conexion y accion de actualizar.
- `Card`: superficie reutilizable para secciones, tablas y paneles de detalle.
- `KpiCard`: tarjeta compacta para metricas operativas del panel general.
- `StatusBadge`: badge semantico para estados de emergencias, ambulancias, asignaciones y eventos.
- `DataTable`: tabla densa reutilizable con columnas declarativas y estado vacio.
- `Button`, `Input`, `Select`, `Textarea`, `Modal`: controles de formularios y acciones.
- `EmptyState`, `LoadingState`, `ErrorState`: estados transversales para datos, carga y errores.
- `Timeline`: linea de tiempo vertical para eventos del sistema y trazabilidad.
- `JsonDetails`: visor expandible para metadata JSON.
- `ScoreBar`, `ReliabilityBar`, `LoadMeter`: visualizaciones simples para puntajes IA, confiabilidad y carga operativa.

## Uso por pantalla

- Panel General: `KpiCard`, `Card`, `DataTable`, `Timeline`, `ReliabilityBar`, `StatusBadge`.
- Emergencias: `DataTable`, `Modal`, `Input`, `Select`, `StatusBadge`.
- Ambulancias: `DataTable`, `Modal`, `ReliabilityBar`, `LoadMeter`, `StatusBadge`.
- Asignaciones: `DataTable`, `Select`, `StatusBadge`.
- Recomendaciones IA: `DataTable`, `ScoreBar`, `StatusBadge`, `EmptyState`.
- Trazabilidad: `Select`, `Card`, `Timeline`, `StatusBadge`.
- Eventos del sistema: `DataTable`, `Input`, `Select`, `JsonDetails`, `StatusBadge`.

## Inspiracion desde Stitch

Se conservaron los patrones principales de Stitch: dashboard clinico, tablas densas, sidebar persistente, badges por estado, cards KPI, timeline, panel de detalle IA, barras de confiabilidad y medidor de carga. Se tradujeron a componentes React reutilizables para evitar duplicar HTML por pantalla.
