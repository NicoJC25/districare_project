export type StatusTone = "default" | "success" | "warning" | "danger" | "info" | "purple";

const emergencyTones: Record<string, StatusTone> = {
  REGISTRADA: "default",
  PRIORIZADA: "info",
  PUBLICADA: "info",
  EN_PROCESO_ASIGNACION: "warning",
  ASIGNADA: "success",
  SIN_UNIDAD_DISPONIBLE: "danger",
  EN_ATENCION: "success",
  FALLO_DETECTADO: "danger",
  REASIGNACION_PENDIENTE: "warning",
  REASIGNADA: "purple",
  CERRADA: "default",
};

const ambulanceTones: Record<string, StatusTone> = {
  DISPONIBLE: "success",
  OCUPADO: "info",
  CANDIDATA: "info",
  INTENTANDO_ACEPTAR: "warning",
  ASIGNADA: "info",
  EN_ATENCION: "success",
  INACTIVO: "default",
  FALLIDO: "danger",
  RECUPERADA: "success",
};

const assignmentTones: Record<string, StatusTone> = {
  PENDIENTE: "warning",
  CONFIRMADA: "success",
  RECHAZADA: "danger",
  FINALIZADA: "default",
  REASIGNADA: "purple",
};

export function toneForStatus(status: string): StatusTone {
  return emergencyTones[status] ?? ambulanceTones[status] ?? assignmentTones[status] ?? "default";
}

export function eventTone(eventType: string): StatusTone {
  if (eventType.includes("FAILED") || eventType.includes("REJECTED")) return "danger";
  if (eventType.includes("RECOVERED") || eventType.includes("CONFIRMED")) return "success";
  if (eventType.includes("REASSIGNMENT") || eventType.includes("ATTEMPTED")) return "warning";
  return "info";
}
