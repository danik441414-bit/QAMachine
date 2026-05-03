"use client";

import { usePathname } from "next/navigation";
import { Bell, Menu } from "lucide-react";
import { useLang } from "@/context/language-context";

interface TopbarProps {
  onMenuClick?: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const pathname = usePathname();
  const { t }    = useLang();
  const n        = t.nav;

  function getTitle(path: string): string {
    if (path.startsWith("/chats/new")) return n.newChat;
    if (path.startsWith("/chats"))     return n.chats;
    if (path === "/dashboard")         return n.home;
    if (path === "/profile")           return n.profile;
    if (path === "/billing" || path.startsWith("/billing")) return n.billing;
    if (path === "/settings")          return n.settings;
    if (path === "/learn")             return n.learn;
    if (path === "/admin")             return "Analytics";
    return "";
  }

  return (
    <header className="h-14 flex items-center justify-between px-4 md:px-6
                        bg-bg-surface border-b border-border shrink-0">
      <div className="flex items-center gap-3">
        <button
          className="md:hidden h-9 w-9 rounded-lg flex items-center justify-center
                     text-text-muted hover:text-text-primary hover:bg-bg-elevated
                     transition-colors"
          onClick={onMenuClick}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <h1 className="text-sm font-semibold text-text-primary">{getTitle(pathname)}</h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="h-8 w-8 rounded-lg flex items-center justify-center
                     text-text-muted hover:text-text-primary hover:bg-bg-elevated
                     transition-colors"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
