import Link from "next/link";
import { Zap } from "lucide-react";

export const metadata = { title: "Terms of Service — QAMachine" };

export default function TermsPage() {
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
        <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
        <p className="text-text-secondary text-sm mb-10">Last updated: May 7, 2025</p>

        <section className="space-y-8 text-text-secondary leading-relaxed">
          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">1. Acceptance of Terms</h2>
            <p>By accessing or using QAMachine ("Service"), you agree to be bound by these Terms of Service. If you do not agree, please do not use the Service.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">2. Description of Service</h2>
            <p>QAMachine is an AI-powered QA automation platform. The Service allows users to submit a URL and a testing task, after which an automated agent browses the website, identifies bugs, and generates a QA report.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">3. User Accounts</h2>
            <p>You must create an account to use the Service. You are responsible for maintaining the security of your account credentials and for all activities that occur under your account. You must notify us immediately of any unauthorized use.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">4. Acceptable Use</h2>
            <p>You agree to use the Service only for lawful purposes. You may not use the Service to test websites you do not own or have explicit permission to test. You may not attempt to disrupt, overload, or gain unauthorized access to any systems.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">5. Subscriptions and Payments</h2>
            <p>Some features of the Service require a paid subscription. Subscriptions are billed in advance on a monthly or annual basis. All payments are processed securely through Paddle. Prices may change with 30 days' notice.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">6. Intellectual Property</h2>
            <p>The Service and its original content, features, and functionality are owned by QAMachine and are protected by international copyright, trademark, and other intellectual property laws. Reports generated using the Service belong to you.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">7. Limitation of Liability</h2>
            <p>The Service is provided "as is" without warranties of any kind. QAMachine shall not be liable for any indirect, incidental, special, or consequential damages resulting from your use or inability to use the Service.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">8. Termination</h2>
            <p>We reserve the right to suspend or terminate your account at any time for violations of these Terms. You may cancel your account at any time through the account settings.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">9. Changes to Terms</h2>
            <p>We may update these Terms from time to time. We will notify you of significant changes via email or a notice on the Service. Continued use of the Service after changes constitutes acceptance of the new Terms.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">10. Contact</h2>
            <p>For questions about these Terms, contact us at: <a href="mailto:support@qamachine.site" className="text-accent hover:underline">support@qamachine.site</a></p>
          </div>
        </section>
      </main>
    </div>
  );
}
