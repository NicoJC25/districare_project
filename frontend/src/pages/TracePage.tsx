import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { Timeline } from "../components/Timeline";
import { Button, Card, EmptyState, LoadingState, Select, StatusBadge } from "../components/ui";
import type { Ambulance, Emergency, EmergencyTrace } from "../types";
import { formatDate, score, shortId } from "../utils/format";
import { toneForStatus } from "../utils/status";

export function TracePage({
  emergencies,
  ambulanceById,
}: {
  emergencies: Emergency[];
  ambulanceById: Map<string, Ambulance>;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const emergencyFromUrl = searchParams.get("emergency") ?? "";
  const [selectedId, setSelectedId] = useState(emergencyFromUrl || emergencies[0]?.id || "");
  const [trace, setTrace] = useState<EmergencyTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const reassignmentEvents = useMemo(
    () => trace?.events.filter((event) => event.event_type === "REASSIGNMENT_STARTED" || event.event_type === "REASSIGNMENT_CONFIRMED") ?? [],
    [trace],
  );

  useEffect(() => {
    if (emergencyFromUrl && emergencyFromUrl !== selectedId) {
      setSelectedId(emergencyFromUrl);
      return;
    }
    if (!selectedId && emergencies[0]?.id) {
      setSelectedId(emergencies[0].id);
    }
  }, [emergencies, emergencyFromUrl, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    api
      .getEmergencyTrace(selectedId)
      .then(setTrace)
      .finally(() => setLoading(false));
  }, [selectedId]);

  return (
    <div className="space-y-6">
      <Card title="Auditoria de Asignacion">
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <label className="flex-1 space-y-1 text-sm font-semibold">
            <span>Seleccionar emergencia</span>
            <Select
              value={selectedId}
              onChange={(event) => {
                setSelectedId(event.target.value);
                setSearchParams(event.target.value ? { emergency: event.target.value } : {});
              }}
            >
              <option value="">Seleccionar</option>
              {emergencies.map((emergency) => (
                <option key={emergency.id} value={emergency.id}>
                  {shortId(emergency.id)} - {emergency.type} - {emergency.state}
                </option>
              ))}
            </Select>
          </label>
          <Button variant="secondary" onClick={() => selectedId && api.getEmergencyTrace(selectedId).then(setTrace)}>
            Consultar trazabilidad
          </Button>
        </div>
      </Card>

      {loading ? (
        <LoadingState />
      ) : trace ? (
        <>
          <section className="grid gap-6 lg:grid-cols-3">
            <TraceSummary title="Emergencia">
              <p className="text-lg font-bold">{trace.emergency.type}</p>
              <p className="text-sm text-muted">Severidad {trace.emergency.severity}/10 · Prioridad {trace.emergency.priority ?? "-"}</p>
              <p className="text-sm text-muted">{trace.emergency.simulated_location}</p>
              <StatusBadge tone={toneForStatus(trace.emergency.state)}>{trace.emergency.state}</StatusBadge>
            </TraceSummary>
            <TraceSummary title="Recomendacion IA">
              {trace.latest_recommendation ? (
                <>
                  <p className="text-lg font-bold">
                    {ambulanceById.get(trace.recommended_ambulance_id ?? "")?.code ?? shortId(trace.recommended_ambulance_id)}
                  </p>
                  <p className="text-sm text-muted">Puntaje {score(trace.latest_recommendation.total_score)}</p>
                  <p className="text-sm text-muted">{formatDate(trace.latest_recommendation.created_at)}</p>
                </>
              ) : (
                <p className="text-sm text-muted">Sin recomendacion registrada.</p>
              )}
            </TraceSummary>
            <TraceSummary title="Asignacion final">
              {trace.selected_assignment ? (
                <>
                  <p className="text-lg font-bold">
                    {ambulanceById.get(trace.assigned_ambulance_id ?? "")?.code ?? shortId(trace.assigned_ambulance_id)}
                  </p>
                  <p className="text-sm text-muted">{formatDate(trace.selected_assignment.assigned_at)}</p>
                  <StatusBadge tone={toneForStatus(trace.selected_assignment.state)}>{trace.selected_assignment.state}</StatusBadge>
                </>
              ) : (
                <p className="text-sm text-muted">Sin asignacion registrada.</p>
              )}
            </TraceSummary>
          </section>

          <Card title="Resultado de comparacion">
            <div className="space-y-3">
              {trace.assignment_matches_recommendation === true && (
                <StatusBadge tone="success">Asignacion coincide con recomendacion IA</StatusBadge>
              )}
              {trace.assignment_matches_recommendation === false && (
                <StatusBadge tone="warning">Asignacion distinta a recomendacion IA</StatusBadge>
              )}
              {trace.assignment_matches_recommendation === null && (
                <StatusBadge tone="default">Sin asignacion comparable</StatusBadge>
              )}
              <p className="rounded-lg bg-surface-muted p-4 text-sm font-medium text-text">{trace.trace_reason}</p>
            </div>
          </Card>

          {reassignmentEvents.length > 0 && (
            <Card title="Reasignaciones detectadas">
              <div className="space-y-3">
                {reassignmentEvents.map((event) => (
                  <div key={event.id} className="rounded-lg border border-border bg-surface-muted p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <StatusBadge tone={toneForStatus(event.event_type)}>{event.event_type}</StatusBadge>
                      <span className="text-xs font-medium text-muted">{formatDate(event.created_at)}</span>
                    </div>
                    <p className="mt-2 text-sm font-medium text-text">{event.description}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card title="Linea de tiempo de la emergencia">
            <Timeline events={trace.events} />
          </Card>
        </>
      ) : (
        <EmptyState title="Selecciona una emergencia" detail="La trazabilidad se consulta bajo demanda para mostrar eventos cronologicos." />
      )}
    </div>
  );
}

function TraceSummary({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      <div className="space-y-2">{children}</div>
    </Card>
  );
}
