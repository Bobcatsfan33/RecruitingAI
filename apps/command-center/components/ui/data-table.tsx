"use client";

import clsx from "clsx";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  width?: string;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, idx: number) => string;
  onRowClick?: (row: T) => void;
  emptyState?: React.ReactNode;
}

export function DataTable<T>({ columns, rows, rowKey, onRowClick, emptyState }: Props<T>) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="text-sm">
          <thead className="vibrancy sticky top-0 z-10">
            <tr>
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  style={col.width ? { width: col.width } : undefined}
                  className="px-4 py-2 text-xs uppercase tracking-wide"
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-secondary">
                  {emptyState ?? "No rows."}
                </td>
              </tr>
            ) : (
              rows.map((row, idx) => (
                <tr
                  key={rowKey(row, idx)}
                  onClick={() => onRowClick?.(row)}
                  className={clsx(
                    "transition",
                    onRowClick && "cursor-pointer hover:bg-primary/5",
                  )}
                >
                  {columns.map((col) => (
                    <td key={String(col.key)} className="px-4 py-2 align-middle text-primary/90">
                      {col.render ? col.render(row) : (row as Record<string, unknown>)[col.key as string] as React.ReactNode}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
