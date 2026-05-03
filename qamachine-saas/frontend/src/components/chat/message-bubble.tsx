"use client";

import { Zap } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import type { Message } from "@/types";
import { RunResult } from "./run-result";
import type { Run } from "@/types";

interface MessageBubbleProps {
  message: Message;
  run?: Run;
}

export function MessageBubble({ message, run }: MessageBubbleProps) {
  const isUser      = message.role === "user";
  const isAssistant = message.role === "assistant";

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[75%]">
          <div
            className="px-4 py-3 rounded-2xl rounded-tr-sm bg-accent/15 border border-accent/20
                       text-text-primary text-sm leading-relaxed whitespace-pre-wrap"
          >
            {message.content}
          </div>
          <p className="text-2xs text-text-muted text-right mt-1 pr-1">
            {formatDate(message.createdAt)}
          </p>
        </div>
      </div>
    );
  }

  // Conversational assistant message (streaming AI responses)
  if (isAssistant) {
    return (
      <div className="flex gap-3 animate-fade-in">
        <div className="h-7 w-7 rounded-lg bg-purple-500/80 flex items-center justify-center
                        shrink-0 mt-0.5 text-white text-xs font-bold">
          AI
        </div>
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-purple-400">QAmachine AI</span>
            {message.createdAt && (
              <span className="text-2xs text-text-muted">{formatDate(message.createdAt)}</span>
            )}
          </div>
          {message.content ? (
            <div
              className="text-sm text-text-primary/90 leading-relaxed prose-machine max-w-none"
              dangerouslySetInnerHTML={{ __html: renderContent(message.content) }}
            />
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse [animation-delay:0.2s]" />
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse [animation-delay:0.4s]" />
            </div>
          )}
        </div>
      </div>
    );
  }

  // Machine (run result) message
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center
                      shrink-0 shadow-glow-sm mt-0.5">
        <Zap className="h-3.5 w-3.5 text-white" />
      </div>

      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-accent">Machine</span>
          <span className="text-2xs text-text-muted">{formatDate(message.createdAt)}</span>
        </div>

        {message.content && (
          <div
            className="text-sm text-text-primary/90 leading-relaxed prose-machine max-w-none"
            dangerouslySetInnerHTML={{ __html: renderContent(message.content) }}
          />
        )}

        {run && <RunResult run={run} />}
      </div>
    </div>
  );
}

function escHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function applyInline(s: string): string {
  return escHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code class="bg-white/10 px-1 rounded text-xs font-mono">$1</code>');
}

function renderContent(text: string): string {
  const lines = text.split("\n");
  const out: string[] = [];
  let inUl = false;
  let inOl = false;

  function closeList() {
    if (inUl) { out.push("</ul>"); inUl = false; }
    if (inOl) { out.push("</ol>"); inOl = false; }
  }

  for (const line of lines) {
    const h3 = line.match(/^### (.+)/);
    if (h3) { closeList(); out.push(`<p class="font-semibold text-text-primary mt-2 mb-0.5">${applyInline(h3[1])}</p>`); continue; }

    const h2 = line.match(/^## (.+)/);
    if (h2) { closeList(); out.push(`<p class="font-bold text-text-primary mt-3 mb-1 text-sm">${applyInline(h2[1])}</p>`); continue; }

    const h1 = line.match(/^# (.+)/);
    if (h1) { closeList(); out.push(`<p class="font-bold text-text-primary mt-3 mb-1">${applyInline(h1[1])}</p>`); continue; }

    const ulItem = line.match(/^[*-] (.+)/);
    if (ulItem) {
      if (inOl) { out.push("</ol>"); inOl = false; }
      if (!inUl) { out.push('<ul class="list-disc pl-4 space-y-0.5 my-1">'); inUl = true; }
      out.push(`<li>${applyInline(ulItem[1])}</li>`);
      continue;
    }

    const olItem = line.match(/^(\d+)\. (.+)/);
    if (olItem) {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (!inOl) { out.push('<ol class="list-decimal pl-4 space-y-0.5 my-1">'); inOl = true; }
      out.push(`<li>${applyInline(olItem[2])}</li>`);
      continue;
    }

    if (line.trim() === "") { closeList(); out.push("<br/>"); continue; }

    closeList();
    out.push(`<span class="block">${applyInline(line)}</span>`);
  }

  closeList();
  return out.join("");
}

// ── Typing indicator ──────────────────────────────────────────────────────────

export function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      {/* Glowing animated avatar */}
      <div className="relative h-7 w-7 shrink-0 mt-0.5">
        <div className="absolute inset-0 rounded-lg bg-accent/40 animate-ping" />
        <div className="relative h-7 w-7 rounded-lg bg-accent flex items-center justify-center shadow-glow-sm">
          <Zap className="h-3.5 w-3.5 text-white" />
        </div>
      </div>

      <div className="flex flex-col justify-center gap-1">
        <span className="text-xs font-semibold text-accent">Machine</span>
        <div className="flex items-baseline gap-0">
          <span
            className="text-sm text-text-secondary"
            style={{ animation: "pulse 2s ease-in-out infinite" }}
          >
            running
          </span>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="text-sm text-accent font-bold"
              style={{ animation: `blink 1.2s step-end infinite ${i * 0.3}s` }}
            >
              .
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
