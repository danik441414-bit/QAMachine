"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Mail, Lock } from "lucide-react";
import { toast } from "sonner";
import { GoogleSignInButton } from "@/components/ui/google-sign-in-button";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [showPass, setShowPass]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [errors, setErrors]         = useState<{ email?: string; password?: string }>({});
  const [notVerified, setNotVerified] = useState(false);
  const [resending, setResending]   = useState(false);
  const [magicEmail, setMagicEmail]     = useState("");
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicSent, setMagicSent]       = useState(false);

  function validate(): boolean {
    const e: typeof errors = {};
    if (!email.trim())    e.email    = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "Enter a valid email";
    if (!password)        e.password = "Password is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!validate() || loading) return;

    setNotVerified(false);
    setMagicSent(false);   // clear magic link panel when using password form
    setLoading(true);
    try {
      const { accessToken } = await authApi.login(email, password);
      localStorage.setItem("access_token", accessToken);
      router.push("/dashboard");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (detail === "EMAIL_NOT_VERIFIED") {
        setNotVerified(true);
      } else {
        toast.error(detail ?? "Invalid email or password");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleMagicLink() {
    if (!magicEmail.trim() || magicLoading) return;
    setErrors({});         // clear password-form errors when using magic link
    setNotVerified(false);
    setMagicLoading(true);
    try {
      await authApi.requestMagicLink(magicEmail.trim());
      setMagicSent(true);
    } catch {
      toast.error("Failed to send login link. Try again.");
    } finally {
      setMagicLoading(false);
    }
  }

  async function handleResend() {
    setResending(true);
    try {
      await authApi.resendVerification(email.trim());
      toast.success("Verification email sent! Check your inbox.");
    } catch {
      toast.error("Failed to resend. Try again.");
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="animate-slide-up">
      {/* Heading */}
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Welcome back</h1>
        <p className="text-sm text-text-secondary">
          Sign in to your QAMachine workspace
        </p>
      </div>

      {/* Email not verified banner */}
      {notVerified && (
        <div className="mb-5 rounded-xl bg-yellow-500/10 border border-yellow-500/20 px-4 py-3 space-y-2">
          <p className="text-sm font-medium text-yellow-400">Verify your email first</p>
          <p className="text-xs text-text-secondary leading-relaxed">
            We sent a link to <strong className="text-text-primary">{email}</strong>.
            Check your inbox (and spam folder).
          </p>
          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            className="text-xs text-accent hover:underline disabled:opacity-50"
          >
            {resending ? "Sending…" : "Resend verification email"}
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => { setEmail(e.target.value); if (errors.email) setErrors((p) => ({ ...p, email: undefined })); }}
          error={errors.email}
          leftIcon={<Mail className="h-4 w-4" />}
          autoComplete="email"
          autoFocus
        />

        <Input
          label="Password"
          type={showPass ? "text" : "password"}
          placeholder="Your password"
          value={password}
          onChange={(e) => { setPassword(e.target.value); if (errors.password) setErrors((p) => ({ ...p, password: undefined })); }}
          error={errors.password}
          leftIcon={<Lock className="h-4 w-4" />}
          rightIcon={
            <button
              type="button"
              onClick={() => setShowPass((v) => !v)}
              className="text-text-muted hover:text-text-secondary transition-colors"
              tabIndex={-1}
            >
              {showPass
                ? <EyeOff className="h-4 w-4" />
                : <Eye className="h-4 w-4" />}
            </button>
          }
          autoComplete="current-password"
        />

        <div className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            Forgot password?
          </Link>
        </div>

        <Button
          type="submit"
          size="lg"
          loading={loading}
          className="w-full mt-2"
        >
          Sign in
        </Button>
      </form>

      {/* Divider */}
      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-text-muted">or</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Google sign-in */}
      <div className="flex justify-center mb-6">
        <GoogleSignInButton text="signin_with" />
      </div>

      {/* Magic link section */}
      <div className="mt-4 rounded-xl border border-border bg-bg-surface p-4">
        <p className="text-xs font-medium text-text-muted mb-3 text-center">
          No password? Sign in with email link
        </p>
        {magicSent ? (
          <div className="text-center py-2 space-y-1">
            <p className="text-sm font-medium text-success">Link sent!</p>
            <p className="text-xs text-text-muted">
              Check <strong className="text-text-secondary">{magicEmail}</strong> — link expires in 15 min.
            </p>
            <button
              type="button"
              onClick={() => { setMagicSent(false); setMagicEmail(""); }}
              className="text-xs text-accent hover:underline mt-1"
            >
              Send to another email
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              type="email"
              value={magicEmail}
              onChange={(e) => setMagicEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleMagicLink()}
              placeholder="your@email.com"
              className="flex-1 h-9 rounded-lg border border-border bg-bg-elevated px-3
                         text-sm text-text-primary placeholder:text-text-muted
                         focus:outline-none focus:border-accent transition-colors"
            />
            <button
              type="button"
              onClick={handleMagicLink}
              disabled={!magicEmail.trim() || magicLoading}
              className="h-9 px-4 rounded-lg bg-accent text-white text-sm font-medium
                         hover:bg-accent/90 disabled:opacity-40 transition-colors shrink-0"
            >
              {magicLoading ? "Sending…" : "Send link"}
            </button>
          </div>
        )}
      </div>

      {/* Sign up link */}
      <p className="text-center text-sm text-text-secondary mt-4">
        Don&apos;t have an account?{" "}
        <Link
          href="/signup"
          className="text-accent hover:text-accent-hover font-medium transition-colors"
        >
          Sign up free
        </Link>
      </p>
    </div>
  );
}
