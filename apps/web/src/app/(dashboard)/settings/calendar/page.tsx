"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function CalendarSettingsPage() {
  const [triggerId, setTriggerId] = useState<string | null>(null);
  const [watching, setWatching] = useState(false);

  const { mutate: startWatch, isPending: starting } = useMutation({
    mutationFn: () => api.post("/calendar/watch", { entity_id: "placeholder" }),
    onSuccess: (data: { trigger_id: string }) => {
      setTriggerId(data.trigger_id);
      setWatching(true);
    },
  });

  const { mutate: stopWatch, isPending: stopping } = useMutation({
    mutationFn: () =>
      triggerId
        ? fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/calendar/watch/${triggerId}`,
            { method: "DELETE" }
          )
        : Promise.resolve(),
    onSuccess: () => {
      setWatching(false);
      setTriggerId(null);
    },
  });

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">Calendar Auto-Join</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Connect your Google Calendar and MeetingMind will automatically join every video call — zero manual effort.
        </p>
      </div>

      <div className="bg-white border border-neutral-200 rounded p-6 space-y-4">
        <div className="flex items-start gap-4">
          <span className="text-3xl">📅</span>
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-neutral-900">Google Calendar</h2>
            <p className="text-xs text-neutral-400 mt-1">
              When enabled, MeetingMind watches your primary calendar and dispatches a recording bot 60 seconds before each meeting with a video link.
            </p>
          </div>
          <StatusChip active={watching} />
        </div>

        <div className="bg-neutral-50 rounded p-3 space-y-1 text-xs text-neutral-500">
          <p>✓ Detects Zoom, Google Meet, and Microsoft Teams links</p>
          <p>✓ Links recurring meetings into a series automatically</p>
          <p>✓ Sends a Slack notification when the bot joins</p>
          <p>✓ Consent notice is shown to participants via bot name</p>
        </div>

        {watching ? (
          <button
            onClick={() => stopWatch()}
            disabled={stopping}
            className="w-full py-2 border border-red-200 rounded text-sm text-red-600 hover:bg-red-50 transition-colors duration-fast disabled:opacity-40"
          >
            {stopping ? "Stopping…" : "Stop watching calendar"}
          </button>
        ) : (
          <button
            onClick={() => startWatch()}
            disabled={starting}
            className="w-full py-2 bg-primary-500 text-white rounded text-sm hover:bg-primary-600 transition-colors duration-fast disabled:opacity-40"
          >
            {starting ? "Connecting…" : "Enable auto-join"}
          </button>
        )}

        {triggerId && (
          <p className="text-xs text-neutral-400 text-center">
            Trigger ID: <code className="font-mono">{triggerId}</code>
          </p>
        )}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded p-4 text-xs text-amber-700">
        <strong>Recording consent:</strong> The bot joins as "MeetingMind Notetaker" and participants see its name in the attendee list. You are responsible for ensuring all participants consent to recording under applicable laws.
      </div>
    </div>
  );
}

function StatusChip({ active }: { active: boolean }) {
  return (
    <span className={`px-2 py-0.5 rounded-sm text-xs font-medium shrink-0 ${
      active ? "bg-green-50 text-green-700" : "bg-neutral-100 text-neutral-500"
    }`}>
      {active ? "Active" : "Inactive"}
    </span>
  );
}
