"use client";

import { useEffect, useState } from "react";
import { adminApi, type AdminAnalytics } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Users, TrendingUp, DollarSign, Eye, Activity,
  RefreshCw, AlertCircle, CheckCircle, XCircle,
} from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

const PLAN_COLORS: Record<string, string> = {
  free:       "text-text-muted",
  pro:        "text-blue-400",
  team:       "text-purple-400",
  enterprise: "text-yellow-400",
};

const PLAN_BG: Record<string, string> = {
  free:       "bg-bg-elevated",
  pro:        "bg-blue-500/10 border border-blue-500/20",
  team:       "bg-purple-500/10 border border-purple-500/20",
  enterprise: "bg-yellow-500/10 border border-yellow-500/20",
};

function fmt(n: number) {
  return n.toLocaleString();
}

function pct(a: number, b: number) {
  if (!b) return "—";
  return ((a / b) * 100).toFixed(1) + "%";
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon, label, value, sub, color = "text-accent",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-xl p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-text-muted text-xs font-medium uppercase tracking-wide">
        <Icon className={cn("h-4 w-4", color)} />
        {label}
      </div>
      <p className="text-2xl font-bold text-text-primary">{fmt(Number(value))}</p>
      {sub && <p className="text-xs text-text-muted">{sub}</p>}
    </div>
  );
}

// ── Mini bar ──────────────────────────────────────────────────────────────────

function MiniBar({ label, value, max, color = "bg-accent" }: {
  label: string; value: number; max: number; color?: string;
}) {
  const w = max ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-secondary w-28 truncate">{label}</span>
      <div className="flex-1 h-2 bg-bg-elevated rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${w}%` }} />
      </div>
      <span className="text-xs text-text-muted w-6 text-right">{value}</span>
    </div>
  );
}

// ── Funnel row ────────────────────────────────────────────────────────────────

