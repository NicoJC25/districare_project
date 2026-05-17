import type { ReactNode } from "react";
import { EmptyState } from "./ui";

export type Column<T> = {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
};

export function DataTable<T>({
  rows,
  columns,
  getRowKey,
  emptyTitle = "No hay registros",
}: {
  rows: T[];
  columns: Column<T>[];
  getRowKey: (row: T) => string;
  emptyTitle?: string;
}) {
  if (rows.length === 0) return <EmptyState title={emptyTitle} />;

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead className="bg-surface-muted text-xs font-semibold uppercase tracking-wide text-muted">
          <tr>
            {columns.map((column) => (
              <th key={column.header} className={`px-4 py-3 ${column.className ?? ""}`}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr key={getRowKey(row)} className="transition hover:bg-surface-muted/60">
              {columns.map((column) => (
                <td key={column.header} className={`px-4 py-3 align-top ${column.className ?? ""}`}>
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
