// ── User ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string | null;
  avatarUrl: string | null;
  createdAt: string;
  plan: PlanType;
  usageCredits: number;
  usageCap: number;
}

// ── Subscription / Billing ────────────────────────────────────────────────────

export type PlanType = "free" | "pro" | "team" | "enterprise";

export interface Plan {
  id: PlanType;
  name: string;
  price: number;
  period: "month" | "year";
  creditsPerMonth: number;
  features: string[];
  isPopular?: boolean;
}

export interface Subscription {
  id: string;
  userId: string;
  plan: PlanType;
  status: "active" | "canceled" | "past_due" | "trialing";
  currentPeriodStart: string;
  currentPeriodEnd: string;
  cancelAtPeriodEnd: boolean;
  stripeSubscriptionId: string | null;
}

export interface BillingInvoice {
  id: string;
  date: string;
  amount: number;
  currency: string;
  status: "paid" | "open" | "failed";
  description: string;
  invoiceUrl: string | null;
}

// ── Chats ─────────────────────────────────────────────────────────────────────

export interface Chat {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  lastMessage: string | null;
  runCount: number;
  status: ChatStatus;
}

export type ChatStatus = "idle" | "running" | "error";

// ── Messages ──────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "machine" | "assistant";

export interface Message {
  id: string;
  chatId: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  runId: string | null;
}

// ── Runs ──────────────────────────────────────────────────────────────────────

export type RunStatus = "queued" | "running" | "completed" | "failed";

export interface Run {
  id: string;
  chatId: string;
  messageId: string;
  targetUrl: string;
  task: string;
  status: RunStatus;
  mode: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  reportPath: string | null;
  errorMessage: string | null;
  stepCount: number;
  maxSteps: number;
  issueCount: number;
  summary: string | null;
  artifacts: RunArtifact[];
}

export interface RunArtifact {
  id: string;
  type: "report" | "screenshot" | "playwright_test" | "qa_doc";
  name: string;
  path: string;
  size: number;
}

// ── API ───────────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface RecentRun {
  id: string;
  chatId: string;
  chatTitle: string;
  targetUrl: string;
  status: RunStatus;
  issueCount: number;
  stepCount: number;
  mode: string | null;
  createdAt: string;
}

export interface DashboardStats {
  totalRuns: number;
  totalIssues: number;
  totalChats: number;
  recentRuns: RecentRun[];
}

// ── Forms ─────────────────────────────────────────────────────────────────────

export interface LoginFormValues {
  email: string;
  password: string;
}

export interface SignupFormValues {
  name: string;
  email: string;
  password: string;
}

export interface NewChatFormValues {
  targetUrl: string;
  task: string;
}

export interface ProfileFormValues {
  name: string;
  email: string;
}
