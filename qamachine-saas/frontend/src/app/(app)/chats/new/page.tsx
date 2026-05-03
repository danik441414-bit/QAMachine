"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Zap, ArrowRight, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, isValidUrl, normalizeUrl } from "@/lib/utils";
import { chatsApi, messagesApi, authApi } from "@/lib/api";
import { useLang } from "@/context/language-context";

// Mode labels are technical QA terms — always in English
const MODES = [
  { id: "functional",       label: "Functional",  desc: "Forms, flows, CRUD, auth",  free: true  },
  { id: "ui_ux",            label: "UI/UX Audit", desc: "Visual, layout, design",    free: true  },
  { id: "mobile",           label: "Mobile",      desc: "Device emulation",           free: false },
  { id: "regression",       label: "Regression",  desc: "After code changes",         free: false },
  { id: "network",          label: "Network",     desc: "HTTP errors, 4xx/5xx",       free: false },
  { id: "api",              label: "API",         desc: "Endpoints health",           free: false },
  { id: "load_performance", label: "Performance", desc: "Load times, Web Vitals",     free: false },
  { id: "all_flows",        label: "All Flows",   desc: "Full site coverage",         free: false },
];

function generateChatTitle(task: string, modeId: string): string {
  const mode = MODES.find((m) => m.id === modeId);

  // Drop credential lines (Username/Password/Логин etc.)
  const coreLines = task.split("\n").filter((line) => {
    const l = line.trim().toLowerCase();
    return l && !/^(username|password|логин|пароль|login|user|pass)[\s:=]/i.test(l);
  });
  // Strip [Mode] prefix and trim
  const clean = coreLines.join(" ").replace(/^\[.*?\]\s*/, "").trim();

  if (!clean) return mode ? `${mode.label} check` : "QA session";

  // Russian imperative → noun
  const verbToNoun: Record<string, string> = {
    "проверь":     "Проверка",
    "проверьте":   "Проверка",
    "проверить":   "Проверка",
    "протестируй": "Тестирование",
    "протестируйте":"Тестирование",
    "найди":       "Поиск",
    "найдите":     "Поиск",
    "запусти":     "Запуск",
    "сделай":      "Проверка",
    "check":       "Check",
    "test":        "Test",
    "audit":       "Audit",
    "find":        "Search",
    "run":         "Run",
  };

  // Stop words to drop
  const stop = new Set([
    "и","все","что","нету","ли","на","в","с","по","для","а","или","не",
    "как","бы","же","там","тут","это","вот","есть","нет","да","нет",
    "the","all","and","for","any","or","a","an","of","in","on","at","to",
  ]);

  const words = clean.split(/\s+/).filter(Boolean);
  const firstLower = words[0]?.toLowerCase() ?? "";

  // Transform first word
  if (verbToNoun[firstLower]) {
    words[0] = verbToNoun[firstLower];
  } else {
    words[0] = words[0].charAt(0).toUpperCase() + words[0].slice(1);
  }

  // Keep first word always, filter stop words from the rest, take max 3 words total
  const result = [
    words[0],
    ...words.slice(1).filter((w) => !stop.has(w.toLowerCase())),
  ].slice(0, 3);

  return result.join(" ") || (mode ? `${mode.label} check` : "QA session");
}

const EXAMPLES = [
  "Test all forms and check for validation errors",
  "Audit the visual design and layout",
  "Check mobile UX on iPhone 12",
  "Test the checkout flow end-to-end",
  "Run a regression test — cart was recently changed",
  "Find all network errors and 4xx responses",
];

export default function NewChatPage() {
  return (
    <Suspense>
      <NewChatForm />
    </Suspense>
  );
}

