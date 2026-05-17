# Decisiones de diseno - Fase 5

## Tokens seleccionados

- Fuente: Inter.
- Fondo: `#F7FAFC`.
- Superficie: `#FFFFFF`.
- Texto principal: `#102A43`.
- Texto secundario: `#62748E`.
- Sidebar: `#0B1F33`.
- Primario medico: `#0E9384`.
- Secundario: `#2563EB`.
- Exito: `#16A34A`.
- Advertencia: `#F79009`.
- Error: `#D92D20`.
- Bordes: `#D9E2EC`.
- Radio base: 8px para cards, botones e inputs.

## Diferencias frente a Stitch

- Se uso Tailwind local en lugar de CDN.
- Se uso Lucide React en lugar de Material Symbols.
- Se mantuvo una estructura visual cercana, pero el HTML estatico de Stitch se convirtio en componentes React.
- Las tablas muestran datos reales de API y no registros mock.
- La paginacion de Stitch no se implemento como backend real porque la API actual retorna listas completas.

## Elementos descartados

- Mapas, GPS y ubicacion actual.
- Perfil de usuario, notificaciones reales y configuracion de cuenta.
- Exportacion o descarga de reportes.
- Acciones de reubicacion o ignorar recomendaciones.
- Campo de motivo de anulacion en asignacion manual, porque el endpoint solo acepta `emergency_id` y `ambulance_id`.

## Criterio aplicado

La UI se limito a capacidades existentes en FastAPI para evitar prometer funciones que no existen en el backend. La prioridad fue dejar una base navegable, auditable y conectada, preparada para refinamiento visual posterior.
