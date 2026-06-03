"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, isPast } from "date-fns";
import { clsx } from "clsx";
import type { ActionItem } from "@meetingmind/shared";
import { api } from "@/lib/api";

export default function TeamPage() {
  const { data: open, isLoading } = useQuery<ActionItem[]>({
    queryKey: ["open-items"],
    queryFn: () => api.get("/action-items/open"),
    refetchInterval: 30_000,
  });

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center text-neutral-400 text-sm">Loading…</div>
  );

  const byOwner = groupByOwner(open ?? []);
  const ownerNames = Object.keys(byOwner).sort();
  const overdueCount = (open ?? []).filter((i) => i.status === "overdue").length;

  return (
    <>
      {/* Command bar */}
      <div className="cmdbar">
        <span className="cmdbar-title">Team</span>
        <div className="flex items-center gap-3 text-sm text-neutral-400">
          <span>{(open ?? []).length} open</span>
          {overdueCount > 0 && (
            <span className="px-2 py-0.5 rounded-sm bg-red-50 text-red-700 text-xs font-semibold">
              {overdueCount} overdue
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {ownerNames.length === 0 ? (
          <div className="card p-10 text-center text-neutral-400 text-sm">No open commitments. 🎉</div>
        ) : (
          <div className="space-y-4 max-w-4xl">
            {ownerNames.map((owner) => (
              <OwnerLane key={owner} owner={owner} items={byOwner[owner]} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function OwnerLane({ owner, items }: { owner: string; items: ActionItem[] }) {
  const overdueCount = items.filter((i) => i.status === "overdue").length;

  return (
    <div className="card">
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-50">
        <div className="flex items-center gap-2.5">
          <Avatar name={owner} />
          <span className="text-sm font-medium text-neutral-900">{owner}</span>
          <span className="text-xs text-neutral-400">{items.length} items</span>
        </div>
        {overdueCount > 0 && (
          <span className="text-xs px-2 py-0.5 bg-red-50 text-red-700 rounded-sm font-semibold">
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

const PRIORITY_BORDER: Record<string, string> = {
  critical: "border-l-red-600",
  high:     "border-l-orange-400",
  medium:   "border-l-primary-500",
  low:      "border-l-neutral-200",
};

const STATUS_PILLS: Record<string, string> = {
  open:        "bg-blue-50 text-blue-700",
  in_progress: "bg-yellow-50 text-yellow-700",
  overdue:     "bg-red-50 text-red-700",
  done:        "bg-green-50 text-green-700",
  deferred:    "bg-neutral-100 text-neutral-500",
};

function CommitmentRow({ item }: { item: ActionItem }) {
  const qc = useQueryClient();
  const isOverdue =
    item.status === "overdue" ||
    (!!item.deadline && isPast(new Date(item.deadline)) && item.status === "open");

  const { mutate: markDone, isPending } = useMutation({
    mutationFn: () => api.post(`/action-items/${item.id}/done`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["open-items"] }),
  });

  return (
    <div className={clsx(
      "px-4 py-3 flex items-start gap-3 hover:bg-neutral-50 transition-colors duration-fast border-l-[3px]",
      PRIORITY_BORDER[item.priority] ?? "border-l-neutral-200"
    )}>
      <div className="flex-1 min-w-0">
        <p className={clsx("text-sm text-neutral-900", item.status === "done" && "line-through text-neutral-400")}>
          {item.task}
        </p>
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          {item.deadline && (
            <span className={clsx("text-xs", isOverdue ? "text-red-600 font-semibold" : "text-neutral-400")}>
              {isOverdue ? "⚠ " : ""}Due {format(new Date(item.deadline), "MMM d")}
            </span>
          )}
          <span className={clsx("text-[11px] px-1.5 py-0.5 rounded-sm font-medium capitalize", STATUS_PILLS[item.status])}>
            {item.status.replace("_", " ")}
          </span>
          {item.verbatimQuote && (
            <span className="text-xs text-neutral-300 italic truncate max-w-[200px]">
              &ldquo;{item.verbatimQuote}&rdquo;
            </span>
          )}
        </div>
      </div>

      <button
        onClick={() => markDone()}
        disabled={isPending || item.status === "done"}
        className="shrink-0 text-xs px-2 py-1 border border-neutral-200 rounded text-neutral-500 font-medium hover:border-green-400 hover:text-green-600 disabled:opacity-40 transition-colors duration-fast"
      >
        {isPending ? "…" : "Done"}
      </button>
    </div>
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
