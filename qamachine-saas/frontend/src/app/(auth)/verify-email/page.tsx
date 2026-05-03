"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { authApi } from "@/lib/api";

function VerifyEmailContent() {
  const params = useSearchParams();
  const router = useRouter();
  const token  = params.get("token") ?? "";

  const [status, setStatus]   = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided.");
      return;
    }
    authApi.verifyEmail(token)
      .then(() => {
        setStatus("success");
        setTimeout(() => router.push("/login"), 3000);
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
          <p className="text-sm text-text-secondary">Verifying your email…</p>
        </>
      )}
      {status === "success" && (
        <>
          <div className="flex justify-center">
            <div className="h-16 w-16 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-green-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary mb-2">Email verified!</h1>
            <p className="text-sm text-text-secondary">Your account is active. Redirecting to login…</p>
          </div>
          <Link href="/login" className="inline-block px-6 py-2.5 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors">
            Go to login →
          </Link>
        </>
      )}
      {status === "error" && (
        <>
          <div className="flex justify-center">
            <div className="h-16 w-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <XCircle className="h-8 w-8 text-red-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary mb-2">Verification failed</h1>
            <p className="text-sm text-text-secondary">{message}</p>
          </div>
          <p className="text-xs text-text-muted">
            <Link href="/signup" className="text-accent hover:underline">Register again</Link>
            {" · "}
            <Link href="/login" className="text-accent hover:underline">Back to login</Link>
          </p>
        </>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="flex justify-center"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}
