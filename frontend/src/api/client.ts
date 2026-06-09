import type {
  AIRecommendation,
  Ambulance,
  AmbulanceCreate,
  Assignment,
  AssignmentAttemptCreate,
  AssignmentAttemptResult,
  CandidateRanking,
  Emergency,
  EmergencyCreate,
  EmergencyStateUpdate,
  EmergencyTrace,
  HealthStatus,
  SystemEvent,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";
const normalizedApiBaseUrl = API_BASE_URL.replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${normalizedApiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Error HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthStatus>("/health"),
  listEmergencies: () => request<Emergency[]>("/emergencies"),
  createEmergency: (payload: EmergencyCreate) =>
    request<Emergency>("/emergencies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateEmergencyState: (emergencyId: string, payload: EmergencyStateUpdate) =>
    request<Emergency>(`/emergencies/${emergencyId}/state`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listAmbulances: () => request<Ambulance[]>("/ambulances"),
  createAmbulance: (payload: AmbulanceCreate) =>
    request<Ambulance>("/ambulances", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  failAmbulance: (ambulanceId: string) =>
    request<{ failure_id: string }>(`/ambulances/${ambulanceId}/fail`, {
      method: "POST",
    }),
  recoverAmbulance: (ambulanceId: string) =>
    request<Ambulance>(`/ambulances/${ambulanceId}/recover`, {
      method: "POST",
    }),
  detectStaleNodes: () =>
    request<{ detected_failures: number; failure_ids: string[] }>("/failures/detect-stale", {
      method: "POST",
    }),
  attemptAssignment: (payload: AssignmentAttemptCreate) =>
    request<AssignmentAttemptResult>("/assignments/attempt", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAssignments: () => request<Assignment[]>("/assignments"),
  listRecommendations: () => request<AIRecommendation[]>("/recommendations"),
  getCandidateRanking: (emergencyId: string) =>
    request<CandidateRanking>(`/emergencies/${emergencyId}/candidate-ranking`),
  getEmergencyTrace: (emergencyId: string) =>
    request<EmergencyTrace>(`/emergencies/${emergencyId}/trace`),
  listEvents: () => request<SystemEvent[]>("/events"),
};
