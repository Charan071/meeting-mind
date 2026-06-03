"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { format, differenceInMinutes } from "date-fns";
import { api } from "@/lib/api";

interface UpcomingMeeting {
  id: string;
  title: string;
  platform: string | null;
  meeting_url: string | null;
  started_at: string | null;
  series_id: string | null;
}

const AUTO_JOIN_RULES = [
  "Join all meetings with a video link",
  "Only join meetings I organise",
  "Skip 1:1 meetings",
  "Skip meetings marked Personal",
] as const;

const DEFAULT_RULES: Record<string, boolean> = {
  "Join all meetings with a video link": true,
  "Only join meetings I organise": false,
  "Skip 1:1 meetings": true,
  "Skip meetings marked Personal": true,
};

export default function CalendarSettingsPage() {
  const [triggerId, setTriggerId] = useState<string | null>(null);
  const [watching, setWatching] = useState(false);
  const [rules, setRules] = useState(DEFAULT_RULES);

  const { mutate: startWatch, isPending: starting } = useMutation({
    mutationFn: () => api.post<{ trigger_id: string }>("/calendar/watch", { entity_id: "placeholder" }),
    onSuccess: (data: { trigger_id: string }) => {
      setTriggerId(data.trigger_id);
      setWatching(true);
    },
  });

  const { mutate: stopWatch, isPending: stopping } = useMutation({
    mutationFn: async () => {
      if (triggerId) {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/calendar/watch/${triggerId}`, { method: "DELETE" });
      }
    },
    onSuccess: () => { setWatching(false); setTriggerId(null); },
  });

  const { data: upcoming } = useQuery<UpcomingMeeting[]>({
    queryKey: ["upcoming"],
    queryFn: () => api.get("/calendar/upcoming"),
    refetchInterval: 60_000,
  });

  return (
    <>
      {/* Command bar */}
      <div className="cmdbar">
        <span className="cmdbar-title">Calendar & Auto-Join</span>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <div className="max-w-xl space-y-3">
          {/* Calendar connection card */}
          <div className="card px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-blue-50 rounded flex items-center justify-center text-lg">📅</div>
              <div>
                <p className="text-sm font-medium text-neutral-900">Google Calendar</p>
                <p className={`text-xs font-medium mt-0.5 ${watching ? "text-success" : "text-neutral-400"}`}>
                  {watching ? "● Active · charan@aixccelerate.com" : "Not connected"}
                </p>
              </div>
            </div>
            {watching ? (
              <button
                onClick={() => stopWatch()}
                disabled={stopping}
                className="text-xs text-neutral-400 hover:text-red-600 transition-colors duration-fast disabled:opacity-40"
              >
                {stopping ? "Stopping…" : "Disconnect"}
              </button>
            ) : (
              <button
                onClick={() => startWatch()}
                disabled={starting}
                className="text-xs px-3 py-1.5 bg-primary-500 text-white rounded font-medium hover:bg-primary-600 transition-colors duration-fast disabled:opacity-40"
              >
                {starting ? "Connecting…" : "Connect"}
              </button>
            )}
          </div>

          {/* Auto-join rules */}
          <div className="card p-4">
            <p className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">Auto-join rules</p>
            <div className="space-y-2.5">
              {AUTO_JOIN_RULES.map((rule) => (
                <label key={rule} className="flex items-center gap-3 cursor-pointer group">
                  <div
                    onClick={() => setRules((r) => ({ ...r, [rule]: !r[rule] }))}
                    className={`w-4 h-4 rounded border-[1.5px] flex items-center justify-center shrink-0 transition-colors duration-fast ${
                      rules[rule]
                        ? "bg-primary-500 border-primary-500"
                        : "bg-white border-neutral-300 group-hover:border-primary-400"
                    }`}
                  >
                    {rules[rule] && (
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  <span className="text-sm text-neutral-700">{rule}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Upcoming meetings */}
          {upcoming && upcoming.length > 0 && (
            <div className="card p-4">
              <p className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">Upcoming</p>
              <div className="space-y-0 divide-y divide-neutral-50">
                {upcoming.map((m) => {
                  const startDate = m.started_at ? new Date(m.started_at) : null;
                  const minsAway = startDate ? differenceInMinutes(startDate, new Date()) : null;
                  const willJoin = !!m.meeting_url;
                  return (
                    <div key={m.id} className="flex items-center justify-between py-2.5">
                      <div>
                        <p className="text-sm text-neutral-900">{m.title}</p>
                        <p className="text-xs text-neutral-400 mt-0.5">
                          {startDate
                            ? minsAway !== null && minsAway > 0 && minsAway < 60
                              ? `in ${minsAway} min`
                              : format(startDate, "MMM d · h:mm a")
                            : ""}
                          {m.series_id ? " · recurring" : ""}
                        </p>
                      </div>
                      <span className={`px-2 py-0.5 rounded-sm text-[11px] font-medium ${
                        willJoin ? "bg-green-50 text-green-700" : "bg-neutral-100 text-neutral-500"
                      }`}>
                        {willJoin ? "will join" : "skipped"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Consent notice */}
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-700">
            <strong>Recording consent:</strong> The bot joins as &ldquo;MeetingMind Notetaker&rdquo; — visible to all participants. Ensure attendees consent under applicable laws.
          </div>
        </div>
      </div>
    </>
  );
}
