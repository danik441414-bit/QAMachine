"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Zap, ArrowRight, Activity, Loader2,
  CheckCircle2, AlertTriangle, Clock, Bug,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RunStatusBadge } from "@/components/ui/badge";
import { dashboardApi, authApi } from "@/lib/api";
import { formatDateShort, cn, PLAN_LABELS } from "@/lib/utils";
import { useLang } from "@/context/language-context";
import type { DashboardStats, RecentRun, User } from "@/types";


export default function DashboardPage() {
  const [stats, setStats]     = useState<DashboardStats | null>(null);
  const [user, setUser]       = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const { t } = useLang();
  const d = t.dashboard;

  useEffect(() => {
    Promise.all([dashboardApi.getStats(), authApi.me()])
      .then(([s, u]) => { setStats(s); setUser(u); })
      .finally(() => setLoading(false));
  }, []);

  const planLabel = user ? (PLAN_LABELS[user.plan] ?? user.plan) : "—";

  const statCards = [
    { label: d.totalRuns,   value: stats ? String(stats.totalRuns)   : "—" },
    { label: d.issuesFound, value: stats ? String(stats.totalIssues) : "—" },
    { label: d.chats,       value: stats ? String(stats.totalChats)  : "—" },
    { label: d.plan,        value: planLabel },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto animate-fade-in">

      {/* ── Welcome ─────────────────────────────────────────────────── */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-text-primary mb-1">{d.greeting}</h2>
        <p className="text-sm text-text-secondary">{d.greetingDesc}</p>
      </div>

      {/* ── CTA ─────────────────────────────────────────────────────── */}
      <div className="mb-8 p-6 rounded-xl bg-accent/5 border border-accent/20
                      flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-text-primary mb-1 flex items-center gap-2">
            <Zap className="h-4 w-4 text-accent" />
            {d.newSession}
          </h3>
          <p className="text-sm text-text-secondary">{d.newSessionDesc}</p>
        </div>
        <Link href="/chats/new">
          <Button size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
            {d.startNewChat}
          </Button>
        </Link>
      </div>

      {/* ── Quick start modes ────────────────────────────────────────── */}
      <div className="mb-8">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          {d.quickStart}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {d.quickStartModes.map((qs) => (
            <Link key={qs.mode} href={`/chats/new?mode=${qs.mode}`}>
              <div className="p-4 rounded-xl bg-bg-surface border border-border
                             hover:border-border-focus hover:shadow-card-hover
                             transition-all duration-150 cursor-pointer h-full">
                <p className="text-sm font-medium text-text-primary mb-1">{qs.label}</p>
                <p className="text-xs text-text-muted leading-relaxed">{qs.example}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ── Stats row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {statCards.map((stat) => (
          <Card key={stat.label} padding="sm">
            <p className="text-xs text-text-muted mb-1">{stat.label}</p>
            {loading && stat.value === "—" ? (
              <div className="h-7 w-8 rounded bg-bg-elevated animate-pulse" />
            ) : (
              <p className="text-lg font-bold text-text-primary">{stat.value}</p>
            )}
          </Card>
        ))}
      </div>

      {/* ── Recent runs ──────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
            {d.recentRuns}
          </h3>
          <Link
            href="/chats"
            className="text-xs text-text-muted hover:text-text-secondary transition-colors
                       flex items-center gap-1"
          >
            {d.viewAll} <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12 gap-2 text-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">{t.common.loading}</span>
          </div>
        ) : stats && stats.recentRuns.length > 0 ? (
          <div className="space-y-2">
            {stats.recentRuns.map((run) => (
              <RecentRunRow key={run.id} run={run} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-bg-surface p-12
                          flex flex-col items-center justify-center gap-3 text-center">
            <div className="h-10 w-10 rounded-xl bg-bg-elevated border border-border
                            flex items-center justify-center">
              <Activity className="h-5 w-5 text-text-muted" />
            </div>
            <p className="text-sm font-medium text-text-secondary">{d.noRuns}</p>
            <p className="text-xs text-text-muted max-w-xs">{d.noRunsDesc}</p>
            <Link href="/chats/new">
              <Button size="sm" variant="secondary">{d.createFirstChat}</Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Recent run row ────────────────────────────────────────────────────────────

function RunIcon({ status }: { status: RecentRun["status"] }) {
  switch (status) {
    case "queued":    return <Clock        className="h-3.5 w-3.5 text-text-muted" />;
    case "running":   return <Loader2      className="h-3.5 w-3.5 text-accent animate-spin" />;
    case "completed": return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
    case "failed":    return <AlertTriangle className="h-3.5 w-3.5 text-error" />;
  }
}

function RecentRunRow({ run }: { run: RecentRun }) {
  return (
    <Link href={`/chats/${run.chatId}`}>
      <div className="flex items-center gap-4 px-4 py-3 rounded-xl bg-bg-surface
                      border border-border hover:border-border-focus hover:shadow-card-hover
                      transition-all duration-150 cursor-pointer">

        <RunIcon status={run.status} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-text-primary truncate">
              {run.chatTitle}
            </p>
            {run.mode && (
              <span className="text-2xs px-2 py-0.5 rounded-full border border-border
                               text-text-muted capitalize shrink-0">
                {run.mode.replace("_", " ")}
              </span>
            )}
          </div>
          <p className="text-xs text-text-muted truncate mt-0.5">{run.targetUrl}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {run.status === "completed" && run.issueCount > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-error">
              <Bug className="h-3 w-3" />
              {run.issueCount}
            </span>
          )}
          <RunStatusBadge status={run.status} />
          <span className="hidden sm:inline text-xs text-text-muted">{formatDateShort(run.createdAt)}</span>
        </div>
      </div>
    </Link>
  );
}
