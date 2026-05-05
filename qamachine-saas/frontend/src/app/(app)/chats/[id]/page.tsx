"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Zap, Loader2 } from "lucide-react";
import { chatsApi, messagesApi, runsApi } from "@/lib/api";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatInput } from "@/components/chat/chat-input";
import type { Chat, Message, Run } from "@/types";

export default function ChatDetailPage() {
  const { id } = useParams<{ id: string }>();

  const [chat, setChat]         = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [runs, setRuns]         = useState<Record<string, Run>>({});
  const [isTyping, setIsTyping] = useState(false);
  const [loading, setLoading]   = useState(true);

  const bottomRef   = useRef<HTMLDivElement>(null);
  const activeEsRef = useRef<EventSource | null>(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Load chat + messages
  useEffect(() => {
    if (!id) return;
    Promise.all([
      chatsApi.get(id),
      messagesApi.list(id),
    ])
      .then(([chatData, msgs]) => {
        setChat(chatData);
        setMessages(msgs);

        // Show typing indicator immediately if chat is running
        if (chatData.status === "running") {
          setIsTyping(true);
        }

        // Subscribe to active run for completion events
        const activeMsg = [...msgs].reverse().find((m) => m.runId);
        if (activeMsg?.runId) {
          runsApi.get(activeMsg.runId).then((run) => {
            setRuns((prev) => ({ ...prev, [run.id]: run }));
            if (run.status === "queued" || run.status === "running") {
              subscribeToRun(run.id);
            } else {
              setIsTyping(false);
            }
          }).catch(() => {/* isTyping already set from chat.status above */});
        }
      })
      .catch(() => toast.error("Failed to load chat"))
      .finally(() => setLoading(false));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Subscribe to run status via SSE
  const subscribeToRun = useCallback((runId: string) => {
    activeEsRef.current?.close();

    const es = runsApi.streamStatus(runId, (updatedRun) => {
      setRuns((prev) => ({ ...prev, [runId]: updatedRun }));

      if (updatedRun.status === "completed" || updatedRun.status === "failed") {
        setIsTyping(false);
        es.close();
        activeEsRef.current = null;

        // Reload both messages and chat status
        Promise.all([
          messagesApi.list(id),
          chatsApi.get(id),
        ]).then(([msgs, chatData]) => {
          setMessages(msgs);
          setChat(chatData);
        }).catch(() => {
          // Fallback: show in-memory message if DB fetch fails
          const content =
            updatedRun.status === "completed"
              ? `Session completed. Found **${updatedRun.issueCount}** issue${updatedRun.issueCount !== 1 ? "s" : ""} across **${updatedRun.stepCount}** steps.`
              : `**Session failed.** An unexpected error stopped the session.\n\nWrite a new message below to try again.`;
          const machineMsg: Message = {
            id:        `machine_${runId}`,
            chatId:    id,
            role:      "machine",
            content,
            createdAt: new Date().toISOString(),
            runId,
          };
          setMessages((prev) => [...prev, machineMsg]);
          setChat((prev) => prev ? { ...prev, status: "idle" } : prev);
        });
      }
    });

    activeEsRef.current = es;
  }, [id]);

  useEffect(() => () => { activeEsRef.current?.close(); }, []);

  async function handleSend(task: string, targetUrl: string) {
    if (!id) return;

    const hasHistory = messages.length > 0;

    // ── First message → run mode with evaluation ─────────────────────────────
    if (!hasHistory) {
      if (chat?.status === "running") {
        toast.error("Machine is already running. Wait for the current session to finish.");
        return;
      }
      try {
        let finalTask = task;
        try {
          const evaluation = await chatsApi.evaluate(id, task, targetUrl);
          if (!evaluation.ready && evaluation.questions) {
            const aiMsgId = `ai_clarify_${Date.now()}`;
            setMessages((prev) => [
              ...prev,
              { id: `user_${Date.now()}`, chatId: id, role: "user", content: targetUrl ? `**URL:** ${targetUrl}\n\n${task}` : task, createdAt: new Date().toISOString(), runId: null },
              { id: aiMsgId, chatId: id, role: "assistant", content: evaluation.questions!, createdAt: new Date().toISOString(), runId: null },
            ]);
            return;
          }
          if (evaluation.improved_task) finalTask = evaluation.improved_task;
        } catch { /* proceed with original */ }

        const tempUserMsg: Message = {
          id: `temp_${Date.now()}`, chatId: id, role: "user",
          content: targetUrl ? `**URL:** ${targetUrl}\n\n${finalTask}` : finalTask,
          createdAt: new Date().toISOString(), runId: null,
        };
        setMessages((prev) => [...prev, tempUserMsg]);
        setIsTyping(true);
        const { run } = await messagesApi.send(id, { task: finalTask, targetUrl });
        setRuns((prev) => ({ ...prev, [run.id]: run }));
        subscribeToRun(run.id);
      } catch (err) {
        setIsTyping(false);
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
        const msg = typeof detail === "string" ? detail
          : Array.isArray(detail) ? (detail as Array<{ msg?: string }>)[0]?.msg ?? "Validation error"
          : "Failed to send task. Please try again.";
        toast.error(msg);
      }
      return;
    }

    // ── Follow-up → ALWAYS AI mode (AI decides whether to run a test) ────────
    const userContent = targetUrl ? `**URL:** ${targetUrl}\n\n${task}` : task;
    const userMsgId   = `user_${Date.now()}`;
    const aiMsgId     = `ai_${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, chatId: id, role: "user",      content: userContent, createdAt: new Date().toISOString(), runId: null },
      { id: aiMsgId,   chatId: id, role: "assistant", content: "",          createdAt: new Date().toISOString(), runId: null },
    ]);

    let fullAiText = "";

    chatsApi.assist(
      id,
      userContent,
      (text) => {
        fullAiText += text;
        setMessages((prev) =>
          prev.map((m) => m.id === aiMsgId ? { ...m, content: m.content + text } : m)
        );
      },
      () => {
        // Check if AI wants to launch a test
        const match = fullAiText.match(/\[RUN_TEST:\s*([^\|]+?)\s*\|\s*(.+?)\]/);
        if (match) {
          const runUrl  = match[1].trim();
          const runTask = match[2].trim();
          // Strip the marker from the displayed message
          setMessages((prev) => prev.map((m) =>
            m.id === aiMsgId
              ? { ...m, content: m.content.replace(/\[RUN_TEST:[^\]]+\]\s*/g, "") }
              : m
          ));
          // Launch test if not already running
          if (chat?.status !== "running") {
            setIsTyping(true);
            messagesApi.send(id, { task: runTask, targetUrl: runUrl })
              .then(({ run }) => {
                setRuns((prev) => ({ ...prev, [run.id]: run }));
                subscribeToRun(run.id);
              })
              .catch(() => {
                setIsTyping(false);
                toast.error("Failed to start test run");
              });
          }
        }
        messagesApi.list(id).then(setMessages).catch(() => {});
      },
      (err) => {
        toast.error(err);
        setMessages((prev) => prev.filter((m) => m.id !== aiMsgId));
      },
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-20 gap-2 text-text-muted">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">Loading chat…</span>
      </div>
    );
  }

  const hasMessages = messages.length > 0;

  // Find the currently active run for progress display
  const activeRun = Object.values(runs).find(
    (r) => r.status === "running" || r.status === "queued"
  ) ?? null;
  const progressPct = activeRun && activeRun.maxSteps > 0
    ? Math.min(Math.round((activeRun.stepCount / activeRun.maxSteps) * 100), 99)
    : 0;

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">

      {/* ── Chat header ─────────────────────────────────────────────── */}
      <div className="px-6 py-3 border-b border-border flex items-center gap-3">
        {/* Avatar — animated when running */}
        <div className="relative h-6 w-6 shrink-0">
          {chat?.status === "running" && (
            <div className="absolute inset-0 rounded-md bg-accent/40 animate-ping" />
          )}
          <div className="relative h-6 w-6 rounded-md bg-accent flex items-center justify-center
                          shadow-glow-sm">
            <Zap className="h-3.5 w-3.5 text-white" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <h2 className="text-sm font-semibold text-text-primary truncate">
            {chat?.title ?? "Chat"}
          </h2>
          {chat?.status === "running" && (
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs text-accent" style={{ animation: "pulse 2s ease-in-out infinite" }}>
                Machine is running
              </span>
              {progressPct > 0 && (
                <span className="text-xs text-accent font-semibold">— {progressPct}%</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Messages ────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full
                          text-center px-6 gap-4">
            <div className="h-14 w-14 rounded-2xl bg-bg-surface border border-border
                            flex items-center justify-center">
              <Zap className="h-7 w-7 text-text-muted" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-text-primary mb-2">
                Machine is ready
              </h3>
              <p className="text-sm text-text-secondary max-w-md leading-relaxed">
                Describe what you want to test. Paste a URL and write a task
                in plain language — Machine will handle the rest.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {EXAMPLE_TASKS.map((ex) => (
                <button
                  key={ex.task}
                  onClick={() => handleSend(ex.task, ex.url)}
                  className="text-left px-4 py-3 rounded-xl bg-bg-surface border border-border
                             hover:border-border-focus hover:bg-bg-elevated transition-all text-xs"
                >
                  <p className="font-medium text-text-secondary mb-0.5">{ex.label}</p>
                  <p className="text-text-muted leading-relaxed">{ex.task}</p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="px-6 py-6 space-y-6 max-w-4xl mx-auto w-full">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                run={msg.runId ? runs[msg.runId] : undefined}
              />
            ))}
            {isTyping && (
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-lg bg-bg-surface border border-border flex items-center justify-center shrink-0">
                  <Zap className="h-4 w-4 text-accent animate-pulse" />
                </div>
                <div className="bg-bg-surface border border-border rounded-xl px-4 py-3 min-w-[220px]">
                  {activeRun && activeRun.maxSteps > 0 ? (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-text-secondary">Testing in progress</span>
                        <span className="text-xs text-accent font-semibold">{progressPct}%</span>
                      </div>
                      <div className="h-1.5 bg-bg-elevated rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all duration-700 ease-out"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                      <div className="mt-1.5 text-xs text-text-muted">
                        Step {activeRun.stepCount} of {activeRun.maxSteps}
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        {[0, 1, 2].map((i) => (
                          <div
                            key={i}
                            className="h-1.5 w-1.5 rounded-full bg-accent animate-bounce"
                            style={{ animationDelay: `${i * 0.15}s` }}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-text-secondary">Initializing…</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ── Input ───────────────────────────────────────────────────── */}
      <div className="border-t border-border">
        <div className="max-w-4xl mx-auto w-full">
          <ChatInput
            onSubmit={handleSend}
            disabled={false}
            placeholder={
              chat?.status === "running"
                ? "Machine is running… Ask a question or wait for results"
                : hasMessages
                  ? "Ask about results, or add a URL to run a new test…"
                  : "Describe what you want Machine to test…"
            }
          />
        </div>
      </div>
    </div>
  );
}

const EXAMPLE_TASKS = [
  {
    label: "UI Audit",
    task:  "Audit the visual design — layout, spacing, contrast, overlapping elements",
    url:   "",
  },
  {
    label: "Functional Test",
    task:  "Test all forms, buttons and navigation flows on this site",
    url:   "",
  },
  {
    label: "Mobile Check",
    task:  "Check mobile UX on iPhone 12 — burger menu, touch targets, horizontal scroll",
    url:   "",
  },
  {
    label: "API Testing",
    task:  "Collect and test all API endpoints from network traffic",
    url:   "",
  },
];
