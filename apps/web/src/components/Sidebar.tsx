"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { Calendar, CheckSquare, Home, Settings, Users } from "lucide-react";

const nav = [
  { href: "/meetings", label: "Meetings", icon: Calendar },
  { href: "/action-items", label: "Action Items", icon: CheckSquare },
  { href: "/team", label: "Team", icon: Users },
  { href: "/settings", label: "Integrations", icon: Settings },
  { href: "/settings/calendar", label: "Auto-Join", icon: Calendar },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar h-screen bg-neutral-800 flex flex-col shrink-0">
      <div className="px-4 py-5 border-b border-neutral-700">
        <span className="text-white font-semibold text-base tracking-tight">MeetingMind</span>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors duration-fast",
              pathname.startsWith(href)
                ? "bg-primary-600 text-white"
                : "text-neutral-300 hover:bg-neutral-700 hover:text-white"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-neutral-700">
        <p className="text-xs text-neutral-500">v0.1.0</p>
      </div>
    </aside>
  );
}
