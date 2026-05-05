import Link from "next/link";
import {
  Zap, ArrowRight, Shield, Clock, BarChart3,
  Globe, Code2, Smartphone, CheckCircle, Layers,
} from "lucide-react";
import { TrackVisit } from "@/components/track-visit";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-text-primary overflow-x-hidden">
      <TrackVisit path="/" />

      {/* ── Nav ──────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 h-16 border-b border-border/50 glass">
        <div className="max-w-6xl mx-auto px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center
                            shadow-glow-sm">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-semibold tracking-tight">QAMachine</span>
          </div>

          <div className="hidden md:flex items-center gap-6">
            {["Features", "How it works", "Pricing"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase().replace(/ /g, "-")}`}
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                {item}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-text-secondary hover:text-text-primary transition-colors px-3"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="h-8 px-4 rounded-lg bg-accent hover:bg-accent-hover text-white
                         text-sm font-medium transition-all shadow-glow-sm"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="relative pt-36 pb-28 px-6">
        {/* Background glow */}
        <div className="absolute inset-0 bg-radial-glow pointer-events-none" />
        <div
          className="absolute inset-0 bg-grid-pattern pointer-events-none opacity-50"
          style={{ backgroundSize: "32px 32px" }}
        />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                          bg-accent-bg border border-accent/20 text-xs text-accent
                          font-medium mb-8">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
            AI-powered QA automation
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-balance mb-6">
            <span className="text-text-primary">Your personal</span>
            <br />
            <span className="accent-gradient-text">AI QA Engineer</span>
          </h1>

          <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-10 text-pretty leading-relaxed">
            QAMachine tests your website like a senior QA engineer —
            UI/UX audits, functional flows, API testing, mobile emulation,
            and more. Results in minutes, not days.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 h-11 px-6 rounded-xl
                         bg-accent hover:bg-accent-hover text-white font-medium
                         transition-all shadow-glow active:scale-[0.98]"
            >
              Start for free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 h-11 px-6 rounded-xl
                         bg-bg-surface hover:bg-bg-elevated text-text-primary font-medium
                         border border-border hover:border-border-focus transition-all"
            >
              See how it works
            </a>
          </div>

          <p className="text-xs text-text-muted mt-6">
            No credit card required · Free plan included · Cancel anytime
          </p>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6 border-t border-border/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text-primary mb-4">
              Everything a QA engineer does — automated
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto">
              Machine covers all testing dimensions so you ship confidently.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="p-5 rounded-xl bg-bg-surface border border-border
                           hover:border-border-focus hover:shadow-card-hover
                           transition-all duration-200 group"
              >
                <div
                  className="h-9 w-9 rounded-lg bg-bg-elevated flex items-center
                              justify-center mb-4 border border-border
                              group-hover:border-accent/30 group-hover:bg-accent-bg
                              transition-all"
                >
                  <f.icon className="h-4.5 w-4.5 text-text-muted group-hover:text-accent
                                     transition-colors" />
                </div>
                <h3 className="text-[0.9375rem] font-semibold text-text-primary mb-1.5">
                  {f.title}
                </h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-6 border-t border-border/50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text-primary mb-4">
              From task to report in minutes
            </h2>
            <p className="text-text-secondary">Simple. Fast. Precise.</p>
          </div>

          <div className="space-y-4">
            {HOW_IT_WORKS.map((step, i) => (
              <div
                key={step.title}
                className="flex items-start gap-5 p-5 rounded-xl bg-bg-surface
                           border border-border"
              >
                <div
                  className="h-8 w-8 rounded-full bg-accent-bg border border-accent/30
                              flex items-center justify-center shrink-0 text-accent
                              text-sm font-bold"
                >
                  {i + 1}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1">
                    {step.title}
                  </h3>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────────────── */}
      <section id="pricing" className="py-24 px-6 border-t border-border/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text-primary mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-text-secondary">
              Start free. Scale as your team grows.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-xl border p-6 flex flex-col relative
                  ${plan.highlighted
                    ? "bg-bg-surface border-accent/40 shadow-glow"
                    : plan.premium
                    ? "bg-bg-surface border-border-focus/60"
                    : "bg-bg-surface border-border"
                  }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium shadow-glow-sm
                      ${plan.highlighted
                        ? "bg-accent text-white"
                        : "bg-bg-elevated border border-border-focus text-text-secondary"
                      }`}>
                      {plan.badge}
                    </span>
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-text-secondary mb-4">
                    {plan.name}
                  </h3>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-3xl font-bold text-text-primary">
                      ${plan.price}
                    </span>
                    {plan.price > 0 && (
                      <span className="text-sm text-text-muted">/month</span>
                    )}
                  </div>
                  <p className="text-sm text-text-secondary mt-2">{plan.description}</p>
                </div>

                <ul className="space-y-2.5 flex-1 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-text-secondary">
                      <CheckCircle
                        className={`h-4 w-4 shrink-0 mt-0.5
                          ${plan.highlighted ? "text-accent" : "text-success"}`}
                      />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/signup"
                  className={`h-10 rounded-lg flex items-center justify-center
                    text-sm font-medium transition-all
                    ${plan.highlighted
                      ? "bg-accent hover:bg-accent-hover text-white shadow-glow-sm"
                      : plan.premium
                      ? "bg-bg-elevated hover:bg-bg-elevated/70 text-text-primary border border-border-focus/60 hover:border-border-focus"
                      : "bg-bg-elevated hover:bg-border text-text-primary border border-border"
                    }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border py-12 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center
                        justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-lg bg-accent flex items-center
                            justify-center">
              <Zap className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold">QAMachine</span>
          </div>
          <p className="text-xs text-text-muted text-center">
            © {new Date().getFullYear()} QAMachine. AI-powered QA for modern teams.
          </p>
          <div className="flex items-center gap-5">
            {["Privacy", "Terms", "Docs"].map((item) => (
              <a
                key={item}
                href="#"
                className="text-xs text-text-muted hover:text-text-secondary transition-colors"
              >
                {item}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}

// ── Data ──────────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: Layers,
    title: "UI/UX Audit",
    description: "Visual defects, layout issues, contrast problems, overlapping elements. Pixel-level precision.",
  },
  {
    icon: CheckCircle,
    title: "Functional Testing",
    description: "Forms, buttons, filters, auth flows, CRUD operations. Every feature tested end-to-end.",
  },
  {
    icon: Globe,
    title: "Network & API",
    description: "4xx/5xx errors, slow requests, broken assets, API endpoint health — all in one pass.",
  },
  {
    icon: Smartphone,
    title: "Mobile Testing",
    description: "Device emulation for iPhone, Pixel, Galaxy. Burger menus, touch targets, horizontal scroll.",
  },
  {
    icon: BarChart3,
    title: "Performance Audit",
    description: "Page load times, slow resources, Web Vitals. Know exactly what's slowing you down.",
  },
  {
    icon: Code2,
    title: "Test Generation",
    description: "Automatically generate runnable Playwright tests and QA documentation from any site.",
  },
];

const HOW_IT_WORKS = [
  {
    title: "Open a chat and paste your URL",
    description:
      "Create a new chat, enter your website URL and describe what you want to test. Machine understands natural language in any language.",
  },
  {
    title: "Machine builds a test plan",
    description:
      "The AI analyzes your request, detects the right testing mode, scopes the test to the area you care about, and starts executing.",
  },
  {
    title: "Watch it work in real time",
    description:
      "Machine navigates your site step by step, detecting issues as a senior QA engineer would — with screenshots and evidence.",
  },
  {
    title: "Get a structured report",
    description:
      "A detailed report with confirmed issues sorted by severity, UX recommendations, and downloadable artifacts — ready to share.",
  },
];

const PLANS = [
  {
    name: "Free",
    price: 0,
    description: "For personal projects",
    highlighted: false,
    premium: false,
    badge: "",
    cta: "Get started free",
    features: [
      "3 QA runs per month",
      "UI/UX & Functional testing",
      "1 chat",
      "20 AI tutor messages",
    ],
  },
  {
    name: "Pro",
    price: 29,
    description: "For solo professionals",
    highlighted: true,
    premium: false,
    badge: "Most popular",
    cta: "Start Pro trial",
    features: [
      "50 QA runs per month",
      "All 9 testing modes",
      "Playwright test generation",
      "QA doc generation",
      "Unlimited chats & AI tutor",
    ],
  },
  {
    name: "Team",
    price: 79,
    description: "For growing teams",
    highlighted: false,
    premium: true,
    badge: "Best value",
    cta: "Start Team trial",
    features: [
      "200 QA runs per month",
      "Everything in Pro",
      "Up to 3 team members",
      "Priority support",
      "API access",
    ],
  },
];
