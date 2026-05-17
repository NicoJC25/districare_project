import { useMemo, useState } from "react";
import { DataTable } from "../components/DataTable";
import { Button, Card, Input, JsonDetails, Select, StatusBadge } from "../components/ui";
import type { Ambulance, Emergency, SystemEvent } from "../types";
import { formatDate, shortId } from "../utils/format";
import { eventTone } from "../utils/status";

export function EventsPage({
  events,
  ambulanceById,
  emergencyById,
}: {
  events: SystemEvent[];
  ambulanceById: Map<string, Ambulance>;
  emergencyById: Map<string, Emergency>;
}) {
  const [search, setSearch] = useState("");
  const [eventType, setEventType] = useState("");
  const eventTypes = Array.from(new Set(events.map((event) => event.event_type))).sort();
  const filteredEvents = useMemo(
    () =>
      events.filter((event) => {
        const haystack = `${event.id} ${event.event_type} ${event.description} ${event.emergency_id ?? ""} ${event.ambulance_id ?? ""}`.toLowerCase();
        return (!search || haystack.includes(search.toLowerCase())) && (!eventType || event.event_type === eventType);
      }),
    [events, search, eventType],
  );

  return (
    <div className="space-y-6">
      <Card title="Auditoria global de eventos">
        <div className="mb-5 grid gap-3 md:grid-cols-[1fr_260px_auto]">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por ID, descripcion o entidad..." />
          <Select value={eventType} onChange={(event) => setEventType(event.target.value)}>
            <option value="">Todos los tipos</option>
            {eventTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </Select>
          <Button variant="secondary" onClick={() => {
            setSearch("");
            setEventType("");
          }}>
            Limpiar filtros
          </Button>
        </div>
        <DataTable<SystemEvent>
          rows={filteredEvents}
          getRowKey={(row) => row.id}
          columns={[
            { header: "Timestamp", cell: (row) => formatDate(row.created_at) },
            { header: "Tipo de evento", cell: (row) => <StatusBadge tone={eventTone(row.event_type)}>{row.event_type}</StatusBadge> },
            { header: "Descripcion", cell: (row) => <span className="font-medium">{row.description}</span> },
            {
              header: "Entidades",
              cell: (row) => (
                <div className="text-sm text-muted">
                  <p>Emergencia: {emergencyById.get(row.emergency_id ?? "")?.type ?? shortId(row.emergency_id)}</p>
                  <p>Ambulancia: {ambulanceById.get(row.ambulance_id ?? "")?.code ?? shortId(row.ambulance_id)}</p>
                </div>
              ),
            },
            { header: "Metadatos", cell: (row) => <JsonDetails value={row.event_metadata} /> },
          ]}
        />
      </Card>
    </div>
  );
}
