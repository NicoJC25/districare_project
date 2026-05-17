import type { ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import type { StatusTone } from "../utils/status";

const toneClasses: Record<StatusTone, string> = {
  default: "bg-slate-100 text-slate-700 border-slate-200",
  success: "bg-green-50 text-success border-green-200",
  warning: "bg-amber-50 text-warning border-amber-200",
  danger: "bg-red-50 text-danger border-red-200",
  info: "bg-blue-50 text-secondary border-blue-200",
  purple: "bg-violet-50 text-purple border-violet-200",
};

export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-card border border-border bg-surface shadow-card ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
          {title && <h2 className="text-base font-semibold text-text">{title}</h2>}
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  const variants = {
    primary: "bg-primary text-white hover:bg-primary-dark",
    secondary: "border border-border bg-surface text-text hover:bg-surface-muted",
    ghost: "text-muted hover:bg-surface-muted hover:text-text",
    danger: "bg-danger text-white hover:bg-red-700",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15 ${props.className ?? ""}`}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 ${props.className ?? ""}`}
    />
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15 ${props.className ?? ""}`}
    />
  );
}

export function StatusBadge({ children, tone }: { children: ReactNode; tone: StatusTone }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClasses[tone]}`}>
      {children}
    </span>
  );
}

export function KpiCard({
  label,
  value,
  icon,
  tone = "info",
}: {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  tone?: StatusTone;
}) {
  return (
    <Card className="min-h-[116px]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-text">{value}</p>
        </div>
        <div className={`rounded-lg border p-2 ${toneClasses[tone]}`}>{icon}</div>
      </div>
    </Card>
  );
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex min-h-[140px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface-muted/50 p-6 text-center">
      <p className="font-semibold text-text">{title}</p>
      {detail && <p className="mt-1 max-w-md text-sm text-muted">{detail}</p>}
    </div>
  );
}

export function LoadingState({ label = "Cargando datos..." }: { label?: string }) {
  return (
    <div className="flex min-h-[140px] items-center justify-center gap-2 text-sm font-medium text-muted">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex min-h-[120px] items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-medium text-danger">
      <AlertCircle className="h-4 w-4" />
      {message}
    </div>
  );
}

export function Modal({
  open,
  title,
  children,
  footer,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-lg overflow-hidden rounded-card border border-border bg-surface shadow-xl">
        <header className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="font-semibold text-text">{title}</h2>
          <Button variant="ghost" className="px-2" onClick={onClose} type="button">
            Cerrar
          </Button>
        </header>
        <div className="p-5">{children}</div>
        {footer && <footer className="flex justify-end gap-3 border-t border-border bg-surface-muted px-5 py-4">{footer}</footer>}
      </div>
    </div>
  );
}

export function JsonDetails({ value }: { value: unknown }) {
  return (
    <details className="rounded-lg border border-border bg-surface-muted p-3 text-xs">
      <summary className="cursor-pointer font-semibold text-primary">Ver metadatos</summary>
      <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-muted">{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

export function ScoreBar({ value, max = 100 }: { value: number; max?: number }) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const width = Math.max(0, Math.min(100, (safeValue / max) * 100));
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-raised">
        <div className="h-full rounded-full bg-primary" style={{ width: `${width}%` }} />
      </div>
      <span className="w-12 text-right text-xs font-semibold tabular-nums text-muted">{safeValue.toFixed(1)}</span>
    </div>
  );
}

export function ReliabilityBar({ value }: { value: number }) {
  const tone = value < 0.9 ? "bg-warning" : "bg-primary";
  return (
    <div className="space-y-1">
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-raised">
        <div className={`h-full ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} />
      </div>
      <p className="text-xs font-semibold tabular-nums text-muted">{Math.round(value * 100)}%</p>
    </div>
  );
}

export function LoadMeter({ value }: { value: number }) {
  const segments = Array.from({ length: 10 }, (_, index) => index < value);
  const color = value >= 8 ? "bg-danger" : value >= 5 ? "bg-warning" : "bg-success";
  return (
    <div className="space-y-1">
      <div className="flex gap-0.5">
        {segments.map((active, index) => (
          <span key={index} className={`h-2 flex-1 rounded-sm ${active ? color : "bg-surface-raised"}`} />
        ))}
      </div>
      <p className="text-xs font-semibold tabular-nums text-muted">{value}/10</p>
    </div>
  );
}
