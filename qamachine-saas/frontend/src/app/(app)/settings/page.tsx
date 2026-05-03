"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Lock, Bell, Code2, ChevronRight, Globe } from "lucide-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { userApi, authApi } from "@/lib/api";
import { useLang } from "@/context/language-context";
import type { Lang } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { User } from "@/types";

export default function SettingsPage() {
  const { t } = useLang();
  const s = t.settings;
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    authApi.me().then(setUser).catch(() => {});
  }, []);

  const isPaid = user?.plan === "pro" || user?.plan === "team";

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-5 animate-fade-in">

      {/* ── Language ────────────────────────────────────────────────── */}
      <LanguageSection />

      {/* ── Password ─────────────────────────────────────────────────── */}
      <PasswordSection />

      {/* ── Notifications ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-text-muted" />
            {s.notifications}
          </CardTitle>
          <span className="text-xs text-text-muted bg-bg-elevated px-2 py-0.5 rounded-full border border-border">
            {s.comingSoon}
          </span>
        </CardHeader>

        <p className="text-sm text-text-secondary py-4 text-center">
          Email and in-app notifications will be available in a future update.
        </p>
      </Card>

      {/* ── API Keys ─────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-text-muted" />
            {s.apiAccess}
          </CardTitle>
          <span className="text-xs text-text-muted bg-bg-elevated px-2 py-0.5 rounded-full border border-border">
            {isPaid ? s.comingSoon : s.proPlus}
          </span>
        </CardHeader>

        {isPaid ? (
          <div className="py-8 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-text-secondary">
              API key management is coming soon. You&apos;ll be able to generate keys to integrate QAmachine into your CI/CD pipeline.
            </p>
            <Button size="sm" variant="outline" disabled>{s.comingSoon}</Button>
          </div>
        ) : (
          <div className="py-8 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-text-secondary">{s.apiDesc}</p>
            <a href="/billing">
              <Button size="sm" variant="outline">{s.upgradePro}</Button>
            </a>
          </div>
        )}
      </Card>

      {/* ── Integrations ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>{s.integrations}</CardTitle>
        </CardHeader>

        {[
          { name: "Slack",   desc: "Send QA reports to Slack channels",    badge: s.comingSoon },
          { name: "Jira",    desc: "Auto-create Jira tickets from issues",  badge: s.comingSoon },
          { name: "GitHub",  desc: "Trigger QA on PR events",               badge: s.comingSoon },
          { name: "Webhook", desc: "POST results to any endpoint",          badge: s.proPlus },
        ].map((item) => (
          <div
            key={item.name}
            className="flex items-center justify-between py-3 border-b border-border/50 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-text-primary">{item.name}</p>
              <p className="text-xs text-text-muted">{item.desc}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted bg-bg-elevated px-2 py-0.5 rounded-full border border-border">
                {item.badge}
              </span>
              <ChevronRight className="h-4 w-4 text-text-muted" />
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}

// ── Language section ──────────────────────────────────────────────────────────

const LANG_OPTIONS: { value: Lang; label: string; code: string }[] = [
  { value: "en", label: "English",    code: "EN" },
  { value: "ru", label: "Русский",    code: "RU" },
  { value: "uk", label: "Українська", code: "UA" },
  { value: "es", label: "Español",    code: "ES" },
];

function LanguageSection() {
  const { lang, setLang, t } = useLang();
  const s = t.settings;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-text-muted" />
          {s.language}
        </CardTitle>
      </CardHeader>

      <p className="text-sm text-text-secondary mb-3">{s.languageDesc}</p>

      <div className="flex gap-2">
        {LANG_OPTIONS.map((opt) => {
          const active = lang === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => setLang(opt.value)}
              className={cn(
                "flex items-center gap-2.5 px-4 py-2.5 rounded-lg border text-sm font-medium",
                "transition-all duration-150",
                active
                  ? "bg-accent-bg border-accent/40 text-accent"
                  : "bg-bg-surface border-border text-text-secondary hover:border-border-focus"
              )}
            >
              <span
                className={cn(
                  "inline-flex items-center justify-center w-7 h-5 rounded text-[10px] font-bold tracking-wider",
                  active ? "bg-accent/20 text-accent" : "bg-bg-elevated text-text-muted"
                )}
              >
                {opt.code}
              </span>
              {opt.label}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

// ── Password section ──────────────────────────────────────────────────────────

function PasswordSection() {
  const { t } = useLang();
  const s = t.settings;

  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [saving, setSaving]   = useState(false);

  async function handleSave() {
    if (!current || !next || saving) return;
    if (next.length < 8) {
      toast.error(s.passwordMin);
      return;
    }
    setSaving(true);
    try {
      await userApi.changePassword(current, next);
      toast.success(s.passwordUpdated);
      setCurrent("");
      setNext("");
    } catch {
      toast.error(s.passwordError);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-text-muted" />
          {s.security}
        </CardTitle>
      </CardHeader>

      <div className="space-y-4">
        <Input
          label={s.currentPassword}
          type="password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          placeholder="••••••••"
          autoComplete="current-password"
        />
        <Input
          label={s.newPassword}
          type="password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          placeholder={s.passwordHint}
          hint={s.passwordHint}
          autoComplete="new-password"
        />
      </div>

      <div className="flex justify-end mt-4">
        <Button
          size="sm"
          loading={saving}
          disabled={!current || !next}
          onClick={handleSave}
        >
          {s.updatePassword}
        </Button>
      </div>
    </Card>
  );
}

// ── Toggle component ──────────────────────────────────────────────────────────

function Toggle({
  defaultChecked = false,
  disabled = false,
}: {
  defaultChecked?: boolean;
  disabled?: boolean;
}) {
  const [on, setOn] = useState(defaultChecked);
  return (
    <button
      onClick={() => !disabled && setOn((v) => !v)}
      disabled={disabled}
      className={cn(
        "relative h-5 w-9 rounded-full transition-colors duration-200",
        on ? "bg-accent" : "bg-bg-elevated border border-border",
        disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
      )}
      role="switch"
      aria-checked={on}
    >
      <span
        className={cn(
          "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200",
          on ? "translate-x-4" : "translate-x-0.5"
        )}
      />
    </button>
  );
}
