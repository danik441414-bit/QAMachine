import * as React from "react";
import { cn } from "@/lib/utils";
import type { RunStatus } from "@/types";

type BadgeVariant = "default" | "accent" | "success" | "warning" | "error" | "outline";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  dot?: boolean;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-bg-elevated text-text-secondary border-border",
  accent:  "bg-accent-bg text-accent-text border-accent/30",
  success: "bg-success-bg text-success-text border-success/30",
  warning: "bg-warning-bg text-warning-text border-warning/30",
  error:   "bg-error-bg text-error-text border-error/30",
  outline: "bg-transparent text-text-secondary border-border",
};

const dotClasses: Record<BadgeVariant, string> = {
  default: "bg-text-muted",
  accent:  "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  error:   "bg-error",
  outline: "bg-text-muted",
};

export function Badge({
  variant = "default",
  size = "md",
  dot = false,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-medium border rounded-full",
        size === "sm" ? "text-2xs px-2 py-0.5" : "text-xs px-2.5 py-1",
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn(
            "rounded-full shrink-0",
            size === "sm" ? "h-1 w-1" : "h-1.5 w-1.5",
            dotClasses[variant],
            variant === "accent" && "animate-pulse"
          )}
        />
      )}
      {children}
    </span>
  );
}

// ── RunStatusBadge ────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<RunStatus, BadgeVariant> = {
  queued:    "default",
  running:   "accent",
  completed: "success",
  failed:    "error",
};

const STATUS_LABELS: Record<RunStatus, string> = {
  queued:    "Queued",
  running:   "Running",
  completed: "Completed",
  failed:    "Failed",
};

export function RunStatusBadge({ status }: { status: RunStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]} dot>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
