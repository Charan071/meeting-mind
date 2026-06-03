export type IntegrationProvider =
  | "slack"
  | "gmail"
  | "linear"
  | "jira"
  | "asana"
  | "hubspot"
  | "salesforce"
  | "google_calendar";

export type IntegrationStatus = "connected" | "disconnected" | "error";

export interface Integration {
  id: string;
  userId: string;
  provider: IntegrationProvider;
  status: IntegrationStatus;
  connectedAt?: string;
  lastSyncAt?: string;
  errorMessage?: string;
}

export interface IntegrationSettings {
  userId: string;
  slackEnabled: boolean;
  slackChannelId?: string;
  gmailEnabled: boolean;
  linearEnabled: boolean;
  jiraEnabled: boolean;
  asanaEnabled: boolean;
  hubspotEnabled: boolean;
  salesforceEnabled: boolean;
}
