import { Activity, Ambulance as AmbulanceIcon, BrainCircuit, ClipboardCheck, Siren, TriangleAlert } from "lucide-react";
import { Card, KpiCard, ReliabilityBar, StatusBadge } from "../components/ui";
import { DataTable } from "../components/DataTable";
import { Timeline } from "../components/Timeline";
import type { Ambulance, Emergency } from "../types";
import type { AppData } from "../App";
import { formatDate, shortId, score } from "../utils/format";
import { toneForStatus } from "../utils/status";

export function DashboardPage({
  data,
  ambulanceById,
}: {
  data: AppData;
  ambulanceById: Map<string, Ambulance>;
  onRefresh: () => void;
}) {
  const activeEmergencies = data.emergencies.filter((emergency) => !["CERRADA"].includes(emergency.state)).length;
  const availableAmbulances = data.ambulances.filter((ambulance) =>
    ["DISPONIBLE", "RECUPERADA"].includes(ambulance.state),
  ).length;
  const busyAmbulances = data.ambulances.filter((ambulance) =>
    ["OCUPADO", "ASIGNADA", "EN_ATENCION"].includes(ambulance.state),
  ).length;
  const failedNodes = data.ambulances.filter((ambulance) => ["FALLIDO", "INACTIVO"].includes(ambulance.state)).length;
  const latestRecommendation = data.recommendations[0];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard label="Emergencias activas" value={activeEmergencies} icon={<Siren className="h-5 w-5" />} tone="danger" />
        <KpiCard label="Ambulancias disponibles" value={availableAmbulances} icon={<AmbulanceIcon className="h-5 w-5" />} tone="success" />
        <KpiCard label="Ambulancias ocupadas" value={busyAmbulances} icon={<Activity className="h-5 w-5" />} tone="info" />
        <KpiCard label="Nodos fallidos" value={failedNodes} icon={<TriangleAlert className="h-5 w-5" />} tone="danger" />
        <KpiCard label="Recomendaciones IA" value={data.recommendations.length} icon={<BrainCircuit className="h-5 w-5" />} tone="purple" />
        <KpiCard label="Asignaciones confirmadas" value={data.assignments.length} icon={<ClipboardCheck className="h-5 w-5" />} tone="success" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,0.8fr)]">
        <Card title="Emergencias recientes">
          <DataTable<Emergency>
            rows={data.emergencies.slice(0, 6)}
            getRowKey={(row) => row.id}
            columns={[
              { header: "ID", cell: (row) => <span className="font-semibold tabular-nums">{shortId(row.id)}</span> },
              { header: "Tipo", cell: (row) => row.type },
              { header: "Severidad", cell: (row) => <span className="font-semibold tabular-nums">{row.severity}/10</span> },
              { header: "Estado", cell: (row) => <StatusBadge tone={toneForStatus(row.state)}>{row.state}</StatusBadge> },
              {
                header: "Ambulancia",
                cell: (row) => ambulanceById.get(row.assigned_ambulance_id ?? "")?.code ?? shortId(row.assigned_ambulance_id),
              },
            ]}
          />
        </Card>

        <Card title="Estado de flota">
          <div className="space-y-4">
            {data.ambulances.slice(0, 5).map((ambulance) => (
              <div key={ambulance.id} className="rounded-lg border border-border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-text">{ambulance.code}</p>
                    <p className="text-xs text-muted">{ambulance.simulated_location}</p>
                  </div>
                  <StatusBadge tone={toneForStatus(ambulance.state)}>{ambulance.state}</StatusBadge>
                </div>
                <div className="mt-3">
                  <ReliabilityBar value={ambulance.reliability} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card title="Actividad reciente del sistema">
          <Timeline events={data.events.slice(0, 6)} />
        </Card>
        <Card title="Ultima recomendacion IA">
          {latestRecommendation ? (
            <div className="space-y-3">
              <p className="text-sm text-muted">{latestRecommendation.decision_reason}</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-surface-muted p-3">
                  <p className="text-xs text-muted">Prioridad</p>
                  <p className="text-2xl font-bold">{latestRecommendation.calculated_priority}</p>
                </div>
                <div className="rounded-lg bg-surface-muted p-3">
                  <p className="text-xs text-muted">Puntaje</p>
                  <p className="text-2xl font-bold">{score(latestRecommendation.total_score)}</p>
                </div>
              </div>
              <p className="text-xs text-muted">Generada: {formatDate(latestRecommendation.created_at)}</p>
            </div>
          ) : (
            <p className="text-sm text-muted">Aun no hay recomendaciones registradas.</p>
          )}
        </Card>
      </section>
    </div>
  );
}
