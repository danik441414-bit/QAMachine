import Link from "next/link";
import { Zap } from "lucide-react";

export const metadata = { title: "Privacy Policy — QAMachine" };

export default function PrivacyPage() {
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
        <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-text-secondary text-sm mb-10">Last updated: May 7, 2025</p>

        <section className="space-y-8 text-text-secondary leading-relaxed">
          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">1. Information We Collect</h2>
            <p>We collect information you provide directly: name, email address, and payment information when you create an account. We also collect URLs and task descriptions you submit for QA testing, and usage data such as session logs and generated reports.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">2. How We Use Your Information</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>To provide and improve the Service</li>
              <li>To process payments and manage subscriptions</li>
              <li>To send transactional emails (account verification, receipts)</li>
              <li>To respond to support requests</li>
              <li>To analyze usage patterns and improve functionality</li>
            </ul>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">3. Data Storage and Security</h2>
            <p>Your data is stored on secure servers. We implement industry-standard security measures including encryption in transit (HTTPS) and at rest. QA session screenshots and reports are stored for 30 days and then automatically deleted.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">4. Third-Party Services</h2>
            <p>We use the following third-party services:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li><strong>Paddle</strong> — payment processing (their privacy policy applies to payment data)</li>
              <li><strong>Anthropic</strong> — AI processing for QA analysis</li>
              <li><strong>Vercel / hosting providers</strong> — infrastructure</li>
            </ul>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">5. Cookies</h2>
            <p>We use cookies for authentication (keeping you logged in) and basic analytics. You can disable cookies in your browser settings, but some features of the Service may not function properly.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">6. Your Rights</h2>
            <p>You have the right to access, correct, or delete your personal data. To request deletion of your account and associated data, contact us at <a href="mailto:support@qamachine.site" className="text-accent hover:underline">support@qamachine.site</a>. We will process your request within 30 days.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">7. Data Retention</h2>
            <p>We retain your account data for as long as your account is active. After account deletion, we remove personal data within 30 days, except where required by law.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">8. Children's Privacy</h2>
            <p>The Service is not intended for users under 16 years of age. We do not knowingly collect personal information from children.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">9. Changes to This Policy</h2>
            <p>We may update this Privacy Policy periodically. We will notify you of significant changes via email. Your continued use of the Service after changes constitutes acceptance.</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-text-primary mb-2">10. Contact</h2>
            <p>For privacy-related questions: <a href="mailto:support@qamachine.site" className="text-accent hover:underline">support@qamachine.site</a></p>
          </div>
        </section>
      </main>
    </div>
  );
}
