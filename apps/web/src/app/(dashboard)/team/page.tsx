"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow, format, isPast } from "date-fns";
import { clsx } from "clsx";
import type { ActionItem } from "@meetingmind/shared";
import { api } from "@/lib/api";

export default function TeamPage() {
  const { data: open, isLoading } = useQuery<ActionItem[]>({
    queryKey: ["open-items"],
    queryFn: () => api.get("/action-items/open"),
    refetchInterval: 30_000,
  });

  if (isLoading) return <div className="text-neutral-500 text-sm">Loading…</div>;

  // Group by owner
  const byOwner = groupByOwner(open ?? []);
  const ownerNames = Object.keys(byOwner).sort();

  const overdueCount = (open ?? []).filter((i) => i.status === "overdue").length;

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-neutral-900">Team Commitments</h1>
        <div className="flex items-center gap-3 text-sm text-neutral-500">
          <span>{(open ?? []).length} open</span>
          {overdueCount > 0 && (
            <span className="px-2 py-0.5 rounded-sm bg-red-50 text-red-700 font-medium">
              {overdueCount} overdue
            </span>
          )}
        </div>
      </div>

      {/* Stats row */}
      <StatsRow items={open ?? []} />

      {/* Per-owner swimlanes */}
      {ownerNames.length === 0 && (
        <div className="bg-white border border-neutral-200 rounded p-10 text-center text-neutral-400 text-sm">
          No open commitments. 🎉
        </div>
      )}

      <div className="space-y-4">
        {ownerNames.map((owner) => (
          <OwnerLane key={owner} owner={owner} items={byOwner[owner]} />
        ))}
      </div>
    </div>
  );
}

function StatsRow({ items }: { items: ActionItem[] }) {
  const counts = {
    open: items.filter((i) => i.status === "open").length,
    in_progress: items.filter((i) => i.status === "in_progress").length,
    overdue: items.filter((i) => i.status === "overdue").length,
  };

  return (
    <div className="grid grid-cols-3 gap-3">
      {[
        { label: "Open", count: counts.open, color: "text-blue-700 bg-blue-50" },
        { label: "In Progress", count: counts.in_progress, color: "text-yellow-700 bg-yellow-50" },
        { label: "Overdue", count: counts.overdue, color: "text-red-700 bg-red-50" },
      ].map(({ label, count, color }) => (
        <div key={label} className="bg-white border border-neutral-200 rounded p-4 text-center">
          <p className={clsx("text-2xl font-semibold", color.split(" ")[0])}>{count}</p>
          <p className="text-xs text-neutral-400 mt-1">{label}</p>
        </div>
      ))}
    </div>
  );
}

function OwnerLane({ owner, items }: { owner: string; items: ActionItem[] }) {
  const overdueCount = items.filter((i) => i.status === "overdue").length;

  return (
    <div className="bg-white border border-neutral-200 rounded">
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100">
        <div className="flex items-center gap-2">
          <Avatar name={owner} />
          <span className="text-sm font-medium text-neutral-900">{owner}</span>
          <span className="text-xs text-neutral-400">{items.length} items</span>
        </div>
        {overdueCount > 0 && (
          <span className="text-xs px-2 py-0.5 bg-red-50 text-red-700 rounded-sm font-medium">
            {overdueCount} overdue
          </span>
        )}
      </div>

      <div className="divide-y divide-neutral-50">
        {items.map((item) => (
          <CommitmentRow key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

function CommitmentRow({ item }: { item: ActionItem }) {
  const qc = useQueryClient();
  const isOverdue = item.status === "overdue" || (item.deadline && isPast(new Date(item.deadline)) && item.status === "open");

  const { mutate: markDone, isPending } = useMutation({
    mutationFn: () => api.post(`/action-items/${item.id}/done`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["open-items"] }),
  });

  return (
    <div className="px-4 py-3 flex items-start gap-3 hover:bg-neutral-50 transition-colors duration-fast">
      {/* Priority dot */}
      <PriorityDot priority={item.priority} />

      <div className="flex-1 min-w-0">
        <p className={clsx("text-sm text-neutral-900", item.status === "done" && "line-through text-neutral-400")}>
          {item.task}
        </p>

        <div className="flex items-center gap-3 mt-1">
          {item.deadline && (
            <span className={clsx("text-xs", isOverdue ? "text-red-600 font-medium" : "text-neutral-400")}>
              {isOverdue ? "⚠ " : ""}Due {format(new Date(item.deadline), "MMM d")}
            </span>
          )}
          <StatusPill status={item.status} />
          {item.verbatimQuote && (
            <span className="text-xs text-neutral-300 italic truncate max-w-[200px]">
              "{item.verbatimQuote}"
            </span>
          )}
        </div>
      </div>

      {/* Quick mark-done */}
      <button
        onClick={() => markDone()}
        disabled={isPending || item.status === "done"}
        className="shrink-0 text-xs px-2 py-1 border border-neutral-200 rounded text-neutral-500 hover:border-green-400 hover:text-green-600 disabled:opacity-40 transition-colors duration-fast"
      >
        {isPending ? "…" : "Done"}
      </button>
    </div>
  );
}

const PRIORITY_DOTS: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  medium: "bg-blue-400",
  low: "bg-neutral-300",
};

function PriorityDot({ priority }: { priority: string }) {
  return <span className={clsx("mt-1.5 h-2 w-2 shrink-0 rounded-full", PRIORITY_DOTS[priority] ?? "bg-neutral-300")} />;
}

const STATUS_PILLS: Record<string, string> = {
  open: "bg-blue-50 text-blue-600",
  in_progress: "bg-yellow-50 text-yellow-600",
  overdue: "bg-red-50 text-red-600",
  done: "bg-green-50 text-green-600",
  deferred: "bg-neutral-100 text-neutral-500",
};

function StatusPill({ status }: { status: string }) {
  return (
    <span className={clsx("text-xs px-1.5 py-0.5 rounded-sm font-medium capitalize", STATUS_PILLS[status])}>
      {status.replace("_", " ")}
    </span>
  );
}

function Avatar({ name }: { name: string }) {
  const initials = name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
  return (
    <span className="h-6 w-6 rounded-full bg-primary-100 text-primary-700 text-xs font-semibold flex items-center justify-center shrink-0">
      {initials}
    </span>
  );
}

function groupByOwner(items: ActionItem[]): Record<string, ActionItem[]> {
  return items.reduce<Record<string, ActionItem[]>>((acc, item) => {
    const key = item.ownerName ?? "Unassigned";
    (acc[key] ??= []).push(item);
    return acc;
  }, {});
}
