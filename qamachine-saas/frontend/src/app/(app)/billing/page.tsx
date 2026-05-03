"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { CheckCircle, Zap, ExternalLink, Receipt, ArrowUpRight } from "lucide-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { billingApi } from "@/lib/api";
import { formatFullDate, cn } from "@/lib/utils";
import { useLang } from "@/context/language-context";
import type { Subscription, BillingInvoice } from "@/types";

const PLAN_META = [
  { id: "free" as const, name: "Free", price: 0,  credits: 3   },
  { id: "pro"  as const, name: "Pro",  price: 29, credits: 50,  highlighted: true },
  { id: "team" as const, name: "Team", price: 79, credits: 200 },
];

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices]         = useState<BillingInvoice[]>([]);
  const [loading, setLoading]           = useState(true);
  const { t } = useLang();
  const b = t.billing;

  const PLANS = PLAN_META.map((p) => ({
    ...p,
    features: b.planFeatures[p.id] as readonly string[],
  }));
  const searchParams = useSearchParams();
  const router       = useRouter();

  async function loadData() {
    setLoading(true);
    try {
      const [sub, invs] = await Promise.all([
        billingApi.getSubscription(),
        billingApi.getInvoices(),
      ]);
      setSubscription(sub);
      setInvoices(invs);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success("Subscription activated! Your plan has been upgraded.");
      router.replace("/billing");
      loadData();
    } else if (searchParams.get("canceled") === "1") {
      toast.info("Checkout canceled. No changes were made.");
      router.replace("/billing");
    }
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleManageBilling() {
    try {
      const { url } = await billingApi.createPortalSession();
      window.open(url, "_blank");
    } catch {
      toast.error(b.portalError);
    }
  }

  const currentPlanId = subscription?.plan ?? "free";

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">

      {/* ── Current plan ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>{b.currentPlan}</CardTitle>
          {subscription?.status && (
            <Badge
              variant={subscription.status === "active" ? "success" : "warning"}
              dot
            >
              {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
            </Badge>
          )}
        </CardHeader>

        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-accent" />
              <span className="text-lg font-bold text-text-primary capitalize">
                {currentPlanId} Plan
              </span>
            </div>
            {subscription?.currentPeriodEnd && (
              <p className="text-sm text-text-secondary">
                {subscription.cancelAtPeriodEnd
                  ? `Cancels on ${formatFullDate(subscription.currentPeriodEnd)}`
                  : `Renews ${formatFullDate(subscription.currentPeriodEnd)}`}
              </p>
            )}
          </div>

          {currentPlanId !== "free" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleManageBilling}
              rightIcon={<ExternalLink className="h-3.5 w-3.5" />}
            >
              {b.manageBilling}
            </Button>
          )}
        </div>
      </Card>

      {/* ── Plan cards ──────────────────────────────────────────────── */}
      <div>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          {b.plans}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLANS.map((plan) => {
            const isCurrent = plan.id === currentPlanId;
            const isUpgrade = !isCurrent && plan.price > (PLANS.find((p) => p.id === currentPlanId)?.price ?? 0);

            return (
              <div
                key={plan.id}
                className={cn(
                  "rounded-xl border p-5 flex flex-col relative transition-all",
                  plan.highlighted && !isCurrent
                    ? "border-accent/40 bg-bg-surface shadow-glow"
                    : "border-border bg-bg-surface",
                  isCurrent && "border-success/40"
                )}
              >
                {plan.highlighted && !isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="px-3 py-1 rounded-full bg-accent text-white text-xs font-medium">
                      {b.popular}
                    </span>
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="px-3 py-1 rounded-full bg-success text-white text-xs font-medium">
                      {b.currentPlanBadge}
                    </span>
                  </div>
                )}

                <div className="mb-4">
                  <p className="text-xs text-text-muted font-medium mb-3">{plan.name}</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold text-text-primary">${plan.price}</span>
                    {plan.price > 0 && <span className="text-sm text-text-muted">/mo</span>}
                  </div>
                  <p className="text-xs text-text-muted mt-1">
                    {plan.credits} {b.runsPerMonth}
                  </p>
                </div>

                <ul className="space-y-2 flex-1 mb-5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-text-secondary">
                      <CheckCircle className="h-3.5 w-3.5 text-success shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                {isCurrent ? (
                  <div className="h-9 rounded-lg bg-success/10 border border-success/20
                                  flex items-center justify-center text-xs font-medium text-success">
                    {b.active}
                  </div>
                ) : (
                  <Button
                    variant={plan.highlighted ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => router.push(`/billing/checkout/${plan.id}`)}
                    className="w-full"
                    rightIcon={<ArrowUpRight className="h-3.5 w-3.5" />}
                  >
                    {isUpgrade ? b.upgrade : b.switchTo} {plan.name}
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Invoices ─────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>{b.billingHistory}</CardTitle>
        </CardHeader>

        {loading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-10 skeleton rounded-lg" />
            ))}
          </div>
        ) : invoices.length === 0 ? (
          <div className="py-8 flex flex-col items-center gap-2 text-center">
            <Receipt className="h-8 w-8 text-text-muted" />
            <p className="text-sm text-text-muted">{b.noInvoices}</p>
          </div>
        ) : (
          <div className="space-y-1">
            {invoices.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between py-2.5 px-3 rounded-lg
                           hover:bg-bg-elevated transition-colors"
              >
                <div>
                  <p className="text-sm text-text-primary">{inv.description}</p>
                  <p className="text-xs text-text-muted">{formatFullDate(inv.date)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-text-primary">
                    ${(inv.amount / 100).toFixed(2)}
                  </span>
                  <Badge
                    variant={inv.status === "paid" ? "success" : inv.status === "failed" ? "error" : "warning"}
                    size="sm"
                  >
                    {inv.status}
                  </Badge>
                  {inv.invoiceUrl && (
                    <a
                      href={inv.invoiceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-text-muted hover:text-text-secondary transition-colors"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
