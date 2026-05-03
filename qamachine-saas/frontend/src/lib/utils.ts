import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format, isToday, isYesterday } from "date-fns";
import type { RunStatus, PlanType } from "@/types";

// ── Classname utility ─────────────────────────────────────────────────────────

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Date formatting ───────────────────────────────────────────────────────────

export function formatDate(date: string | Date): string {
  const d = new Date(date);
  if (isToday(d)) return `Today at ${format(d, "HH:mm")}`;
  if (isYesterday(d)) return `Yesterday at ${format(d, "HH:mm")}`;
  return format(d, "MMM d, HH:mm");
}

export function formatDateShort(date: string | Date): string {
  const d = new Date(date);
  if (isToday(d)) return format(d, "HH:mm");
  if (isYesterday(d)) return "Yesterday";
  return format(d, "MMM d");
}

export function formatRelative(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function formatFullDate(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = new Date(date);
  if (isNaN(d.getTime())) return "—";
  return format(d, "MMMM d, yyyy");
}

// ── Run status ────────────────────────────────────────────────────────────────

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

export const RUN_STATUS_COLORS: Record<RunStatus, string> = {
  queued:    "text-text-secondary bg-bg-elevated border-border",
  running:   "text-accent bg-accent-bg border-accent/30",
  completed: "text-success bg-success-bg border-success/30",
  failed:    "text-error bg-error-bg border-error/30",
};

// ── Plan ──────────────────────────────────────────────────────────────────────

export const PLAN_LABELS: Record<PlanType, string> = {
  free:       "Free",
  pro:        "Pro",
  team:       "Team",
  enterprise: "Enterprise",
};

export const PLAN_COLORS: Record<PlanType, string> = {
  free:       "text-text-secondary",
  pro:        "text-accent",
  team:       "text-success",
  enterprise: "text-warning",
};

// ── Truncate ──────────────────────────────────────────────────────────────────

export function truncate(str: string, n: number): string {
  if (str.length <= n) return str;
  return str.slice(0, n - 3) + "...";
}

// ── Initials ──────────────────────────────────────────────────────────────────

export function getInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

// ── File size ─────────────────────────────────────────────────────────────────

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── URL validation ────────────────────────────────────────────────────────────

export function isValidUrl(url: string): boolean {
  try {
    const u = new URL(url.startsWith("http") ? url : `https://${url}`);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export function normalizeUrl(url: string): string {
  if (!url) return "";
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    return `https://${url}`;
  }
  return url;
}
