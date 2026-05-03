import axios from "axios";
import type {
  User, Chat, Message, Run, Subscription,
  BillingInvoice, ApiResponse, PaginatedResponse,
  NewChatFormValues, ProfileFormValues, DashboardStats,
} from "@/types";

// ── snake_case → camelCase transformer ───────────────────────────────────────

function toCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

function camelizeKeys(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(camelizeKeys);
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        toCamel(k),
        camelizeKeys(v),
      ])
    );
  }
  return obj;
}

// ── Client setup ──────────────────────────────────────────────────────────────

const BASE_URL = "";

export const apiClient = axios.create({
  baseURL: `/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Attach JWT token from localStorage on each request
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → redirect to login, and convert snake_case → camelCase
apiClient.interceptors.response.use(
  (res) => {
    res.data = camelizeKeys(res.data);
    return res;
  },
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    const res = await apiClient.post<{ accessToken: string; tokenType: string }>(
      "/auth/token",
      form.toString(),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );
    return res.data;
  },

  signup: async (name: string, email: string, password: string) => {
    const res = await apiClient.post<{
      id: string; email: string; name: string | null;
      emailVerified: boolean; verificationRequired: boolean;
    }>("/auth/register", { name, email, password });
    return res.data;
  },

  verifyEmail: async (token: string) => {
    const res = await apiClient.get<{ ok: boolean; message: string }>(
      `/auth/verify-email?token=${encodeURIComponent(token)}`
    );
    return res.data;
  },

  resendVerification: async (email: string) => {
    const res = await apiClient.post<{ ok: boolean; message: string }>(
      "/auth/resend-verification", { email }
    );
    return res.data;
  },

  me: async () => {
    const res = await apiClient.get<User>("/auth/me");
    return res.data;
  },

  forgotPassword: async (email: string) => {
    const res = await apiClient.post<ApiResponse<null>>("/auth/forgot-password", { email });
    return res.data;
  },

  resetPassword: async (token: string, password: string) => {
    const res = await apiClient.post<{ ok: boolean; message: string }>(
      "/auth/reset-password", { token, password }
    );
    return res.data;
  },

  googleLogin: async (credential: string) => {
    const res = await apiClient.post<{ accessToken: string; tokenType: string }>(
      "/auth/google", { credential }
    );
    return res.data;
  },

  requestMagicLink: async (email: string) => {
    const res = await apiClient.post<{ ok: boolean; message: string }>(
      "/auth/magic-link", { email }
    );
    return res.data;
  },

  verifyMagicLink: async (token: string) => {
    const res = await apiClient.get<{ accessToken: string; tokenType: string }>(
      `/auth/magic-link/verify?token=${encodeURIComponent(token)}`
    );
    return res.data;
  },
};

// ── Chats ─────────────────────────────────────────────────────────────────────

export const chatsApi = {
  list: async (page = 1, pageSize = 20) => {
    const res = await apiClient.get<PaginatedResponse<Chat>>("/chats", {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  create: async (title?: string) => {
    const res = await apiClient.post<Chat>("/chats", { title: title ?? "New Chat" });
    return res.data;
  },

  get: async (id: string) => {
    const res = await apiClient.get<Chat>(`/chats/${id}`);
    return res.data;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/chats/${id}`);
  },

  rename: async (id: string, title: string) => {
    const res = await apiClient.patch<Chat>(`/chats/${id}`, { title });
    return res.data;
  },

  evaluate: async (chatId: string, task: string, targetUrl: string): Promise<{
    ready: boolean;
    questions?: string;
    improved_task?: string;
  }> => {
    const res = await apiClient.post(`/chats/${chatId}/evaluate`, {
      task,
      target_url: targetUrl,
    });
    return res.data;
  },

  assist: (
    chatId:  string,
    message: string,
    onText:  (text: string) => void,
    onDone:  () => void,
    onError: (msg: string) => void,
  ): (() => void) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    let aborted = false;

    (async () => {
      try {
        const res = await fetch(`/api/v1/chats/${chatId}/assist`, {
          method:  "POST",
          headers: {
            "Content-Type":  "application/json",
            "Authorization": `Bearer ${token ?? ""}`,
          },
          body: JSON.stringify({ message }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          onError(data?.detail ?? "AI assistant unavailable");
          return;
        }

        const reader  = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.text) onText(event.text);
              if (event.done) onDone();
              if (event.error) onError(event.error);
            } catch { /* ignore */ }
          }
        }
      } catch {
        if (!aborted) onError("Connection error. Please try again.");
      }
    })();

    return () => { aborted = true; };
  },
};

// ── Messages ──────────────────────────────────────────────────────────────────

export const messagesApi = {
  list: async (chatId: string) => {
    const res = await apiClient.get<Message[]>(`/chats/${chatId}/messages`);
    return res.data;
  },

  send: async (chatId: string, values: NewChatFormValues) => {
    const res = await apiClient.post<{ message: Message; run: Run }>(
      `/chats/${chatId}/messages`,
      {
        target_url: values.targetUrl,
        task: values.task,
      }
    );
    return res.data;
  },
};

