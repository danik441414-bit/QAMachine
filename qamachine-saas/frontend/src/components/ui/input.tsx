"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, leftIcon, rightIcon, id, ...props }, ref) => {
    const inputId = id ?? React.useId();

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-text-secondary"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
              {leftIcon}
            </span>
          )}

          <input
            ref={ref}
            id={inputId}
            className={cn(
              "w-full h-10 rounded-lg bg-bg-surface border border-border",
              "px-3 text-sm text-text-primary placeholder:text-text-placeholder",
              "transition-colors duration-150 cursor-text",
              "hover:border-border-focus hover:bg-bg-elevated",
              "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
              "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-bg-surface disabled:hover:border-border",
              error && "border-error/60 focus:border-error focus:ring-error/20",
              leftIcon  && "pl-9",
              rightIcon && "pr-9",
              className
            )}
            {...props}
          />

          {rightIcon && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted">
              {rightIcon}
            </span>
          )}
        </div>

        {error && <p className="text-xs text-error">{error}</p>}
        {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";

// ── Textarea ──────────────────────────────────────────────────────────────────

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const textareaId = id ?? React.useId();

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={textareaId}
            className="text-sm font-medium text-text-secondary"
          >
            {label}
          </label>
        )}

        <textarea
          ref={ref}
          id={textareaId}
          className={cn(
            "w-full rounded-lg bg-bg-surface border border-border",
            "px-3 py-2.5 text-sm text-text-primary placeholder:text-text-placeholder",
            "transition-colors duration-150 resize-none",
            "hover:border-border-focus",
            "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            error && "border-error/60 focus:border-error focus:ring-error/20",
            className
          )}
          {...props}
        />

        {error && <p className="text-xs text-error">{error}</p>}
        {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
