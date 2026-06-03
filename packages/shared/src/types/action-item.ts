export type ActionItemStatus =
  | "open"
  | "in_progress"
  | "done"
  | "overdue"
  | "deferred";

export type ActionItemPriority = "low" | "medium" | "high" | "critical";

export interface ActionItem {
  id: string;
  meetingId: string;
  task: string;
  ownerName?: string;
  ownerEmail?: string;
  deadline?: string;
  priority: ActionItemPriority;
  status: ActionItemStatus;
  verbatimQuote?: string;
  resolvedInMeetingId?: string;
  embeddingId?: string;
  createdAt: string;
  updatedAt: string;
}
