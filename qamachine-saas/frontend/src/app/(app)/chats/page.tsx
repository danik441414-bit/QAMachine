"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus, MessageSquare, Clock, ChevronRight,
  Loader2, Search, Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { chatsApi } from "@/lib/api";
import { formatDateShort, truncate, cn } from "@/lib/utils";
import { useLang } from "@/context/language-context";
import type { Chat } from "@/types";

const STATUS_DOT: Record<Chat["status"], string> = {
  idle:    "bg-text-muted",
  running: "bg-accent animate-pulse",
  error:   "bg-error",
};

export default function ChatsPage() {
  const [chats, setChats]     = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState("");
  const { t } = useLang();
  const c = t.chats;

  useEffect(() => {
    chatsApi.list()
      .then((res) => setChats(res.items))
      .catch(() => toast.error(t.common.error))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await chatsApi.delete(id);
      setChats((prev) => prev.filter((ch) => ch.id !== id));
      toast.success(t.common.success);
    } catch {
      toast.error(t.common.error);
    }
  }

  const filtered = chats.filter(
    (ch) => !search || ch.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-4xl mx-auto animate-fade-in">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <div>
          <h2 className="text-xl font-bold text-text-primary">{c.title}</h2>
          <p className="text-sm text-text-secondary mt-0.5">{c.subtitle}</p>
        </div>
        <Link href="/chats/new">
          <Button leftIcon={<Plus className="h-4 w-4" />}>
            {c.newChat}
          </Button>
        </Link>
      </div>

      {/* ── Search ─────────────────────────────────────────────────── */}
      {chats.length > 0 && (
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted
                             pointer-events-none" />
          <input
            type="text"
            placeholder={c.searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-10 pl-9 pr-4 rounded-lg bg-bg-surface border border-border
                       text-sm text-text-primary placeholder:text-text-placeholder
                       focus:outline-none focus:border-accent transition-colors"
          />
        </div>
      )}

      {/* ── Content ────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex items-center justify-center py-20 gap-2 text-text-muted">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">{t.common.loading}</span>
        </div>
      ) : chats.length === 0 ? (
        <div className="rounded-xl border border-border bg-bg-surface p-16
                        flex flex-col items-center text-center gap-3">
          <div className="h-12 w-12 rounded-xl bg-bg-elevated border border-border
                          flex items-center justify-center">
            <MessageSquare className="h-6 w-6 text-text-muted" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary mb-1">{c.noChats}</p>
            <p className="text-sm text-text-muted max-w-xs">{c.noChatsDesc}</p>
          </div>
          <Link href="/chats/new">
            <Button variant="secondary" leftIcon={<Plus className="h-4 w-4" />}>
              {c.createFirst}
            </Button>
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center text-sm text-text-muted">
          {c.noMatching} &ldquo;{search}&rdquo;
        </div>
      ) : (
        <div className="space-y-1.5">
          {filtered.map((chat) => (
            <Link key={chat.id} href={`/chats/${chat.id}`}>
              <div
                className="flex items-center gap-4 px-4 py-3.5 rounded-xl
                           bg-bg-surface border border-border
                           hover:border-border-focus hover:shadow-card-hover
                           transition-all duration-150 group cursor-pointer"
              >
                <div className={cn("h-2.5 w-2.5 rounded-full shrink-0", STATUS_DOT[chat.status])} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {chat.title}
                    </p>
                    {chat.status === "running" && (
                      <span className="text-2xs px-2 py-0.5 rounded-full
                                       bg-accent-bg text-accent border border-accent/20
                                       font-medium">
                        {c.running}
                      </span>
                    )}
                  </div>
                  {chat.lastMessage && (
                    <p className="text-xs text-text-muted mt-0.5 truncate">
                      {truncate(chat.lastMessage, 80)}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {chat.runCount > 0 && (
                    <span className="hidden sm:inline text-xs text-text-muted">
                      {chat.runCount} {chat.runCount === 1 ? c.run : c.runs}
                    </span>
                  )}
                  <span className="text-xs text-text-muted flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDateShort(chat.updatedAt)}
                  </span>
                  <button
                    onClick={(e) => handleDelete(chat.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity
                               text-text-muted hover:text-error p-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                  <ChevronRight className="h-4 w-4 text-text-muted" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
