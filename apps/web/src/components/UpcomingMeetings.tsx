"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow, format, isPast } from "date-fns";
import { clsx } from "clsx";
import { api } from "@/lib/api";

interface UpcomingMeeting {
  id: string;
  title: string;
  platform: string | null;
  meeting_url: string | null;
  started_at: string | null;
  series_id: string | null;
}

const PLATFORM_ICON: Record<string, string> = {
  zoom: "🎥",
  google_meet: "🟢",
  teams: "🟦",
  other: "📹",
};

export function UpcomingMeetings() {
  const qc = useQueryClient();

  const { data: meetings, isLoading } = useQuery<UpcomingMeeting[]>({
    queryKey: ["upcoming"],
    queryFn: () => api.get("/calendar/upcoming"),
    refetchInterval: 60_000,
  });

  const { mutate: joinNow, isPending } = useMutation({
    mutationFn: (id: string) => api.post(`/meetings/${id}/join`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["upcoming", "meetings"] }),
  });

  if (isLoading) return null;
  if (!meetings?.length) return null;

  return (
    <div className="bg-white border border-neutral-200 rounded">
      <div className="px-4 py-3 border-b border-neutral-100 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-900">Upcoming</h2>
        <span className="text-xs text-neutral-400">{meetings.length} scheduled</span>
      </div>

      <div className="divide-y divide-neutral-50">
        {meetings.map((m) => {
          const startedAt = m.started_at ? new Date(m.started_at) : null;
          const isStarting = startedAt && Math.abs(Date.now() - startedAt.getTime()) < 5 * 60 * 1000;
          const icon = PLATFORM_ICON[m.platform ?? ""] ?? "📅";

          return (
            <div key={m.id} className="px-4 py-3 flex items-center gap-3">
              <span className="text-lg shrink-0">{icon}</span>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-900 truncate">{m.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {startedAt && (
                    <span className={clsx(
                      "text-xs",
                      isStarting ? "text-orange-600 font-medium" : "text-neutral-400"
                    )}>
                      {isStarting ? "Starting now" : format(startedAt, "h:mm a")}
                    </span>
                  )}
                  {m.series_id && (
                    <span className="text-xs text-neutral-300">· recurring</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {/* Auto-join badge */}
                <span className="text-xs text-primary-500 font-medium">Auto ✓</span>

                {/* Manual override join */}
                <button
                  onClick={() => joinNow(m.id)}
                  disabled={isPending}
                  className="text-xs px-2 py-1 border border-neutral-200 rounded text-neutral-500 hover:border-primary-400 hover:text-primary-600 transition-colors duration-fast disabled:opacity-40"
                >
                  Join now
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
