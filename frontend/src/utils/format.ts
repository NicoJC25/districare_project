export function shortId(id: string | null | undefined): string {
  if (!id) return "-";
  return id.length <= 10 ? id : `${id.slice(0, 8)}...`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "sin registro";
  const diffMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(diffMs / 60000));
  if (minutes < 1) return "hace segundos";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return formatDate(value);
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function score(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}
