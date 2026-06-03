"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { clsx } from "clsx";
import {
  Calendar,
  CheckSquare,
  Clock,
  Settings,
  Users,
} from "lucide-react";

const nav = [
  { href: "/meetings",          label: "Meetings",      icon: Calendar    },
  { href: "/action-items",      label: "Action Items",  icon: CheckSquare },
  { href: "/team",              label: "Team",          icon: Users       },
  { href: "/settings",          label: "Integrations",  icon: Settings    },
  { href: "/settings/calendar", label: "Auto-Join",     icon: Clock       },
];

function isActive(pathname: string, href: string) {
  if (href === "/settings") return pathname === "/settings";
  return pathname === href || pathname.startsWith(href + "/");
}

function Avatar({ name }: { name?: string | null }) {
  const initials = (name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  return (
    <span className="h-7 w-7 rounded-full bg-primary-500 text-white text-xs font-semibold flex items-center justify-center shrink-0">
      {initials}
    </span>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const user = session?.user;

  return (
    <aside className="w-[220px] shrink-0 h-screen bg-neutral-850 flex flex-col">
      {/* Brand */}
      <div className="h-12 px-4 flex items-center gap-2.5 border-b border-white/[0.06]">
        <div className="w-6 h-6 rounded-md bg-primary-500 flex items-center justify-center shrink-0">
          <Clock size={13} strokeWidth={2} className="text-white" />
        </div>
        <span className="text-white font-semibold text-sm tracking-tight">MeetingMind</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-2 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors duration-fast relative",
                "border-l-[3px]",
                active
                  ? "bg-primary-500/20 text-white font-medium border-l-primary-400"
                  : "text-neutral-300 hover:bg-white/[0.07] hover:text-white border-l-transparent"
              )}
            >
              <Icon size={15} strokeWidth={1.8} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="px-3 py-3 border-t border-white/[0.06] flex items-center gap-2.5 min-w-0">
        <Avatar name={user?.name} />
        <div className="min-w-0 flex-1">
          <p className="text-xs text-white font-medium truncate">{user?.name ?? "You"}</p>
          <p className="text-[10px] text-neutral-400 truncate">{user?.email ?? ""}</p>
        </div>
      </div>
    </aside>
  );
}
