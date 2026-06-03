"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, isPast } from "date-fns";
import { clsx } from "clsx";
import type { ActionItem } from "@meetingmind/shared";
import { api } from "@/lib/api";

const STATUS_FILTERS = [
  { value: "",            label: "All"         },
  { value: "open",        label: "Open"        },
  { value: "in_progress", label: "In Progress" },
  { value: "overdue",     label: "Overdue"     },
  { value: "done",        label: "Done"        },
  { value: "deferred",    label: "Deferred"    },
] as const;

const STATUS_PILL: Record<string, string> = {
  open:        "bg-blue-50 text-blue-700",
  in_progress: "bg-yellow-50 text-yellow-700",
  overdue:     "bg-red-50 text-red-700",
  done:        "bg-green-50 text-green-700",
  deferred:    "bg-neutral-100 text-neutral-500",
};

const PRIORITY_BORDER: Record<string, string> = {
  critical: "border-l-red-600",
  high:     "border-l-orange-400",
  medium:   "border-l-primary-500",
  low:      "border-l-neutral-300",
};

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
    <>
      {/* Command bar */}
      <div className="cmdbar">
        <span className="cmdbar-title">Action Items</span>
        {overdueCount > 0 && (
          <span className="px-2.5 py-1 rounded bg-red-50 text-red-700 text-xs font-semibold">
            ⚠ {overdueCount} overdue
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {/* Filter tabs */}
        <div className="flex gap-0.5 mb-4 bg-neutral-100 rounded p-1 w-fit">
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

        <div className="card">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 border-b border-neutral-100">
              <tr>
                {["Task", "Owner", "Deadline", "Status", ""].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-50">
              {isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-neutral-400 text-sm">Loading…</td>
                </tr>
              )}
              {!isLoading && items?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-neutral-400 text-sm">No action items.</td>
                </tr>
              )}
              {items?.map((item) => (
                <ActionItemRow key={item.id} item={item} onMarkDone={() => markDone(item.id)} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function ActionItemRow({ item, onMarkDone }: { item: ActionItem; onMarkDone: () => void }) {
  const isOverdue =
    item.status === "overdue" ||
    (!!item.deadline && isPast(new Date(item.deadline)) && item.status === "open");

  return (
    <tr className={clsx(
      "hover:bg-neutral-50 transition-colors duration-fast",
      isOverdue && "bg-red-50/40"
    )}>
      <td className={clsx(
        "px-4 py-3 border-l-[3px]",
        PRIORITY_BORDER[item.priority] ?? "border-l-neutral-200"
      )}>
        <p className={clsx("text-neutral-900", item.status === "done" && "line-through text-neutral-400")}>
          {item.task}
        </p>
        {item.verbatimQuote && (
          <blockquote className="verbatim-quote mt-1.5">&ldquo;{item.verbatimQuote}&rdquo;</blockquote>
        )}
      </td>
      <td className="px-4 py-3 text-neutral-500 text-xs">{item.ownerName ?? "—"}</td>
      <td className={clsx("px-4 py-3 text-xs", isOverdue ? "text-red-600 font-semibold" : "text-neutral-400")}>
        {item.deadline
          ? <>{isOverdue && <span className="mr-1">⚠</span>}{format(new Date(item.deadline), "MMM d, yyyy")}</>
          : "—"}
      </td>
      <td className="px-4 py-3">
        <span className={clsx("px-2 py-0.5 rounded-sm text-[11px] font-medium capitalize", STATUS_PILL[item.status])}>
          {item.status.replace("_", " ")}
        </span>
      </td>
      <td className="px-4 py-3">
        {item.status !== "done" && item.status !== "deferred" && (
          <button
            onClick={onMarkDone}
            className="text-xs px-2 py-1 border border-neutral-200 rounded text-neutral-500 font-medium hover:border-green-400 hover:text-green-600 transition-colors duration-fast"
          >
            Done
          </button>
        )}
      </td>
    </tr>
  );
}
