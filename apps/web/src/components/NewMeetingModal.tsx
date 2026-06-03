"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

interface MeetingResponse {
  id: string;
  status: string;
}

function detectPlatform(url: string): string | null {
  if (/zoom\.us/.test(url)) return "Zoom";
  if (/meet\.google\.com/.test(url)) return "Google Meet";
  if (/teams\.microsoft\.com/.test(url)) return "Teams";
  if (/webex\.com/.test(url)) return "Webex";
  return null;
}

export function NewMeetingModal({ open, onClose }: Props) {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const qc = useQueryClient();
  const urlRef = useRef<HTMLInputElement>(null);

  const platform = url ? detectPlatform(url) : null;

  const { mutate: create, isPending, error } = useMutation({
    mutationFn: async () => {
      const meeting: MeetingResponse = await api.post("/meetings", {
        title: title.trim() || "Untitled Meeting",
        meeting_url: url.trim(),
      });
      await api.post(`/meetings/${meeting.id}/join`, {});
      return meeting;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meetings"] });
      setUrl("");
      setTitle("");
      onClose();
    },
  });

  // Focus URL input on open
  useEffect(() => {
    if (open) setTimeout(() => urlRef.current?.focus(), 50);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const canSubmit = url.trim().length > 0 && !isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(32,31,30,0.72)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-lg w-full max-w-md shadow-[0_4px_24px_rgba(0,0,0,0.2)]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
          <h2 className="text-base font-semibold text-neutral-900">Start a new meeting</h2>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-5 space-y-4">
          {/* URL field */}
          <div>
            <label className="block text-[11px] font-semibold text-neutral-500 uppercase tracking-wider mb-1.5">
              Meeting URL <span className="text-error">*</span>
            </label>
            <input
              ref={urlRef}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://meet.google.com/…"
              className="w-full border border-neutral-200 rounded px-3 py-2 text-sm text-neutral-900 placeholder-neutral-300 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/10 transition"
            />
            {platform && (
              <div className="flex items-center gap-1.5 mt-1.5">
                <span className="text-[11px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-medium">{platform}</span>
                <span className="text-[11px] text-neutral-400">detected</span>
              </div>
            )}
            <p className="text-[11px] text-neutral-400 mt-1">Google Meet, Zoom, Teams, and Webex supported.</p>
          </div>

          {/* Name field */}
          <div>
            <label className="block text-[11px] font-semibold text-neutral-500 uppercase tracking-wider mb-1.5">
              Meeting name <span className="text-neutral-300 font-normal normal-case">(optional)</span>
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q3 Kickoff"
              className="w-full border border-neutral-200 rounded px-3 py-2 text-sm text-neutral-900 placeholder-neutral-300 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/10 transition"
            />
          </div>

          {/* Consent note */}
          <div className="bg-primary-50 border border-primary-100 rounded px-3 py-2.5 flex gap-2.5 items-start">
            <div className="w-4 h-4 rounded-full bg-primary-500 flex items-center justify-center shrink-0 mt-0.5">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <p className="text-xs text-primary-700">
              The bot joins as <strong>MeetingMind</strong> and is visible to all participants.
            </p>
          </div>

          {error && (
            <p className="text-xs text-error">{(error as Error).message}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-neutral-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-neutral-600 border border-neutral-200 rounded hover:bg-neutral-50 transition-colors duration-fast"
          >
            Cancel
          </button>
          <button
            onClick={() => create()}
            disabled={!canSubmit}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-500 rounded hover:bg-primary-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-fast flex items-center gap-2"
          >
            {isPending ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Sending bot…
              </>
            ) : (
              "Send Bot"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
