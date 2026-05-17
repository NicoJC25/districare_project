export type HealthStatus = {
  status: string;
  service: string;
  database: string;
};

export type Emergency = {
  id: string;
  type: string;
  severity: number;
  priority: number | null;
  simulated_location: string;
  state: string;
  assigned_ambulance_id: string | null;
  created_at: string;
  closed_at: string | null;
};

export type Ambulance = {
  id: string;
  code: string;
  state: string;
  simulated_location: string;
  operational_load: number;
  reliability: number;
  last_heartbeat_at: string | null;
};

export type Assignment = {
  id: string;
  emergency_id: string;
  ambulance_id: string;
  recommendation_id: string | null;
  recommended_ambulance_id: string | null;
  state: string;
  active: boolean;
  assigned_at: string;
  finalized_at: string | null;
  reassignment_reason: string | null;
  assignment_reason: string | null;
};

export type RankingItem = {
  ambulance_id: string;
  code: string;
  state?: string;
  distance: number;
  operational_load?: number;
  reliability?: number;
  normalized_scores?: Record<string, number>;
  weighted_scores?: Record<string, number>;
  total_score?: number;
  score?: number;
};

export type RecommendationCriteria = {
  weights?: Record<string, number>;
  references?: Record<string, unknown>;
  emergency?: Record<string, unknown>;
  selected?: RankingItem | null;
  no_candidate_reason?: string | null;
  ranking?: RankingItem[];
};

export type AIRecommendation = {
  id: string;
  emergency_id: string;
  recommended_ambulance_id: string | null;
  calculated_priority: number;
  total_score: number;
  decision_reason: string;
  candidates_count: number;
  criteria: RecommendationCriteria;
  created_at: string;
};

export type CandidateRanking = {
  recommendation_id: string;
  emergency_id: string;
  recommended_ambulance_id: string | null;
  decision_reason: string;
  candidates_count: number;
  ranking: RankingItem[];
};

export type SystemEvent = {
  id: string;
  emergency_id: string | null;
  ambulance_id: string | null;
  event_type: string;
  description: string;
  event_metadata: Record<string, unknown>;
  created_at: string;
};

export type EmergencyTrace = {
  emergency: Emergency;
  latest_recommendation: AIRecommendation | null;
  selected_assignment: Assignment | null;
  recommended_ambulance_id: string | null;
  assigned_ambulance_id: string | null;
  assignment_matches_recommendation: boolean | null;
  trace_reason: string;
  events: SystemEvent[];
};

export type EmergencyCreate = {
  type: string;
  severity: number;
  simulated_location: string;
};

export type EmergencyStateUpdate = {
  state: "EN_ATENCION" | "CERRADA";
};

export type AmbulanceCreate = {
  code: string;
  simulated_location: string;
  operational_load: number;
  reliability: number;
};

export type AssignmentAttemptCreate = {
  emergency_id: string;
  ambulance_id: string;
};

export type AssignmentAttemptResult = {
  accepted: boolean;
  assignment: Assignment | null;
  reason: string | null;
};
