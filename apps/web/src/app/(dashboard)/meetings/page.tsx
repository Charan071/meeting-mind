"use client";

import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import type { Meeting } from "@meetingmind/shared";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { UpcomingMeetings } from "@/components/UpcomingMeetings";

export default function MeetingsPage() {
  const { data: meetings, isLoading } = useQuery<Meeting[]>({
    queryKey: ["meetings"],
    queryFn: () => api.get("/meetings"),
  });

  if (isLoading) {
    return <div className="text-neutral-500 text-sm">Loading meetings...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-neutral-900">Meetings</h1>
        <NewMeetingButton />
      </div>

      {/* Upcoming auto-join panel */}
      <UpcomingMeetings />

      <div className="bg-white rounded border border-neutral-200 divide-y divide-neutral-100">
        {meetings?.length === 0 && (
          <div className="py-12 text-center text-neutral-400 text-sm">
            No meetings yet. Join or create one to get started.
          </div>
        )}
        {meetings?.map((meeting) => (
          <MeetingRow key={meeting.id} meeting={meeting} />
        ))}
      </div>
    </div>
  );

}

function MeetingRow({ meeting }: { meeting: Meeting }) {
  return (
    <a href={`/meetings/${meeting.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50 transition-colors duration-fast">
      <div>
        <p className="text-sm font-medium text-neutral-900">{meeting.title}</p>
        {meeting.startedAt && (
          <p className="text-xs text-neutral-400 mt-0.5">
            {formatDistanceToNow(new Date(meeting.startedAt), { addSuffix: true })}
          </p>
        )}
      </div>
      <StatusBadge status={meeting.status} />
    </a>
  );
}

function NewMeetingButton() {
  return (
    <button className="px-3 py-1.5 bg-primary-500 text-white text-sm rounded hover:bg-primary-600 transition-colors duration-fast">
      New Meeting
    </button>
  );
}