function FunnelRow({ label, count, pctLabel, accent = false }: {
  label: string; count: number; pctLabel: string; accent?: boolean;
}) {
  return (
    <div className={cn(
      "flex items-center justify-between px-4 py-3 rounded-lg",
      accent ? "bg-accent/10 border border-accent/20" : "bg-bg-elevated",
    )}>
      <span className={cn("text-sm font-medium", accent ? "text-accent" : "text-text-primary")}>
        {label}
      </span>
      <div className="flex items-center gap-3">
        <span className="text-xs text-text-muted">{pctLabel}</span>
        <span className={cn("text-base font-bold", accent ? "text-accent" : "text-text-primary")}>
          {fmt(count)}
        </span>
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [data, setData]       = useState<AdminAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [refreshed, setRefreshed] = useState(false);
  const [updatingPlan, setUpdatingPlan] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const analytics = await adminApi.getAnalytics();
      setData(analytics);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Failed to load analytics";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handlePlanChange(userId: string, plan: string) {
    setUpdatingPlan(userId);
    try {
      await adminApi.updateUserPlan(userId, plan);
      await load();
    } catch {
      alert("Failed to update plan");
    } finally {
      setUpdatingPlan(null);
    }
  }

  async function handleRefresh() {
    await load();
    setRefreshed(true);
    setTimeout(() => setRefreshed(false), 2000);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-5 w-5 text-accent animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <AlertCircle className="h-8 w-8 text-error" />
        <p className="text-sm text-text-muted">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const { users, runs, visits, payments, dailyRegistrations, recentUsers } = data;
  const modeEntries = Object.entries(runs.modes).sort((a, b) => b[1] - a[1]);
  const maxMode     = modeEntries[0]?.[1] ?? 1;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Analytics</h1>
          <p className="text-sm text-text-muted mt-0.5">Admin view — real-time data from database</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-elevated hover:bg-border
                     text-text-secondary text-xs transition-colors"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", refreshed && "text-accent")} />
          Refresh
        </button>
      </div>

      {/* ── Funnel ───────────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide mb-3">
          Conversion funnel
        </h2>
        <div className="space-y-2">
          <FunnelRow
            label="🌐  Visited (30 days, unique IP)"
            count={visits.uniqueMonth}
            pctLabel="100%"
          />
          <FunnelRow
            label="✍️  Registered (total)"
            count={users.total}
            pctLabel={pct(users.total, visits.uniqueMonth || users.total)}
          />
          <FunnelRow
            label="🚀  Used the product (ran at least 1 test)"
            count={runs.total}
            pctLabel={pct(runs.total, users.total)}
          />
          <FunnelRow
            label="💳  Paid (active paid plan)"
            count={users.paid}
            pctLabel={pct(users.paid, users.total)}
            accent
          />
          <FunnelRow
            label="🔁  Paid again (repeat payments)"
            count={payments.repeatPayers}
            pctLabel={pct(payments.repeatPayers, users.paid || 1)}
          />
        </div>
      </section>

      {/* ── Top stats ────────────────────────────────────────────────────── */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Eye}
          label="Visits today"
          value={visits.today}
          sub={`${fmt(visits.week)} this week · ${fmt(visits.total)} total`}
          color="text-blue-400"
        />
        <StatCard
          icon={Users}
          label="Registrations"
          value={users.total}
          sub={`+${users.newToday} today · +${users.newWeek} week · +${users.newMonth} month`}
          color="text-green-400"
        />
        <StatCard
          icon={TrendingUp}
          label="Paid users"
          value={users.paid}
          sub={`${pct(users.paid, users.total)} conversion · ${fmt(users.byPlan.pro ?? 0)} Pro · ${fmt(users.byPlan.team ?? 0)} Team`}
          color="text-accent"
        />
        <StatCard
          icon={DollarSign}
          label="Est. monthly revenue"
          value={`$${payments.estimatedMonthlyRevenue}`}
          sub={`${fmt(payments.total)} payments · ${fmt(payments.repeatPayers)} repeat`}
          color="text-yellow-400"
        />
      </section>

      {/* ── Middle row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Plans breakdown */}
        <div className="bg-bg-surface border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-medium text-text-primary">Users by plan</h2>
          {(["free", "pro", "team", "enterprise"] as const).map((plan) => {
            const c = users.byPlan[plan] ?? 0;
            return (
              <div key={plan} className={cn("flex items-center justify-between px-3 py-2 rounded-lg", PLAN_BG[plan])}>
                <span className={cn("text-sm font-medium capitalize", PLAN_COLORS[plan])}>{plan}</span>
                <span className="text-sm font-bold text-text-primary">{fmt(c)}</span>
              </div>
            );
          })}
        </div>

        {/* Runs stats */}
        <div className="bg-bg-surface border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-medium text-text-primary">Runs</h2>
          <div className="space-y-2 text-sm">
            {[
              { label: "Total", value: runs.total },
              { label: "Today", value: runs.today },
              { label: "This week", value: runs.week },
              { label: "Completed ✓", value: runs.completed },
              { label: "Failed ✗", value: runs.failed },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span className="text-text-muted">{label}</span>
                <span className="text-text-primary font-medium">{fmt(value)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Mode distribution */}
        <div className="bg-bg-surface border border-border rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-medium text-text-primary">Modes used (30d)</h2>
          {modeEntries.length === 0 ? (
            <p className="text-xs text-text-muted">No data yet</p>
          ) : (
            <div className="space-y-2.5">
              {modeEntries.map(([mode, count]) => (
                <MiniBar key={mode} label={mode} value={count} max={maxMode} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Daily registrations sparkline ────────────────────────────────── */}
      <section className="bg-bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-medium text-text-primary mb-4">Registrations — last 14 days</h2>
        <div className="flex items-end gap-1 h-20">
          {dailyRegistrations.map(({ date, count }) => {
            const maxCount = Math.max(...dailyRegistrations.map(d => d.count), 1);
            const h = Math.round((count / maxCount) * 100);
            return (
              <div key={date} className="flex-1 flex flex-col items-center gap-1 group relative">
                <div
                  className="w-full bg-accent/40 hover:bg-accent rounded-t transition-colors"
                  style={{ height: `${Math.max(h, 2)}%` }}
                />
                <span className="text-2xs text-text-muted" style={{ fontSize: "9px" }}>{date}</span>
                {count > 0 && (
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-bg-elevated border border-border
                                  text-xs px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity
                                  pointer-events-none whitespace-nowrap z-10">
                    {count} reg
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Recent users ─────────────────────────────────────────────────── */}
      <section className="bg-bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-sm font-medium text-text-primary">Recent registrations</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg-elevated">
                {["Email", "Name", "Plan", "Runs used", "Registered", ""].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-text-muted">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recentUsers.map((u, i) => (
                <tr
                  key={u.id}
                  className={cn(
                    "border-b border-border/50 hover:bg-bg-elevated transition-colors",
                    i % 2 === 0 ? "" : "bg-bg-elevated/30",
                  )}
                >
                  <td className="px-4 py-2.5 text-text-primary font-mono text-xs">{u.email}</td>
                  <td className="px-4 py-2.5 text-text-secondary">{u.name ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <span className={cn("text-xs font-medium capitalize", PLAN_COLORS[u.plan])}>
                      {u.plan}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-text-secondary">{u.usageCredits}</td>
                  <td className="px-4 py-2.5 text-text-muted text-xs">
                    {new Date(u.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <select
                      value={u.plan}
                      disabled={updatingPlan === u.id}
                      onChange={(e) => handlePlanChange(u.id, e.target.value)}
                      className="text-xs bg-bg-elevated border border-border rounded px-2 py-1
                                 text-text-primary cursor-pointer hover:border-accent transition-colors
                                 disabled:opacity-50"
                    >
                      {["free", "pro", "team", "enterprise"].map(p => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {recentUsers.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-text-muted text-sm">
                    No users yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
