import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  Ambulance,
  BrainCircuit,
  ClipboardList,
  FileClock,
  HeartPulse,
  LayoutDashboard,
  RefreshCw,
  Siren,
} from "lucide-react";
import { Button } from "./ui";

const navItems = [
  { to: "/", label: "Panel General", icon: LayoutDashboard },
  { to: "/emergencias", label: "Emergencias", icon: Siren },
  { to: "/ambulancias", label: "Ambulancias", icon: Ambulance },
  { to: "/asignaciones", label: "Asignaciones", icon: ClipboardList },
  { to: "/recomendaciones-ia", label: "Recomendaciones IA", icon: BrainCircuit },
  { to: "/trazabilidad", label: "Trazabilidad", icon: FileClock },
  { to: "/eventos", label: "Eventos del sistema", icon: Activity },
];

function pageTitle(pathname: string): string {
  return navItems.find((item) => item.to === pathname)?.label ?? "Panel General";
}

export function AppShell({
  children,
  apiOnline,
  lastSync,
  onRefresh,
}: {
  children: ReactNode;
  apiOnline: boolean;
  lastSync: Date | null;
  onRefresh: () => void;
}) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background text-text">
      <aside className="fixed left-0 top-0 z-20 hidden h-full w-[260px] flex-col border-r border-slate-800 bg-sidebar px-4 py-5 text-white md:flex">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <HeartPulse className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight">DistriCare</h1>
            <p className="text-xs text-slate-300">Centro de coordinacion</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                    isActive ? "bg-primary text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <div className="md:pl-[260px]">
        <header className="sticky top-0 z-10 flex h-[72px] items-center justify-between border-b border-border bg-surface/95 px-4 backdrop-blur md:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">DistriCare</p>
            <h2 className="text-xl font-bold text-text">{pageTitle(location.pathname)}</h2>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`hidden rounded-full px-3 py-1 text-xs font-semibold sm:inline-flex ${
                apiOnline ? "bg-green-50 text-success" : "bg-red-50 text-danger"
              }`}
            >
              {apiOnline ? "API conectada" : "API sin conexion"}
            </span>
            <span className="hidden text-xs text-muted lg:inline">
              Ultima sincronizacion: {lastSync ? lastSync.toLocaleTimeString("es-CO") : "-"}
            </span>
            <Button variant="secondary" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </Button>
          </div>
        </header>
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
