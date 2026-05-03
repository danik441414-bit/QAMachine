"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Lock, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api";

function ResetPasswordForm() {
  const router  = useRouter();
  const params  = useSearchParams();
  const token   = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  if (!token) {
    return (
      <div className="animate-slide-up text-center space-y-4">
        <h1 className="text-xl font-bold text-text-primary">Invalid link</h1>
        <p className="text-sm text-text-secondary">This reset link is missing or invalid.</p>
        <Link href="/forgot-password" className="text-accent hover:underline text-sm">
          Request a new one
        </Link>
      </div>
    );
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (password.length < 8) { setError("Minimum 8 characters"); return; }
    setError("");
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      toast.success("Password updated! You can now log in.");
      router.push("/login");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Invalid or expired link. Request a new one.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-slide-up">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Set new password</h1>
        <p className="text-sm text-text-secondary">Enter your new password below.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="New password"
          type={showPass ? "text" : "password"}
          placeholder="Min. 8 characters"
          value={password}
          onChange={(e) => { setPassword(e.target.value); setError(""); }}
          error={error}
          leftIcon={<Lock className="h-4 w-4" />}
          rightIcon={
            <button
              type="button"
              onClick={() => setShowPass((v) => !v)}
              className="text-text-muted hover:text-text-secondary transition-colors"
              tabIndex={-1}
            >
              {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          }
          autoComplete="new-password"
          autoFocus
        />
        <Button type="submit" size="lg" loading={loading} className="w-full mt-2">
          Update password
        </Button>
      </form>

      <p className="text-center text-sm text-text-secondary mt-6">
        <Link href="/login" className="text-accent hover:text-accent-hover font-medium transition-colors">
          Back to login
        </Link>
      </p>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="flex justify-center"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
