import { Link } from "react-router-dom";
import "./LegalPage.css";

const APP_NAME   = "LeadFlow AI";
const COMPANY    = "SoftPeak Technologies";
const CONTACT    = "technologiessoftpeak@gmail.com";
const SITE_URL   = "https://ai-lead-generation-platform-one.vercel.app";
const UPDATED_AT = "November 14, 2026";

function PrivacyPolicyPage() {
  return (
    <div className="legal-page">

      {/* ── Nav ─────────────────────────────────── */}
      <nav className="legal-nav">
        <Link to="/login" className="legal-logo">
          <span className="legal-logo-icon">⚡</span>
          {APP_NAME}
        </Link>
        <div className="legal-nav-links">
          <Link to="/privacy-policy" className="legal-nav-active">Privacy Policy</Link>
          <Link to="/terms">Terms of Service</Link>
          <Link to="/login" className="legal-nav-btn">Sign In</Link>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────── */}
      <header className="legal-hero">
        <div className="legal-hero-grid" />
        <div className="legal-hero-inner">
          <span className="legal-badge">Legal · Privacy</span>
          <h1>Privacy Policy</h1>
          <p className="legal-hero-sub">
            We are committed to protecting your personal data and your right to privacy.
            This policy explains exactly what we collect, why we collect it, and how we use it.
          </p>
          <div className="legal-hero-pills">
            <span className="legal-hero-pill">🔒 AES-256 Encrypted Tokens</span>
            <span className="legal-hero-pill">📧 Gmail OAuth 2.0</span>
            <span className="legal-hero-pill">🚫 No Data Selling</span>
            <span className="legal-hero-pill">✅ GDPR Compliant</span>
          </div>
          <p className="legal-hero-date">Last updated: {UPDATED_AT}</p>
        </div>
      </header>

      {/* ── Body ────────────────────────────────── */}
      <main className="legal-body">

        <section className="legal-section">
          <h2>1. Introduction</h2>
          <p>
            Welcome to <strong>{APP_NAME}</strong>, operated by <strong>{COMPANY}</strong>
            {" "}("<em>we</em>", "<em>us</em>", or "<em>our</em>"). This Privacy Policy explains how
            we collect, use, disclose, and safeguard your information when you use our
            AI-powered lead generation and email outreach platform (the "Service") available
            at <a href={SITE_URL} target="_blank" rel="noreferrer">{SITE_URL}</a>.
          </p>
          <p>
            By accessing or using the Service you agree to this Privacy Policy. If you do not
            agree, please discontinue use immediately.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Information We Collect</h2>

          <h3>2.1 Account Information</h3>
          <p>When you register, we collect your name, email address, and password (hashed — never stored in plain text).</p>

          <h3>2.2 Google / Gmail OAuth Data</h3>
          <p>
            When you connect a Gmail account for outreach, we receive and securely store:
          </p>
          <ul>
            <li>Your Gmail address</li>
            <li>OAuth access token &amp; refresh token (AES-256 encrypted at rest)</li>
            <li>Gmail send / receive permissions granted via Google OAuth 2.0</li>
          </ul>
          <p>
            We use these credentials exclusively to send outreach emails on your behalf through
            the Gmail API. We do <strong>not</strong> read, index, or store the content of your
            existing Gmail inbox.
          </p>

          <h3>2.3 Lead &amp; Business Data</h3>
          <p>
            Our platform discovers publicly available business information (business names,
            website URLs, phone numbers, publicly listed email addresses) from sources such as
            Google Places API and public websites. This data is stored in your account for
            outreach purposes.
          </p>

          <h3>2.4 Email Campaign Data</h3>
          <p>
            We store the outreach emails you compose or generate with AI, the delivery status,
            open/reply tracking metadata, and campaign analytics.
          </p>

          <h3>2.5 Usage &amp; Log Data</h3>
          <p>
            We automatically collect server logs, IP addresses, browser type, and pages visited
            to operate and improve the Service.
          </p>
        </section>

        <section className="legal-section">
          <h2>3. How We Use Your Information</h2>
          <ul>
            <li>To authenticate your identity and manage your account</li>
            <li>To send outreach emails via Gmail on your explicit instruction</li>
            <li>To generate AI-powered email drafts based on lead data you provide</li>
            <li>To discover and qualify business leads using public data sources</li>
            <li>To track email delivery, opens, and replies for campaign analytics</li>
            <li>To improve and debug the platform</li>
            <li>To comply with legal obligations</li>
          </ul>
          <p>
            We do <strong>not</strong> sell, rent, or share your personal data or your leads'
            data with third parties for their own marketing purposes.
          </p>
        </section>

        <section className="legal-section">
          <h2>4. Google API Scopes &amp; Data Usage</h2>
          <p>
            {APP_NAME} uses the following Google API scope:
          </p>
          <ul>
            <li><code>https://www.googleapis.com/auth/gmail.modify</code> — to send outreach emails and read replies in your Gmail account</li>
          </ul>
          <p>
            Our use of Google user data is limited to the practices disclosed in this Privacy Policy
            and complies with the{" "}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noreferrer"
            >
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements.
          </p>
          <p>
            We do <strong>not</strong> use Gmail data to serve advertisements, do not allow
            humans to read your Gmail data (except for security investigations with your
            explicit consent), and do not use Gmail data for any purpose other than providing
            the outreach features you explicitly request.
          </p>
        </section>

        <section className="legal-section">
          <h2>5. Data Storage &amp; Security</h2>
          <ul>
            <li>All data is stored on <strong>Supabase</strong> (PostgreSQL), hosted on AWS ap-southeast-2.</li>
            <li>OAuth tokens are encrypted with <strong>AES-256 (Fernet)</strong> before being written to the database.</li>
            <li>Passwords are hashed using industry-standard bcrypt.</li>
            <li>All communication between your browser and our servers uses <strong>HTTPS/TLS</strong>.</li>
            <li>We perform regular security reviews and access audits.</li>
          </ul>
          <p>
            Despite our measures, no transmission over the internet is 100 % secure. You use
            the Service at your own risk.
          </p>
        </section>

        <section className="legal-section">
          <h2>6. Data Retention</h2>
          <p>
            We retain your account data for as long as your account is active. You may request
            deletion of your account and all associated data at any time by emailing us at{" "}
            <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. We will process deletion requests
            within 30 days.
          </p>
          <p>
            Lead data you have discovered is owned by you. We store it solely to power your
            campaigns and do not retain it after account deletion.
          </p>
        </section>

        <section className="legal-section">
          <h2>7. Third-Party Services</h2>
          <p>The Service integrates with:</p>
          <ul>
            <li><strong>Google Gmail API</strong> — for sending outreach emails</li>
            <li><strong>Google Places API</strong> — for discovering business leads</li>
            <li><strong>Cloudflare AI</strong> — for AI email generation (prompt data only; no PII is sent)</li>
            <li><strong>Supabase</strong> — for authentication and database hosting</li>
            <li><strong>Vercel</strong> — for frontend hosting</li>
          </ul>
          <p>Each third-party service has its own privacy policy. We are not responsible for their practices.</p>
        </section>

        <section className="legal-section">
          <h2>8. Your Rights</h2>
          <p>Depending on your jurisdiction, you may have the right to:</p>
          <ul>
            <li>Access the personal data we hold about you</li>
            <li>Correct inaccurate data</li>
            <li>Request deletion of your data ("right to be forgotten")</li>
            <li>Withdraw Google OAuth consent at any time via <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer">Google Account Permissions</a></li>
            <li>Object to or restrict certain processing activities</li>
          </ul>
          <p>To exercise any of these rights, contact us at <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.</p>
        </section>

        <section className="legal-section">
          <h2>9. Children's Privacy</h2>
          <p>
            The Service is intended for users aged 18 and older. We do not knowingly collect
            personal information from children under 13. If you believe we have inadvertently
            collected such information, contact us immediately.
          </p>
        </section>

        <section className="legal-section">
          <h2>10. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. We will notify registered
            users of material changes by email. The "Last updated" date at the top reflects
            the most recent revision. Continued use of the Service after changes constitutes
            acceptance.
          </p>
        </section>

        <section className="legal-section">
          <h2>11. Contact Us</h2>
          <p>
            If you have any questions, concerns, or requests regarding this Privacy Policy,
            please contact us:
          </p>
          <address>
            <strong>{COMPANY}</strong><br />
            Email: <a href={`mailto:${CONTACT}`}>{CONTACT}</a><br />
            Website: <a href={SITE_URL} target="_blank" rel="noreferrer">{SITE_URL}</a>
          </address>
        </section>

      </main>

      {/* ── Footer ──────────────────────────────── */}
      <footer className="legal-footer">
        <div className="legal-footer-inner">
          <div className="legal-footer-brand">
            <span className="legal-footer-logo">⚡</span>
            <div>
              <strong>AI Lead Generation &amp; Business Outreach Platform</strong>
              <span>by {COMPANY}</span>
            </div>
          </div>
          <p className="legal-footer-desc">
            Empowering businesses with AI-powered lead discovery and email outreach.
            Your data is always secure and private.
          </p>
          <div className="legal-footer-links">
            <Link to="/privacy-policy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
            <Link to="/login">Sign In</Link>
            <Link to="/register">Register</Link>
          </div>
          <p className="legal-footer-copy">
            © {new Date().getFullYear()} {COMPANY}. All rights reserved.
          </p>
        </div>
      </footer>

    </div>
  );
}

export default PrivacyPolicyPage;
