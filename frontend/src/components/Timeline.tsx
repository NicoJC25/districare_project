import { JsonDetails, StatusBadge } from "./ui";
import type { SystemEvent } from "../types";
import { formatDate, shortId } from "../utils/format";
import { eventTone } from "../utils/status";

export function Timeline({ events }: { events: SystemEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted">No hay eventos registrados.</p>;
  }

  return (
    <ol className="relative space-y-5 border-l-2 border-border pl-5">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span className="absolute -left-[30px] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-primary shadow" />
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <StatusBadge tone={eventTone(event.event_type)}>{event.event_type}</StatusBadge>
              <p className="mt-2 font-medium text-text">{event.description}</p>
              <p className="mt-1 text-xs text-muted">
                Emergencia {shortId(event.emergency_id)} · Ambulancia {shortId(event.ambulance_id)}
              </p>
            </div>
            <time className="text-xs font-semibold text-muted">{formatDate(event.created_at)}</time>
          </div>
          {Object.keys(event.event_metadata ?? {}).length > 0 && (
            <div className="mt-3">
              <JsonDetails value={event.event_metadata} />
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
