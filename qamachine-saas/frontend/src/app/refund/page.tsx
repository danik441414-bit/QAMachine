import Link from "next/link";
import { Zap } from "lucide-react";

export const metadata = { title: "Refund Policy — QAMachine" };

export default function RefundPage() {
  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <nav className="h-16 border-b border-border/50 flex items-center px-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold tracking-tight">QAMachine</span>
        </Link>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">Refund Policy</h1>
        <p className="text-text-secondary text-sm mb-10">Last updated: May 7, 2025</p>

        <section className="space-y-8 text-text-secondary leading-relaxed">
          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">14-Day Money-Back Guarantee</h2>
            <p>We offer a full refund within <strong className="text-text-primary">14 days</strong> of your initial subscription purchase if you are not satisfied with the Service. No questions asked.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">How to Request a Refund</h2>
            <p>To request a refund, email us at <a href="mailto:support@qamachine.site" className="text-accent hover:underline">support@qamachine.site</a> with the subject line "Refund Request" and include your account email. We will process the refund within 5 business days.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">Renewal Charges</h2>
            <p>Monthly and annual subscriptions renew automatically. If you wish to cancel, you must do so before the renewal date through your account settings. Refunds are not provided for renewal charges after the billing date.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">Exceptions</h2>
            <p>Refunds will not be issued for:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Accounts suspended or terminated due to violation of our Terms of Service</li>
              <li>Requests made more than 14 days after the initial purchase</li>
              <li>Previously refunded accounts</li>
            </ul>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">Contact</h2>
            <p>For refund requests or billing questions: <a href="mailto:support@qamachine.site" className="text-accent hover:underline">support@qamachine.site</a></p>
          </div>
        </section>
      </main>
    </div>
  );
}
