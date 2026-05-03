"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size    = "sm" | "md" | "lg" | "icon";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  asChild?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-accent hover:bg-accent-hover text-white shadow-glow-sm border border-accent/50 " +
    "hover:shadow-glow active:scale-[0.98]",
  secondary:
    "bg-bg-elevated hover:bg-border text-text-primary border border-border " +
    "hover:border-border-focus active:scale-[0.98]",
  outline:
    "bg-transparent hover:bg-bg-elevated text-text-secondary hover:text-text-primary " +
    "border border-border hover:border-border-focus",
  ghost:
    "bg-transparent hover:bg-bg-elevated text-text-secondary hover:text-text-primary border-transparent",
  danger:
    "bg-error/10 hover:bg-error/20 text-error border border-error/30 hover:border-error/50 " +
    "active:scale-[0.98]",
};

const sizeClasses: Record<Size, string> = {
  sm:   "h-7 px-3 text-xs gap-1.5",
  md:   "h-9 px-4 text-sm gap-2",
  lg:   "h-11 px-5 text-sm gap-2",
  icon: "h-9 w-9 p-0",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base
          "inline-flex items-center justify-center font-medium rounded-lg",
          "transition-all duration-150 ease-out select-none",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
          // Variant
          variantClasses[variant],
          // Size
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {loading ? (
          <Spinner className={size === "icon" ? "h-4 w-4" : "h-3.5 w-3.5"} />
        ) : leftIcon ? (
          <span className="shrink-0">{leftIcon}</span>
        ) : null}

        {size !== "icon" && children && (
          <span className={loading ? "opacity-0" : ""}>{children}</span>
        )}
        {size === "icon" && !loading && children}

        {rightIcon && !loading && (
          <span className="shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

// ── Spinner ───────────────────────────────────────────────────────────────────

function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("animate-spin", className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12" cy="12" r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
