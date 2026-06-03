"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { formatDistanceToNow, isThisWeek, isToday } from "date-fns";
import type { Meeting, ActionItem } from "@meetingmind/shared";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { UpcomingMeetings } from "@/components/UpcomingMeetings";
import { NewMeetingModal } from "@/components/NewMeetingModal";
import { Plus } from "lucide-react";

const STATUS_BAR: Record<string, string> = {
  completed:  "bg-success",
  recording:  "bg-error",
  processing: "bg-warning",
  scheduled:  "bg-neutral-300",
  failed:     "bg-error",
};

function greeting(name?: string | null) {
  const hour = new Date().getHours();
  const time = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
  return `Good ${time}${name ? `, ${name.split(" ")[0]}` : ""}`;
}

export default function MeetingsPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data: session } = useSession();

  const { data: meetings, isLoading } = useQuery<Meeting[]>({
    queryKey: ["meetings"],
    queryFn: () => api.get("/meetings"),
  });

  const { data: allItems } = useQuery<ActionItem[]>({
    queryKey: ["action-items", ""],
    queryFn: () => api.get("/action-items"),
  });

  const thisWeek  = (meetings ?? []).filter((m) => m.startedAt && isThisWeek(new Date(m.startedAt))).length;
  const openCount = (allItems  ?? []).filter((i) => i.status === "open" || i.status === "in_progress").length;
  const overdueCount = (allItems ?? []).filter((i) => i.status === "overdue").length;
  const doneToday = (allItems  ?? []).filter((i) => i.status === "done" && i.deadline && isToday(new Date(i.deadline))).length;

  return (
    <>
      {/* Command bar */}
      <div className="cmdbar">
        <span className="cmdbar-title">{greeting(session?.user?.name)} 👋</span>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-500 text-white text-xs font-medium rounded hover:bg-primary-600 transition-colors duration-fast"
        >
          <Plus size={13} strokeWidth={2.5} />
          New Meeting
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { value: thisWeek,     label: "Meetings this week",  accent: "bg-primary-50",  dot: "bg-primary-500" },
            { value: openCount,    label: "Open action items",   accent: "bg-blue-50",     dot: "bg-blue-500"    },
            { value: overdueCount, label: "Overdue",             accent: "bg-red-50",      dot: "bg-error"       },
            { value: doneToday,    label: "Completed today",     accent: "bg-green-50",    dot: "bg-success"     },
          ].map(({ value, label, accent, dot }) => (
            <div key={label} className="card p-4">
              <div className={`w-7 h-7 rounded ${accent} flex items-center justify-center mb-2`}>
                <div className={`w-3 h-3 rounded-sm ${dot}`} />
              </div>
              <p className="text-2xl font-semibold text-neutral-900">{value}</p>
              <p className="text-xs text-neutral-400 mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        {/* Upcoming auto-join */}
        <UpcomingMeetings />

        {/* Meetings list */}
        <div className="card">
          <div className="px-4 py-2.5 border-b border-neutral-50 flex items-center justify-between">
            <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Meetings</p>
            <span className="text-xs text-neutral-400">{meetings?.length ?? 0} total</span>
          </div>

          {isLoading && (
            <div className="px-4 py-8 text-center text-neutral-400 text-sm">Loading…</div>
          )}

          {!isLoading && meetings?.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-3xl mb-3 opacity-20">📅</p>
              <p className="text-sm font-medium text-neutral-500">No meetings yet</p>
              <p className="text-xs text-neutral-400 mt-1">Join or create a meeting to get started.</p>
              <button
                onClick={() => setModalOpen(true)}
                className="mt-4 px-3 py-1.5 bg-primary-500 text-white text-xs font-medium rounded hover:bg-primary-600 transition-colors"
              >
                New Meeting
              </button>
            </div>
          )}

          {meetings?.map((meeting) => (
            <MeetingRow key={meeting.id} meeting={meeting} />
          ))}
        </div>
      </div>

      <NewMeetingModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}

function MeetingRow({ meeting }: { meeting: Meeting }) {
  return (
    <a
      href={`/meetings/${meeting.id}`}
      className="list-row"
    >
      <div className={`list-row-bar ${STATUS_BAR[meeting.status] ?? "bg-neutral-200"}`} />
      <div className="flex-1 py-3 min-w-0">
        <p className="text-sm font-medium text-neutral-900 truncate">{meeting.title}</p>
        {meeting.startedAt && (
          <p className="text-xs text-neutral-400 mt-0.5">
            {formatDistanceToNow(new Date(meeting.startedAt), { addSuffix: true })}
          </p>
        )}
      </div>
      <div className="px-4 shrink-0">
        <StatusBadge status={meeting.status} />
      </div>
    </a>
  );
}
