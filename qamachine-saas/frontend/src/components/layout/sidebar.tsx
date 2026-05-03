"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  MessageSquare, Plus, User, CreditCard,
  Settings, LogOut, Zap, Home, GraduationCap, BarChart3,
} from "lucide-react";
import { cn, getInitials, PLAN_COLORS, PLAN_LABELS } from "@/lib/utils";
import { useLang } from "@/context/language-context";
import type { User as UserType } from "@/types";

interface SidebarProps {
  user: UserType | null;
  onClose?: () => void;
  className?: string;
}

export function Sidebar({ user, onClose, className }: SidebarProps) {
  const pathname = usePathname();
  const router   = useRouter();
  const { t }    = useLang();
  const n        = t.nav;

  const ADMIN_EMAILS = ["danik441414@gmail.com"];
  const isAdmin = user?.email ? ADMIN_EMAILS.includes(user.email) : false;

  const NAV_ITEMS = [
    { href: "/dashboard", label: n.home,     icon: Home,           exact: true  },
    { href: "/chats",     label: n.chats,    icon: MessageSquare,  exact: false },
    { href: "/learn",     label: n.learn,    icon: GraduationCap,  exact: false },
    { href: "/profile",   label: n.profile,  icon: User,           exact: true  },
    { href: "/billing",   label: n.billing,  icon: CreditCard,     exact: true  },
    { href: "/settings",  label: n.settings, icon: Settings,       exact: true  },
    ...(isAdmin ? [{ href: "/admin", label: "Analytics", icon: BarChart3, exact: false }] : []),
  ];

  function isActive(item: typeof NAV_ITEMS[number]) {
    if (item.exact) return pathname === item.href;
    return pathname.startsWith(item.href);
  }

  function handleLogout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
    }
    router.push("/login");
  }

  return (
    <aside className={cn(
      "flex flex-col w-60 bg-bg-surface border-r border-border shrink-0",
      className,
    )}>

      {/* ── Logo ──────────────────────────────────────────────────── */}
      <div className="px-5 h-14 flex items-center gap-2 border-b border-border shrink-0">
        <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center shadow-glow-sm">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-text-primary tracking-tight">
          QAMachine
        </span>
      </div>

      {/* ── New Chat ──────────────────────────────────────────────── */}
      <div className="px-3 pt-4 pb-2">
        <Link
          href="/chats/new"
          onClick={onClose}
          className={cn(
            "flex items-center gap-2.5 w-full h-9 px-3 rounded-lg",
            "bg-accent/10 hover:bg-accent/20 border border-accent/20 hover:border-accent/40",
            "text-accent text-sm font-medium transition-all duration-150",
            "group"
          )}
        >
          <Plus className="h-4 w-4 shrink-0 transition-transform group-hover:rotate-90 duration-200" />
          {n.newChat}
        </Link>
      </div>

      {/* ── Nav ───────────────────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto no-scrollbar">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn(
                "flex items-center gap-2.5 h-9 px-3 rounded-lg text-sm transition-all duration-150",
                active
                  ? "bg-accent-bg text-accent border border-accent/20"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-accent" : "text-text-muted"
                )}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* ── User footer ───────────────────────────────────────────── */}
      {user && (
        <div className="px-3 pb-4 pt-2 border-t border-border mt-auto">
          <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg
                          hover:bg-bg-elevated transition-colors cursor-default group">
            <div
              className="h-7 w-7 rounded-full bg-accent-muted flex items-center justify-center
                         shrink-0 text-accent text-xs font-semibold"
            >
              {getInitials(user.name, user.email)}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-text-primary truncate">
                {user.name ?? user.email}
              </p>
              <p className={cn("text-2xs font-medium", PLAN_COLORS[user.plan])}>
                {PLAN_LABELS[user.plan]}
              </p>
            </div>

            <button
              onClick={handleLogout}
              title={n.logOut}
              className="text-text-muted hover:text-error transition-colors opacity-0
                         group-hover:opacity-100 shrink-0"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
