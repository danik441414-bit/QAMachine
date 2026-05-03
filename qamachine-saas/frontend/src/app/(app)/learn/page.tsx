"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { GraduationCap, Send, RefreshCw, Lock, Loader2, User, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { tutorApi, type TutorMessage, type TutorUsage } from "@/lib/api";
import { useLang } from "@/context/language-context";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export default function LearnPage() {
  const { t } = useLang();
  const l     = t.learn as LearnTranslation;

  const [messages,  setMessages]  = useState<DisplayMessage[]>([]);
  const [input,     setInput]     = useState("");
  const [streaming, setStreaming] = useState(false);
  const [usage,     setUsage]     = useState<TutorUsage | null>(null);
  const bottomRef   = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const stopRef     = useRef<(() => void) | null>(null);

  useEffect(() => {
    tutorApi.getUsage().then(setUsage).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const limitReached = usage?.isLimited && usage.remaining <= 0;

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || streaming || limitReached) return;

    const userMsg: DisplayMessage = { role: "user", content: text.trim() };
    const history: TutorMessage[] = [
      ...messages.map((m) => ({ role: m.role, content: m.content })),
      { role: "user", content: text.trim() },
    ];

    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "", streaming: true }]);
    setInput("");
    setStreaming(true);

    const stop = tutorApi.streamChat(
      history,
      (chunk) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last    = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: last.content + chunk };
          }
          return updated;
        });
      },
      (newUsage) => {
        setUsage((prev) => prev
          ? { ...prev, tutorCredits: newUsage.tutorCredits, tutorCap: newUsage.tutorCap, remaining: newUsage.remaining }
          : null
        );
        setMessages((prev) => {
          const updated = [...prev];
          const last    = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, streaming: false };
          }
          return updated;
        });
        setStreaming(false);
        stopRef.current = null;
        setTimeout(() => textareaRef.current?.focus(), 50);
      },
      (errMsg) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last    = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = {
              ...last, content: `_Error: ${errMsg}_`, streaming: false,
            };
          }
          return updated;
        });
        setStreaming(false);
        stopRef.current = null;
      },
    );
    stopRef.current = stop;
  }, [messages, streaming, limitReached]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleTopicClick(prompt: string) {
    if (messages.length === 0) {
      sendMessage(prompt);
    } else {
      setInput(prompt);
      textareaRef.current?.focus();
    }
  }

  function handleNewChat() {
    stopRef.current?.();
    setMessages([]);
    setInput("");
    setStreaming(false);
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">

      {/* ── Left panel — topics ──────────────────────────────────────── */}
      <aside className="w-56 shrink-0 border-r border-border flex flex-col bg-bg-surface overflow-y-auto no-scrollbar">
        <div className="px-4 pt-5 pb-3">
          <div className="flex items-center gap-2 mb-1">
            <GraduationCap className="h-4 w-4 text-accent" />
            <span className="text-sm font-semibold text-text-primary">{l.topicsTitle}</span>
          </div>
        </div>

        <div className="px-3 pb-3 space-y-1 flex-1">
          {l.topics.map((topic) => (
            <button
              key={topic.label}
              onClick={() => handleTopicClick(topic.prompt)}
              className="w-full text-left px-3 py-2 rounded-lg text-xs text-text-secondary
                         hover:bg-bg-elevated hover:text-text-primary transition-all"
            >
              {topic.label}
            </button>
          ))}
        </div>

        <div className="px-3 pb-4 border-t border-border pt-3">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs
                       text-text-muted hover:text-text-secondary hover:bg-bg-elevated transition-all"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {l.newChat}
          </button>
        </div>
      </aside>

      {/* ── Main chat ────────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Header */}
        <div className="px-6 py-3 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center shadow-glow-sm">
              <GraduationCap className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">{l.title}</h2>
              <p className="text-xs text-text-secondary">{l.subtitle}</p>
            </div>
          </div>

          {/* Usage badge — only for free */}
          {usage?.isLimited && (
            <div className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs",
              usage.remaining <= 5
                ? "bg-error/10 text-error border border-error/20"
                : "bg-bg-elevated text-text-muted border border-border"
            )}>
              {usage.remaining <= 0
                ? <Lock className="h-3 w-3" />
                : <Sparkles className="h-3 w-3" />
              }
              <span>
                {usage.remaining > 0
                  ? `${usage.remaining} ${l.limitWarning}`
                  : l.limitReached
                }
              </span>
              {usage.remaining <= 0 && (
                <a href="/billing" className="text-accent hover:underline ml-1">
                  {l.upgradeLink}
                </a>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {!hasMessages ? (
            <EmptyState l={l} onTopicClick={handleTopicClick} />
          ) : (
            <div className="px-6 py-6 space-y-6 max-w-3xl mx-auto w-full">
              {messages.map((msg, i) => (
                <MessageRow key={i} msg={msg} />
              ))}
              {streaming && messages[messages.length - 1]?.role !== "assistant" && (
                <ThinkingIndicator label={l.thinking} />
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border px-6 pb-5 pt-3 shrink-0">
          {limitReached ? (
            <div className="flex items-center justify-between px-4 py-3 rounded-xl
                            bg-error/5 border border-error/20">
              <span className="text-sm text-text-secondary">{l.limitReached}</span>
              <a href="/billing"
                 className="text-sm font-medium text-accent hover:underline shrink-0 ml-4">
                {l.upgradeLink}
              </a>
            </div>
          ) : (
            <div className={cn(
              "flex gap-3 items-end rounded-xl border transition-all",
              "bg-bg-surface",
              input.length > 0 || streaming
                ? "border-border-focus shadow-glow-sm"
                : "border-border hover:border-border-focus"
            )}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={l.placeholder}
                disabled={streaming}
                rows={1}
                style={{ resize: "none", overflow: "hidden" }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = Math.min(el.scrollHeight, 160) + "px";
                }}
                className={cn(
                  "flex-1 bg-transparent px-4 py-3 text-sm text-text-primary",
                  "placeholder:text-text-placeholder outline-none border-none focus:outline-none",
                  "disabled:opacity-50"
                )}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || streaming}
                className={cn(
                  "h-8 w-8 rounded-lg flex items-center justify-center m-2 shrink-0 transition-all",
                  input.trim() && !streaming
                    ? "bg-accent hover:bg-accent-hover text-white shadow-glow-sm"
                    : "bg-bg-elevated text-text-muted cursor-not-allowed"
                )}
              >
                {streaming
                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : <Send className="h-3.5 w-3.5" />
                }
              </button>
            </div>
          )}
          <p className="text-xs text-text-muted mt-2 text-center">
            Shift+Enter for newline · Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MessageRow({ msg }: { msg: DisplayMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3 animate-fade-in", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div className={cn(
        "h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
        isUser ? "bg-bg-elevated border border-border" : "bg-accent shadow-glow-sm"
      )}>
        {isUser
          ? <User className="h-3.5 w-3.5 text-text-muted" />
          : <GraduationCap className="h-3.5 w-3.5 text-white" />
        }
      </div>

      {/* Bubble */}
      <div className={cn(
        "max-w-[78%] rounded-xl px-4 py-3 text-sm leading-relaxed",
        isUser
          ? "bg-accent text-white rounded-tr-sm"
          : "bg-bg-elevated border border-border text-text-primary rounded-tl-sm"
      )}>
        {msg.streaming && !msg.content ? (
          <ThinkingDots />
        ) : (
          <MarkdownText text={msg.content} streaming={msg.streaming} />
        )}
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-accent/60"
          style={{ animation: `dotBounce 1.2s ease-in-out infinite ${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}

function ThinkingIndicator({ label }: { label: string }) {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center shadow-glow-sm shrink-0 mt-0.5">
        <GraduationCap className="h-3.5 w-3.5 text-white" />
      </div>
      <div className="bg-bg-elevated border border-border rounded-xl rounded-tl-sm px-4 py-3">
        <ThinkingDots />
      </div>
    </div>
  );
}

// Minimal markdown renderer: bold, inline code, code blocks, headings, lists
function MarkdownText({ text, streaming }: { text: string; streaming?: boolean }) {
  const segments = parseMarkdown(text);
  return (
    <div className="space-y-1">
      {segments.map((seg, i) => {
        if (seg.type === "code_block") {
          return (
            <pre key={i} className="bg-bg-surface border border-border rounded-lg px-3 py-2
                                    text-xs font-mono mt-2 mb-2 overflow-x-auto whitespace-pre-wrap">
              {seg.content}
            </pre>
          );
        }
        if (seg.type === "h2")  return <p key={i} className="font-bold text-text-primary mt-3 mb-1 text-base">{renderInline(seg.content)}</p>;
        if (seg.type === "h3")  return <p key={i} className="font-semibold text-text-primary mt-2 mb-1">{renderInline(seg.content)}</p>;
        if (seg.type === "li")  return <li key={i} className="ml-4 list-disc text-sm leading-relaxed">{renderInline(seg.content)}</li>;
        if (seg.type === "br")  return <div key={i} className="h-1" />;
        return <p key={i} className="text-sm leading-relaxed">{renderInline(seg.content)}</p>;
      })}
      {streaming && (
        <span className="inline-block w-1.5 h-4 bg-accent/80 animate-pulse align-middle rounded-sm" />
      )}
    </div>
  );
}

type Segment = { type: "code_block" | "h2" | "h3" | "li" | "br" | "p"; content: string };

function parseMarkdown(text: string): Segment[] {
  const segments: Segment[] = [];
  const lines = text.split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      segments.push({ type: "code_block", content: codeLines.join("\n") });
    } else if (line.startsWith("## ")) {
      segments.push({ type: "h2", content: line.slice(3) });
    } else if (line.startsWith("### ")) {
      segments.push({ type: "h3", content: line.slice(4) });
    } else if (line.startsWith("- ") || line.startsWith("• ")) {
      segments.push({ type: "li", content: line.slice(2) });
    } else if (line.trim() === "") {
      segments.push({ type: "br", content: "" });
    } else {
      segments.push({ type: "p", content: line });
    }
    i++;
  }
  return segments;
}

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /(\*\*(.+?)\*\*|`(.+?)`)/g;
  let last = 0, m: RegExpExecArray | null;
  let idx  = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(<span key={idx++}>{text.slice(last, m.index)}</span>);
    if (m[2]) parts.push(<strong key={idx++} className="font-semibold">{m[2]}</strong>);
    if (m[3]) parts.push(<code key={idx++} className="bg-bg-surface border border-border rounded px-1 py-0.5 text-xs font-mono text-accent">{m[3]}</code>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(<span key={idx++}>{text.slice(last)}</span>);
  return parts;
}

interface LearnTranslation {
  title: string; subtitle: string; placeholder: string; send: string;
  limitWarning: string; limitReached: string; upgradeLink: string;
  thinking: string; topicsTitle: string; newChat: string;
  topics: ReadonlyArray<{ label: string; prompt: string }>;
}

function EmptyState({ l, onTopicClick }: { l: LearnTranslation; onTopicClick: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 gap-6 text-center">
      <div className="h-16 w-16 rounded-2xl bg-accent/10 border border-accent/20
                      flex items-center justify-center">
        <GraduationCap className="h-8 w-8 text-accent" />
      </div>
      <div>
        <h3 className="text-lg font-bold text-text-primary mb-2">{l.title}</h3>
        <p className="text-sm text-text-secondary max-w-md leading-relaxed">{l.subtitle}</p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full max-w-2xl">
        {l.topics.slice(0, 8).map((topic) => (
          <button
            key={topic.label}
            onClick={() => onTopicClick(topic.prompt)}
            className="px-3 py-2.5 rounded-xl bg-bg-surface border border-border
                       text-xs text-text-secondary hover:border-border-focus hover:text-text-primary
                       transition-all text-left"
          >
            {topic.label}
          </button>
        ))}
      </div>
    </div>
  );
}
