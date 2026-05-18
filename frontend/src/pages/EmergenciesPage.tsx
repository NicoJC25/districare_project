import { useState } from "react";
import { Eye, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { DataTable } from "../components/DataTable";
import { Button, Card, Input, Modal, Select, StatusBadge } from "../components/ui";
import type { Ambulance, Emergency } from "../types";
import type { AppData } from "../App";
import { formatDate, shortId } from "../utils/format";
import { toneForStatus } from "../utils/status";

export function EmergenciesPage({
  data,
  ambulanceById,
  onRefresh,
}: {
  data: AppData;
  ambulanceById: Map<string, Ambulance>;
  onRefresh: () => void;
}) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("Accidente");
  const [severity, setSeverity] = useState(7);
  const [location, setLocation] = useState("4.7110,-74.0721");
  const [busy, setBusy] = useState(false);

  async function createEmergency() {
    setBusy(true);
    try {
      await api.createEmergency({ type, severity, simulated_location: location });
      setOpen(false);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  async function updateState(emergency: Emergency, state: "EN_ATENCION" | "CERRADA") {
    const label = state === "EN_ATENCION" ? "iniciar atencion" : "cerrar emergencia";
    if (!window.confirm(`Confirmar accion: ${label}?`)) return;
    setBusy(true);
    try {
      await api.updateEmergencyState(emergency.id, { state });
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  function canStartAttention(emergency: Emergency) {
    return emergency.state === "ASIGNADA";
  }

  function canClose(emergency: Emergency) {
    return emergency.state === "EN_ATENCION" || emergency.state === "SIN_UNIDAD_DISPONIBLE";
  }

  return (
    <div className="space-y-6">
      <Card
        title="Registro de Emergencias"
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" />
            Nueva emergencia
          </Button>
        }
      >
        <DataTable<Emergency>
          rows={data.emergencies}
          getRowKey={(row) => row.id}
          columns={[
            { header: "Tipo", cell: (row) => <span className="font-semibold">{row.type}</span> },
            { header: "Severidad", cell: (row) => <span className="font-semibold tabular-nums">{row.severity}/10</span> },
            { header: "Prioridad", cell: (row) => row.priority ?? "-" },
            { header: "Ubicacion", cell: (row) => row.simulated_location },
            { header: "Estado", cell: (row) => <StatusBadge tone={toneForStatus(row.state)}>{row.state}</StatusBadge> },
            {
              header: "Ambulancia",
              cell: (row) => ambulanceById.get(row.assigned_ambulance_id ?? "")?.code ?? shortId(row.assigned_ambulance_id),
            },
            { header: "Fecha", cell: (row) => formatDate(row.created_at) },
            { header: "Cierre", cell: (row) => row.closed_at ? formatDate(row.closed_at) : "-" },
            {
              header: "Acciones",
              cell: (row) => (
                <div className="flex flex-wrap gap-2">
                  <Button variant="ghost" className="px-2" onClick={() => navigate(`/trazabilidad?emergency=${row.id}`)}>
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="secondary"
                    className="px-3 py-1.5"
                    disabled={busy || !canStartAttention(row)}
                    onClick={() => updateState(row, "EN_ATENCION")}
                  >
                    Atender
                  </Button>
                  <Button
                    variant="danger"
                    className="px-3 py-1.5"
                    disabled={busy || !canClose(row)}
                    onClick={() => updateState(row, "CERRADA")}
                  >
                    Cerrar
                  </Button>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={open}
        title="Registrar nueva emergencia"
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)} type="button">
              Cancelar
            </Button>
            <Button onClick={createEmergency} disabled={busy || !type || !location} type="button">
              Registrar y publicar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block space-y-1 text-sm font-semibold">
            <span>Tipo de emergencia</span>
            <Select value={type} onChange={(event) => setType(event.target.value)}>
              <option>Accidente</option>
              <option>Paro cardiaco</option>
              <option>Trauma multiple</option>
              <option>ACV</option>
              <option>Malestar general</option>
            </Select>
          </label>
          <label className="block space-y-2 text-sm font-semibold">
            <span>Severidad estimada: {severity}</span>
            <input
              className="w-full accent-primary"
              type="range"
              min={1}
              max={10}
              value={severity}
              onChange={(event) => setSeverity(Number(event.target.value))}
            />
          </label>
          <label className="block space-y-1 text-sm font-semibold">
            <span>Ubicacion simulada</span>
            <Input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Ej: 4.7110,-74.0721" />
          </label>
        </div>
      </Modal>
    </div>
  );
}
