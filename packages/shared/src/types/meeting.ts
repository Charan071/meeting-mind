export type MeetingStatus =
  | "scheduled"
  | "recording"
  | "processing"
  | "completed"
  | "failed";

export interface Meeting {
  id: string;
  title: string;
  status: MeetingStatus;
  startedAt: string;
  endedAt?: string;
  durationSeconds?: number;
  recallBotId?: string;
  meetingUrl?: string;
  platform?: "zoom" | "google_meet" | "teams";
  transcriptUrl?: string;
  summaryShort?: string;
  seriesId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface MeetingExtraction {
  meetingId: string;
  summary: string;
  decisions: string[];
  openQuestions: string[];
  rawTranscript?: string;
}
