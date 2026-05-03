"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { authApi } from "@/lib/api";
import type { User } from "@/types";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser]           = useState<User | null>(null);
  const [loading, setLoading]     = useState(true);
  const [sidebarOpen, setSidebar] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    authApi.me()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("access_token");
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <span className="text-sm text-text-secondary">Loading…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-bg">

      {/* ── Desktop sidebar (always visible ≥ md) ─────────────────── */}
      <div className="hidden md:flex shrink-0">
        <Sidebar user={user} className="min-h-screen" />
      </div>

      {/* ── Mobile drawer ─────────────────────────────────────────── */}
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/60 transition-opacity duration-200 md:hidden ${
          sidebarOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setSidebar(false)}
        aria-hidden="true"
      />
      {/* Drawer panel */}
      <div
        className={`fixed inset-y-0 left-0 z-50 h-full md:hidden transition-transform duration-200 ease-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar
          user={user}
          onClose={() => setSidebar(false)}
          className="h-full"
        />
      </div>

      {/* ── Main area ─────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar onMenuClick={() => setSidebar((v) => !v)} />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
