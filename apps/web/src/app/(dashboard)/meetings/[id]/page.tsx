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

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: meeting } = useQuery<Meeting>({
    queryKey: ["meeting", id],
    queryFn: () => api.get(`/meetings/${id}`),
    refetchInterval: (data) =>
      data?.status === "processing" || data?.status === "recording" ? 3000 : false,
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

  // WebSocket — push updates when pipeline finishes
  useWsMeeting(id, () => {
    queryClient.invalidateQueries({ queryKey: ["meeting", id] });
    queryClient.invalidateQueries({ queryKey: ["extraction", id] });
    queryClient.invalidateQueries({ queryKey: ["meeting-actions", id] });
  });

  if (!meeting) return <div className="text-neutral-500 text-sm">Loading…</div>;

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">{meeting.title}</h1>
          {meeting.startedAt && (
            <p className="text-sm text-neutral-400 mt-1">
              {format(new Date(meeting.startedAt), "PPP p")}
              {meeting.durationSeconds && ` · ${Math.round(meeting.durationSeconds / 60)} min`}
            </p>
          )}
        </div>
        <StatusBadge status={meeting.status} />
      </div>

      {/* Processing banner */}
      {(meeting.status === "processing" || meeting.status === "recording") && (
        <ProcessingBanner status={meeting.status} />
      )}

      {/* Summary */}
      {extraction && (
        <Section title="Summary">
          <p className="text-sm text-neutral-700 leading-relaxed">{extraction.summary}</p>
        </Section>
      )}

      {/* Action Items */}
      {actionItems && actionItems.length > 0 && (
        <Section title={`Action Items (${actionItems.length})`}>
          <div className="space-y-3">
            {actionItems.map((item) => (
              <ActionItemCard key={item.id} item={item} />
            ))}
          </div>
        </Section>
      )}

      {/* Decisions */}
      {extraction?.decisions?.length ? (
        <Section title="Decisions">
          <ul className="space-y-1">
            {extraction.decisions.map((d, i) => (
              <li key={i} className="text-sm text-neutral-700 flex gap-2">
                <span className="text-primary-500 mt-0.5">✓</span>
                {d}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {/* Open Questions */}
      {extraction?.open_questions?.length ? (
        <Section title="Open Questions">
          <ul className="space-y-1">
            {extraction.open_questions.map((q, i) => (
              <li key={i} className="text-sm text-neutral-700 flex gap-2">
                <span className="text-warning mt-0.5">?</span>
                {q}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-neutral-200 rounded p-4">
      <h2 className="text-sm font-semibold text-neutral-900 mb-3">{title}</h2>
      {children}
    </div>
  );
}

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  medium: "bg-blue-400",
  low: "bg-neutral-300",
};

const STATUS_PILL: Record<string, string> = {
  open: "bg-blue-50 text-blue-700",
  in_progress: "bg-yellow-50 text-yellow-700",
  overdue: "bg-red-50 text-red-700",
  done: "bg-green-50 text-green-700",
};

function ActionItemCard({ item }: { item: ActionItem }) {
  return (
    <div className="border border-neutral-100 rounded p-3 space-y-1.5">
      <div className="flex items-start gap-2">
        <span className={clsx("w-2 h-2 rounded-full mt-1.5 shrink-0", PRIORITY_DOT[item.priority])} />
        <p className="text-sm text-neutral-900 flex-1">{item.task}</p>
        <span className={clsx("px-1.5 py-0.5 text-xs rounded-sm font-medium shrink-0", STATUS_PILL[item.status])}>
          {item.status.replace("_", " ")}
        </span>
      </div>

      <div className="flex gap-4 text-xs text-neutral-400 pl-4">
        {item.ownerName && <span>Owner: <span className="text-neutral-600">{item.ownerName}</span></span>}
        {item.deadline && <span>Due: <span className="text-neutral-600">{format(new Date(item.deadline), "MMM d")}</span></span>}
      </div>

      {item.verbatimQuote && (
        <blockquote className="verbatim-quote pl-4 text-xs">
          "{item.verbatimQuote}"
        </blockquote>
      )}
    </div>
  );
}

function ProcessingBanner({ status }: { status: string }) {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded px-4 py-3 text-sm text-yellow-800 flex items-center gap-2">
      <PulsingDot />
      {status === "recording"
        ? "Bot is recording the meeting…"
        : "Processing transcript with AI — this takes about 30 seconds."}
    </div>
  );
}

function PulsingDot() {
  return (
    <span className="relative flex h-2.5 w-2.5 shrink-0">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-yellow-500" />
    </span>
  );
}

function useWsMeeting(meetingId: string, onUpdate: () => void) {
  const ref = useRef<WebSocket | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const wsUrl = apiUrl.replace(/^http/, "ws") + `/api/v1/meetings/${meetingId}/ws`;
    const ws = new WebSocket(wsUrl);
    ref.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === "meeting.completed") onUpdate();
      } catch {}
    };

    // Heartbeat
    const ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 25000);

    return () => {
      clearInterval(ping);
      ws.close();
    };
  }, [meetingId]);
}
