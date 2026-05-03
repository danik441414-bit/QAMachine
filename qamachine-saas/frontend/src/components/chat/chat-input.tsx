"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Link2, X, Loader2 } from "lucide-react";
import TextareaAutosize from "react-textarea-autosize";
import { cn, isValidUrl, normalizeUrl } from "@/lib/utils";

interface ChatInputProps {
  onSubmit: (task: string, targetUrl: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSubmit,
  disabled = false,
  placeholder = "Describe what you want Machine to test…",
}: ChatInputProps) {
  const [task, setTask]         = useState("");
  const [url, setUrl]           = useState("");
  const [showUrl, setShowUrl]   = useState(false);
  const [urlError, setUrlError] = useState("");
  const [sending, setSending]   = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled) textareaRef.current?.focus();
  }, [disabled]);

  function handleUrlChange(v: string) {
    setUrl(v);
    setUrlError("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  async function handleSubmit() {
    const taskTrimmed = task.trim();
    if (!taskTrimmed || sending || disabled) return;

    // Validate URL if provided
    let finalUrl = url.trim();
    if (finalUrl) {
      finalUrl = normalizeUrl(finalUrl);
      if (!isValidUrl(finalUrl)) {
        setUrlError("Enter a valid URL (https://…)");
        return;
      }
    }

    setSending(true);
    try {
      await onSubmit(taskTrimmed, finalUrl);
      setTask("");
      setUrl("");
      setShowUrl(false);
    } finally {
      setSending(false);
    }
  }

  const canSubmit = task.trim().length > 0 && !sending && !disabled;

  return (
    <div className="px-4 pb-4 pt-2">
      <div
        className={cn(
          "rounded-xl border transition-all duration-150",
          "bg-bg-surface",
          showUrl || task.length > 0
            ? "border-border-focus shadow-glow-sm"
            : "border-border hover:border-border-focus"
        )}
      >
        {/* URL bar */}
        {showUrl && (
          <div className="flex items-center gap-2 px-3 pt-3 pb-0">
            <Link2 className="h-3.5 w-3.5 text-text-muted shrink-0" />
            <input
              type="url"
              value={url}
              onChange={(e) => handleUrlChange(e.target.value)}
              placeholder="https://example.com"
              className={cn(
                "flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-placeholder",
                "outline-none border-none focus:outline-none",
                urlError && "text-error"
              )}
              disabled={sending || disabled}
            />
            {url && (
              <button
                onClick={() => { setUrl(""); setUrlError(""); }}
                className="text-text-muted hover:text-text-secondary transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
        {urlError && (
          <p className="px-4 pt-1 text-xs text-error">{urlError}</p>
        )}

        {/* Textarea */}
        <TextareaAutosize
          ref={textareaRef}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={sending || disabled}
          minRows={3}
          maxRows={10}
          className={cn(
            "w-full resize-none bg-transparent px-3 py-3",
            "text-sm text-text-primary placeholder:text-text-placeholder",
            "outline-none border-none focus:outline-none",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            showUrl ? "pt-2" : "pt-3"
          )}
        />

        {/* Toolbar */}
        <div className="flex items-center justify-between px-3 pb-3">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setShowUrl((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-xs font-medium",
                "transition-colors duration-150",
                showUrl
                  ? "bg-accent-bg text-accent border border-accent/30"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-elevated"
              )}
              title="Add target URL"
            >
              <Link2 className="h-3.5 w-3.5" />
              {showUrl ? "URL added" : "Add URL"}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-2xs text-text-muted">
              {task.length > 0 ? `${task.length} chars` : "Shift+Enter for newline"}
            </span>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className={cn(
                "h-8 w-8 rounded-lg flex items-center justify-center",
                "transition-all duration-150",
                canSubmit
                  ? "bg-accent hover:bg-accent-hover text-white shadow-glow-sm"
                  : "bg-bg-elevated text-text-muted cursor-not-allowed"
              )}
              title="Send (Enter)"
            >
              {sending
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <Send className="h-3.5 w-3.5" />
              }
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