// ── Runs ──────────────────────────────────────────────────────────────────────

export const runsApi = {
  get: async (runId: string) => {
    const res = await apiClient.get<Run>(`/runs/${runId}`);
    return res.data;
  },

  // SSE stream for real-time status
  streamStatus: (runId: string, onUpdate: (run: Run) => void): EventSource => {
    const token = typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;
    const url = `${BASE_URL}/api/v1/runs/${runId}/stream?token=${token ?? ""}`;
    const es = new EventSource(url);
    es.onmessage = (e) => {
      try { onUpdate(camelizeKeys(JSON.parse(e.data)) as Run); } catch { /* ignore */ }
    };
    return es;
  },
};

// ── User / Profile ────────────────────────────────────────────────────────────

export const userApi = {
  updateProfile: async (values: ProfileFormValues) => {
    const res = await apiClient.patch<User>("/users/me", values);
    return res.data;
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    const res = await apiClient.post<ApiResponse<null>>("/users/me/password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return res.data;
  },
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const dashboardApi = {
  getStats: async () => {
    const res = await apiClient.get<DashboardStats>("/dashboard/stats");
    return res.data;
  },
};

// ── Tutor ─────────────────────────────────────────────────────────────────────

export interface TutorMessage { role: "user" | "assistant"; content: string; }
export interface TutorUsage   { tutorCredits: number; tutorCap: number; remaining: number; isLimited: boolean; }

export const tutorApi = {
  getUsage: async (): Promise<TutorUsage> => {
    const res = await apiClient.get<TutorUsage>("/tutor/usage");
    return res.data;
  },

  streamChat: (
    messages: TutorMessage[],
    onText:   (text: string) => void,
    onDone:   (usage: { tutorCredits: number; tutorCap: number; remaining: number }) => void,
    onError:  (msg: string) => void,
  ): (() => void) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    let aborted = false;

    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/v1/tutor/chat`, {
          method:  "POST",
          headers: {
            "Content-Type":  "application/json",
            "Authorization": `Bearer ${token ?? ""}`,
          },
          body: JSON.stringify({ messages }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          const detail = data?.detail ?? "Tutor request failed";
          onError(typeof detail === "string" ? detail : "Tutor request failed");
          return;
        }

        const reader  = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.text)  onText(event.text);
              if (event.done)  onDone({ tutorCredits: event.tutorCredits, tutorCap: event.tutorCap, remaining: event.remaining });
              if (event.error) onError(event.error);
            } catch { /* ignore malformed */ }
          }
        }
      } catch (e) {
        if (!aborted) onError("Connection error. Please try again.");
      }
    })();

    return () => { aborted = true; };
  },
};

// ── Billing ───────────────────────────────────────────────────────────────────

export const billingApi = {
  getSubscription: async () => {
    const res = await apiClient.get<Subscription>("/billing/subscription");
    return res.data;
  },

  getInvoices: async () => {
    const res = await apiClient.get<BillingInvoice[]>("/billing/invoices");
    return res.data;
  },

  createCheckoutSession: async (planId: string) => {
    const res = await apiClient.post<{ url: string }>("/billing/checkout", {
      plan_id: planId,
    });
    return res.data;
  },

  createPortalSession: async () => {
    const res = await apiClient.post<{ url: string }>("/billing/portal");
    return res.data;
  },

  createCryptoCheckoutSession: async (planId: string) => {
    const res = await apiClient.post<{ url: string }>("/billing/checkout/crypto", {
      plan_id: planId,
    });
    return res.data;
  },

  createCardCheckoutSession: async (planId: string) => {
    const res = await apiClient.post<{ url: string }>("/billing/checkout/card", {
      plan_id: planId,
    });
    return res.data;
  },
};

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface AdminAnalytics {
  users: {
    total: number; newToday: number; newWeek: number; newMonth: number;
    byPlan: Record<string, number>; paid: number;
  };
  runs: {
    total: number; today: number; week: number;
    completed: number; failed: number; modes: Record<string, number>;
  };
  visits: { total: number; today: number; week: number; uniqueMonth: number };
  payments: { total: number; repeatPayers: number; estimatedMonthlyRevenue: number };
  dailyRegistrations: { date: string; count: number }[];
  recentUsers: {
    id: string; email: string; name: string | null;
    plan: string; usageCredits: number; createdAt: string;
  }[];
}

export const adminApi = {
  getAnalytics: async (): Promise<AdminAnalytics> => {
    const res = await apiClient.get<AdminAnalytics>("/admin/analytics");
    return res.data;
  },
  trackVisit: async (path: string) => {
    await apiClient.post(`/admin/track?path=${encodeURIComponent(path)}`).catch(() => {});
  },

  updateUserPlan: async (userId: string, plan: string) => {
    const res = await apiClient.patch(`/admin/users/${userId}/plan`, { plan });
    return res.data;
  },
};
