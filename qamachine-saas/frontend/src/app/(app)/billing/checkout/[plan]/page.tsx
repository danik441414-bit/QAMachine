"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft, CreditCard, Bitcoin, CheckCircle,
  Zap, Shield, Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { billingApi } from "@/lib/api";
import { useLang } from "@/context/language-context";

const PLAN_META = {
  pro:  { name: "Pro",  price: 29, credits: 50  },
  team: { name: "Team", price: 79, credits: 200 },
} as const;

type PlanId = keyof typeof PLAN_META;

const PAYMENT_METHODS = [
  {
    id: "card" as const,
    label: "Bank Card",
    description: "Visa, Mastercard — any country",
    icon: CreditCard,
    badge: null,
    color: "text-blue-400",
    border: "hover:border-blue-500/50",
    bg: "hover:bg-blue-500/5",
  },
  {
    id: "crypto" as const,
    label: "Crypto (USDT)",
    description: "USDT TRC20 / BEP20 — no KYC, 1% fee",
    icon: Bitcoin,
    badge: "Recommended",
    color: "text-orange-400",
    border: "hover:border-orange-500/50",
    bg: "hover:bg-orange-500/5",
  },
];

export default function CheckoutPage() {
  const { plan: planParam } = useParams<{ plan: string }>();
  const router = useRouter();
  const { t } = useLang();
  const meta = PLAN_META[planParam as PlanId];
  const plan = meta ? {
    ...meta,
    features: t.billing.planFeatures[planParam as PlanId] as readonly string[],
  } : null;

  const [selected, setSelected]   = useState<"card" | "crypto" | null>(null);
  const [loading, setLoading]      = useState(false);

  if (!plan) {
    router.replace("/billing");
    return null;
  }

  async function handleContinue() {
    if (!selected) return;
    setLoading(true);
    try {
      if (selected === "card") {
        const { url } = await billingApi.createCardCheckoutSession(planParam);
        window.location.href = url;
      } else {
        const { url } = await billingApi.createCryptoCheckoutSession(planParam);
        window.location.href = url;
      }
    } catch {
      toast.error(
        selected === "card"
          ? "Card payment unavailable. Try crypto."
          : "Crypto payment unavailable. Try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-full flex items-start justify-center p-6">
      <div className="w-full max-w-lg animate-fade-in">

        {/* Back */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-secondary
                     transition-colors mb-6 group"
        >
          <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" />
          Back to plans
        </button>

        {/* Plan summary */}
        <div className="rounded-xl border border-border bg-bg-surface p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-accent" />
              <span className="font-semibold text-text-primary">{plan.name} Plan</span>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold text-text-primary">${plan.price}</span>
              <span className="text-sm text-text-muted">/mo</span>
            </div>
          </div>
          <ul className="grid grid-cols-2 gap-1.5">
            {plan.features.map((f) => (
              <li key={f} className="flex items-center gap-1.5 text-xs text-text-secondary">
                <CheckCircle className="h-3 w-3 text-success shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Payment method selection */}
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
          Choose payment method
        </h2>

        <div className="space-y-3 mb-6">
          {PAYMENT_METHODS.map((method) => {
            const Icon = method.icon;
            const isSelected = selected === method.id;
            return (
              <button
                key={method.id}
                onClick={() => setSelected(method.id)}
                className={cn(
                  "w-full rounded-xl border p-4 flex items-center gap-4 text-left",
                  "transition-all duration-150",
                  method.border, method.bg,
                  isSelected
                    ? "border-accent bg-accent/5 shadow-glow-sm"
                    : "border-border bg-bg-surface"
                )}
              >
                {/* Radio */}
                <div className={cn(
                  "h-4 w-4 rounded-full border-2 shrink-0 flex items-center justify-center",
                  isSelected ? "border-accent" : "border-border"
                )}>
                  {isSelected && (
                    <div className="h-2 w-2 rounded-full bg-accent" />
                  )}
                </div>

                <Icon className={cn("h-5 w-5 shrink-0", method.color)} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">{method.label}</span>
                    {method.badge && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium
                                       bg-accent/15 text-accent">
                        {method.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-muted mt-0.5">{method.description}</p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Trust badges */}
        <div className="flex items-center gap-4 mb-6 text-xs text-text-muted">
          <div className="flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5" />
            Secure checkout
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            Instant activation
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle className="h-3.5 w-3.5" />
            Cancel anytime
          </div>
        </div>

        {/* CTA */}
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          disabled={!selected}
          loading={loading}
          onClick={handleContinue}
        >
          Continue to payment
        </Button>
      </div>
    </div>
  );
}
