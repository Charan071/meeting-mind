"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, isPast } from "date-fns";
import { clsx } from "clsx";
import type { ActionItem } from "@meetingmind/shared";
import { api } from "@/lib/api";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In Progress" },
  { value: "overdue", label: "Overdue" },
  { value: "done", label: "Done" },
  { value: "deferred", label: "Deferred" },
] as const;

export default function ActionItemsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const qc = useQueryClient();

  const { data: items, isLoading } = useQuery<ActionItem[]>({
    queryKey: ["action-items", statusFilter],
    queryFn: () => api.get(`/action-items${statusFilter ? `?status=${statusFilter}` : ""}`),
    refetchInterval: 15_000,
  });

  const { mutate: markDone } = useMutation({
    mutationFn: (id: string) => api.post(`/action-items/${id}/done`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["action-items"] }),
  });

  const overdueCount = (items ?? []).filter((i) => i.status === "overdue").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-neutral-900">Action Items</h1>
        {overdueCount > 0 && (
          <span className="px-2.5 py-1 rounded-sm bg-red-50 text-red-700 text-sm font-medium">
            ⚠ {overdueCount} overdue
          </span>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-4 bg-neutral-100 rounded p-1 w-fit">
        {STATUS_FILTERS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={clsx(
              "px-3 py-1 rounded text-xs font-medium transition-colors duration-fast",
              statusFilter === value
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-500 hover:text-neutral-700"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded border border-neutral-200">
        <table className="w-full text-sm">
          <thead className="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-neutral-600 w-1/2">Task</th>
              <th className="text-left px-4 py-2.5 font-medium text-neutral-600">Owner</th>
              <th className="text-left px-4 py-2.5 font-medium text-neutral-600">Deadline</th>
              <th className="text-left px-4 py-2.5 font-medium text-neutral-600">Status</th>
              <th className="px-4 py-2.5 w-16" />
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-neutral-400 text-sm">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && items?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-neutral-400">
                  No action items.
                </td>
              </tr>
            )}
            {items?.map((item) => (
              <ActionItemRow key={item.id} item={item} onMarkDone={() => markDone(item.id)} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const PRIORITY_COLOR: Record<string, string> = {
  critical: "text-red-600 font-semibold",
  high: "text-orange-600",
  medium: "text-neutral-700",
  low: "text-neutral-400",
};

const STATUS_PILL: Record<string, string> = {
  open: "bg-blue-50 text-blue-700",
  in_progress: "bg-yellow-50 text-yellow-700",
  overdue: "bg-red-50 text-red-700",
  done: "bg-green-50 text-green-700",
  deferred: "bg-neutral-100 text-neutral-500",
};

function ActionItemRow({ item, onMarkDone }: { item: ActionItem; onMarkDone: () => void }) {
  const isOverdue =
    item.status === "overdue" ||
    (item.deadline && isPast(new Date(item.deadline)) && item.status === "open");

  return (
    <tr className={clsx("hover:bg-neutral-50 transition-colors duration-fast", isOverdue && "bg-red-50/30")}>
      <td className="px-4 py-3">
        <p className={clsx("text-neutral-900", item.status === "done" && "line-through text-neutral-400")}>
          {item.task}
        </p>
        {item.verbatimQuote && (
          <blockquote className="verbatim-quote mt-1.5 text-xs">
            "{item.verbatimQuote}"
          </blockquote>
        )}
      </td>
      <td className="px-4 py-3 text-neutral-600">{item.ownerName ?? "—"}</td>
      <td className={clsx("px-4 py-3 text-sm", isOverdue ? "text-red-600 font-medium" : "text-neutral-500")}>
        {item.deadline ? (
          <>
            {isOverdue && <span className="mr-1">⚠</span>}
            {format(new Date(item.deadline), "MMM d, yyyy")}
          </>
        ) : "—"}
      </td>
      <td className="px-4 py-3">
        <span className={clsx("px-2 py-0.5 rounded-sm text-xs font-medium capitalize", STATUS_PILL[item.status])}>
          {item.status.replace("_", " ")}
        </span>
      </td>
      <td className="px-4 py-3">
        {item.status !== "done" && item.status !== "deferred" && (
          <button
            onClick={onMarkDone}
            className="text-xs px-2 py-0.5 border border-neutral-200 rounded text-neutral-500 hover:border-green-400 hover:text-green-600 transition-colors duration-fast"
          >
            Done
          </button>
        )}
      </td>
    </tr>
  );
}
