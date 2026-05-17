import { useMemo, useState } from "react";
import { BrainCircuit } from "lucide-react";
import { DataTable } from "../components/DataTable";
import { Card, EmptyState, ScoreBar, StatusBadge } from "../components/ui";
import type { AIRecommendation, Ambulance, RankingItem } from "../types";
import type { AppData } from "../App";
import { formatDate, score, shortId } from "../utils/format";
import { toneForStatus } from "../utils/status";

const criteriaLabels: Record<string, string> = {
  severity: "Gravedad",
  distance: "Distancia",
  availability: "Disponibilidad",
  operational_load: "Carga",
  reliability: "Confiabilidad",
  waiting_time: "Espera",
};

export function RecommendationsPage({
  data,
  ambulanceById,
}: {
  data: AppData;
  ambulanceById: Map<string, Ambulance>;
}) {
  const [selectedId, setSelectedId] = useState(data.recommendations[0]?.id ?? "");
  const selected = useMemo(
    () => data.recommendations.find((recommendation) => recommendation.id === selectedId) ?? data.recommendations[0],
    [data.recommendations, selectedId],
  );
  const ranking = selected?.criteria.ranking ?? [];
  const weights = selected?.criteria.weights ?? {};

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-violet-50 p-3 text-purple">
            <BrainCircuit className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-text">Recomendaciones IA heuristicas</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              Ranking auditable basado en gravedad, distancia, disponibilidad, carga, confiabilidad y tiempo de espera.
            </p>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_440px]">
        <Card title="Evaluaciones generadas">
          <DataTable<AIRecommendation>
            rows={data.recommendations}
            getRowKey={(row) => row.id}
            columns={[
              { header: "Emergencia", cell: (row) => shortId(row.emergency_id) },
              {
                header: "Ambulancia rec.",
                cell: (row) => ambulanceById.get(row.recommended_ambulance_id ?? "")?.code ?? shortId(row.recommended_ambulance_id),
              },
              { header: "Prioridad", cell: (row) => row.calculated_priority },
              { header: "Puntaje", cell: (row) => <span className="font-bold tabular-nums">{score(row.total_score)}</span> },
              { header: "Candidatas", cell: (row) => row.candidates_count },
              { header: "Fecha", cell: (row) => formatDate(row.created_at) },
              {
                header: "Seleccion",
                cell: (row) => (
                  <button className="font-semibold text-primary hover:underline" onClick={() => setSelectedId(row.id)}>
                    Ver detalle
                  </button>
                ),
              },
            ]}
          />
        </Card>

        <Card title="Detalle auditable">
          {selected ? (
            <div className="space-y-5">
              <div className="rounded-lg bg-surface-muted p-4">
                <p className="text-sm font-medium text-text">{selected.decision_reason}</p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <Metric label="Prioridad" value={selected.calculated_priority} />
                <Metric label="Puntaje" value={score(selected.total_score)} />
                <Metric label="Candidatas" value={selected.candidates_count} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-semibold text-text">Pesos de decision</h3>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(weights).map(([key, value]) => (
                    <div key={key} className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted">{criteriaLabels[key] ?? key}</p>
                      <p className="font-bold tabular-nums">{Math.round(value * 100)}%</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="mb-3 text-sm font-semibold text-text">Ranking de candidatas</h3>
                {ranking.length > 0 ? (
                  <div className="space-y-3">
                    {ranking.map((item, index) => (
                      <RankingRow key={item.ambulance_id} item={item} index={index} />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="Sin candidatas disponibles"
                    detail={selected.criteria.no_candidate_reason ?? "La heuristica no encontro unidades elegibles."}
                  />
                )}
              </div>
            </div>
          ) : (
            <EmptyState title="Sin recomendaciones" detail="Crea una emergencia para generar evidencia IA." />
          )}
        </Card>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-bold tabular-nums">{value}</p>
    </div>
  );
}

function RankingRow({ item, index }: { item: RankingItem; index: number }) {
  const totalScore = item.total_score ?? item.score ?? 0;
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
            {index + 1}
          </span>
          <div>
            <p className="font-bold">{item.code}</p>
            <p className="text-xs text-muted">
              Distancia {item.distance}
              {item.operational_load !== undefined ? ` · Carga ${item.operational_load}/10` : ""}
              {item.reliability !== undefined ? ` · Conf. ${Math.round(item.reliability * 100)}%` : ""}
            </p>
          </div>
        </div>
        <StatusBadge tone={toneForStatus(item.state ?? "CANDIDATA")}>{item.state ?? "CANDIDATA"}</StatusBadge>
      </div>
      <ScoreBar value={totalScore} max={Math.max(100, totalScore)} />
    </div>
  );
}
