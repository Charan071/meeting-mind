"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { clsx } from "clsx";

interface IntegrationSettings {
  slack_enabled: boolean;
  slack_channel_id: string | null;
  gmail_enabled: boolean;
  linear_enabled: boolean;
  jira_enabled: boolean;
  asana_enabled: boolean;
  hubspot_enabled: boolean;
  salesforce_enabled: boolean;
}

interface Integration {
  provider: string;
  status: string;
  connected_at: string | null;
}

const INTEGRATIONS = [
  {
    key: "slack",
    label: "Slack",
    desc: "Post a formatted digest to a channel after every meeting.",
    icon: "💬",
    settingKey: "slack_enabled" as const,
  },
  {
    key: "gmail",
    label: "Gmail",
    desc: "Email the meeting summary to all attendees.",
    icon: "✉️",
    settingKey: "gmail_enabled" as const,
  },
  {
    key: "linear",
    label: "Linear",
    desc: "Create issues for each action item automatically.",
    icon: "⚡",
    settingKey: "linear_enabled" as const,
  },
  {
    key: "jira",
    label: "Jira",
    desc: "Create Jira tasks from action items in project MM.",
    icon: "🎯",
    settingKey: "jira_enabled" as const,
  },
  {
    key: "hubspot",
    label: "HubSpot",
    desc: "Attach meeting notes to contact records.",
    icon: "🧡",
    settingKey: "hubspot_enabled" as const,
  },
  {
    key: "salesforce",
    label: "Salesforce",
    desc: "Create tasks in Salesforce for each action item.",
    icon: "☁️",
    settingKey: "salesforce_enabled" as const,
  },
] as const;

export default function SettingsPage() {
  const qc = useQueryClient();

  const { data: settings } = useQuery<IntegrationSettings>({
    queryKey: ["integration-settings"],
    queryFn: () => api.get("/integrations/settings"),
  });

  const { data: connections } = useQuery<Integration[]>({
    queryKey: ["integrations"],
    queryFn: () => api.get("/integrations"),
  });

  const { mutate: updateSettings } = useMutation({
    mutationFn: (patch: Partial<IntegrationSettings>) =>
      api.patch("/integrations/settings", patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integration-settings"] }),
  });

  const { mutate: connect } = useMutation({
    mutationFn: (provider: string) => api.post(`/integrations/${provider}/connect`, {}),
    onSuccess: (data: { auth_url?: string }) => {
      if (data?.auth_url) window.open(data.auth_url, "_blank");
      qc.invalidateQueries({ queryKey: ["integrations"] });
    },
  });

  const { mutate: disconnect } = useMutation({
    mutationFn: (provider: string) => api.post(`/integrations/${provider}/disconnect`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations"] }),
  });

  const connectedSet = new Set(
    (connections ?? []).filter((c) => c.status === "connected").map((c) => c.provider)
  );

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold text-neutral-900">Integrations</h1>
      <p className="text-sm text-neutral-500">
        Connect your tools. MeetingMind will push digests and action items after every meeting.
      </p>

      <div className="space-y-3">
        {INTEGRATIONS.map((intg) => {
          const connected = connectedSet.has(intg.key);
          const enabled = settings?.[intg.settingKey] ?? false;

          return (
            <div
              key={intg.key}
              className="bg-white border border-neutral-200 rounded p-4 flex items-center gap-4"
            >
              <span className="text-2xl w-8 text-center shrink-0">{intg.icon}</span>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-900">{intg.label}</p>
                <p className="text-xs text-neutral-400 mt-0.5">{intg.desc}</p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {/* Connect / Disconnect */}
                {connected ? (
                  <button
                    onClick={() => disconnect(intg.key)}
                    className="text-xs text-neutral-400 hover:text-red-600 transition-colors duration-fast"
                  >
                    Disconnect
                  </button>
                ) : (
                  <button
                    onClick={() => connect(intg.key)}
                    className="text-xs px-2.5 py-1 border border-neutral-200 rounded text-neutral-700 hover:bg-neutral-50 transition-colors duration-fast"
                  >
                    Connect
                  </button>
                )}

                {/* Enable/disable toggle — only active when connected */}
                <Toggle
                  checked={connected && enabled}
                  disabled={!connected}
                  onChange={(val) => updateSettings({ [intg.settingKey]: val })}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Slack channel config */}
      {connectedSet.has("slack") && settings?.slack_enabled && (
        <SlackChannelInput
          value={settings.slack_channel_id ?? ""}
          onSave={(v) => updateSettings({ slack_channel_id: v })}
        />
      )}
    </div>
  );
}

function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors duration-150",
        checked ? "bg-primary-500" : "bg-neutral-200",
        disabled && "opacity-40 cursor-not-allowed"
      )}
    >
      <span
        className={clsx(
          "inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform duration-150",
          checked ? "translate-x-4.5" : "translate-x-0.5"
        )}
      />
    </button>
  );
}

function SlackChannelInput({
  value,
  onSave,
}: {
  value: string;
  onSave: (v: string) => void;
}) {
  return (
    <div className="bg-white border border-neutral-200 rounded p-4 space-y-2">
      <label className="text-sm font-medium text-neutral-900">Slack channel</label>
      <p className="text-xs text-neutral-400">
        Enter the channel ID (e.g. <code className="font-mono">C012AB3CD</code>) where digests will be posted.
      </p>
      <div className="flex gap-2">
        <input
          defaultValue={value}
          placeholder="C012AB3CD"
          className="flex-1 border border-neutral-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          onBlur={(e) => onSave(e.target.value)}
        />
      </div>
    </div>
  );
}
