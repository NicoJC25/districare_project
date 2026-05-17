import { useState } from "react";
import { Send } from "lucide-react";
import { api } from "../api/client";
import { DataTable } from "../components/DataTable";
import { Button, Card, Select, StatusBadge } from "../components/ui";
import type { Ambulance, Assignment, Emergency } from "../types";
import type { AppData } from "../App";
import { formatDate, shortId } from "../utils/format";
import { toneForStatus } from "../utils/status";

export function AssignmentsPage({
  data,
  ambulanceById,
  emergencyById,
  onRefresh,
}: {
  data: AppData;
  ambulanceById: Map<string, Ambulance>;
  emergencyById: Map<string, Emergency>;
  onRefresh: () => void;
}) {
  const [emergencyId, setEmergencyId] = useState(data.emergencies[0]?.id ?? "");
  const [ambulanceId, setAmbulanceId] = useState(data.ambulances[0]?.id ?? "");
  const [result, setResult] = useState<string | null>(null);
  const assignableEmergencies = data.emergencies.filter((emergency) =>
    ["PRIORIZADA", "PUBLICADA", "EN_PROCESO_ASIGNACION", "REASIGNACION_PENDIENTE"].includes(emergency.state),
  );
  const assignableAmbulances = data.ambulances.filter((ambulance) =>
    ["DISPONIBLE", "RECUPERADA", "CANDIDATA", "INTENTANDO_ACEPTAR"].includes(ambulance.state),
  );

  async function attemptAssignment() {
    const response = await api.attemptAssignment({ emergency_id: emergencyId, ambulance_id: ambulanceId });
    setResult(response.accepted ? "Asignacion aceptada." : response.reason ?? "Asignacion rechazada.");
    await onRefresh();
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <Card title="Registro Central de Asignaciones">
        <DataTable<Assignment>
          rows={data.assignments}
          getRowKey={(row) => row.id}
          columns={[
            {
              header: "Emergencia",
              cell: (row) => (
                <div>
                  <p className="font-semibold">{shortId(row.emergency_id)}</p>
                  <p className="text-xs text-muted">{emergencyById.get(row.emergency_id)?.type ?? "Sin detalle"}</p>
                </div>
              ),
            },
            { header: "Ambulancia", cell: (row) => ambulanceById.get(row.ambulance_id)?.code ?? shortId(row.ambulance_id) },
            {
              header: "Vigencia",
              cell: (row) => (
                <StatusBadge tone={row.active ? "success" : "default"}>{row.active ? "Activa" : "Historica"}</StatusBadge>
              ),
            },
            { header: "Recomendacion", cell: (row) => shortId(row.recommendation_id) },
            {
              header: "Amb. recomendada",
              cell: (row) => ambulanceById.get(row.recommended_ambulance_id ?? "")?.code ?? shortId(row.recommended_ambulance_id),
            },
            { header: "Estado", cell: (row) => <StatusBadge tone={toneForStatus(row.state)}>{row.state}</StatusBadge> },
            {
              header: "Tipo",
              cell: (row) =>
                row.recommended_ambulance_id === row.ambulance_id ? (
                  <StatusBadge tone="success">Coincide con IA</StatusBadge>
                ) : (
                  <StatusBadge tone="warning">Intento distribuido</StatusBadge>
                ),
            },
            { header: "Fecha", cell: (row) => formatDate(row.assigned_at) },
            { header: "Finalizada", cell: (row) => row.finalized_at ? formatDate(row.finalized_at) : "-" },
            { header: "Razon", cell: (row) => <span className="text-sm text-muted">{row.assignment_reason ?? "-"}</span> },
          ]}
        />
      </Card>

      <Card title="Intentar asignacion manual">
        <div className="space-y-4">
          <label className="block space-y-1 text-sm font-semibold">
            <span>Emergencia asignable</span>
            <Select value={emergencyId} onChange={(event) => setEmergencyId(event.target.value)}>
              <option value="">Seleccionar emergencia</option>
              {assignableEmergencies.map((emergency) => (
                <option key={emergency.id} value={emergency.id}>
                  {shortId(emergency.id)} - {emergency.type}
                </option>
              ))}
            </Select>
          </label>
          <label className="block space-y-1 text-sm font-semibold">
            <span>Unidad disponible</span>
            <Select value={ambulanceId} onChange={(event) => setAmbulanceId(event.target.value)}>
              <option value="">Seleccionar ambulancia</option>
              {assignableAmbulances.map((ambulance) => (
                <option key={ambulance.id} value={ambulance.id}>
                  {ambulance.code} - {ambulance.state}
                </option>
              ))}
            </Select>
          </label>
          <Button className="w-full" onClick={attemptAssignment} disabled={!emergencyId || !ambulanceId}>
            <Send className="h-4 w-4" />
            Intentar asignar
          </Button>
          {result && <p className="rounded-lg bg-surface-muted p-3 text-sm font-medium text-text">{result}</p>}
        </div>
      </Card>
    </div>
  );
}
