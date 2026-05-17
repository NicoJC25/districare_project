import { useCallback, useEffect, useMemo, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import { AppShell } from "./components/AppShell";
import { ErrorState, LoadingState } from "./components/ui";
import type { AIRecommendation, Ambulance, Assignment, Emergency, SystemEvent } from "./types";
import { DashboardPage } from "./pages/DashboardPage";
import { EmergenciesPage } from "./pages/EmergenciesPage";
import { AmbulancesPage } from "./pages/AmbulancesPage";
import { AssignmentsPage } from "./pages/AssignmentsPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { TracePage } from "./pages/TracePage";
import { EventsPage } from "./pages/EventsPage";

export type AppData = {
  emergencies: Emergency[];
  ambulances: Ambulance[];
  assignments: Assignment[];
  recommendations: AIRecommendation[];
  events: SystemEvent[];
};

const emptyData: AppData = {
  emergencies: [],
  ambulances: [],
  assignments: [],
  recommendations: [],
  events: [],
};

export default function App() {
  const [data, setData] = useState<AppData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [health, emergencies, ambulances, assignments, recommendations, events] = await Promise.all([
        api.health(),
        api.listEmergencies(),
        api.listAmbulances(),
        api.listAssignments(),
        api.listRecommendations(),
        api.listEvents(),
      ]);
      setApiOnline(health.status === "ok");
      setData({ emergencies, ambulances, assignments, recommendations, events });
      setLastSync(new Date());
    } catch (err) {
      setApiOnline(false);
      setError(err instanceof Error ? err.message : "No se pudo conectar con la API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 10000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const ambulanceById = useMemo(
    () => new Map(data.ambulances.map((ambulance) => [ambulance.id, ambulance])),
    [data.ambulances],
  );

  const emergencyById = useMemo(
    () => new Map(data.emergencies.map((emergency) => [emergency.id, emergency])),
    [data.emergencies],
  );

  return (
    <AppShell apiOnline={apiOnline} lastSync={lastSync} onRefresh={refresh}>
      {loading ? (
        <LoadingState />
      ) : error && data.emergencies.length === 0 && data.ambulances.length === 0 ? (
        <ErrorState message={error} />
      ) : (
        <Routes>
          <Route
            path="/"
            element={<DashboardPage data={data} ambulanceById={ambulanceById} onRefresh={refresh} />}
          />
          <Route
            path="/emergencias"
            element={<EmergenciesPage data={data} ambulanceById={ambulanceById} onRefresh={refresh} />}
          />
          <Route path="/ambulancias" element={<AmbulancesPage data={data} onRefresh={refresh} />} />
          <Route
            path="/asignaciones"
            element={
              <AssignmentsPage
                data={data}
                ambulanceById={ambulanceById}
                emergencyById={emergencyById}
                onRefresh={refresh}
              />
            }
          />
          <Route
            path="/recomendaciones-ia"
            element={<RecommendationsPage data={data} ambulanceById={ambulanceById} />}
          />
          <Route
            path="/trazabilidad"
            element={<TracePage emergencies={data.emergencies} ambulanceById={ambulanceById} />}
          />
          <Route
            path="/eventos"
            element={<EventsPage events={data.events} ambulanceById={ambulanceById} emergencyById={emergencyById} />}
          />
        </Routes>
      )}
    </AppShell>
  );
}
