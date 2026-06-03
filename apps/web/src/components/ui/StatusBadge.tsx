import { clsx } from "clsx";

const MAP: Record<string, string> = {
  scheduled:  "bg-neutral-100 text-neutral-600",
  recording:  "bg-red-50 text-red-700",
  processing: "bg-yellow-50 text-yellow-700",
  completed:  "bg-green-50 text-green-700",
  failed:     "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx("px-2 py-0.5 rounded-sm text-xs font-medium capitalize", MAP[status] ?? MAP.scheduled)}>
      {status}
    </span>
  );
}