function NewChatForm() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const initialMode  = searchParams.get("mode") ?? "";
  const { t }        = useLang();
  const nc           = t.newChat;

  const [url, setUrl]         = useState("");
  const [task, setTask]       = useState("");
  const [mode, setMode]       = useState(initialMode);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors]   = useState<{ url?: string; task?: string }>({});
  const [userPlan, setUserPlan] = useState<string>("free");

  useEffect(() => {
    authApi.me().then((u) => setUserPlan(u.plan)).catch(() => {});
  }, []);

  const isFree = userPlan === "free";

  function buildTask(): string {
    const selectedMode = MODES.find((m) => m.id === mode);
    if (!selectedMode || !task.trim()) return task.trim();
    return `[${selectedMode.label}] ${task.trim()}`;
  }

  function validate(): boolean {
    const e: typeof errors = {};
    if (!url.trim()) e.url = nc.urlRequired;
    else if (!isValidUrl(normalizeUrl(url.trim()))) e.url = nc.urlInvalid;
    if (!task.trim()) e.task = nc.taskRequired;
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleStart() {
    if (!validate() || loading) return;

    setLoading(true);
    try {
      const targetUrl = normalizeUrl(url.trim());
      const finalTask = buildTask();

      const chat = await chatsApi.create(generateChatTitle(task, mode));
      await messagesApi.send(chat.id, { task: finalTask, targetUrl });

      router.push(`/chats/${chat.id}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? t.common.error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto animate-slide-up">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 mb-8">
        <div className="h-9 w-9 rounded-xl bg-accent flex items-center justify-center shadow-glow">
          <Zap className="h-5 w-5 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-text-primary">{nc.title}</h2>
          <p className="text-sm text-text-secondary">{nc.subtitle}</p>
        </div>
      </div>

      {/* ── Form ───────────────────────────────────────────────────── */}
      <div className="space-y-6">

        {/* URL */}
        <Input
          label={nc.urlLabel}
          type="url"
          placeholder={nc.urlPlaceholder}
          value={url}
          onChange={(e) => { setUrl(e.target.value); setErrors((p) => ({ ...p, url: undefined })); }}
          error={errors.url}
          hint={nc.urlHint}
          autoFocus
        />

        {/* Mode selector */}
        <div>
          <label className="text-sm font-medium text-text-secondary mb-2 block">
            {nc.modeLabel}{" "}
            <span className="text-text-muted font-normal">{nc.modeOptional}</span>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {MODES.map((m) => {
              const locked = isFree && !m.free;
              return (
                <button
                  key={m.id}
                  onClick={() => {
                    if (locked) {
                      toast.error("Upgrade to Pro to unlock all testing modes");
                      return;
                    }
                    setMode(mode === m.id ? "" : m.id);
                  }}
                  className={cn(
                    "px-3 py-2.5 rounded-lg text-left text-xs transition-all border relative",
                    locked
                      ? "bg-bg-elevated border-border text-text-muted opacity-60 cursor-not-allowed"
                      : mode === m.id
                        ? "bg-accent/15 border-accent text-accent ring-1 ring-accent/30 shadow-glow-sm"
                        : "bg-bg-surface border-border text-text-secondary hover:border-border-focus"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-sm">{m.label}</p>
                    {locked && <Lock className="h-3 w-3 text-text-muted shrink-0" />}
                  </div>
                  <p className="text-text-muted mt-0.5">{m.desc}</p>
                </button>
              );
            })}
          </div>
          {isFree && (
            <p className="text-xs text-text-muted mt-1.5">
              🔒 Free plan: Functional & UI/UX only.{" "}
              <a href="/billing" className="text-accent hover:underline">Upgrade to Pro</a>
              {" "}to unlock all 8 modes.
            </p>
          )}
        </div>

        {/* Task description */}
        <div>
          <label className="text-sm font-medium text-text-secondary mb-2 block">
            {nc.taskLabel}
          </label>
          <textarea
            placeholder={nc.taskPlaceholder}
            value={task}
            onChange={(e) => { setTask(e.target.value); setErrors((p) => ({ ...p, task: undefined })); }}
            rows={4}
            className={cn(
              "w-full rounded-lg bg-bg-surface border px-3 py-2.5",
              "text-sm text-text-primary placeholder:text-text-placeholder",
              "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
              "transition-colors resize-none",
              errors.task ? "border-error/60" : "border-border hover:border-border-focus"
            )}
          />
          {errors.task && <p className="text-xs text-error mt-1">{errors.task}</p>}
          <p className="text-xs text-text-muted mt-1.5">{nc.taskHint}</p>
        </div>

        {/* Example prompts */}
        <div>
          <p className="text-xs font-medium text-text-muted mb-2">{nc.examples}</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setTask(ex)}
                className="text-xs px-2.5 py-1 rounded-full bg-bg-surface border border-border
                           text-text-muted hover:text-text-secondary hover:border-border-focus
                           transition-all"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end pt-2">
          <Button
            size="lg"
            loading={loading}
            onClick={handleStart}
            rightIcon={!loading ? <ArrowRight className="h-4 w-4" /> : undefined}
          >
            {nc.startSession}
          </Button>
        </div>
      </div>
    </div>
  );
}
