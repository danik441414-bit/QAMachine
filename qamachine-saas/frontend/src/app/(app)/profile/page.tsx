"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { User, Mail, Camera, Save, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, Divider } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { authApi, userApi } from "@/lib/api";
import { getInitials, PLAN_LABELS, PLAN_COLORS, formatFullDate } from "@/lib/utils";
import { useLang } from "@/context/language-context";
import type { User as UserType } from "@/types";

export default function ProfilePage() {
  const [user, setUser]       = useState<UserType | null>(null);
  const [name, setName]       = useState("");
  const [email, setEmail]     = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const { t } = useLang();
  const p = t.profile;

  useEffect(() => {
    authApi.me()
      .then((u) => {
        setUser(u);
        setName(u.name ?? "");
        setEmail(u.email);
      })
      .catch(() => toast.error(t.common.error))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    if (!user || saving) return;
    setSaving(true);
    try {
      const updated = await userApi.updateProfile({ name, email });
      setUser(updated);
      toast.success("Changes saved!");
    } catch {
      toast.error(t.common.error);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6 max-w-2xl mx-auto space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 skeleton rounded-xl" />
        ))}
      </div>
    );
  }

  if (!user) return null;

  const isDirty = name !== (user.name ?? "") || email !== user.email;

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-5 animate-fade-in">

      {/* ── Avatar + Identity ───────────────────────────────────────── */}
      <Card>
        <div className="flex items-center gap-5">
          <div className="relative">
            <div
              className="h-16 w-16 rounded-2xl bg-accent-muted flex items-center
                         justify-center text-accent text-xl font-bold border border-accent/20"
            >
              {getInitials(user.name, user.email)}
            </div>
            <button
              className="absolute -bottom-1 -right-1 h-6 w-6 rounded-full
                         bg-bg-elevated border border-border flex items-center
                         justify-center text-text-muted hover:text-text-primary
                         transition-colors"
              title="Coming soon"
            >
              <Camera className="h-3 w-3" />
            </button>
          </div>

          <div>
            <h3 className="text-base font-semibold text-text-primary">
              {user.name ?? p.noName}
            </h3>
            <p className="text-sm text-text-secondary">{user.email}</p>
            <div className="flex items-center gap-2 mt-1.5">
              <Badge variant={user.plan === "free" ? "default" : "accent"} size="sm">
                {PLAN_LABELS[user.plan]} plan
              </Badge>
              <span className="text-xs text-text-muted">
                {p.memberSince} {formatFullDate(user.createdAt)}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* ── Edit Info ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>{p.title}</CardTitle>
        </CardHeader>

        <div className="space-y-4">
          <Input
            label={p.nameLabel}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            leftIcon={<User className="h-4 w-4" />}
            placeholder={p.namePlaceholder}
          />
          <Input
            label={p.emailLabel}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            leftIcon={<Mail className="h-4 w-4" />}
            placeholder="you@example.com"
          />
        </div>

        {isDirty && (
          <div className="flex justify-end mt-5">
            <Button
              size="sm"
              loading={saving}
              onClick={handleSave}
              leftIcon={<Save className="h-3.5 w-3.5" />}
            >
              {p.saveChanges}
            </Button>
          </div>
        )}
      </Card>

      {/* ── Usage ────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>{p.usage}</CardTitle>
          <Badge variant="default" size="sm">
            {PLAN_LABELS[user.plan]}
          </Badge>
        </CardHeader>

        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-text-secondary">{p.usageDesc}</span>
              <span className="text-text-primary font-medium">
                {user.usageCredits} / {user.usageCap}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-bg-elevated overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${Math.min(100, (user.usageCredits / user.usageCap) * 100)}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-text-muted">{p.usageReset}</p>
        </div>

        <Divider />

        <div className="flex justify-between items-center">
          <p className="text-sm text-text-secondary">{p.needMore}</p>
          <a href="/billing">
            <Button size="sm" variant="outline">{p.upgradePlan}</Button>
          </a>
        </div>
      </Card>

      {/* ── Danger zone ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-error">{p.dangerZone}</CardTitle>
        </CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-text-primary">{p.deleteAccount}</p>
            <p className="text-xs text-text-muted">{p.deleteDesc}</p>
          </div>
          <Button
            size="sm"
            variant="danger"
            leftIcon={<AlertTriangle className="h-3.5 w-3.5" />}
            onClick={() => toast.error("Contact support to delete your account")}
          >
            {p.deleteAccount}
          </Button>
        </div>
      </Card>
    </div>
  );
}
