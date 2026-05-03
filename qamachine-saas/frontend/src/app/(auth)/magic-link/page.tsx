"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { authApi } from "@/lib/api";

function MagicLinkContent() {
  const params = useSearchParams();
  const router = useRouter();
  const token  = params.get("token") ?? "";

  const [status, setStatus]   = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No login token provided.");
      return;
    }
    authApi.verifyMagicLink(token)
      .then(({ accessToken }) => {
        localStorage.setItem("access_token", accessToken);
        setStatus("success");
        setTimeout(() => router.push("/dashboard"), 1500);
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail ?? "Invalid or expired link.";
        setStatus("error");
        setMessage(detail);
      });
  }, [token, router]);

  return (
    <div className="animate-slide-up text-center space-y-5">
      {status === "loading" && (
        <>
          <div className="flex justify-center">
            <Loader2 className="h-12 w-12 text-accent animate-spin" />
          </div>
          <p className="text-sm text-text-secondary">Signing you in…</p>
        </>
      )}

      {status === "success" && (
        <>
          <div className="flex justify-center">
            <div className="h-16 w-16 rounded-2xl bg-green-500/10 border border-green-500/20
                            flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-green-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary mb-2">You&apos;re in!</h1>
            <p className="text-sm text-text-secondary">Redirecting to your dashboard…</p>
          </div>
        </>
      )}

      {status === "error" && (
        <>
          <div className="flex justify-center">
            <div className="h-16 w-16 rounded-2xl bg-red-500/10 border border-red-500/20
                            flex items-center justify-center">
              <XCircle className="h-8 w-8 text-red-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary mb-2">Link invalid</h1>
            <p className="text-sm text-text-secondary">{message}</p>
          </div>
          <p className="text-xs text-text-muted">
            <Link href="/login" className="text-accent hover:underline">
              Back to login
            </Link>
          </p>
        </>
      )}
    </div>
  );
}

export default function MagicLinkPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    }>
      <MagicLinkContent />
    </Suspense>
  );
}
