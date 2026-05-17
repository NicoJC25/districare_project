import { useState } from "react";
import { Plus, ShieldAlert, Stethoscope } from "lucide-react";
import { api } from "../api/client";
import { DataTable } from "../components/DataTable";
import { Button, Card, Input, LoadMeter, Modal, ReliabilityBar, StatusBadge } from "../components/ui";
import type { Ambulance } from "../types";
import type { AppData } from "../App";
import { formatRelative } from "../utils/format";
import { toneForStatus } from "../utils/status";

export function AmbulancesPage({ data, onRefresh }: { data: AppData; onRefresh: () => void }) {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("AMB-X");
  const [location, setLocation] = useState("0,0");
  const [load, setLoad] = useState(0);
  const [reliability, setReliability] = useState(1);
  const [busy, setBusy] = useState(false);

  async function createAmbulance() {
    setBusy(true);
    try {
      await api.createAmbulance({ code, simulated_location: location, operational_load: load, reliability });
      setOpen(false);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  async function failAmbulance(id: string) {
    if (!window.confirm("Marcar esta ambulancia como fallida?")) return;
    await api.failAmbulance(id);
    await onRefresh();
  }

  async function recoverAmbulance(id: string) {
    await api.recoverAmbulance(id);
    await onRefresh();
  }

  async function detectStale() {
    await api.detectStaleNodes();
    await onRefresh();
  }

  return (
    <div className="space-y-6">
      <Card
        title="Estado de Flota"
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={detectStale}>
              <ShieldAlert className="h-4 w-4" />
              Detectar inactivos
            </Button>
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" />
              Registrar ambulancia
            </Button>
          </div>
        }
      >
        <DataTable<Ambulance>
          rows={data.ambulances}
          getRowKey={(row) => row.id}
          columns={[
            { header: "Codigo", cell: (row) => <span className="font-bold">{row.code}</span> },
            { header: "Estado", cell: (row) => <StatusBadge tone={toneForStatus(row.state)}>{row.state}</StatusBadge> },
            { header: "Ubicacion", cell: (row) => row.simulated_location },
            { header: "Carga", cell: (row) => <LoadMeter value={row.operational_load} /> },
            { header: "Confiabilidad", cell: (row) => <ReliabilityBar value={row.reliability} /> },
            { header: "Heartbeat", cell: (row) => formatRelative(row.last_heartbeat_at) },
            {
              header: "Acciones",
              cell: (row) => (
                <div className="flex flex-wrap gap-2">
                  <Button variant="danger" className="px-3 py-1.5" onClick={() => failAmbulance(row.id)}>
                    Fallo
                  </Button>
                  <Button variant="secondary" className="px-3 py-1.5" onClick={() => recoverAmbulance(row.id)}>
                    Recuperar
                  </Button>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={open}
        title="Registrar nueva unidad"
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={createAmbulance} disabled={busy || !code || !location}>
              <Stethoscope className="h-4 w-4" />
              Registrar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block space-y-1 text-sm font-semibold">
            <span>Codigo de unidad</span>
            <Input value={code} onChange={(event) => setCode(event.target.value)} placeholder="Ej: AMB-A" />
          </label>
          <label className="block space-y-1 text-sm font-semibold">
            <span>Ubicacion inicial</span>
            <Input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Ej: 5,3" />
          </label>
          <label className="block space-y-2 text-sm font-semibold">
            <span>Carga operativa: {load}/10</span>
            <input className="w-full accent-primary" type="range" min={0} max={10} value={load} onChange={(event) => setLoad(Number(event.target.value))} />
          </label>
          <label className="block space-y-2 text-sm font-semibold">
            <span>Confiabilidad: {Math.round(reliability * 100)}%</span>
            <input className="w-full accent-primary" type="range" min={0} max={1} step={0.05} value={reliability} onChange={(event) => setReliability(Number(event.target.value))} />
          </label>
        </div>
      </Modal>
    </div>
  );
}
