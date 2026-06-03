"use client";

import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { format } from "date-fns";
import { clsx } from "clsx";
import type { Meeting, ActionItem } from "@meetingmind/shared";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface Extraction {
  id: string;
  meeting_id: string;
  summary: string;
  decisions: string[];
  open_questions: string[];
  created_at: string;
}

const PRIORITY_BORDER: Record<string, string> = {
  critical: "border-l-red-600",
  high:     "border-l-orange-400",
  medium:   "border-l-primary-500",
  low:      "border-l-neutral-300",
};

const STATUS_PILL: Record<string, string> = {
  open:        "bg-blue-50 text-blue-700",
  in_progress: "bg-yellow-50 text-yellow-700",
  overdue:     "bg-red-50 text-red-700",
  done:        "bg-green-50 text-green-700",
};

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: meeting } = useQuery<Meeting>({
    queryKey: ["meeting", id],
    queryFn: () => api.get(`/meetings/${id}`),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "processing" || s === "recording" ? 3000 : false;
    },
  });

  const { data: extraction } = useQuery<Extraction>({
    queryKey: ["extraction", id],
    queryFn: () => api.get(`/meetings/${id}/extraction`),
    enabled: meeting?.status === "completed",
    retry: false,
  });

  const { data: actionItems } = useQuery<ActionItem[]>({
    queryKey: ["meeting-actions", id],
    queryFn: () => api.get(`/meetings/${id}/action-items`),
    enabled: meeting?.status === "completed",
  });

  useWsMeeting(id, () => {
    queryClient.invalidateQueries({ queryKey: ["meeting", id] });
    queryClient.invalidateQueries({ queryKey: ["extraction", id] });
    queryClient.invalidateQueries({ queryKey: ["meeting-actions", id] });
  });

  if (!meeting) return (
    <div className="flex-1 flex items-center justify-center text-neutral-400 text-sm">Loading…</div>
  );

  return (
    <>
      {/* Command bar */}
      <div className="cmdbar">
        <span className="cmdbar-title">{meeting.title}</span>
        <div className="flex items-center gap-2">
          <StatusBadge status={meeting.status} />
          {meeting.status === "completed" && (
            <button className="px-3 py-1.5 text-xs font-medium border border-neutral-200 rounded bg-white text-neutral-600 hover:bg-neutral-50 transition-colors duration-fast">
              Push to Slack
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <div className="max-w-2xl space-y-3">
          {/* Meta */}
          {meeting.startedAt && (
            <p className="text-xs text-neutral-400">
              {format(new Date(meeting.startedAt), "PPP · p")}
              {meeting.durationSeconds && ` · ${Math.round(meeting.durationSeconds / 60)} min`}
            </p>
          )}

          {/* Processing banner */}
          {(meeting.status === "processing" || meeting.status === "recording") && (
            <ProcessingBanner status={meeting.status} />
          )}

          {/* Summary */}
          {extraction && (
            <section className="card p-4">
              <h2 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-2">Summary</h2>
              <p className="text-sm text-neutral-700 leading-relaxed">{extraction.summary}</p>
            </section>
          )}

          {/* Action Items */}
          {actionItems && actionItems.length > 0 && (
            <section className="card p-4">
              <h2 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">
                Action Items ({actionItems.length})
              </h2>
              <div className="space-y-2">
                {actionItems.map((item) => (
                  <ActionItemCard key={item.id} item={item} />
                ))}
              </div>
            </section>
          )}

          {/* Decisions */}
          {extraction?.decisions?.length ? (
            <section className="card p-4">
              <h2 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-2">Decisions</h2>
              <ul className="space-y-1.5">
                {extraction.decisions.map((d, i) => (
                  <li key={i} className="text-sm text-neutral-700 flex gap-2">
                    <span className="text-success shrink-0">✓</span>
                    {d}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* Open Questions */}
          {extraction?.open_questions?.length ? (
            <section className="card p-4">
              <h2 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-2">Open Questions</h2>
              <ul className="space-y-1.5">
                {extraction.open_questions.map((q, i) => (
                  <li key={i} className="text-sm text-neutral-700 flex gap-2">
                    <span className="text-warning shrink-0">?</span>
                    {q}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      </div>
    </>
  );
}

function ActionItemCard({ item }: { item: ActionItem }) {
  return (
    <div className={clsx("priority-card", PRIORITY_BORDER[item.priority] ?? "border-l-neutral-300")}>
      <div className="flex items-start gap-2">
        <p className="text-sm text-neutral-900 flex-1">{item.task}</p>
        <span className={clsx("px-1.5 py-0.5 text-[11px] rounded-sm font-medium shrink-0 capitalize", STATUS_PILL[item.status])}>
          {item.status.replace("_", " ")}
        </span>
      </div>
      <div className="flex gap-4 text-xs text-neutral-400 mt-1.5">
        {item.ownerName && <span>Owner: <span className="text-neutral-600">{item.ownerName}</span></span>}
        {item.deadline && <span>Due: <span className="text-neutral-600">{format(new Date(item.deadline), "MMM d")}</span></span>}
      </div>
      {item.verbatimQuote && (
        <blockquote className="verbatim-quote mt-2">&ldquo;{item.verbatimQuote}&rdquo;</blockquote>
      )}
    </div>
  );
}

function ProcessingBanner({ status }: { status: string }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded px-4 py-3 text-sm text-amber-800 flex items-center gap-3">
      <PulsingDot />
      {status === "recording"
        ? "Bot is recording the meeting… Transcript will be processed when the call ends."
        : "Processing transcript with AI — this takes about 30 seconds."}
    </div>
  );
}

function PulsingDot() {
  return (
    <span className="relative flex h-2.5 w-2.5 shrink-0">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
    </span>
  );
}

function useWsMeeting(meetingId: string, onUpdate: () => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const cbRef = useRef(onUpdate);
  cbRef.current = onUpdate;

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const wsUrl = apiUrl.replace(/^http/, "ws") + `/api/v1/meetings/${meetingId}/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === "meeting.completed") cbRef.current();
      } catch {}
    };

    const ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 25000);

    return () => {
      clearInterval(ping);
      ws.close();
    };
  }, [meetingId]);
}
